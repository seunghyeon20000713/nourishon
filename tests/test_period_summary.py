"""서버 기간 요약이 화면(PeriodAnalysis.tsx)과 같은 규칙으로 계산되는지 확인한다.

브라우저 테스트(frontend/tests/period-analysis.spec.ts)와 같은 가상 기록·기대값을 쓴다.
"""
import unittest
from datetime import date

from backend.period_summary import month_bounds, period_summary, week_bounds


def meal(day, value, partial=False):
    return {'date': day, 'kind': '점심', 'calculation': {'foods': [], 'totals': {'energy': {
        'unit': 'kcal', 'known_total': value, 'missing_count': 1 if value is None or partial else 0,
        'status': 'missing' if value is None else 'partial' if partial else 'complete'}}}}


MEALS = [meal('2024-02-26', 100, True), meal('2024-02-27', 0), meal('2024-02-28', None),
         meal('2024-02-01', 200), meal('2024-03-01', 400)]
TODAY = date(2026, 11, 17)


class PeriodSummaryTests(unittest.TestCase):
    def test_week_matches_screen(self):
        start, end = week_bounds(date(2024, 2, 29))
        self.assertEqual((start.isoformat(), end.isoformat()), ('2024-02-26', '2024-03-03'))
        result = period_summary(MEALS, start, end, TODAY)
        energy = result['totals']['energy']
        self.assertEqual(energy['known_total'], 500)
        self.assertEqual(energy['status'], 'partial')
        average = result['recorded_day_averages']['energy']
        self.assertAlmostEqual(average['value'], 500 / 3)
        self.assertEqual(average['days'], 3)
        days = {day['date']: day for day in result['days']}
        self.assertEqual(days['2024-02-27']['energy']['known_total'], 0)   # 0으로 기록한 날은 0
        self.assertIsNone(days['2024-02-28']['energy']['known_total'])     # 결측은 None
        self.assertEqual(days['2024-02-29']['meal_count'], 0)              # 미기록
        self.assertEqual((result['recorded_days'], result['days_in_period']), (4, 7))

    def test_month_matches_screen(self):
        start, end = month_bounds(date(2024, 2, 29))
        self.assertEqual((start.isoformat(), end.isoformat()), ('2024-02-01', '2024-02-29'))
        result = period_summary(MEALS, start, end, TODAY)
        self.assertEqual((result['meal_count'], result['recorded_days']), (4, 4))
        self.assertEqual(result['totals']['energy']['known_total'], 300)
        self.assertEqual(result['recorded_day_averages']['energy']['value'], 100)
        self.assertEqual(result['recorded_day_averages']['energy']['days'], 3)
        fiber = result['totals']['fiber']
        self.assertIsNone(fiber['known_total'])
        self.assertEqual(fiber['status'], 'missing')
        self.assertIsNone(result['recorded_day_averages']['fiber']['value'])

    def test_future_days_are_not_counted(self):
        result = period_summary(MEALS, date(2024, 2, 26), date(2024, 3, 3), date(2024, 2, 27))
        self.assertEqual(result['days_in_period'], 2)
        self.assertEqual(result['totals']['energy']['known_total'], 100)
        self.assertEqual(result['counted_until'], '2024-02-27')

    def test_no_records_is_missing_not_zero(self):
        result = period_summary([], date(2024, 2, 1), date(2024, 2, 7), TODAY)
        self.assertEqual(result['recorded_days'], 0)
        self.assertIsNone(result['totals']['energy']['known_total'])
        self.assertIsNone(result['recorded_day_averages']['energy']['value'])

    def test_reversed_period_is_rejected(self):
        with self.assertRaises(ValueError):
            period_summary(MEALS, date(2024, 3, 3), date(2024, 2, 26), TODAY)


if __name__ == '__main__':
    unittest.main()
