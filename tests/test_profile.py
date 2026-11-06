"""공식 예시와 입력 경계 검증. 모두 가상의 연습용 프로필."""
import unittest
from pydantic import ValidationError
from backend.profile import ProfileInput, estimate_profile

class ProfileTests(unittest.TestCase):
    def profile(self, **kwargs):
        return ProfileInput(**(dict(age=30, height_cm=170.0, weight_kg=70.0,
            equation_sex='male', activity='inactive', scope_confirmed=True) | kwargs))

    def test_independent_energy_and_bmi(self):
        result = estimate_profile(self.profile())
        self.assertEqual(result['maintenance_kcal'], 2520)
        self.assertEqual(result['bmi'], 24.22)
        self.assertEqual(result['protein_reference_g'], 56)

    def test_all_equations(self):
        expected = {'male': [2520, 2713, 2902, 3149], 'female': [2167, 2337, 2476, 2723]}
        for sex, values in expected.items():
            for activity, expected_value in zip(['inactive','low_active','active','very_active'], values):
                with self.subTest(sex=sex, activity=activity):
                    self.assertEqual(estimate_profile(self.profile(equation_sex=sex, activity=activity))['maintenance_kcal'], expected_value)

    def test_body_does_not_modify_energy(self):
        base = estimate_profile(self.profile())
        enriched = estimate_profile(self.profile(body={'measured_on':'2020-01-01','fat_mass_kg':20.0}))
        self.assertEqual(base['maintenance_kcal'], enriched['maintenance_kcal'])
        self.assertFalse(enriched['body_used_in_energy_equation'])

    def test_invalid_values(self):
        for change in [dict(age=18),dict(age=65),dict(age=True),dict(weight_kg=float('nan')),
                       dict(weight_kg=-1),dict(height_cm='170'),dict(scope_confirmed=False),
                       dict(body={'measured_on':'2999-01-01','fat_mass_kg':10}),
                       dict(body={'measured_on':'2020-01-01'}),
                       dict(body={'measured_on':'2020-01-01','fat_mass_kg':50,'skeletal_muscle_kg':40})]:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                self.profile(**change)

    def test_kdri_macro_ranges_and_version(self):
        result = estimate_profile(self.profile())
        # 반올림 전 EER 2520.17kcal를 4/4/9kcal/g으로 환산한다.
        ranges = result['macro_reference_ranges']
        self.assertEqual(ranges['carbohydrate'], {'percent':[50,65], 'min_g':315.0, 'max_g':409.5})
        self.assertEqual(ranges['protein'], {'percent':[10,20], 'min_g':63.0, 'max_g':126.0})
        self.assertEqual(ranges['fat'], {'percent':[15,30], 'min_g':42.0, 'max_g':84.0})
        self.assertIn('2025', result['macro_reference_version'])

    def test_source_version_scope_and_check_date(self):
        result = estimate_profile(self.profile())
        self.assertEqual(len(result['sources']), 5)
        for source in result['sources']:
            self.assertEqual(source['checked_on'], '2026-11-06')
            self.assertTrue(source['version'])
            self.assertTrue(source['applies_to'])
            self.assertTrue(source['usage'])
        self.assertIn('북미', result['sources'][1]['version'])

    def test_measurement_dates(self):
        for change in [dict(measured_on='2999-01-01'),
                       dict(measured_on='2020-01-01', body={'measured_on':'2020-01-02','fat_mass_kg':20})]:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                self.profile(**change)
        self.assertEqual(self.profile(measured_on='2020-01-01').measured_on.isoformat(),'2020-01-01')
