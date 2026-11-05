import unittest

from backend.prepare_food_sample import NUTRIENTS, prepare_sample


def practice_row(code="practice-1", basis="100g"):
    """실제 식품 데이터가 아닌 테스트용 가상 행이다."""
    return {
        "FOOD_CD": code, "FOOD_NM": "연습용 식품",
        "NUT_CON_SRTR_QUA": basis, "SRC_NM": "연습용",
        "CRTR_YMD": "2026-11-05", "DATA_PROD_NM": "연습용",
        **{key: "200" for key in NUTRIENTS},
    }


class FoodSampleTests(unittest.TestCase):
    def test_selection_skips_volume_basis_and_preserves_order(self):
        rows = [practice_row("volume", "100ml"), practice_row("first"), practice_row("second")]
        foods = prepare_sample(rows, count=2)
        self.assertEqual([f["food_code"] for f in foods], ["first", "second"])
        self.assertEqual([f["source_row_number"] for f in foods], [2, 3])
        self.assertEqual(foods[0]["nutrients"]["energy"]["consumed"], 300)

    def test_missing_and_zero_are_distinct_and_units_are_preserved(self):
        row = practice_row()
        row.update(FIBTG="", SUGAR="0.00", NAT="10", PROT=None)
        nutrients = prepare_sample([row], count=1)[0]["nutrients"]
        self.assertIsNone(nutrients["fiber"]["consumed"])
        self.assertEqual(nutrients["fiber"]["status"], "missing")
        self.assertIsNone(nutrients["protein"]["per_100g"])
        self.assertEqual(nutrients["sugar"]["consumed"], 0)
        self.assertEqual(nutrients["sugar"]["status"], "available")
        self.assertEqual(nutrients["sodium"]["unit"], "mg")
        self.assertEqual(nutrients["sodium"]["consumed"], 15)

    def test_invalid_values_are_not_silently_replaced(self):
        for value in ("미검출", "NaN", "inf", "-1", True):
            with self.subTest(value=value):
                row = practice_row()
                row["ENERC"] = value
                with self.assertRaises((ValueError, TypeError)):
                    prepare_sample([row], count=1)

    def test_invalid_intake_is_rejected_even_when_all_nutrients_missing(self):
        row = practice_row()
        row.update({key: None for key in NUTRIENTS})
        with self.assertRaises(ValueError):
            prepare_sample([row], intake_g=-1, count=1)
        self.assertIsNone(prepare_sample([row], intake_g=0, count=1)[0]["nutrients"]["energy"]["consumed"])

    def test_insufficient_or_duplicate_foods_are_rejected(self):
        for rows in ([], [practice_row()], [practice_row(), practice_row()]):
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    prepare_sample(rows, count=2)

    def test_missing_column_is_not_treated_as_missing_measurement(self):
        row = practice_row()
        del row["FIBTG"]
        with self.assertRaises(KeyError):
            prepare_sample([row], count=1)
