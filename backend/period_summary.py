"""기간 영양 합계(화면 PeriodAnalysis.tsx와 같은 규칙을 서버로 옮긴 것, 2026-11-17).

AI 건강 비서가 숫자를 직접 계산하지 않고 이 함수를 도구로 부르기 위해 만들었다.
- 결측은 0으로 채우지 않고 '누락 N개'로 센다.
- 기록하지 않은 날은 평균 분모에서 빼고, 며칠 중 며칠 기록인지 함께 돌려준다. 0으로 기록한 날은 포함한다.
- 오늘 이후 날짜는 집계하지 않는다.
"""
import math
from datetime import date, timedelta

NUTRIENTS = {'energy': 'kcal', 'carbohydrate': 'g', 'protein': 'g', 'fat': 'g', 'sugar': 'g', 'fiber': 'g', 'sodium': 'mg'}


def week_bounds(anchor: date) -> tuple[date, date]:
    start = anchor - timedelta(days=anchor.weekday())
    return start, start + timedelta(days=6)


def month_bounds(anchor: date) -> tuple[date, date]:
    start = anchor.replace(day=1)
    following = (start + timedelta(days=32)).replace(day=1)
    return start, following - timedelta(days=1)


def sum_nutrient(records: list[dict], key: str) -> dict:
    """화면 sum()과 같은 규칙: 값이 있는 기록만 더하고, 없거나 일부 누락이면 누락 수를 센다."""
    values, missing = [], 0
    for record in records:
        nutrient = (record.get('calculation') or {}).get('totals', {}).get(key)
        if nutrient and nutrient.get('known_total') is not None:
            values.append(float(nutrient['known_total']))
        if nutrient:
            missing += max(int(nutrient.get('missing_count') or 0), 0 if nutrient.get('status') == 'complete' else 1)
        else:
            missing += 1
    total = math.fsum(values) if values else None
    status = 'missing' if not values else 'partial' if missing else 'complete'
    return {'known_total': total, 'missing_count': missing, 'status': status, 'unit': NUTRIENTS.get(key, 'g')}


def period_summary(meals: list[dict], start: date, end: date, today: date) -> dict:
    if end < start:
        raise ValueError('기간을 확인하세요.')
    counted_end = min(end, today)
    days = []
    current = start
    while current <= counted_end:
        rows = [row for row in meals if row.get('date') == current.isoformat()]
        days.append({'date': current.isoformat(), 'meal_count': len(rows), 'energy': sum_nutrient(rows, 'energy')})
        current += timedelta(days=1)
    records = [row for row in meals if start.isoformat() <= row.get('date', '') <= counted_end.isoformat()]
    recorded = [day for day in days if day['meal_count']]
    totals = {key: sum_nutrient(records, key) for key in NUTRIENTS}
    averages = {}
    for key in NUTRIENTS:
        # 기록일 평균: 그 성분 값이 있는 기록일만 분모로 쓴다(결측일·미기록일 제외).
        known_days = [day['date'] for day in recorded
                      if sum_nutrient([row for row in records if row['date'] == day['date']], key)['known_total'] is not None]
        value = totals[key]['known_total']
        averages[key] = {'value': value / len(known_days) if value is not None and known_days else None,
                         'days': len(known_days), 'unit': NUTRIENTS[key]}
    return {
        'start': start.isoformat(), 'end': end.isoformat(), 'counted_until': counted_end.isoformat() if days else None,
        'days_in_period': len(days), 'recorded_days': len(recorded), 'meal_count': len(records),
        'totals': totals, 'recorded_day_averages': averages,
        'days': days,
        'note': '기록된 값만 합산합니다. 기록하지 않은 날은 0이 아니며 평균 분모에서 뺍니다. 실제 하루 섭취량과 다를 수 있습니다.',
    }
