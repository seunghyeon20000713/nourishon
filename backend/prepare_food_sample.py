"""공식 JSON 표본에서 100g 기준 식품을 골라 섭취량을 계산한다."""

import argparse
import hashlib
import json
from pathlib import Path

from backend.nutrition import calculate_nutrient


NUTRIENTS = {
    "ENERC": ("energy", "kcal"),
    "PROT": ("protein", "g"),
    "FATCE": ("fat", "g"),
    "CHOCDF": ("carbohydrate", "g"),
    "SUGAR": ("sugar", "g"),
    "FIBTG": ("fiber", "g"),
    "NAT": ("sodium", "mg"),
}


def prepare_sample(rows: list[dict], intake_g: float = 150, count: int = 5) -> list[dict]:
    """원본 순서에서 100g 기준 첫 count개를 선택한다. 결측은 None으로 보존한다."""
    calculate_nutrient(0, intake_g)  # 모든 성분이 결측이어도 섭취량은 먼저 검증한다.
    if type(count) is not int or count < 1:
        raise ValueError("선택 개수는 1 이상의 정수여야 합니다.")
    foods = []
    seen = set()
    for row_number, row in enumerate(rows, 1):
        if row["NUT_CON_SRTR_QUA"] != "100g":
            continue
        code = row["FOOD_CD"]
        if not isinstance(code, str) or not code.strip() or code in seen:
            raise ValueError("선택 식품코드가 없거나 중복되었습니다.")
        seen.add(code)
        nutrients = {}
        for source_key, (name, unit) in NUTRIENTS.items():
            raw_value = row[source_key]  # 열 자체가 없으면 결측으로 숨기지 않고 오류 처리한다.
            missing = raw_value is None or (
                isinstance(raw_value, str) and not raw_value.strip()
            )
            per_100g = None
            consumed = None
            if not missing:
                if type(raw_value) not in (str, int, float):
                    raise TypeError(f"{source_key}: 숫자 또는 숫자 문자열이어야 합니다.")
                per_100g = float(raw_value)
                consumed = calculate_nutrient(per_100g, intake_g)
            nutrients[name] = {
                "unit": unit,
                "per_100g": per_100g,
                "consumed": consumed,
                "status": "missing" if missing else "available",
            }
        foods.append({
            "food_code": code,
            "food_name": row["FOOD_NM"],
            "source_row_number": row_number,
            "basis": "100g",
            "intake_g": intake_g,
            "source_name": row["SRC_NM"],
            "reference_date": row["CRTR_YMD"],
            "created_date": row.get("CRT_YMD"),
            "updated_date": row.get("UPDATE_DATE"),
            "generation_method": row["DATA_PROD_NM"],
            "nutrients": nutrients,
        })
        if len(foods) == count:
            return foods
    raise ValueError(f"100g 기준 식품이 {count}개보다 적습니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    foods = prepare_sample(json.loads(raw.decode("utf-8")))
    result = {
        "source_file": args.source.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "selection_rule": "원본 순서에서 기준량이 정확히 100g인 첫 5개; 추천 아님",
        "foods": foods,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(f"{len(foods)}개 식품의 150g 계산 결과 저장: {args.output}")
