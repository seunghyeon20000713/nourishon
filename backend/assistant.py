"""AI 건강 비서 API. 로그인 사용자의 본인 프로필 기록만 도구로 읽는다.

흐름: 세션·CSRF 확인 → 본인 프로필 확인 → 진단·처방 질문 거절 → 하루 질문 수 확인
     → 식별 정보 지우기 → 설정된 제공자로 답변(실패 시 가짜 AI로 전환) → 숫자 검사 → 응답.
질문 원문과 답변은 저장하지 않는다. 사용 횟수만 센다.
"""
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, StringConstraints

from backend.accounts import dsn, owned, serialize, session
from backend.assistant_providers import FakeProvider, ProviderError, Reply, build_provider, unknown_numbers
from backend.assistant_tools import ToolBox
from backend.database import connect

router = APIRouter()
KST = timezone(timedelta(hours=9))

REFUSAL = ('진단·처방·약·질환에 대한 판단은 도와드릴 수 없어요. 증상이 있거나 치료 중이라면 의사·임상영양사 등 전문가와 상담해 주세요. '
           '기록된 식사·운동 숫자를 설명하는 것은 도와드릴 수 있어요.')
# 진단·처방·약·질환 판단 요청. '약간'처럼 다른 뜻의 단어는 걸리지 않게 구체적인 표현만 둔다.
REFUSE_PATTERNS = re.compile(
    r'진단|처방|치료|복용|약을|약 ?먹|먹는 ?약|약물|영양제|보충제|용량|부작용|질환|질병|병원|증상|통증|아파|아픈|'
    r'당뇨|혈당|고혈압|혈압|고지혈|콜레스테롤|신장|간 ?수치|갑상선|암\b|암이|임신|수유|우울|불면|섭식|거식|폭식')

DATA_NOTICE = {
    'fake': '외부로 전송하지 않는 기본 설명 모드예요. 기록된 숫자를 정해진 문장으로 설명해요.',
    'gemini': '질문과 기록 숫자가 Google AI(Gemini 무료 등급)로 전송되며 Google 서비스 개선에 쓰일 수 있어요. 실제 건강정보·이름·연락처는 입력하지 마세요.',
}
FALLBACK_NOTICE = 'AI 응답을 받지 못해(무료 사용량 초과 또는 연결 오류) 기본 설명으로 답했어요.'
NUMBER_NOTICE = 'AI 설명에 기록에서 확인할 수 없는 숫자가 있어 기본 설명으로 바꿨어요.'


@dataclass
class AssistantConfig:
    provider: str = 'fake'
    api_key: str | None = None
    model: str = 'gemini-3.1-flash-lite'
    daily_limit: int = 20
    service_daily_limit: int = 200

    @classmethod
    def from_env(cls):
        provider = os.environ.get('NOURISHON_AI_PROVIDER', 'fake').strip().lower()
        if provider not in {'fake', 'gemini'}:
            raise ValueError('NOURISHON_AI_PROVIDER는 fake 또는 gemini여야 합니다.')
        return cls(provider=provider, api_key=os.environ.get('NOURISHON_GEMINI_API_KEY') or None,
                   model=os.environ.get('NOURISHON_GEMINI_MODEL', cls.model).strip(),
                   daily_limit=int(os.environ.get('NOURISHON_AI_DAILY_LIMIT', cls.daily_limit)),
                   service_daily_limit=int(os.environ.get('NOURISHON_AI_SERVICE_DAILY_LIMIT', cls.service_daily_limit)))


class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    profile_id: UUID
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


def today():
    return datetime.now(KST).date()


def scrub(question: str, secrets: list[str]) -> str:
    """질문 속 아이디·닉네임을 지운다(외부 AI에 식별 정보를 보내지 않기 위해)."""
    for value in sorted({s for s in secrets if s and len(s) >= 2}, key=len, reverse=True):
        question = re.sub(re.escape(value), '사용자', question, flags=re.IGNORECASE)
    return question


def config(request: Request) -> AssistantConfig:
    value = getattr(request.app.state, 'assistant', None)
    if value is None:
        value = request.app.state.assistant = AssistantConfig.from_env()
    return value


def provider(request: Request, cfg: AssistantConfig):
    # 테스트는 app.state.assistant_provider로 가짜 Gemini 응답을 주입한다.
    override = getattr(request.app.state, 'assistant_provider', None)
    return override if override is not None else build_provider(cfg.provider, cfg.api_key, cfg.model)


def usage(conn, user_id, day):
    row = conn.execute('SELECT questions FROM assistant_usage WHERE user_id=%s AND day=%s', (user_id, day)).fetchone()
    total = conn.execute('SELECT COALESCE(sum(questions),0) AS n FROM assistant_usage WHERE day=%s', (day,)).fetchone()
    return (row['questions'] if row else 0), total['n']


@router.get('/assistant/status')
def status(request: Request):
    cfg = config(request)
    with connect(dsn(request)) as conn:
        user = session(request, conn)
        used, _ = usage(conn, user['user_id'], today())
    return {'provider': cfg.provider, 'notice': DATA_NOTICE[cfg.provider], 'daily_limit': cfg.daily_limit,
            'remaining': max(cfg.daily_limit - used, 0)}


@router.post('/assistant/ask')
def ask(payload: Question, request: Request):
    cfg = config(request)
    day = today()
    with connect(dsn(request)) as conn:
        user = session(request, conn, write=True)
        profile = owned(conn, user['user_id'], payload.profile_id)   # 다른 사용자의 프로필이면 404
        data = serialize(conn, profile)['data']
        used, service_used = usage(conn, user['user_id'], day)
        if used >= cfg.daily_limit:
            raise HTTPException(429, f'오늘 질문 {cfg.daily_limit}개를 모두 사용했어요. 내일 다시 이용해 주세요.')
        if service_used >= cfg.service_daily_limit:
            raise HTTPException(429, '오늘 서비스 전체 질문 수가 가득 찼어요. 내일 다시 이용해 주세요.')
        conn.execute('INSERT INTO assistant_usage(user_id,day,questions) VALUES(%s,%s,1) '
                     'ON CONFLICT(user_id,day) DO UPDATE SET questions=assistant_usage.questions+1', (user['user_id'], day))
        conn.commit()
        remaining = cfg.daily_limit - used - 1
        if REFUSE_PATTERNS.search(payload.question):
            return {'answer': REFUSAL, 'provider': 'rule', 'refused': True, 'notice': None, 'tool_calls': [], 'remaining': remaining}
        question = scrub(payload.question, [user['username'], profile['nickname']])
        tools = ToolBox(data, day)
        notice = None
        try:
            reply = provider(request, cfg).answer(question, tools, day)
        except ProviderError:
            reply, notice = FakeProvider().answer(question, ToolBox(data, day), day), FALLBACK_NOTICE
        if reply.provider != 'fake' and unknown_numbers(reply.text, question, reply.tool_calls, day):
            reply, notice = FakeProvider().answer(question, ToolBox(data, day), day), NUMBER_NOTICE
        if notice:
            conn.execute('UPDATE assistant_usage SET fallbacks=fallbacks+1 WHERE user_id=%s AND day=%s', (user['user_id'], day))
    return {'answer': reply.text, 'provider': reply.provider, 'refused': False, 'notice': notice,
            'tool_calls': reply.tool_calls, 'remaining': remaining}
