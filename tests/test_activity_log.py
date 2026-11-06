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

    def test_new_activity_reference_values(self):
        # 70kg·30분: 공식 MET × 35. 기존 코드와 추가 코드의 계산 검증.
        for code, met, expected in [('12020',7.5,262.5),('12028',6.5,227.5),
                                    ('12030',8.5,297.5),('12050',9.3,325.5),
                                    ('02056',3.0,105),('02054',3.5,122.5),
                                    ('02050',6.0,210),('15660',4.0,140)]:
            with self.subTest(code=code):
                value = calculate_activity(self.record(activity_code=code))['calculation']
                self.assertEqual(value['met'], met)
                self.assertEqual(value['gross_kcal'], expected)

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
