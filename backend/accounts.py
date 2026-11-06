"""로컬 회원·세션·소유권이 있는 PostgreSQL 기록 API."""
import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, field_validator, model_validator
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from backend.database import connect
from backend.exercise import ExerciseInput, plan_exercise
from backend.profile import ProfileInput, BodyComposition, estimate_profile

COOKIE = 'nourishon_session'
HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY = HASHER.hash(secrets.token_urlsafe(24))
ORIGINS = {'http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:8000', 'http://127.0.0.1:8000'}
Nickname = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
router = APIRouter()


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True, pattern=r'^[a-z0-9_]{3,40}$')]
    password: SecretStr

    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode='after')
    def length(self):
        if not 4 <= len(self.password.get_secret_value()) <= 128:
            raise ValueError('비밀번호는 4~128자입니다.')
        return self


class Registration(Credentials):
    username: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True, pattern=r'^[a-z0-9_]{4,40}$')]


class NewProfile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nickname: Nickname


class Measurement(BodyComposition):
    id: UUID
    weight_kg: Annotated[float, Field(strict=True, ge=25, le=350, allow_inf_nan=False)]

    @model_validator(mode='after')
    def validate_mass(self):
        values = self.model_dump(exclude={'id','weight_kg'}, mode='json')
        if any(values[k] is not None for k in ('skeletal_muscle_kg','fat_mass_kg','body_fat_percent')):
            ProfileInput(age=30, height_cm=170, weight_kg=self.weight_kg, equation_sex='female',
                         activity='inactive', scope_confirmed=True, body=values)
        elif self.measured_on > datetime.now(timezone(timedelta(hours=9))).date():
            raise ValueError('미래 측정일')
        return self


class MealItem(BaseModel):
    # 클라이언트가 보낸 합계·출처는 신뢰하지 않고 식품코드·섭취량만 읽는다.
    food_code: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    intake_g: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]


class MealCalculation(BaseModel):
    foods: Annotated[list[MealItem], Field(min_length=1, max_length=100)]


class StoredMeal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID
    date: date
    kind: Literal['아침','점심','저녁','간식']
    calculation: MealCalculation

    @model_validator(mode='after')
    def not_future(self):
        if self.date > datetime.now(timezone(timedelta(hours=9))).date():
            raise ValueError('미래 식사일')
        return self


class WellnessInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    profile: ProfileInput | None = None
    estimate: dict | None = None
    records: Annotated[list[StoredMeal], Field(max_length=2000)] = Field(default_factory=list)
    measurements: Annotated[list[Measurement], Field(max_length=1000)] = Field(default_factory=list)
    exerciseInput: ExerciseInput | None = None
    exercisePlan: dict | None = None

    @model_validator(mode='after')
    def unique_ids(self):
        for entries in (self.records, self.measurements):
            if len({x.id for x in entries}) != len(entries):
                raise ValueError('중복 식별자')
        if self.exerciseInput and not self.profile:
            raise ValueError('운동 계획에는 프로필이 필요합니다.')
        return self


class SaveData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: Annotated[int, Field(strict=True, ge=0)]
    data: WellnessInput


def dsn(request: Request):
    value = request.app.state.database_url
    if not value:
        raise HTTPException(503, 'DB 설정과 실행 상태를 확인하세요.')
    return value


def mutation_guard(request: Request):
    if request.headers.get('origin') not in ORIGINS or request.headers.get('x-nourishon-client') != 'web':
        raise HTTPException(403, '허용된 로컬 화면에서 요청하세요.')


def session(request: Request, conn, write=False):
    token = request.cookies.get(COOKIE, '')
    if not token or len(token) > 200:
        raise HTTPException(401, '로그인이 필요합니다.')
    row = conn.execute('SELECT s.*,u.username FROM sessions s JOIN users u ON u.id=s.user_id '
                       'WHERE token_hash=%s AND expires_at>now()', (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not row:
        raise HTTPException(401, '다시 로그인하세요.')
    if write:
        mutation_guard(request)
        if not secrets.compare_digest(request.headers.get('x-csrf-token', '').encode(), row['csrf_token'].encode()):
            raise HTTPException(403, '요청을 확인할 수 없습니다. 화면을 새로고침하세요.')
    return row


def throttle(request: Request, username: str):
    # 실패 시에도 별도 트랜잭션으로 시도 수가 남는다. 원문 아이디·IP는 기록하지 않는다.
    with connect(dsn(request)) as conn:
        for key, limit in [(f'ip:{request.client.host}', 40), (f'user:{username}', 10)]:
            bucket = hashlib.sha256(key.encode()).hexdigest()
            row = conn.execute('INSERT INTO auth_attempts(bucket,attempts,window_end) VALUES(%s,1,now()+interval \'15 minutes\') '
                'ON CONFLICT(bucket) DO UPDATE SET attempts=CASE WHEN auth_attempts.window_end<now() THEN 1 ELSE auth_attempts.attempts+1 END, '
                'window_end=CASE WHEN auth_attempts.window_end<now() THEN now()+interval \'15 minutes\' ELSE auth_attempts.window_end END RETURNING attempts', (bucket,)).fetchone()
            if row['attempts'] > limit:
                # 카운트를 커밋한 뒤 오류를 반환한다.
                conn.commit()
                raise HTTPException(429, '시도가 많습니다. 15분 뒤 다시 시도하세요.')
        conn.execute('DELETE FROM auth_attempts WHERE window_end<now()-interval \'1 day\'')


def new_session(request, response, conn, user):
    old = request.cookies.get(COOKIE)
    if old:
        conn.execute('DELETE FROM sessions WHERE token_hash=%s', (hashlib.sha256(old.encode()).hexdigest(),))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    conn.execute('DELETE FROM sessions WHERE expires_at<now()')
    conn.execute('INSERT INTO sessions(token_hash,user_id,csrf_token,expires_at) VALUES(%s,%s,%s,now()+interval \'8 hours\')',
                 (hashlib.sha256(token.encode()).hexdigest(), user['id'], csrf))
    # HTTP 로컬 전용. 외부 서비스 배포 시 HTTPS와 Secure 쿠키 설정이 필요하다.
    response.set_cookie(COOKIE, token, httponly=True, samesite='strict', secure=False, max_age=28800, path='/')
    return {'user': {'id': str(user['id']), 'username': user['username']}, 'csrf_token': csrf, 'database_enabled': True}


@router.get('/auth/me')
def me(request: Request):
    if not request.app.state.database_url:
        return {'user': None, 'database_enabled': False}
    with connect(dsn(request)) as conn:
        if not request.cookies.get(COOKIE):
            return {'user': None, 'database_enabled': True}
        row = session(request, conn)
        return {'user': {'id': str(row['user_id']), 'username': row['username']}, 'csrf_token': row['csrf_token'], 'database_enabled': True}


@router.post('/auth/register', status_code=201)
def register(payload: Registration, request: Request, response: Response):
    mutation_guard(request)
    throttle(request, payload.username)
    password_hash = HASHER.hash(payload.password.get_secret_value())
    try:
        with connect(dsn(request)) as conn:
            user = conn.execute('INSERT INTO users(id,username,password_hash) VALUES(%s,%s,%s) RETURNING id,username',
                                (uuid4(), payload.username, password_hash)).fetchone()
            conn.execute('INSERT INTO profiles(id,user_id,nickname) VALUES(%s,%s,%s)', (uuid4(), user['id'], '나의 프로필'))
            return new_session(request, response, conn, user)
    except UniqueViolation:
        raise HTTPException(409, '사용할 수 없는 아이디입니다.') from None


@router.post('/auth/login')
def login(payload: Credentials, request: Request, response: Response):
    mutation_guard(request)
    throttle(request, payload.username)
    with connect(dsn(request)) as conn:
        user = conn.execute('SELECT * FROM users WHERE username=%s', (payload.username,)).fetchone()
        try:
            valid = HASHER.verify(user['password_hash'] if user else DUMMY, payload.password.get_secret_value())
        except (VerificationError, InvalidHashError):
            valid = False
        if not user or not valid:
            raise HTTPException(401, '아이디와 비밀번호를 확인하세요.')
        if HASHER.check_needs_rehash(user['password_hash']):
            conn.execute('UPDATE users SET password_hash=%s WHERE id=%s', (HASHER.hash(payload.password.get_secret_value()), user['id']))
        return new_session(request, response, conn, user)


@router.post('/auth/logout')
def logout(request: Request, response: Response):
    with connect(dsn(request)) as conn:
        row = session(request, conn, write=True)
        conn.execute('DELETE FROM sessions WHERE token_hash=%s', (row['token_hash'],))
    response.delete_cookie(COOKIE, path='/')
    return {'ok': True}


def serialize(conn, profile):
    measurements = []
    for row in conn.execute('SELECT * FROM body_measurements WHERE profile_id=%s ORDER BY position', (profile['id'],)):
        measurements.append({'id': str(row['id']), 'measured_on': row['measured_on'].isoformat(),
                             'weight_kg': float(row['weight_kg']), **row['composition']})
    records = [{'id': str(row['id']), 'date': row['eaten_on'].isoformat(), 'kind': row['kind'], 'calculation': row['calculation']}
               for row in conn.execute('SELECT * FROM meals WHERE profile_id=%s ORDER BY position', (profile['id'],))]
    return {'id': str(profile['id']), 'nickname': profile['nickname'], 'revision': profile['revision'],
            'data': {'profile': profile['settings'], 'estimate': profile['estimate'], 'records': records,
                     'measurements': measurements, 'exerciseInput': profile['exercise_input'], 'exercisePlan': profile['exercise_plan']}}


def owned(conn, user_id, profile_id, lock=False):
    row = conn.execute('SELECT * FROM profiles WHERE id=%s AND user_id=%s' + (' FOR UPDATE' if lock else ''), (profile_id, user_id)).fetchone()
    if not row:
        raise HTTPException(404, '프로필을 찾을 수 없습니다.')
    return row


@router.get('/account/profiles')
def profiles(request: Request):
    with connect(dsn(request)) as conn:
        user = session(request, conn)
        return {'profiles': [serialize(conn, p) for p in conn.execute('SELECT * FROM profiles WHERE user_id=%s ORDER BY created_at,id', (user['user_id'],)).fetchall()]}


@router.post('/account/profiles', status_code=201)
def create_profile(payload: NewProfile, request: Request):
    with connect(dsn(request)) as conn:
        user = session(request, conn, write=True)
        row = conn.execute('INSERT INTO profiles(id,user_id,nickname) VALUES(%s,%s,%s) RETURNING *',
                           (uuid4(), user['user_id'], payload.nickname)).fetchone()
        return serialize(conn, row)


@router.put('/account/profiles/{profile_id}/data')
def save(profile_id: UUID, payload: SaveData, request: Request):
    with connect(dsn(request)) as conn:
        user = session(request, conn, write=True)
        old = owned(conn, user['user_id'], profile_id, lock=True)
        if old['revision'] != payload.revision:
            raise HTTPException(409, '다른 화면에서 기록이 변경됐습니다. 다시 불러온 뒤 수정하세요.')
        data = payload.data
        estimate = estimate_profile(data.profile) if data.profile else None
        plan = plan_exercise(data.profile, data.exerciseInput) if data.profile and data.exerciseInput else None
        existing = {str(r['id']): r['calculation'] for r in conn.execute('SELECT id,calculation FROM meals WHERE profile_id=%s', (profile_id,))}
        meals = []
        for record in data.records:
            entries = [f.model_dump() for f in record.calculation.foods]
            prior = existing.get(str(record.id))
            # 동일 식품·섭취량의 과거 기록은 당시 출처와 값 그대로 유지한다.
            if prior and [{'food_code':f['food_code'], 'intake_g':f['intake_g']} for f in prior['foods']] == entries:
                calculation = prior
            else:
                try:
                    calculation = request.app.state.catalog.meal(entries)
                except (LookupError, ValueError, TypeError, OverflowError):
                    raise HTTPException(422, '식사 식품코드·섭취량을 확인하세요.') from None
            meals.append((record, calculation))
        conn.execute('UPDATE profiles SET settings=%s,estimate=%s,exercise_input=%s,exercise_plan=%s,revision=revision+1,updated_at=now() WHERE id=%s',
                     (Jsonb(data.profile.model_dump(mode='json')) if data.profile else None, Jsonb(estimate) if estimate else None,
                      Jsonb(data.exerciseInput.model_dump()) if data.exerciseInput else None, Jsonb(plan) if plan else None, profile_id))
        conn.execute('DELETE FROM body_measurements WHERE profile_id=%s', (profile_id,))
        for position, item in enumerate(data.measurements):
            composition = item.model_dump(exclude={'id','weight_kg','measured_on'}, mode='json')
            conn.execute('INSERT INTO body_measurements(id,profile_id,measured_on,weight_kg,composition,position) VALUES(%s,%s,%s,%s,%s,%s)',
                         (item.id, profile_id, item.measured_on, item.weight_kg, Jsonb(composition), position))
        conn.execute('DELETE FROM meals WHERE profile_id=%s', (profile_id,))
        for position, (record, calculation) in enumerate(meals):
            conn.execute('INSERT INTO meals(id,profile_id,eaten_on,kind,calculation,position) VALUES(%s,%s,%s,%s,%s,%s)',
                         (record.id, profile_id, record.date, record.kind, Jsonb(calculation), position))
        return serialize(conn, owned(conn, user['user_id'], profile_id))


@router.post('/account/profiles/{profile_id}/exercise-plan')
def exercise(profile_id: UUID, payload: ExerciseInput, request: Request):
    with connect(dsn(request)) as conn:
        user = session(request, conn, write=True)
        profile = owned(conn, user['user_id'], profile_id)
        if not profile['settings']:
            raise HTTPException(422, '신체 프로필을 먼저 등록하세요.')
        return plan_exercise(ProfileInput(**profile['settings']), payload)
