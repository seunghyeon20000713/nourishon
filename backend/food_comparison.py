"""검색한 100g 기준 식품 안에서 성분 값을 비교한다. 개인 적합성 추천 아님."""
import heapq
import math
from backend.food_search import _normalize_name
from backend.prepare_food_sample import prepare_sample

FIELDS = {'protein': ('PROT', True), 'fiber': ('FIBTG', True), 'sodium': ('NAT', False)}


def compare_foods(rows, names, query: str, focus: str, offset: int, limit: int):
    keyword = _normalize_name(query)
    if not keyword or focus not in FIELDS:
        raise ValueError('검색어와 비교 성분을 확인하세요.')
    field, descending = FIELDS[focus]
    matches = ((index, row) for index, (row, name) in enumerate(zip(rows, names)) if row["NUT_CON_SRTR_QUA"] == "100g" and keyword in name)
    total = 0
    def ordered():
        nonlocal total
        for index, row in matches:
            total += 1
            raw = row[field]
            value = None if raw is None or (isinstance(raw, str) and not raw.strip()) else float(raw)
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError('성분 값 확인 필요')
            yield (value is None, (-value if descending else value) if value is not None else 0, index, row)
    # 검색 결과 전체에서 정렬하되 상위 페이지 범위만 메모리에 유지한다.
    selected = heapq.nsmallest(offset + limit, ordered(), key=lambda item: item[:3])[offset:]
    items = []
    for item in selected:
        food = prepare_sample([item[3]], intake_g=100, count=1)[0]
        food['source_row_number'] = item[2] + 1
        items.append(food)
    return {'query': query.strip(), 'focus': focus, 'basis': '100g', 'total': total,
            'offset': offset, 'limit': limit, 'items': items,
            'sort_note': '검색 결과 안에서 단백질·식이섬유는 많은 순, 나트륨은 적은 순입니다. 누락값은 뒤에 표시하며 0으로 채우지 않습니다.',
            'scope': '같은 검색어의 100g당 값 비교이며 권장 1회 제공량·개인 맞춤 적합성·건강 순위가 아닙니다.'}
