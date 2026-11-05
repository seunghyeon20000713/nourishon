import unittest

from backend.food_search import search_foods, select_food


class FoodSearchTests(unittest.TestCase):
    def setUp(self):
        # 실제 식품이 아닌 가상 데이터로 검색 규칙을 검증한다.
        self.rows = [
            {"FOOD_CD": "practice-1", "FOOD_NM": "연습용 두부", "NUT_CON_SRTR_QUA": "100g"},
            {"FOOD_CD": "practice-2", "FOOD_NM": "연습용 두부", "NUT_CON_SRTR_QUA": "100g"},
            {"FOOD_CD": "practice-3", "FOOD_NM": "연습용 두부 음료", "NUT_CON_SRTR_QUA": "100ml"},
            {"FOOD_CD": "practice-4", "FOOD_NM": "ＡＢＣ  연습용", "NUT_CON_SRTR_QUA": "100g"},
        ]

    def test_partial_search_preserves_order_and_excludes_volume(self):
        matches = search_foods(self.rows, " 두부 ")
        self.assertEqual([r["FOOD_CD"] for r in matches], ["practice-1", "practice-2"])

    def test_name_normalization(self):
        matches = search_foods(self.rows, "abc   연습용")
        self.assertEqual(matches[0]["FOOD_CD"], "practice-4")
        self.assertEqual(matches[0]["FOOD_NM"], "ＡＢＣ  연습용")

    def test_empty_or_invalid_query_is_rejected(self):
        for query, error in (("", ValueError), ("  \t", ValueError), (None, TypeError)):
            with self.subTest(query=query), self.assertRaises(error):
                search_foods(self.rows, query)

    def test_no_matches_returns_empty_list(self):
        self.assertEqual(search_foods(self.rows, "존재하지 않는 식품"), [])

    def test_code_selects_between_same_names_without_mutating_source(self):
        selected = select_food(self.rows, " practice-2 ")
        self.assertEqual(selected["FOOD_CD"], "practice-2")
        selected["FOOD_NM"] = "변경"
        self.assertEqual(self.rows[1]["FOOD_NM"], "연습용 두부")

    def test_missing_and_volume_codes_are_rejected(self):
        for code in ("unknown", "practice-3", "practice-10"):
            with self.subTest(code=code), self.assertRaises(LookupError):
                select_food(self.rows, code)

    def test_invalid_or_duplicate_code_is_rejected(self):
        for code, error in ((" ", ValueError), (None, TypeError)):
            with self.subTest(code=code), self.assertRaises(error):
                select_food(self.rows, code)
        with self.assertRaises(ValueError):
            select_food(self.rows + [self.rows[0]], "practice-1")
