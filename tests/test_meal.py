import unittest

from backend.meal import calculate_meal, format_meal
from backend.prepare_food_sample import NUTRIENTS


def practice_row(code, energy):
    return {
        **{key: "0" for key in NUTRIENTS},
        "FOOD_CD": code, "FOOD_NM": "연습용 식품", "NUT_CON_SRTR_QUA": "100g",
        "SRC_NM": "가상 자료", "CRTR_YMD": "2026-11-05", "DATA_PROD_NM": "연습용",
        "ENERC": energy,
    }


class MealTests(unittest.TestCase):
    def setUp(self):
        self.rows = [practice_row("practice-1", "200"), practice_row("practice-2", "100")]
        self.entries = [{"food_code": "practice-1", "intake_g": 150},
                        {"food_code": "practice-2", "intake_g": 50}]

    def test_multiple_intakes_and_source_rows(self):
        self.rows[0]["NAT"] = "10"
        self.rows[1]["NAT"] = "20"
        meal = calculate_meal(self.rows, self.entries)
        self.assertEqual(meal["totals"]["energy"]["known_total"], 350)
        self.assertEqual(meal["totals"]["sodium"]["known_total"], 25)
        self.assertEqual(meal["totals"]["sodium"]["unit"], "mg")
        self.assertEqual([f["source_row_number"] for f in meal["foods"]], [1, 2])

    def test_partial_missing_is_marked_without_replacing_with_zero(self):
        self.rows[0]["FIBTG"] = ""
        self.rows[1]["FIBTG"] = "2"
        meal = calculate_meal(self.rows, self.entries)
        self.assertEqual(meal["totals"]["fiber"], {
            "unit": "g", "known_total": 1, "missing_count": 1, "status": "partial"})
        self.assertIn("확인된 값만 합산, 누락 1개", format_meal(meal))

    def test_all_missing_and_real_zero_are_distinct(self):
        for row in self.rows:
            row["FIBTG"] = None
        meal = calculate_meal(self.rows, self.entries)
        self.assertIsNone(meal["totals"]["fiber"]["known_total"])
        self.assertEqual(meal["totals"]["fiber"]["missing_count"], 2)
        self.assertEqual(meal["totals"]["sugar"]["known_total"], 0)
        self.assertEqual(meal["totals"]["sugar"]["status"], "complete")
        self.assertIn("식이섬유: 정보 없음 (누락 2개)", format_meal(meal))

    def test_zero_intake_and_repeat_entries(self):
        entries = [{"food_code": "practice-1", "intake_g": 0},
                   {"food_code": "practice-1", "intake_g": 50}]
        self.assertEqual(calculate_meal(self.rows, entries)["totals"]["energy"]["known_total"], 100)

    def test_empty_invalid_intake_or_unknown_code_is_rejected(self):
        cases = [[], [{"food_code": "unknown", "intake_g": 100}],
                 [{"food_code": "practice-1", "intake_g": -1}],
                 [{"food_code": "practice-1", "intake_g": float("nan")}]]
        for entries in cases:
            with self.subTest(entries=entries), self.assertRaises((ValueError, LookupError)):
                calculate_meal(self.rows, entries)

    def test_total_overflow_is_rejected(self):
        for row in self.rows:
            row["ENERC"] = "1e308"
        entries = [{"food_code": r["FOOD_CD"], "intake_g": 100} for r in self.rows]
        with self.assertRaises(ValueError):
            calculate_meal(self.rows, entries)
