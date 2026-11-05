"""수집한 API 원본을 기존 검색·계산용 형식으로 변환한다. 네트워크 호출 없음."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from backend.collect_food_api import parse_response
from backend.nutrition import calculate_nutrient


# 공공데이터포털 15127578의 FoodNtrCpntDbInfo03 Swagger 응답 명세, 2026-11-05 확인.
FIELD_MAP = {
    "AMT_NUM1": ("ENERC", "에너지", "kcal"),
    "AMT_NUM3": ("PROT", "단백질", "g"),
    "AMT_NUM4": ("FATCE", "지방", "g"),
    "AMT_NUM6": ("CHOCDF", "탄수화물", "g"),
    "AMT_NUM7": ("SUGAR", "당류", "g"),
    "AMT_NUM8": ("FIBTG", "식이섬유", "g"),
    "AMT_NUM13": ("NAT", "나트륨", "mg"),
}


def parse_nutrient_value(value) -> float | None:
    """빈 값은 None, 올바른 천 단위 쉼표만 제거한다. 특수 표기는 거부한다."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if type(value) not in (str, int, float):
        raise TypeError("영양성분은 숫자 또는 숫자 문자열이어야 합니다.")
    if isinstance(value, str):
        value = value.strip()
        if "," in value:
            if not re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?", value):
                raise ValueError("천 단위 구분 형식이 올바르지 않습니다.")
            value = value.replace(",", "")
    number = float(value)
    calculate_nutrient(number, 100)
    return number


def normalize_rows(rows: list[dict]) -> tuple[list[dict], dict]:
    foods, excluded, seen = [], [], set()
    counts = {target: {"missing": 0, "zero": 0} for target, _, _ in FIELD_MAP.values()}
    for index, row in enumerate(rows, 1):
        if row["SERVING_SIZE"] != "100g":
            excluded.append({"row_number": index, "food_code": row["FOOD_CD"],
                             "basis": row["SERVING_SIZE"], "reason": "100g 기준이 아님"})
            continue
        code, name = row["FOOD_CD"], row["FOOD_NM_KR"]
        if not isinstance(code, str) or not code.strip() or code in seen:
            raise ValueError("식품코드가 없거나 중복되었습니다.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("식품명이 없습니다.")
        seen.add(code)
        food = {
            "FOOD_CD": code, "FOOD_NM": name, "NUT_CON_SRTR_QUA": "100g",
            "SRC_NM": row["SUB_REF_NAME"], "DATA_PROD_NM": row["CRT_MTH_NM"],
            "CRT_YMD": row["RESEARCH_YMD"], "UPDATE_DATE": row["UPDATE_DATE"],
            "CRTR_YMD": None,  # 수정일을 기준일로 오인하지 않는다.
            "FOOD_CAT1_NM": row["FOOD_CAT1_NM"], "TYPE_NM": row["DB_GRP_NM"],
            "API_SOURCE_ROW_NUMBER": index,
        }
        for source, (target, _, _) in FIELD_MAP.items():
            value = row[source]  # 열 자체가 없으면 오류. 측정값 결측과 구분한다.
            number = parse_nutrient_value(value)
            if number is None:
                food[target] = None
                counts[target]["missing"] += 1
                continue
            food[target] = number
            counts[target]["zero"] += int(number == 0)
        foods.append(food)
    return foods, {"input_count": len(rows), "output_count": len(foods),
                   "excluded": excluded, "nutrients": counts,
                   "category_counts": dict(Counter(f["FOOD_CAT1_NM"] for f in foods))}


def normalize_collection(source: Path, output: Path) -> dict:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest["collection_status"] != "completed_requested_pages":
        raise ValueError("완료된 수집본만 변환할 수 있습니다.")
    rows, sources = [], []
    for request in manifest["requests"]:
        filename = request["raw_file"]
        if Path(filename).name != filename:
            raise ValueError("원본 파일명 형식이 잘못됐습니다.")
        raw = (source / filename).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != request["sha256"]:
            raise ValueError("원본 해시가 수집 기록과 다릅니다.")
        _, items = parse_response(raw)
        if len(items) != request["received_count"]:
            raise ValueError("원본 건수가 수집 기록과 다릅니다.")
        rows.extend(items)
        sources.append({"raw_file": filename, "sha256": digest})
    if len(rows) != manifest["received_count"]:
        raise ValueError("전체 수신 건수가 수집 기록과 다릅니다.")
    foods, report = normalize_rows(rows)
    report.update({"source_directory": source.name, "sources": sources,
                   "field_mapping_version": "mfds-15127578-2026-11-05"})
    output.mkdir(parents=True, exist_ok=False)
    for filename, content in (("foods.json", foods), ("report.json", report)):
        with (output / filename).open("x", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write("\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="수집 manifest와 원본 JSON이 있는 폴더")
    parser.add_argument("output", type=Path, help="새 가공 결과 폴더. 기존 폴더 덮어쓰기 금지")
    args = parser.parse_args()
    try:
        report = normalize_collection(args.source, args.output)
    except (OSError, ValueError, TypeError, LookupError, OverflowError):
        parser.exit(1, "변환 실패: 원본·수집 기록·필수 열·숫자·출력 경로를 확인하세요.\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
