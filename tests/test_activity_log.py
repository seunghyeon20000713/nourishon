"""가상 활동으로 표준 MET 계산 경계와 출처를 검증한다."""
import unittest
from uuid import uuid4
from datetime import date
from pydantic import ValidationError
from backend.activity_log import ActivityRecord, calculate_activity

class ActivityLogTests(unittest.TestCase):
    def record(self, **changes):
        return ActivityRecord(**(dict(id=uuid4(), date=date(2020, 1, 1), age=30,
            activity_code='17152', weight_kg=70, minutes=30) | changes))

    def test_independent_gross_and_above_rest(self):
        result = calculate_activity(self.record())
        self.assertEqual(result['calculation']['gross_kcal'], 98)
        self.assertEqual(result['calculation']['above_rest_kcal'], 63)
        self.assertEqual(result['calculation']['met'], 2.8)
        self.assertIn('2024', result['calculation']['version'])
        self.assertEqual(calculate_activity(self.record(activity_code='01214'))['calculation']['gross_kcal'], 140)

    def test_zero_and_boundaries(self):
        result = calculate_activity(self.record(minutes=0))
        self.assertEqual(result['calculation']['gross_kcal'], 0)
        self.assertEqual(result['calculation']['above_rest_kcal'], 0)
        for age in (19, 59):
            self.assertEqual(self.record(age=age).age, age)

    def test_invalid_inputs(self):
        for invalid in [dict(age=18), dict(age=60), dict(minutes=-1), dict(minutes=301),
                        dict(weight_kg=float('nan')), dict(minutes=float('inf')), dict(minutes=True),
                        dict(activity_code='unknown'), dict(date=date(2999, 1, 1))]:
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                self.record(**invalid)
