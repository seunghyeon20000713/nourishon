import unittest

from backend.nutrition import calculate_nutrient


class NutritionTests(unittest.TestCase):
    """실제 식품이 아닌 연습용 값으로 계산 계약을 검증한다."""

    def test_normal_and_fractional_intake(self):
        for per_100g, intake_g, expected in (
            (200, 150, 300.0),
            (200, 100, 200.0),
            (12.5, 30.5, 3.8125),
        ):
            with self.subTest(per_100g=per_100g, intake_g=intake_g):
                self.assertAlmostEqual(calculate_nutrient(per_100g, intake_g), expected)

    def test_zero_is_valid(self):
        for args in ((200, 0), (0, 150), (0, 0)):
            with self.subTest(args=args):
                self.assertEqual(calculate_nutrient(*args), 0.0)

    def test_negative_values_are_rejected(self):
        for args in ((-200, 150), (200, -150), (-200, -150), (-1, 0)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    calculate_nutrient(*args)

    def test_invalid_types_are_rejected_in_both_inputs(self):
        for value in (None, "200", "", True, False, [], {}):
            for args in ((value, 150), (200, value)):
                with self.subTest(args=args):
                    with self.assertRaises(TypeError):
                        calculate_nutrient(*args)

    def test_nonfinite_values_are_rejected_in_both_inputs(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            for args in ((value, 150), (200, value)):
                with self.subTest(args=args):
                    with self.assertRaises(ValueError):
                        calculate_nutrient(*args)

    def test_out_of_range_inputs_are_rejected(self):
        for args in ((10**400, 150), (200, 10**400)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    calculate_nutrient(*args)

    def test_result_overflow_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_nutrient(1e308, 1000)
