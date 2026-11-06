"""실제 식품이 아닌 가상 영양 스냅샷으로 근거 기반 검토를 확인한다."""
import unittest
from pydantic import ValidationError
from backend.nutrition_review import ReviewInput, review_nutrition, UNITS

def meal(**changes):
    values=dict(energy=200,carbohydrate=30,protein=10,fat=5,sodium=800,fiber=3,sugar=2)|changes
    return {'foods':[{'food_name':'연습용 음식','nutrients':{k:{'unit':unit,'consumed':values[k]} for k,unit in UNITS.items()}}]}

class NutritionReviewTests(unittest.TestCase):
    def review(self,*meals):return review_nutrition(ReviewInput(meals=list(meals)))
    def test_recorded_ratios_and_reference(self):
        report=self.review(meal())
        self.assertEqual(report['macro_status'],'available')
        ratios={m['key']:m for m in report['macros']}
        self.assertEqual(ratios['carbohydrate']['percent'],60)
        self.assertEqual(ratios['protein']['reference'],[10,20])
        self.assertIn('하루 전체',report['scope'])
    def test_missing_does_not_become_zero(self):
        r=self.review(meal(fiber=None,protein=None),meal())
        self.assertEqual(r['totals']['fiber'],{'value':3,'unit':'g','missing':1})
        self.assertEqual(r['macro_status'],'missing')
        self.assertEqual(r['macros'],[])
    def test_all_missing_and_zero_are_distinct(self):
        missing=self.review(meal(sugar=None))
        zero=self.review(meal(sugar=0))
        self.assertIsNone(missing['totals']['sugar']['value'])
        self.assertEqual(zero['totals']['sugar']['value'],0)
    def test_zero_energy_and_inconsistency_hold_evaluation(self):
        self.assertEqual(self.review(meal(energy=0))['macro_status'],'zero_energy')
        self.assertEqual(self.review(meal(energy=1000))['macro_status'],'inconsistent')
    def test_sodium_contribution_and_partial_exceedance(self):
        a,b=meal(sodium=2100),meal(sodium=None)
        a['foods'][0]['food_name']='연습용 국물'
        r=self.review(a,b)
        self.assertEqual(r['sodium_contributors'][0]['food_name'],'연습용 국물')
        self.assertEqual(r['totals']['sodium']['missing'],1)
        self.assertIn('국물',r['actions'][0])
    def test_no_records(self):
        self.assertEqual(self.review()['macro_status'],'no_records')
    def test_bad_units_negative_and_nonfinite(self):
        for value in [-1,float('inf'),float('nan')]:
            with self.subTest(value=value),self.assertRaises(ValidationError):ReviewInput(meals=[meal(sodium=value)])
        wrong=meal();wrong['foods'][0]['nutrients']['sodium']['unit']='g'
        with self.assertRaises(ValidationError):ReviewInput(meals=[wrong])
