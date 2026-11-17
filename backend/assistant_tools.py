"""AI 건강 비서가 부르는 도구(Tool Calling). 숫자는 모두 기존에 테스트된 함수가 계산한다.

원칙
- 도구 입력에는 사용자·프로필 ID가 없다. 서버가 로그인 세션의 본인 프로필 데이터만 넘긴다.
- 도구 결과에는 숫자·날짜·정해진 라벨만 담는다. 아이디·닉네임·음식 이름 같은 자유 문자열은 넣지 않는다.
  `ensure_safe_payload`가 이를 검사하고, 테스트가 모든 도구 결과를 이 검사에 통과시킨다.
"""
import re
from datetime import date, timedelta

from backend.activity_log import ACTIVITIES
from backend.nutrition_review import ReviewFood, ReviewInput, ReviewMeal, review_nutrition
from backend.period_summary import NUTRIENTS, period_summary

MAX_DAYS = 31
MEAL_KINDS = ('아침', '점심', '저녁', '간식')
NUTRIENT_LABELS = {'energy': '열량', 'carbohydrate': '탄수화물', 'protein': '단백질', 'fat': '지방',
                   'sugar': '당류', 'fiber': '식이섬유', 'sodium': '나트륨'}
NOTES = {
    'period': '기록된 값만 합산합니다. 기록하지 않은 날은 0이 아니며 평균 분모에서 뺍니다. 실제 하루 섭취량과 다를 수 있습니다.',
    'review': '기록된 식사만 검토합니다. 하루 전체 섭취 평가나 결핍 진단이 아닙니다.',
    'activity': '2024 Adult Compendium 표준 MET 기반 추정입니다. 개인 실측값이 아닙니다.',
    'reference': '유지 에너지 추정과 일반 성인 참고값입니다. 감량·증량 처방이나 남은 권장 섭취량이 아닙니다.',
    'no_profile': '신체 프로필이 없어 개인 참고값을 계산하지 않았습니다.',
}
SOURCES = {
    'kdri': '2025 한국인 영양소 섭취기준',
    'who_diet': 'WHO Healthy diet (나트륨 2,000mg 미만·식이섬유 25g 이상, 일반 성인)',
    'compendium': '2024 Adult Compendium of Physical Activities',
}

TOOL_SPECS = [
    {'name': 'get_period_nutrition',
     'description': '기간(최대 31일)의 기록된 영양 합계, 기록한 날 수, 기록일 평균, 성분별 누락 수를 돌려준다.',
     'parameters': {'type': 'object', 'properties': {
         'start': {'type': 'string', 'description': '시작일 YYYY-MM-DD'},
         'end': {'type': 'string', 'description': '종료일 YYYY-MM-DD'}}, 'required': ['start', 'end']}},
    {'name': 'get_day_meals',
     'description': '하루의 끼니별 영양 합계와 누락 수를 돌려준다. 음식 이름은 포함하지 않는다.',
     'parameters': {'type': 'object', 'properties': {
         'date': {'type': 'string', 'description': '날짜 YYYY-MM-DD'}}, 'required': ['date']}},
    {'name': 'get_nutrition_review',
     'description': '기간의 기록된 식사로 탄수화물·단백질·지방 에너지 비율과 참고 범위 비교, 판단 보류 여부를 돌려준다.',
     'parameters': {'type': 'object', 'properties': {
         'start': {'type': 'string', 'description': '시작일 YYYY-MM-DD'},
         'end': {'type': 'string', 'description': '종료일 YYYY-MM-DD'}}, 'required': ['start', 'end']}},
    {'name': 'get_activity_summary',
     'description': '기간의 운동 기록 건수·시간·표준 MET 기반 소모량 추정 합계를 돌려준다.',
     'parameters': {'type': 'object', 'properties': {
         'start': {'type': 'string', 'description': '시작일 YYYY-MM-DD'},
         'end': {'type': 'string', 'description': '종료일 YYYY-MM-DD'}}, 'required': ['start', 'end']}},
    {'name': 'get_my_reference',
     'description': '현재 신체 프로필 기준 유지 에너지 추정, 단백질·식이섬유·나트륨 일반 성인 참고값과 출처를 돌려준다.',
     'parameters': {'type': 'object', 'properties': {}}},
]
TOOL_NAMES = {spec['name'] for spec in TOOL_SPECS}


class ToolError(ValueError):
    """AI가 잘못된 입력(날짜 형식·범위)을 준 경우. 오류 문장은 정해진 문구만 쓴다."""


def _date(value) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ToolError('날짜는 YYYY-MM-DD 형식이어야 합니다.') from None


def _period(args: dict, today: date) -> tuple[date, date]:
    start, end = _date(args.get('start')), _date(args.get('end'))
    if end < start:
        raise ToolError('시작일이 종료일보다 늦습니다.')
    if (end - start).days + 1 > MAX_DAYS:
        raise ToolError('기간은 최대 31일입니다.')
    if start > today:
        raise ToolError('미래 기간은 조회할 수 없습니다.')
    return start, min(end, today)


def _nutrients(totals: dict) -> dict:
    return {key: {'label': NUTRIENT_LABELS[key], 'value': value['known_total'], 'unit': value['unit'],
                  'missing_count': value['missing_count'], 'status': value['status']}
            for key, value in totals.items()}


class ToolBox:
    """한 사용자의 한 프로필 데이터만 가진다. 다른 사용자의 데이터에 접근할 입력이 없다."""

    def __init__(self, data: dict, today: date):
        self.meals = list(data.get('records') or [])
        self.activities = list(data.get('activityRecords') or [])
        self.estimate = data.get('estimate')
        self.today = today

    def run(self, name: str, args: dict | None) -> dict:
        if name not in TOOL_NAMES:
            raise ToolError('지원하지 않는 도구입니다.')
        args = args or {}
        result = getattr(self, name)(args)
        ensure_safe_payload(result)
        return result

    def get_period_nutrition(self, args):
        start, end = _period(args, self.today)
        summary = period_summary(self.meals, start, end, self.today)
        return {'start': summary['start'], 'end': summary['end'], 'days_in_period': summary['days_in_period'],
                'recorded_days': summary['recorded_days'], 'meal_count': summary['meal_count'],
                'totals': _nutrients(summary['totals']),
                'recorded_day_averages': {key: {'label': NUTRIENT_LABELS[key], **value}
                                          for key, value in summary['recorded_day_averages'].items()},
                'note': NOTES['period']}

    def get_day_meals(self, args):
        day = _date(args.get('date'))
        if day > self.today:
            raise ToolError('미래 날짜는 조회할 수 없습니다.')
        rows = [row for row in self.meals if row.get('date') == day.isoformat()]
        summary = period_summary(rows, day, day, self.today)
        meals = []
        for kind in MEAL_KINDS:
            same = [row for row in rows if row.get('kind') == kind]
            if same:
                part = period_summary(same, day, day, self.today)
                meals.append({'kind': kind, 'meal_count': len(same), 'totals': _nutrients(part['totals'])})
        return {'date': day.isoformat(), 'recorded': bool(rows), 'meal_count': len(rows), 'meals': meals,
                'totals': _nutrients(summary['totals']), 'note': NOTES['period']}

    def get_nutrition_review(self, args):
        start, end = _period(args, self.today)
        entries = []
        for row in self.meals:
            if start.isoformat() <= row.get('date', '') <= end.isoformat():
                foods = (row.get('calculation') or {}).get('foods') or []
                parsed = [ReviewFood(food_name='기록된 음식', nutrients={key: value for key, value in (food.get('nutrients') or {}).items() if key in NUTRIENTS})
                          for food in foods if food.get('nutrients')]
                if parsed:
                    entries.append(ReviewMeal(foods=parsed))
        review = review_nutrition(ReviewInput(meals=entries[:100]))
        return {'start': start.isoformat(), 'end': end.isoformat(), 'reviewed_meals': review['recorded_meals'],
                'skipped_meals_without_detail': sum(1 for row in self.meals if start.isoformat() <= row.get('date', '') <= end.isoformat()) - len(entries),
                'macro_status': review['macro_status'],
                'macros': [{'label': item['label'], 'percent': item['percent'], 'reference_low': item['reference'][0],
                            'reference_high': item['reference'][1], 'comparison': item['comparison']} for item in review['macros']],
                'totals': {key: {'label': NUTRIENT_LABELS[key], 'value': value['value'], 'unit': value['unit'], 'missing_count': value['missing']}
                           for key, value in review['totals'].items()},
                'sodium_contributor_count': len(review['sodium_contributors']),
                'source': SOURCES['kdri'], 'note': NOTES['review']}

    def get_activity_summary(self, args):
        start, end = _period(args, self.today)
        rows = [row for row in self.activities if start.isoformat() <= row.get('date', '') <= end.isoformat()]
        categories = {}
        for row in rows:
            category = ACTIVITIES.get(row.get('activity_code'), {}).get('category', '기타')
            item = categories.setdefault(category, {'category': category, 'count': 0, 'minutes': 0.0})
            item['count'] += 1
            item['minutes'] += float(row.get('minutes') or 0)
        return {'start': start.isoformat(), 'end': end.isoformat(), 'record_count': len(rows),
                'active_days': len({row['date'] for row in rows}), 'days_in_period': (end - start).days + 1,
                'total_minutes': sum(float(row.get('minutes') or 0) for row in rows),
                'gross_kcal_estimate': sum(float(row['calculation']['gross_kcal']) for row in rows),
                'above_rest_kcal_estimate': sum(float(row['calculation']['above_rest_kcal']) for row in rows),
                'by_category': sorted(categories.values(), key=lambda item: -item['minutes']),
                'source': SOURCES['compendium'], 'note': NOTES['activity']}

    def get_my_reference(self, args):
        if not self.estimate:
            return {'available': False, 'note': NOTES['no_profile']}
        return {'available': True,
                'maintenance_kcal_estimate': self.estimate.get('maintenance_kcal'),
                'protein_reference_g': self.estimate.get('protein_reference_g'),
                'fiber_reference_g': 25, 'sodium_reference_mg_under': 2000,
                'sources': [SOURCES['kdri'], SOURCES['who_diet']], 'note': NOTES['reference']}


_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
ALLOWED_STRINGS = (set(NUTRIENT_LABELS.values()) | set(NUTRIENTS.values()) | set(MEAL_KINDS) | set(NOTES.values())
                   | set(SOURCES.values()) | {'missing', 'partial', 'complete', 'no_records', 'zero_energy', 'inconsistent', 'available',
                                               '범위보다 낮음', '범위보다 높음', '참고 범위 안', '기타'}
                   | {item['category'] for item in ACTIVITIES.values()})


def ensure_safe_payload(value, path='result'):
    """AI로 보낼 수 있는 값만 있는지 확인한다: 숫자·불리언·None·날짜·정해진 라벨. 그 밖의 문자열이 있으면 오류."""
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        if value in ALLOWED_STRINGS or _DATE.match(value):
            return
        raise ValueError(f'{path}: 허용되지 않은 문자열')
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not re.fullmatch(r'[a-z_]+', key):
                raise ValueError(f'{path}: 허용되지 않은 키')
            ensure_safe_payload(item, f'{path}.{key}')
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            ensure_safe_payload(item, f'{path}[{index}]')
        return
    raise ValueError(f'{path}: 허용되지 않은 형식')
