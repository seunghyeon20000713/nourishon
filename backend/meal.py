"""로컬 식품코드와 섭취량으로 한 끼 합계를 계산한다. 기록을 저장하지 않는다."""

import argparse
import json
import math
from pathlib import Path

from backend.food_search import select_food
from backend.prepare_food_sample import NUTRIENTS, prepare_sample


LABELS = {
    "energy": "열량", "protein": "단백질", "fat": "지방",
    "carbohydrate": "탄수화물", "sugar": "당류", "fiber": "식이섬유",
    "sodium": "나트륨",
}


def calculate_meal(rows: list[dict], entries: list[dict]) -> dict:
    """각 항목은 food_code와 intake_g를 가진다. 결측을 0으로 대체하지 않는다."""
    if not entries:
        raise ValueError("한 끼에 포함할 음식을 하나 이상 입력해야 합니다.")
    foods = []
    for entry in entries:
        row = select_food(rows, entry["food_code"])
        food = prepare_sample([row], intake_g=entry["intake_g"], count=1)[0]
        food["source_row_number"] = next(
            index for index, original in enumerate(rows, 1)
            if original["FOOD_CD"] == food["food_code"]
            and original["NUT_CON_SRTR_QUA"] == "100g"
        )
        foods.append(food)

    totals = {}
    for name, unit in NUTRIENTS.values():
        known = [f["nutrients"][name]["consumed"] for f in foods
                 if f["nutrients"][name]["consumed"] is not None]
        missing_count = len(foods) - len(known)
        try:
            total = math.fsum(known) if known else None
        except OverflowError:
            raise ValueError("한 끼 합계가 계산 가능한 범위를 넘었습니다.") from None
        if total is not None and not math.isfinite(total):
            raise ValueError("한 끼 합계가 계산 가능한 범위를 넘었습니다.")
        totals[name] = {
            "unit": unit,
            "known_total": total,
            "missing_count": missing_count,
            "status": "missing" if not known else ("partial" if missing_count else "complete"),
        }
    return {"foods": foods, "totals": totals}


def format_meal(meal: dict) -> str:
    """계산값은 유지하고 터미널 표시만 소수 셋째 자리까지 반올림한다."""
    lines = ["입력한 음식 (계산 예시이며 권장 식사량이 아닙니다)"]
    for index, food in enumerate(meal["foods"], 1):
        lines.append(f'{index}. {food["food_name"]} — {food["intake_g"]:g}g')
    lines.append("\n한 끼 영양 합계")
    for name, nutrient in meal["totals"].items():
        if nutrient["known_total"] is None:
            text = f'정보 없음 (누락 {nutrient["missing_count"]}개)'
        else:
            value = f'{nutrient["known_total"]:.3f}'.rstrip("0").rstrip(".")
            text = f'{value} {nutrient["unit"]}'
            if nutrient["status"] == "partial":
                text += f' (확인된 값만 합산, 누락 {nutrient["missing_count"]}개)'
        lines.append(f"{LABELS[name]}: {text}")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--food", nargs=2, action="append", required=True,
                        metavar=("식품코드", "섭취량_g"))
    args = parser.parse_args()
    try:
        rows = json.loads(args.source.read_text(encoding="utf-8"))
        entries = [{"food_code": code, "intake_g": float(grams)} for code, grams in args.food]
        result = calculate_meal(rows, entries)
    except (OSError, ValueError, TypeError, LookupError, OverflowError) as error:
        parser.exit(1, f"오류: {error}\n")
    print(format_meal(result))
