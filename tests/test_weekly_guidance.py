"""가상 식사·측정·운동을 연결하되 진단·보상 운동량을 만들지 않는지 검증."""
import unittest
from uuid import uuid4
from backend.weekly_guidance import WeeklyInput, weekly_guidance
from tests.test_nutrition_review import meal

class WeeklyGuidanceTests(unittest.TestCase):
    def request(self, **changes):
        return WeeklyInput(**(dict(end='2026-01-07',profile=dict(age=30,height_cm=170,weight_kg=70,equation_sex='female',activity='inactive',goal='lose',scope_confirmed=True),exercise_input=dict(experience='beginner',days=3,minutes=15,current_weekly_minutes=0,has_limitations=False,has_symptoms=False,scope_confirmed=True)) | changes))
    def activity(self, code='12030', minutes=30, **changes):
        return dict(id=str(uuid4()), date='2026-01-07', age=30, activity_code=code, weight_kg=70, minutes=minutes, calculation={'gross_kcal':999999}) | changes
    def test_connected_counts_and_derived_values(self):
        meals=[dict(id='a',date='2026-01-01',**meal(sodium=2100)),dict(id='b',date='2026-01-07',**meal(sodium=None)),dict(id='outside',date='2025-12-31',**meal())]
        measures=[dict(id=str(uuid4()),measured_on='2026-01-01',weight_kg=70,body_fat_percent=20),dict(id=str(uuid4()),measured_on='2026-01-07',weight_kg=69,body_fat_percent=18)]
        r=weekly_guidance(self.request(meals=meals,measurements=measures,activities=[self.activity(),self.activity('02056')]))
        self.assertEqual(r['coverage']['meal_records'],2)
        self.assertEqual(r['activity']['recorded_minutes'],60)
        self.assertEqual(r['activity']['gross_kcal'],402.5)
        self.assertEqual(r['activity']['strength_recorded_days'],1)
        self.assertEqual(r['nutrition']['sodium_reference_days'],['2026-01-01'])
        self.assertEqual(r['body_changes'][0]['difference'],-1)
        self.assertEqual(r['body_changes'][3]['difference'],-2)
        self.assertEqual(r['body_changes'][3]['unit'],'%p')
        self.assertIn('sodium',[x['id'] for x in r['recommendations']])
        self.assertEqual(r['activity']['plan_status'],'draft')
    def test_missing_zero_and_same_day(self):
        r=weekly_guidance(self.request(meals=[dict(id='legacy',date='2026-01-07',foods=None)],activities=[self.activity(minutes=0)]))
        self.assertEqual(r['coverage']['legacy_meals'],1)
        self.assertEqual(r['coverage']['reviewed_days'],0)
        self.assertEqual(r['activity']['recorded_minutes'],0)
        self.assertEqual(r['activity']['strength_recorded_days'],0)
        self.assertTrue(all(x['difference'] is None for x in r['body_changes']))
        self.assertIn('food_records',[x['id'] for x in r['recommendations']])
    def test_safety_hold_and_missing_inputs(self):
        request=self.request();request.exercise_input.has_symptoms=True
        r=weekly_guidance(request)
        self.assertEqual(r['activity']['plan_status'],'needs_assessment')
        self.assertEqual(r['recommendations'][0]['id'],'assessment')
        self.assertNotIn('activity',[x['id'] for x in r['recommendations']])
        r=weekly_guidance(self.request(profile=None,exercise_input=None))
        self.assertEqual(r['activity']['plan_status'],'needs_input')
        self.assertIn('activity_input',[x['id'] for x in r['recommendations']])
    def test_body_and_food_do_not_escalate_exercise(self):
        base=weekly_guidance(self.request())
        altered=weekly_guidance(self.request(meals=[dict(id='large',date='2026-01-07',**meal(energy=9000))],measurements=[dict(id=str(uuid4()),measured_on='2026-01-01',weight_kg=70),dict(id=str(uuid4()),measured_on='2026-01-07',weight_kg=80)]))
        action=lambda r:next(x['action'] for x in r['recommendations'] if x['id']=='activity')
        self.assertEqual(action(base),action(altered))
    def test_duplicate_future_and_units_rejected(self):
        from pydantic import ValidationError
        a=self.activity()
        for change in [dict(end='2999-01-01'),dict(activities=[a,a]),dict(meals=[dict(id='wrong',date='2026-01-07',foods=[{'food_name':'가상','nutrients':{'sodium':{'unit':'g','consumed':1}}}])])]:
            with self.subTest(change=change),self.assertRaises(ValidationError):self.request(**change)
