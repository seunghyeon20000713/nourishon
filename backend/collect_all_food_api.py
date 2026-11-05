"""분류 필터 없이 API 전체 페이지를 수동 수집하고 검증한다. 중단 시 이어받기 가능."""

import argparse
import hashlib
import json
import math
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path

from backend.collect_food_api import ENDPOINT, fetch_page, load_key, parse_response


def save_manifest(path: Path, data: dict) -> None:
    data["recorded_at_kst"] = datetime.now(timezone(timedelta(hours=9))).isoformat()
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    temp.replace(path)


def validate_page(raw: bytes, page: int, size: int, total: int | None) -> tuple[int, list[dict]]:
    body, items = parse_response(raw)
    current_total = int(body["totalCount"])
    if total is not None and current_total != total:
        raise ValueError("수집 중 전체 건수가 변했습니다. 동일 시점 전체 수집으로 확정할 수 없습니다.")
    expected = min(size, max(0, current_total - (page - 1) * size))
    if int(body["pageNo"]) != page or len(items) != expected:
        raise ValueError("페이지 번호 또는 실제 수신 건수가 예상과 다릅니다.")
    if any(not isinstance(r.get("FOOD_CD"), str) or not r["FOOD_CD"].strip() for r in items):
        raise ValueError("식품코드가 없는 항목이 있습니다.")
    return current_total, items


def collect_all(key: str, output: Path, size: int = 500, delay: float = 0.2, workers: int = 1) -> dict:
    if type(size) is not int or not 1 <= size <= 500:
        raise ValueError("페이지당 건수는 1~500이어야 합니다.")
    if type(workers) is not int or not 1 <= workers <= 3:
        raise ValueError("동시 요청 수는 1~3이어야 합니다.")
    if not math.isfinite(delay) or delay < 0:
        raise ValueError("호출 간격이 올바르지 않습니다.")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        report = json.loads(manifest_path.read_text(encoding="utf-8"))
        if report.get("endpoint") != ENDPOINT or report.get("page_size") != size or report.get("filters") != {}:
            raise ValueError("이어받기 설정이 기존 수집과 다릅니다.")
    else:
        if any(output.iterdir()):
            raise ValueError("수집 기록이 없는 기존 폴더는 사용할 수 없습니다.")
        report = {"endpoint": ENDPOINT, "filters": {}, "page_size": size,
                  "full_collection_complete": False, "collection_status": "in_progress",
                  "reported_total_count": None, "requests": []}
    total = report["reported_total_count"]
    seen, received = set(), 0
    groups, bases, categories = Counter(), Counter(), Counter()
    executor = ThreadPoolExecutor(max_workers=workers)
    pending = {}

    def download(page):
        for attempt in range(3):
            try:
                raw, _, _ = fetch_page(key, None, page, size)
                return raw
            except ValueError:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)

    def account(items):
        nonlocal received
        for row in items:
            code = row["FOOD_CD"]
            if code in seen:
                raise ValueError("페이지 간 중복 식품코드가 있어 완료로 확정하지 않습니다.")
            seen.add(code)
            groups[row.get("DB_GRP_NM")] += 1
            bases[row.get("SERVING_SIZE")] += 1
            categories[row.get("FOOD_CAT1_NM")] += 1
        received += len(items)

    try:
        for page, entry in enumerate(report["requests"], 1):
            if entry["page"] != page or entry["raw_file"] != f"page-{page:05d}.json":
                raise ValueError("이어받기 페이지 기록이 연속되지 않습니다.")
            raw = (output / entry["raw_file"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError("이어받기 원본 해시가 다릅니다.")
            total, items = validate_page(raw, page, size, total)
            if len(items) != entry["received_count"]:
                raise ValueError("이어받기 원본 건수가 기록과 다릅니다.")
            account(items)
        report["collection_status"] = "in_progress"
        report["full_collection_complete"] = False
        page = len(report["requests"]) + 1
        while total is None or received < total:
            filename = f"page-{page:05d}.json"
            target = output / filename
            # 파일 저장 직후 중단됐다면 기록되지 않은 해당 페이지를 검증해 복구한다.
            if target.exists():
                raw = target.read_bytes()
            else:
                last = page if total is None else min(math.ceil(total / size), page + workers - 1)
                for candidate in range(page, last + 1):
                    if candidate not in pending and not (output / f"page-{candidate:05d}.json").exists():
                        pending[candidate] = executor.submit(download, candidate)
                raw = pending.pop(page).result()
            total, items = validate_page(raw, page, size, total)
            account(items)
            if not target.exists():
                with target.open("xb") as f:
                    f.write(raw)
            report["reported_total_count"] = total
            report["requests"].append({"page": page, "raw_file": filename,
                "received_count": len(items), "sha256": hashlib.sha256(raw).hexdigest()})
            report["received_count"] = received
            save_manifest(manifest_path, report)
            print(f"수집 {page}/{math.ceil(total / size)}페이지: {received:,}/{total:,}개", flush=True)
            page += 1
            time.sleep(delay)
        if received != total or len(seen) != total:
            raise ValueError("전체 건수·수신 건수·고유 코드 수가 일치하지 않습니다.")
        report.update({"collection_status": "completed", "full_collection_complete": True,
                       "received_count": received, "unique_food_codes": len(seen),
                       "duplicate_food_codes": 0, "group_counts": dict(groups),
                       "basis_counts": dict(bases), "category_counts": dict(categories)})
        return report
    except BaseException:
        report["collection_status"] = "interrupted_or_failed"
        report["full_collection_complete"] = False
        raise
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
        save_manifest(manifest_path, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="새 수집 또는 이어받을 폴더")
    parser.add_argument("--size", type=int, default=500)
    parser.add_argument("--workers", type=int, default=3, help="동시 요청 수 1~3")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        result = collect_all(load_key(root / ".env"), args.output, args.size, workers=args.workers)
    except KeyboardInterrupt:
        parser.exit(130, "수집을 중단했습니다. 같은 명령을 실행하면 검증 후 이어받습니다.\n")
    except (OSError, ValueError, TypeError, KeyError):
        parser.exit(1, "전체 수집 중단: 인증·연결·페이지·건수·중복·수집 기록을 확인하세요. 원문과 비밀값은 출력하지 않습니다.\n")
    print(f'전체 수집 검증 완료: {result["received_count"]:,}개, 고유 코드 {result["unique_food_codes"]:,}개')
