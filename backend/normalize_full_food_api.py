"""전체 수집본을 페이지별로 정제한다. 단위 미지원·검토 대상은 계산 목록과 분리한다."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from backend.collect_all_food_api import validate_page
from backend.normalize_food_api import FIELD_MAP, normalize_rows


def review_reasons(food: dict) -> list[str]:
    """프로젝트의 보수적 데이터 점검 규칙이다. 공식 영양 기준이나 진단 기준이 아니다."""
    reasons = []
    for target, _, unit in FIELD_MAP.values():
        number = food[target]
        if number is None:
            continue
        if unit == "g" and number > 100:
            reasons.append(f"{target}: 100g 기준 성분이 100g 초과")
        if target == "NAT" and number > 100000:
            reasons.append("NAT: 100g 기준 나트륨이 100000mg 초과")
        if target == "ENERC" and number > 1000:
            reasons.append("ENERC: 프로젝트 검토 임계값 1000kcal/100g 초과")
    return reasons


def normalize_full(source: Path, output: Path) -> dict:
    manifest_bytes = (source / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("collection_status") != "completed" or not manifest.get("full_collection_complete"):
        raise ValueError("전체 수집 완료가 검증된 원본만 사용할 수 있습니다.")
    total = manifest["reported_total_count"]
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "in_progress", "source_directory": source.name,
              "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "input_count": 0, "output_count": 0, "excluded_basis_count": 0,
              "quarantine_count": 0, "mapping_version": "mfds-15127578-2026-11-05",
              "review_rules_version": "nourishon-sanity-v1"}
    seen, categories, bases, reasons, groups = set(), Counter(), Counter(), Counter(), Counter()
    counts = {target: {"missing": 0, "zero": 0} for target, _, _ in FIELD_MAP.values()}
    comma_counts = Counter()
    temp = output / "foods.json.tmp"
    try:
        with temp.open("x", encoding="utf-8") as foods_file, \
                (output / "excluded-basis.jsonl").open("x", encoding="utf-8") as excluded_file, \
                (output / "quarantine.jsonl").open("x", encoding="utf-8") as quarantine_file:
            foods_file.write("[\n")
            first = True
            for page, request in enumerate(manifest["requests"], 1):
                filename = request["raw_file"]
                if request["page"] != page or filename != f"page-{page:05d}.json":
                    raise ValueError("원본 페이지 기록이 연속되지 않습니다.")
                raw = (source / filename).read_bytes()
                if hashlib.sha256(raw).hexdigest() != request["sha256"]:
                    raise ValueError("원본 파일 해시가 수집 기록과 다릅니다.")
                _, rows = validate_page(raw, page, manifest["page_size"], total)
                if len(rows) != request["received_count"]:
                    raise ValueError("원본 페이지 건수가 기록과 다릅니다.")
                for local_index, row in enumerate(rows, 1):
                    report["input_count"] += 1
                    code = row["FOOD_CD"]
                    if code in seen:
                        raise ValueError("전체 원본 식품코드가 중복되었습니다.")
                    seen.add(code)
                    basis = row["SERVING_SIZE"]
                    bases[basis] += 1
                    origin = {"food_code": code, "source_file": filename,
                              "source_file_row": local_index, "basis": basis}
                    if basis != "100g":
                        report["excluded_basis_count"] += 1
                        excluded_file.write(json.dumps(origin, ensure_ascii=False) + "\n")
                        continue
                    try:
                        foods, _ = normalize_rows([row])
                        food = foods[0]
                        flags = review_reasons(food)
                    except (ValueError, TypeError, KeyError, OverflowError):
                        flags = ["필수 열·식품명·숫자 형식 검토 필요"]
                    if flags:
                        report["quarantine_count"] += 1
                        reasons.update(flags)
                        origin["reasons"] = flags
                        quarantine_file.write(json.dumps(origin, ensure_ascii=False) + "\n")
                        continue
                    food["API_SOURCE_ROW_NUMBER"] = report["input_count"]
                    food["API_SOURCE_FILE"] = filename
                    food["API_SOURCE_FILE_ROW"] = local_index
                    for field, (target, _, _) in FIELD_MAP.items():
                        counts[target]["missing"] += int(food[target] is None)
                        counts[target]["zero"] += int(food[target] == 0)
                        if isinstance(row[field], str) and "," in row[field]:
                            comma_counts[target] += 1
                    if not first:
                        foods_file.write(",\n")
                    foods_file.write(json.dumps(food, ensure_ascii=False, allow_nan=False))
                    first = False
                    report["output_count"] += 1
                    categories[food["FOOD_CAT1_NM"]] += 1
                    groups[food["TYPE_NM"]] += 1
            foods_file.write("\n]\n")
        if report["input_count"] != total or len(seen) != total:
            raise ValueError("원본 전체 건수와 처리 건수가 다릅니다.")
        if sum(report[k] for k in ("output_count", "excluded_basis_count", "quarantine_count")) != total:
            raise ValueError("변환·제외·검토 건수의 합이 원본과 다릅니다.")
        temp.rename(output / "foods.json")
        report.update({"status": "completed", "nutrients": counts,
                       "comma_conversions": dict(comma_counts), "basis_counts": dict(bases),
                       "review_reason_counts": dict(reasons), "category_counts": dict(categories),
                       "group_counts": dict(groups)})
        return report
    except BaseException:
        report["status"] = "failed"
        raise
    finally:
        with (output / "report.json").open("x", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        report = normalize_full(args.source, args.output)
    except (OSError, ValueError, TypeError, LookupError, OverflowError):
        parser.exit(1, "전체 정제 실패: 수집 기록·원본·출력 경로를 확인하세요.\n")
    print(json.dumps({k: report[k] for k in ("status", "input_count", "output_count",
                     "excluded_basis_count", "quarantine_count", "review_reason_counts")},
                     ensure_ascii=False, indent=2))
