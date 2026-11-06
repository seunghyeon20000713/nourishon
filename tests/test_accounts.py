"""별도 PostgreSQL 테스트 DB에서만 실행. 테스트가 만든 계정만 정리한다."""
import hashlib
import os
import secrets
import unittest
from uuid import uuid4
from datetime import date
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict
from backend.api import create_app
from backend.accounts import HASHER, Credentials, Registration
from backend.database import connect
from tests.test_api import practice_row

TEST_DSN=os.environ.get('NOURISHON_TEST_DATABASE_URL')
HEADERS={'Origin':'http://localhost:5173','X-NourishOn-Client':'web'}

@unittest.skipUnless(TEST_DSN,'별도 PostgreSQL 테스트 DB 설정이 필요합니다.')
class AccountTests(unittest.TestCase):
    def setUp(self):
        if conninfo_to_dict(TEST_DSN).get('dbname') != 'nourishon_test':
            raise RuntimeError('테스트 전용 DB만 허용합니다.')
        self.names=[]
        self.client=TestClient(create_app(rows=[practice_row('practice-1','연습용 음식')],database_url=TEST_DSN))
        self.client.__enter__()
        with connect(TEST_DSN) as conn:conn.execute('DELETE FROM auth_attempts')
    def tearDown(self):
        self.client.__exit__(None,None,None)
        with connect(TEST_DSN) as conn:
            for username in self.names:conn.execute('DELETE FROM users WHERE username=%s',(username,))
    def register(self, client=None):
        client=client or self.client
        name='practice_'+uuid4().hex[:16];self.names.append(name)
        password=secrets.token_urlsafe(24)
        r=client.post('/auth/register',json={'username':name,'password':password},headers=HEADERS)
        self.assertEqual(r.status_code,201)
        return r.json(),password
    def test_four_character_signup_and_login(self):
        # 별도 테스트 DB의 사용하지 않는 4자 가상 아이디만 생성한다.
        with connect(TEST_DSN) as conn:
            while True:
                name = secrets.token_hex(2)
                if not conn.execute('SELECT 1 FROM users WHERE username=%s', (name,)).fetchone():
                    break
        self.names.append(name)
        password = secrets.token_hex(2)
        for username, secret in [(name[:3], password), (name, password[:3])]:
            response = self.client.post('/auth/register', json={'username':username,'password':secret}, headers=HEADERS)
            self.assertEqual(response.status_code, 422)
        response = self.client.post('/auth/register', json={'username':name,'password':password}, headers=HEADERS)
        self.assertEqual(response.status_code, 201)
        user = response.json()
        self.assertEqual(self.client.post('/auth/register', json={'username':name,'password':password}, headers=HEADERS).status_code, 409)
        self.assertEqual(self.client.post('/auth/logout', headers=self.headers(user)).status_code, 200)
        response = self.client.post('/auth/login', json={'username':name,'password':password}, headers=HEADERS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['username'], name)

    def headers(self,user):return HEADERS|{'X-CSRF-Token':user['csrf_token']}
    def profile_id(self,client=None):return (client or self.client).get('/account/profiles').json()['profiles'][0]['id']
    def data(self):
        return {'profile':dict(age=30,height_cm=170,weight_kg=70,equation_sex='female',activity='inactive',scope_confirmed=True,measured_on='2020-01-01'),
                'records':[{'id':str(uuid4()),'date':date.today().isoformat(),'kind':'점심','calculation':{'foods':[{'food_code':'practice-1','intake_g':150}],'totals':{'energy':{'known_total':999999}}}}],
                'measurements':[{'id':str(uuid4()),'measured_on':'2020-01-01','weight_kg':70}]}
    def test_registration_hash_cookie_and_logout(self):
        user,password=self.register()
        with connect(TEST_DSN) as conn:
            row=conn.execute('SELECT password_hash FROM users WHERE username=%s',(user['user']['username'],)).fetchone()
            self.assertTrue(row['password_hash'].startswith('$argon2id$'))
            self.assertTrue(HASHER.verify(row['password_hash'],password))
            token=self.client.cookies.get('nourishon_session')
            session=conn.execute('SELECT token_hash FROM sessions WHERE user_id=%s',(user['user']['id'],)).fetchone()
            self.assertEqual(session['token_hash'],hashlib.sha256(token.encode()).hexdigest())
        r=self.client.post('/auth/logout',headers=self.headers(user));self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.get('/account/profiles').status_code,401)
        self.client.cookies.set('nourishon_session',token)
        self.assertEqual(self.client.get('/account/profiles').status_code,401)
    def test_persistence_recalculation_and_revision(self):
        user,_=self.register();pid=self.profile_id();data=self.data()
        r=self.client.put(f'/account/profiles/{pid}/data',json={'revision':0,'data':data},headers=self.headers(user))
        self.assertEqual(r.status_code,200)
        saved=r.json()
        self.assertEqual(saved['data']['records'][0]['calculation']['totals']['energy']['known_total'],300)
        self.assertEqual(saved['data']['estimate']['maintenance_kcal'],2167)
        self.assertEqual(saved['revision'],1)
        self.assertEqual(self.client.get('/account/profiles').json()['profiles'][0]['data'],saved['data'])
        stale=self.client.put(f'/account/profiles/{pid}/data',json={'revision':0,'data':data},headers=self.headers(user))
        self.assertEqual(stale.status_code,409)
        data['records'][0]['calculation']['foods'][0]['food_code']='unknown'
        r=self.client.put(f'/account/profiles/{pid}/data',json={'revision':1,'data':data},headers=self.headers(user))
        self.assertEqual(r.status_code,422)
        self.assertEqual(self.client.get('/account/profiles').json()['profiles'][0]['revision'],1)
    def test_user_isolation(self):
        a,_=self.register();pid=self.profile_id()
        with TestClient(create_app(rows=[practice_row('practice-1','연습용 음식')],database_url=TEST_DSN)) as other:
            b,_=self.register(other)
            self.assertNotEqual(self.profile_id(other),pid)
            r=other.put(f'/account/profiles/{pid}/data',json={'revision':0,'data':self.data()},headers=self.headers(b))
            self.assertEqual(r.status_code,404)
            exercise=dict(experience='beginner',days=3,minutes=15,current_weekly_minutes=0,has_limitations=False,has_symptoms=False,scope_confirmed=True)
            self.assertEqual(other.post(f'/account/profiles/{pid}/exercise-plan',json=exercise,headers=self.headers(b)).status_code,404)
    def test_csrf_origin_validation_and_no_echo(self):
        self.assertEqual(self.client.get('/account/profiles').status_code,401)
        user,_=self.register()
        r=self.client.post('/account/profiles',json={'nickname':'연습'},headers=HEADERS)
        self.assertEqual(r.status_code,403)
        r=self.client.post('/account/profiles',json={'nickname':'연습'},headers=self.headers(user)|{'Origin':'https://untrusted.example'})
        self.assertEqual(r.status_code,403)
        marker='private-marker'
        r=self.client.post('/auth/register',json={'username':'bad!','password':marker},headers=HEADERS)
        self.assertEqual(r.status_code,422);self.assertNotIn(marker,r.text)
    def test_login_and_session_expiry(self):
        user,password=self.register()
        self.client.post('/auth/logout',headers=self.headers(user))
        r=self.client.post('/auth/login',json={'username':user['user']['username'],'password':'wrong-password-at-least15'},headers=HEADERS)
        self.assertEqual(r.status_code,401)
        r=self.client.post('/auth/login',json={'username':user['user']['username'],'password':password},headers=HEADERS)
        self.assertEqual(r.status_code,200)
        self.assertIn('HttpOnly',r.headers['set-cookie']);self.assertIn('SameSite=strict',r.headers['set-cookie'])
        self.assertEqual(r.headers['cache-control'],'no-store')
        with connect(TEST_DSN) as conn:conn.execute('UPDATE sessions SET expires_at=now()-interval \'1 second\' WHERE user_id=%s',(user['user']['id'],))
        self.assertEqual(self.client.get('/account/profiles').status_code,401)
    def test_login_rate_limit(self):
        name='missing_'+uuid4().hex[:12]
        for _ in range(10):
            r=self.client.post('/auth/login',json={'username':name,'password':'not-real-password-12345'},headers=HEADERS)
            self.assertEqual(r.status_code,401)
        self.assertEqual(self.client.post('/auth/login',json={'username':name,'password':'not-real-password-12345'},headers=HEADERS).status_code,429)
    def test_exercise_saved_and_guarded(self):
        user,_=self.register();pid=self.profile_id();data=self.data()
        exercise=dict(experience='beginner',days=3,minutes=15,current_weekly_minutes=0,has_limitations=False,has_symptoms=False,scope_confirmed=True)
        self.assertEqual(self.client.post(f'/account/profiles/{pid}/exercise-plan',json=exercise,headers=self.headers(user)).status_code,422)
        data['exerciseInput']=exercise
        r=self.client.put(f'/account/profiles/{pid}/data',json={'revision':0,'data':data},headers=self.headers(user))
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['data']['exercisePlan']['status'],'draft')
        exercise['has_symptoms']=True
        r=self.client.post(f'/account/profiles/{pid}/exercise-plan',json=exercise,headers=self.headers(user))
        self.assertEqual(r.json()['status'],'needs_assessment')
        self.assertEqual(r.json()['schedule'],[])

    def test_snapshot_kept_and_app_role_not_superuser(self):
        user,_=self.register();pid=self.profile_id();data=self.data()
        first=self.client.put(f'/account/profiles/{pid}/data',json={'revision':0,'data':data},headers=self.headers(user)).json()
        # 공공 데이터 갱신 이후에도 동일 섭취 기록의 과거 스냅샷을 유지한다.
        self.client.app.state.catalog.by_code['practice-1'][1]['ENERC']=999
        r=self.client.put(f'/account/profiles/{pid}/data',json={'revision':1,'data':first['data']},headers=self.headers(user))
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['data']['records'][0]['calculation']['totals']['energy']['known_total'],300)
        with connect(TEST_DSN) as conn:
            self.assertFalse(conn.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()['rolsuper'])

    def test_activity_snapshot_and_legacy_save(self):
        user, _ = self.register()
        pid = self.profile_id()
        activity = dict(id=str(uuid4()), date=date.today().isoformat(), age=30,
                        activity_code='17152', weight_kg=70, minutes=30,
                        calculation={'gross_kcal':999999})
        data = self.data() | {'activityRecords':[activity]}
        response = self.client.put(f'/account/profiles/{pid}/data', json={'revision':0,'data':data}, headers=self.headers(user))
        self.assertEqual(response.status_code, 200)
        saved = response.json()
        self.assertEqual(saved['data']['activityRecords'][0]['calculation']['gross_kcal'], 98)
        # 운동 필드를 모르는 이전 클라이언트 저장이 기존 운동 기록을 지우지 않는다.
        legacy = saved['data'].copy()
        legacy.pop('activityRecords')
        response = self.client.put(f'/account/profiles/{pid}/data', json={'revision':saved['revision'],'data':legacy}, headers=self.headers(user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['activityRecords'], saved['data']['activityRecords'])
        self.assertEqual(self.client.get('/account/profiles').json()['profiles'][0]['data']['activityRecords'], saved['data']['activityRecords'])

    def test_staging_secure_cookie_and_readiness(self):
        from unittest.mock import patch
        from backend.settings import load_settings
        from tests.test_deployment import ENV
        with patch.dict(os.environ,ENV,clear=True):
            settings=load_settings()
        app=create_app(rows=[practice_row('practice-1','가상')],database_url=TEST_DSN,settings=settings)
        with TestClient(app,base_url='https://preview.example.com') as client:
            name='practice_'+uuid4().hex[:16];self.names.append(name)
            headers={'Origin':'https://preview.example.com','X-NourishOn-Client':'web'}
            response=client.post('/auth/register',json={'username':name,'password':secrets.token_urlsafe(24)},headers=headers)
            self.assertEqual(response.status_code,201)
            cookie=response.headers['set-cookie']
            self.assertIn('__Host-nourishon_session=',cookie)
            self.assertIn('Secure',cookie)
            self.assertIn('HttpOnly',cookie)
            self.assertIn('SameSite=strict',cookie)
            self.assertNotIn('Domain=',cookie)
            self.assertEqual(client.get('/account/profiles').status_code,200)
            self.assertEqual(client.get('/ready').status_code,200)
            self.assertEqual(client.post('/auth/logout',headers=headers|{'X-CSRF-Token':response.json()['csrf_token']}).status_code,200)
            self.assertFalse(client.cookies.get('__Host-nourishon_session'))

    def test_request_body_limit(self):
        r=self.client.post('/auth/register',content=b'x'*2_000_001,headers=HEADERS|{'Content-Type':'application/json'})
        self.assertEqual(r.status_code,413)
        self.assertEqual(r.headers['cache-control'],'no-store')


class CredentialInputTests(unittest.TestCase):
    def test_registration_length_boundaries(self):
        from pydantic import ValidationError
        for name, password in [('abc', 'abcd'), ('abcd', 'abc'), ('a'*41, 'abcd'), ('abcd', 'a'*129)]:
            with self.subTest(username_length=len(name), password_length=len(password)):
                with self.assertRaises(ValidationError):
                    Registration(username=name, password=password)
        for name, password in [('ABCD', 'abcd'), ('a'*40, 'a'*128)]:
            self.assertEqual(Registration(username=name, password=password).username, name.lower())
        self.assertEqual(Credentials(username='abc', password='abcd').username, 'abc')

    def test_normalize_login_name(self):
        value=Credentials(username=' Practice_User ',password=secrets.token_urlsafe(24))
        self.assertEqual(value.username,'practice_user')
