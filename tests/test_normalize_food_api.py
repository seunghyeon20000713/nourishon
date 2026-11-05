import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from backend.food_search import search_foods
from backend.meal import calculate_meal
from backend.normalize_food_api import normalize_collection, normalize_rows


def practice_row():
    return {"FOOD_CD": "practice-1", "FOOD_NM_KR": "연습용 음식", "SERVING_SIZE": "100g",
            "SUB_REF_NAME": "가상 자료", "CRT_MTH_NM": "연습용", "RESEARCH_YMD": "2026-01-01",
            "UPDATE_DATE": "2026-02-01", "FOOD_CAT1_NM": "연습분류", "DB_GRP_NM": "음식",
            "AMT_NUM1": "200", "AMT_NUM3": "10", "AMT_NUM4": "5", "AMT_NUM6": "30",
            "AMT_NUM7": "0.00", "AMT_NUM8": "", "AMT_NUM13": "100"}


class NormalizeFoodApiTests(unittest.TestCase):
    def test_mapping_units_dates_and_search_meal_connection(self):
        foods, report = normalize_rows([practice_row()])
        food = search_foods(foods, "연습용")[0]
        self.assertEqual([food[k] for k in ("ENERC", "PROT", "FATCE", "CHOCDF", "SUGAR", "FIBTG", "NAT")],
                         [200, 10, 5, 30, 0, None, 100])
        meal = calculate_meal(foods, [{"food_code": food["FOOD_CD"], "intake_g": 150}])
        self.assertEqual(meal["totals"]["sodium"]["known_total"], 150)
        self.assertEqual(meal["totals"]["sodium"]["unit"], "mg")
        self.assertEqual(meal["totals"]["energy"]["known_total"], 300)
        self.assertEqual(meal["foods"][0]["updated_date"], "2026-02-01")
        self.assertIsNone(meal["foods"][0]["reference_date"])
        self.assertEqual(report["nutrients"]["FIBTG"]["missing"], 1)

    def test_zero_and_missing_are_distinct(self):
        foods, report = normalize_rows([practice_row()])
        self.assertEqual(foods[0]["SUGAR"], 0)
        self.assertIsNone(foods[0]["FIBTG"])
        self.assertEqual(report["nutrients"]["SUGAR"], {"missing": 0, "zero": 1})

    def test_unsupported_bases_are_reported_not_converted(self):
        for basis in ("100ml", "1회", None):
            row = practice_row()
            row["SERVING_SIZE"] = basis
            foods, report = normalize_rows([row])
            self.assertEqual(foods, [])
            self.assertEqual(report["excluded"][0]["basis"], basis)

    def test_bad_values_missing_columns_and_duplicate_codes_are_rejected(self):
        for value in ("미검출", "NaN", "inf", "-1", True):
            row = practice_row()
            row["AMT_NUM3"] = value
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                normalize_rows([row])
        row = practice_row()
        del row["AMT_NUM8"]
        with self.assertRaises(KeyError):
            normalize_rows([row])
        with self.assertRaises(ValueError):
            normalize_rows([practice_row(), practice_row()])

    def test_collection_integrity_and_output_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = json.dumps({"header": {"resultCode": "00"}, "body": {
                "totalCount": 1, "items": [practice_row()]}}).encode()
            (root / "page.json").write_bytes(raw)
            manifest = {"collection_status": "completed_requested_pages", "received_count": 1,
                        "requests": [{"raw_file": "page.json", "received_count": 1,
                                      "sha256": hashlib.sha256(raw).hexdigest()}]}
            (root / "manifest.json").write_text(json.dumps(manifest))
            normalize_collection(root, root / "output")
            self.assertEqual(len(json.loads((root / "output/foods.json").read_text())), 1)
            with self.assertRaises(FileExistsError):
                normalize_collection(root, root / "output")
            (root / "page.json").write_bytes(b'changed')
            with self.assertRaises(ValueError):
                normalize_collection(root, root / "other")

    def test_incomplete_collection_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text('{"collection_status":"failed"}')
            with self.assertRaises(ValueError):
                normalize_collection(root, root / "output")
