"""식약처 API를 수동 호출해 분류별 한 페이지를 보존한다. 자동 갱신하지 않는다."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode
from urllib.request import urlopen


ENDPOINT = "https://apis.data.go.kr/1471000/FoodNtrCpntDbInfo03/getFoodNtrCpntDbInq03"
DEFAULT_CATEGORIES = ("밥류", "국 및 탕류", "면 및 만두류", "채소류", "과일류")


def load_key(path: Path) -> str:
    """키를 출력하지 않는다. Encoding/Decoding 두 형태 모두 요청 시 한 번 인코딩한다."""
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, sep, value = line.partition("=")
        if sep and name.strip() == "DATA_GO_KR_SERVICE_KEY":
            key = unquote(value.strip().strip("\"'"))
            if key and not any(char.isspace() for char in key):
                return key
            break
    raise ValueError(".env의 인증키가 없거나 형식이 올바르지 않습니다.")


def parse_response(raw: bytes) -> tuple[dict, list[dict]]:
    """응답 원문이나 서버 오류 메시지를 예외에 포함하지 않는다."""
    try:
        data = json.loads(raw)
        container = data.get("response", data)
        if str(container["header"]["resultCode"]) not in ("00", "0"):
            raise ValueError
        body = container["body"]
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list) or any(not isinstance(r, dict) for r in items):
            raise ValueError
        if int(body["totalCount"]) < len(items):
            raise ValueError
        return body, items
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError("API 응답이 정상 결과 또는 예상한 구조가 아닙니다.") from None


def fetch_page(key: str, category: str, page: int, size: int) -> tuple[bytes, dict, list[dict]]:
    params = {"serviceKey": key, "type": "json", "pageNo": page,
              "numOfRows": size, "FOOD_CAT1_NM": category}
    try:
        with urlopen(ENDPOINT + "?" + urlencode(params), timeout=40) as response:
            raw = response.read()
    except HTTPError as error:
        raise ValueError(f"API HTTP 오류 {error.code}. 활용 승인·키·호출 한도를 확인하세요.") from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("API 네트워크 연결에 실패했습니다.") from None
    for secret in (key, quote(key, safe=""), urlencode({"key": key}).split("=", 1)[1]):
        if secret.encode() in raw:
            raise ValueError("응답에 인증 정보가 포함되어 보존을 중단했습니다.")
    body, items = parse_response(raw)
    if len(items) > size or int(body["pageNo"]) != page:
        raise ValueError("응답 건수 또는 페이지가 요청과 다릅니다.")
    # 필터가 부분 일치일 수 있으므로 요청값과 실제 분류의 일치를 검증한다.
    if any(r.get("FOOD_CAT1_NM") != category for r in items):
        raise ValueError("분류 필터와 실제 응답 분류가 다릅니다.")
    return raw, body, items


def collect(key: str, categories: list[str], size: int, page: int, output: Path) -> dict:
    """명시된 분류별 한 페이지만 수집한다. 원본·요약 파일을 덮어쓰지 않는다."""
    if type(size) is not int or not 1 <= size <= 100:
        raise ValueError("분류별 요청 건수는 1~100이어야 합니다.")
    if type(page) is not int or page < 1 or not categories:
        raise ValueError("양의 페이지 번호와 하나 이상의 분류가 필요합니다.")
    if len(set(categories)) != len(categories) or any(not c.strip() for c in categories):
        raise ValueError("분류가 비어 있거나 중복되었습니다.")
    output.mkdir(parents=True, exist_ok=False)
    report = {"endpoint": ENDPOINT, "full_collection_complete": False,
              "collection_status": "in_progress", "requests": []}
    all_rows = []
    try:
        for index, category in enumerate(categories, 1):
            raw, body, items = fetch_page(key, category, page, size)
            if any(not r.get("FOOD_CD") for r in items):
                raise ValueError("응답에 식품코드가 없는 항목이 있습니다.")
            filename = f"category-{index:02d}-page-{page}.json"
            with (output / filename).open("xb") as f:
                f.write(raw)
            report["requests"].append({
                "category": category, "page": page, "requested_count": size,
                "received_count": len(items), "reported_total_count": int(body["totalCount"]),
                "raw_file": filename, "sha256": hashlib.sha256(raw).hexdigest(),
            })
            all_rows.extend(items)
        codes = [r["FOOD_CD"] for r in all_rows]
        report.update({
            "collection_status": "completed_requested_pages",
            "received_count": len(all_rows), "unique_food_codes": len(set(codes)),
            "duplicate_food_codes": len(codes) - len(set(codes)),
            "category_counts": dict(Counter(r["FOOD_CAT1_NM"] for r in all_rows)),
            "group_counts": dict(Counter(r.get("DB_GRP_NM") for r in all_rows)),
            "basis_counts": dict(Counter(r.get("SERVING_SIZE") for r in all_rows)),
            "update_date_counts": dict(Counter(r.get("UPDATE_DATE") for r in all_rows)),
        })
        if len(set(codes)) != len(codes):
            raise ValueError("중복 식품코드가 있습니다. 식품을 임의로 병합하지 않습니다.")
        return report
    except Exception:
        report["collection_status"] = "failed"
        raise
    finally:
        report["recorded_at_kst"] = datetime.now(timezone(timedelta(hours=9))).isoformat()
        with (output / "manifest.json").open("x", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", action="append", help="분류별 한 페이지. 생략하면 기본 5개 분류")
    parser.add_argument("--size", type=int, default=20)
    parser.add_argument("--page", type=int, default=1)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    stamp = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d-%H%M%S-%f")
    try:
        report = collect(load_key(root / ".env"), args.category or list(DEFAULT_CATEGORIES),
                         args.size, args.page, root / "data/raw" / f"mfds-api-{stamp}")
    except (ValueError, OSError, TypeError, KeyError):
        parser.exit(1, "수집 실패: 인증·네트워크·분류·응답 구조를 확인하세요. 비밀값은 출력하지 않습니다.\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
