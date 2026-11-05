import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from backend.normalize_food_api import normalize_rows, parse_nutrient_value
from backend.normalize_full_food_api import normalize_full


def practice_row(code="practice-1"):
    return {"FOOD_CD": code, "FOOD_NM_KR": "연습용 식품", "SERVING_SIZE": "100g",
            "SUB_REF_NAME": "가상", "CRT_MTH_NM": "연습용", "RESEARCH_YMD": "2026-01-01",
            "UPDATE_DATE": "2026-02-01", "FOOD_CAT1_NM": "가상분류", "DB_GRP_NM": "음식",
            "AMT_NUM1": "200", "AMT_NUM3": "10", "AMT_NUM4": "5", "AMT_NUM6": "30",
            "AMT_NUM7": "0", "AMT_NUM8": "", "AMT_NUM13": "1,315.000"}


def write_collection(root, rows, size=2):
    requests = []
    for start in range(0, len(rows), size):
        page = start // size + 1
        items = rows[start:start + size]
        raw = json.dumps({"header": {"resultCode": "00"}, "body": {
            "pageNo": page, "totalCount": len(rows), "items": items}}).encode()
        name = f"page-{page:05d}.json"
        (root / name).write_bytes(raw)
        requests.append({"page": page, "raw_file": name, "received_count": len(items),
                         "sha256": hashlib.sha256(raw).hexdigest()})
    (root / "manifest.json").write_text(json.dumps({"collection_status": "completed",
        "full_collection_complete": True, "reported_total_count": len(rows),
        "page_size": size, "requests": requests}))


class NormalizeFullFoodApiTests(unittest.TestCase):
    def test_valid_grouped_number_keeps_value_and_unit(self):
        for text, expected in (("1,315.000", 1315), ("10,000", 10000), ("0.00", 0)):
            self.assertEqual(parse_nutrient_value(text), expected)
        foods, _ = normalize_rows([practice_row()])
        self.assertEqual(foods[0]["NAT"], 1315)

    def test_invalid_grouping_is_not_silently_corrected(self):
        for text in ("1,23", "1,2,3", "1,000,00", "미검출", "NaN"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_nutrient_value(text)

    def test_full_stream_separates_basis_review_and_missing(self):
        rows = [practice_row(f"practice-{i}") for i in range(3)]
        rows[1]["SERVING_SIZE"] = "100mL"
        rows[2]["AMT_NUM1"] = "2,000"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_collection(root, rows)
            output = root / "output"
            report = normalize_full(root, output)
            self.assertEqual([report[k] for k in ("input_count", "output_count", "excluded_basis_count", "quarantine_count")], [3, 1, 1, 1])
            foods = json.loads((output / "foods.json").read_text())
            self.assertEqual(foods[0]["API_SOURCE_FILE"], "page-00001.json")
            self.assertIsNone(foods[0]["FIBTG"])
            self.assertEqual(report["comma_conversions"], {"NAT": 1})
            self.assertEqual(report["nutrients"]["SUGAR"]["zero"], 1)
            self.assertEqual(len((output / "excluded-basis.jsonl").read_text().splitlines()), 1)
            self.assertEqual(len((output / "quarantine.jsonl").read_text().splitlines()), 1)
            with self.assertRaises(FileExistsError):
                normalize_full(root, output)

    def test_bad_numeric_and_mass_values_go_to_review(self):
        rows = [practice_row(f"practice-{i}") for i in range(3)]
        rows[0]["AMT_NUM13"] = "100,001"
        rows[1]["AMT_NUM3"] = "101"
        rows[2]["AMT_NUM8"] = "미검출"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_collection(root, rows)
            report = normalize_full(root, root / "output")
            self.assertEqual(report["quarantine_count"], 3)
            self.assertEqual(json.loads((root / "output/foods.json").read_text()), [])

    def test_tampered_raw_does_not_publish_partial_foods(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_collection(root, [practice_row()])
            (root / "page-00001.json").write_bytes(b'changed')
            with self.assertRaises(ValueError):
                normalize_full(root, root / "output")
            self.assertFalse((root / "output/foods.json").exists())
            self.assertEqual(json.loads((root / "output/report.json").read_text())["status"], "failed")

    def test_duplicate_codes_across_pages_block_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_collection(root, [practice_row(), practice_row()], size=1)
            with self.assertRaises(ValueError):
                normalize_full(root, root / "output")
            self.assertFalse((root / "output/foods.json").exists())
