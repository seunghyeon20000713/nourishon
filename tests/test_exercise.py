"""연습용 일반 성인 프로필의 활동 계획 경계 검증."""
import unittest
from pydantic import ValidationError
from backend.exercise import ExerciseInput, plan_exercise
from backend.profile import ProfileInput

class ExerciseTests(unittest.TestCase):
    def profile(self, **kw):
        return ProfileInput(**(dict(age=30,height_cm=170,weight_kg=70,equation_sex='female',activity='inactive',goal='maintain',scope_confirmed=True)|kw))
    def request(self, **kw):
        return ExerciseInput(**(dict(experience='beginner',days=3,minutes=15,current_weekly_minutes=0,has_limitations=False,has_symptoms=False,scope_confirmed=True)|kw))
    def test_beginner_and_time_budget(self):
        plan=plan_exercise(self.profile(), self.request())
        self.assertEqual(plan['status'],'draft')
        self.assertFalse(plan['medical_prescription'])
        active=[x for x in plan['schedule'] if not x['rest']]
        self.assertEqual(len(active),3)
        self.assertEqual(plan['weekly_strength_days'],2)
        for day in active:
            self.assertEqual(day['total_minutes'],10)
            self.assertEqual(sum(day[k] for k in ['warmup_minutes','cooldown_minutes','aerobic_minutes','strength_minutes']),10)
    def test_symptoms_or_limitations_stop_plan(self):
        for kw in [dict(has_symptoms=True),dict(has_limitations=True)]:
            plan=plan_exercise(self.profile(),self.request(**kw))
            self.assertEqual(plan['status'],'needs_assessment')
            self.assertEqual(plan['schedule'],[])
    def test_minimum_time_and_regular(self):
        for days in range(2,7):
            for minutes in [5,10,60]:
                p=plan_exercise(self.profile(goal='gain'),self.request(days=days,minutes=minutes,experience='regular',current_weekly_minutes=150))
                for d in p['schedule']:
                    self.assertLessEqual(d['total_minutes'],minutes)
                    self.assertGreaterEqual(d.get('aerobic_minutes',0),0)
                self.assertEqual(p['weekly_strength_days'],2)
    def test_inbody_does_not_determine_intensity(self):
        body=dict(measured_on='2020-01-01',fat_mass_kg=20)
        a=plan_exercise(self.profile(),self.request())
        b=plan_exercise(self.profile(body=body),self.request())
        self.assertEqual(a['schedule'],b['schedule'])
    def test_invalid_input(self):
        for kw in [dict(days=1),dict(minutes=0),dict(current_weekly_minutes=-1),dict(has_limitations='no'),dict(scope_confirmed=False)]:
            with self.subTest(kw=kw),self.assertRaises(ValidationError):self.request(**kw)
