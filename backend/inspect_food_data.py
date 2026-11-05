"""공식 다운로드 JSON 표본을 검사하고 CSV와 요약을 생성한다. 네트워크 호출 없음."""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


def inspect_food_data(source: Path, columns: Path, output: Path) -> dict:
    raw = source.read_bytes()
    rows = json.loads(raw.decode("utf-8"))
    headers = json.loads(columns.read_text(encoding="utf-8"))["columList"]
    codes = [h["columCode"] for h in headers]
    if not isinstance(rows, list) or not rows:
        raise ValueError("원본은 비어 있지 않은 행 목록이어야 합니다.")
    if any(not isinstance(row, dict) or set(row) != set(codes) for row in rows):
        raise ValueError("원본 행의 열이 공식 열 정보와 일치하지 않습니다.")

    summary = {
        "source_file": source.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_encoding": "utf-8",
        "row_count": len(rows),
        "column_count": len(codes),
        "duplicate_food_codes": len(rows) - len({r["FOOD_CD"] for r in rows}),
        "basis_counts": dict(Counter(r["NUT_CON_SRTR_QUA"] for r in rows)),
        "source_counts": dict(Counter(r["SRC_NM"] for r in rows)),
        "reference_date_counts": dict(Counter(r["CRTR_YMD"] for r in rows)),
        "nutrients": {},
    }
    for key in ("ENERC", "PROT", "FATCE", "CHOCDF", "SUGAR", "FIBTG", "NAT"):
        counts = {"missing": 0, "zero": 0, "invalid_numeric": 0}
        for row in rows:
            value = row[key]
            if value is None or (isinstance(value, str) and not value.strip()):
                counts["missing"] += 1
                continue
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError):
                counts["invalid_numeric"] += 1
                continue
            if isinstance(value, bool) or not math.isfinite(number) or number < 0:
                counts["invalid_numeric"] += 1
            elif number == 0:
                counts["zero"] += 1
        summary["nutrients"][key] = counts

    output.mkdir(parents=True, exist_ok=True)
    # 공식 CSV 원본이 아닌, 원본 JSON에서 변환한 검사용 CSV다.
    # 빈 값을 0으로 바꾸지 않고 원본 JSON과 함께 보존한다.
    with (output / "food-sample.csv").open("x", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([h["columNm"] for h in headers])
        writer.writerows([[r[c] for c in codes] for r in rows])
    with (output / "inspection.json").open("x", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("columns", type=Path)
    parser.add_argument("output", type=Path, help="기존 결과 파일은 덮어쓰지 않음")
    args = parser.parse_args()
    print(json.dumps(inspect_food_data(args.source, args.columns, args.output),
                     ensure_ascii=False, indent=2))
