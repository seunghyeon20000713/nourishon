"""AI 제공자(가짜 / Gemini). 설정 하나(NOURISHON_AI_PROVIDER)로 바꾼다.

모든 제공자는 같은 약속을 지킨다: 질문을 받아 도구를 부르고(실행은 서버 ToolBox), 결과를 설명하는 문장을 돌려준다.
- FakeProvider: 외부 전송 없이 규칙(키워드·날짜 표현)으로 도구를 고르고 정해진 문장 틀로 설명한다. 비용 0원.
  Gemini가 실패하면 이 제공자로 자동 전환한다.
- GeminiProvider: Google Gemini API의 함수 호출(function calling). 보내는 것은 질문과 도구 결과(숫자·날짜·라벨)뿐이다.
"""
import json
import re
from decimal import ROUND_HALF_UP, Decimal
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta

from backend.assistant_tools import TOOL_SPECS, ToolBox, ToolError

SYSTEM_PROMPT = """너는 NourishOn의 식생활 기록 도우미다. 한국어로 3~5문장으로 답한다.
규칙:
1. 숫자는 직접 계산하지 말고 반드시 도구를 불러 받은 값만 쓴다. 도구 결과에 없는 숫자를 만들지 않는다.
2. 기록된 값만 설명한다. 누락(missing_count)이나 기록하지 않은 날이 있으면 먼저 말하고, 그 경우 충분·부족을 판단하지 않는다.
3. 진단·처방·치료 효과·약·질환에 대한 판단은 하지 않는다. 증상이나 질환 이야기가 나오면 전문가 상담을 권한다.
4. 참고값과 비교할 때는 출처(2025 한국인 영양소 섭취기준, WHO)를 밝히고, 개인 처방이 아니라고 말한다.
5. 오늘 날짜는 {today}이다. '이번 주'는 월요일부터 오늘까지, '어제'는 오늘 전날이다."""


class ProviderError(RuntimeError):
    """제공자 호출 실패(키 없음·사용량 초과·네트워크·형식 오류). 메시지에 키나 질문 원문을 넣지 않는다."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class Reply:
    text: str
    provider: str
    tool_calls: list = field(default_factory=list)


def fmt(value, unit: str) -> str:
    """화면 nutrientFormat.ts와 같은 표시 규칙: kcal·mg 정수, g 소수 첫째 자리."""
    if value is None:
        return '정보 없음'
    digits = 0 if unit in ('kcal', 'mg') else 1
    # 화면(Intl.NumberFormat)과 같은 '반올림(0.5 올림)'. 파이썬 기본 round는 짝수 쪽으로 반올림해 41.25 → 41.2가 된다.
    rounded = Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    if value > 0 and rounded == 0:
        return f"{'1' if digits == 0 else '0.1'} 미만 {unit}"
    text = f'{rounded:,.{digits}f}'
    if digits and text.endswith('.0'):
        text = text[:-2]
    return f'{text} {unit}'


# ---------------------------------------------------------------- 가짜 AI(규칙 기반)
KEYWORDS = [('sodium', ('나트륨', '소금', '짜게', '짠')), ('protein', ('단백질',)), ('fiber', ('식이섬유', '섬유')),
            ('sugar', ('당류', '설탕', '단 거')), ('fat', ('지방',)), ('carbohydrate', ('탄수화물', '탄수')),
            ('activity', ('운동', '걷기', '등산', '활동')), ('energy', ('열량', '칼로리', 'kcal', '얼마나 먹'))]


def resolve_period(question: str, today: date) -> tuple[date, date, str]:
    if '어제' in question:
        day = today - timedelta(days=1)
        return day, day, '어제'
    if '그제' in question or '그저께' in question:
        day = today - timedelta(days=2)
        return day, day, '그저께'
    if '지난주' in question or '지난 주' in question:
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=6), '지난주'
    if '이번 달' in question or '이번달' in question:
        return today.replace(day=1), today, '이번 달'
    if '최근' in question or '일주일' in question or '7일' in question:
        return today - timedelta(days=6), today, '최근 7일'
    if '오늘' in question:
        return today, today, '오늘'
    return today - timedelta(days=today.weekday()), today, '이번 주'


class FakeProvider:
    name = 'fake'

    def answer(self, question: str, tools: ToolBox, today: date) -> Reply:
        topic = next((key for key, words in KEYWORDS if any(word in question for word in words)), 'energy')
        start, end, label = resolve_period(question, today)
        calls = []

        def call(name, args):
            result = tools.run(name, args)
            calls.append({'name': name, 'args': args, 'result': result})
            return result

        period = {'start': start.isoformat(), 'end': end.isoformat()}
        span = f'{label}({start})' if start == end else f'{label}({start}~{end})'
        if topic == 'activity':
            data = call('get_activity_summary', period)
            if not data['record_count']:
                text = f'{span}에는 운동 기록이 없어요. 기록하지 않은 날을 운동 0분으로 보지는 않아요.'
            else:
                text = (f"{span} {data['days_in_period']}일 중 {data['active_days']}일, 운동 {data['record_count']}건을 기록했어요. "
                        f"총 {fmt(data['total_minutes'], '분').replace(' 분', '분')}, 표준 MET 기준 추정 {fmt(data['gross_kcal_estimate'], 'kcal')}예요. "
                        '개인 실측값이 아니며, 식사 열량에서 자동으로 빼지 않아요.')
            return Reply(text, self.name, calls)

        data = call('get_period_nutrition', period)
        nutrient = data['totals'][topic]
        average = data['recorded_day_averages'][topic]
        days = f"{span} {data['days_in_period']}일 중 {data['recorded_days']}일 기록"
        if not data['recorded_days']:
            text = f'{span}에는 식사 기록이 없어요. 기록하지 않은 날은 0으로 계산하지 않아서 판단할 수 없어요.'
        elif nutrient['value'] is None:
            text = f"{days}했지만 {nutrient['label']} 정보가 있는 음식이 없어요(누락 {nutrient['missing_count']}개). 정보가 없어서 판단하지 않아요."
        else:
            text = f"{days} 기준, 확인된 {nutrient['label']} 합계는 {fmt(nutrient['value'], nutrient['unit'])}"
            if average['days'] > 1:
                text += f"이고 기록일 평균은 {fmt(average['value'], nutrient['unit'])}({average['days']}일)"
            text += '이에요. '
            if nutrient['missing_count']:
                text += f"다만 정보가 빠진 항목이 {nutrient['missing_count']}개 있어 실제보다 적을 수 있어 충분·부족을 판단하지 않아요. "
            reference = call('get_my_reference', {})
            if topic == 'sodium':
                text += 'WHO는 일반 성인 나트륨을 하루 2,000mg 미만으로 권고해요. '
            elif topic == 'protein' and reference.get('available') and reference.get('protein_reference_g'):
                text += f"내 정보 기준 일반 성인 단백질 참고값은 하루 {fmt(reference['protein_reference_g'], 'g')}이에요(2025 한국인 영양소 섭취기준). "
            elif topic == 'fiber':
                text += 'WHO는 일반 성인 식이섬유를 하루 25g 이상으로 권고해요. '
            text += '기록된 식사만 본 참고 설명이고 진단이나 처방이 아니에요.'
        return Reply(text, self.name, calls)


# ---------------------------------------------------------------- Gemini
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'


def _post_json(url: str, body: dict, headers: dict, timeout: float) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
        raise ProviderError('quota' if status == 429 else f'http_{status}') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProviderError('network') from None
    except (ValueError, UnicodeDecodeError):
        raise ProviderError('bad_response') from None


class GeminiProvider:
    name = 'gemini'

    def __init__(self, api_key: str, model: str, post=_post_json, timeout: float = 20.0, max_rounds: int = 3):
        if not api_key:
            raise ProviderError('missing_key')
        self.api_key, self.model, self.post, self.timeout, self.max_rounds = api_key, model, post, timeout, max_rounds

    def request_body(self, contents: list, today: date) -> dict:
        return {'systemInstruction': {'parts': [{'text': SYSTEM_PROMPT.format(today=today.isoformat())}]},
                'contents': contents,
                'tools': [{'functionDeclarations': TOOL_SPECS}],
                'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 600}}

    def answer(self, question: str, tools: ToolBox, today: date) -> Reply:
        contents = [{'role': 'user', 'parts': [{'text': question}]}]
        calls = []
        url = GEMINI_URL.format(model=self.model)
        # API 키는 URL이 아니라 헤더로 보낸다(로그·오류 메시지에 남지 않게).
        headers = {'Content-Type': 'application/json', 'x-goog-api-key': self.api_key}
        for _ in range(self.max_rounds + 1):
            data = self.post(url, self.request_body(contents, today), headers, self.timeout)
            try:
                parts = data['candidates'][0]['content']['parts']
            except (KeyError, IndexError, TypeError):
                raise ProviderError('bad_response') from None
            function_calls = [part['functionCall'] for part in parts if isinstance(part, dict) and 'functionCall' in part]
            if not function_calls:
                text = ''.join(part.get('text', '') for part in parts if isinstance(part, dict)).strip()
                if not text:
                    raise ProviderError('empty')
                return Reply(text, self.name, calls)
            if len(calls) + len(function_calls) > 6:
                raise ProviderError('too_many_calls')
            contents.append({'role': 'model', 'parts': [{'functionCall': call} for call in function_calls]})
            responses = []
            for call in function_calls:
                name, args = call.get('name'), call.get('args') or {}
                try:
                    result = tools.run(name, args)
                except ToolError as error:
                    result = {'error': str(error)}
                calls.append({'name': name, 'args': args, 'result': result})
                responses.append({'functionResponse': {'name': name, 'response': result}})
            contents.append({'role': 'user', 'parts': responses})
        raise ProviderError('too_many_rounds')


def build_provider(kind: str, api_key: str | None, model: str):
    if kind == 'gemini':
        return GeminiProvider(api_key or '', model)
    return FakeProvider()


# ---------------------------------------------------------------- 숫자 보호
_NUMBER = re.compile(r'\d[\d,]*(?:\.\d+)?')


def _numbers(value, found: set):
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        for digits in (0, 1, 2):
            found.add(round(float(value), digits))
        return
    if isinstance(value, str):
        for match in _NUMBER.findall(value):
            found.add(float(match.replace(',', '')))
        return
    if isinstance(value, dict):
        for item in value.values():
            _numbers(item, found)
    if isinstance(value, list):
        for item in value:
            _numbers(item, found)


def unknown_numbers(text: str, question: str, calls: list, today: date) -> list[str]:
    """AI 문장의 숫자 중 도구 결과·질문·날짜·고정 기준값에 없는 것을 찾는다(지어낸 숫자 차단)."""
    allowed = {2000.0, 25.0, 0.0, float(today.year), float(today.month), float(today.day)}
    _numbers(question, allowed)
    for call in calls:
        _numbers(call['args'], allowed)
        _numbers(call['result'], allowed)
        for value in re.findall(r'\d{4}-\d{2}-\d{2}', json.dumps(call['result'])):
            year, month, day = value.split('-')
            allowed |= {float(year), float(month), float(day)}
    bad = []
    for match in _NUMBER.findall(text):
        number = float(match.replace(',', ''))
        if not any(abs(number - ok) < 1e-9 for ok in allowed):
            bad.append(match)
    return bad
