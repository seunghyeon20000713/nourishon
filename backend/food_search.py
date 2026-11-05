"""로컬 원본 JSON에서 100g 기준 식품을 검색하고 코드로 선택한다."""

import argparse
import json
import unicodedata
from pathlib import Path


def _normalize_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def search_foods(rows: list[dict], query: str) -> list[dict]:
    """이름 부분 일치로 검색한다. 빈 검색어는 거부하고 원본 순서를 유지한다."""
    if not isinstance(query, str):
        raise TypeError("검색어는 문자열이어야 합니다.")
    keyword = _normalize_name(query)
    if not keyword:
        raise ValueError("검색어를 입력해야 합니다.")
    return [dict(row) for row in rows
            if row["NUT_CON_SRTR_QUA"] == "100g"
            and keyword in _normalize_name(row["FOOD_NM"])]


def select_food(rows: list[dict], food_code: str) -> dict:
    """100g 기준 식품을 정확한 코드로 선택한다. 없거나 중복이면 오류 처리한다."""
    if not isinstance(food_code, str):
        raise TypeError("식품코드는 문자열이어야 합니다.")
    code = food_code.strip()
    if not code:
        raise ValueError("식품코드를 입력해야 합니다.")
    matches = [row for row in rows
               if row["NUT_CON_SRTR_QUA"] == "100g" and row["FOOD_CD"] == code]
    if not matches:
        raise LookupError("해당 코드의 100g 기준 식품이 없습니다.")
    if len(matches) > 1:
        raise ValueError("식품코드가 중복되어 하나를 선택할 수 없습니다.")
    return dict(matches[0])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--query", help="식품명 부분 검색")
    mode.add_argument("--food-code", help="정확한 식품코드 선택")
    args = parser.parse_args()
    try:
        rows = json.loads(args.source.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("원본은 식품 행의 목록이어야 합니다.")
        matches = (search_foods(rows, args.query) if args.query is not None
                   else [select_food(rows, args.food_code)])
        display = [{key: row[key] for key in (
            "FOOD_CD", "FOOD_NM", "NUT_CON_SRTR_QUA", "SRC_NM", "CRTR_YMD"
        )} for row in matches]
    except (OSError, ValueError, TypeError, LookupError) as error:
        parser.exit(1, f"오류: {error}\n")
    print(json.dumps(display, ensure_ascii=False, indent=2))
    print(f"검색·선택 결과: {len(display)}개")
