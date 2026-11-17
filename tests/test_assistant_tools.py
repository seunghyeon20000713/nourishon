"""AI 건강 비서의 도구·가짜 AI·Gemini 요청·안전장치를 DB 없이 검증한다. 모든 데이터는 가상 값."""
import json
import unittest
from datetime import date

from backend.assistant import REFUSE_PATTERNS, scrub
from backend.assistant_providers import FakeProvider, GeminiProvider, ProviderError, fmt, unknown_numbers
from backend.assistant_tools import TOOL_SPECS, ToolBox, ToolError, ensure_safe_payload

TODAY = date(2026, 11, 18)   # 수요일


def food(name, **values):
    units = {'energy': 'kcal', 'sodium': 'mg'}
    return {'food_name': name, 'nutrients': {key: {'unit': units.get(key, 'g'), 'consumed': value} for key, value in values.items()}}


def meal(day, kind, foods):
    totals = {}
    for key in ('energy', 'carbohydrate', 'protein', 'fat', 'sugar', 'fiber', 'sodium'):
        values = [f['nutrients'][key]['consumed'] for f in foods if key in f['nutrients'] and f['nutrients'][key]['consumed'] is not None]
        missing = len(foods) - len(values)
        totals[key] = {'unit': 'kcal' if key == 'energy' else 'mg' if key == 'sodium' else 'g',
                       'known_total': sum(values) if values else None, 'missing_count': missing,
                       'status': 'missing' if not values else 'partial' if missing else 'complete'}
    return {'id': f'{day}-{kind}', 'date': day, 'kind': kind, 'calculation': {'foods': foods, 'totals': totals}}


SECRET_FOOD = '비밀연습음식'
DATA = {
    'records': [
        meal('2026-11-16', '아침', [food(SECRET_FOOD, energy=400, carbohydrate=60, protein=20, fat=9, sugar=5, fiber=None, sodium=900)]),
        meal('2026-11-17', '점심', [food('연습 국밥', energy=600, carbohydrate=80, protein=30, fat=18, sugar=3, fiber=2, sodium=1500)]),
        meal('2026-11-17', '저녁', [food('연습 샐러드', energy=300, carbohydrate=30, protein=25, fat=9, sugar=4, fiber=6, sodium=400)]),
    ],
    'activityRecords': [{'id': 'a1', 'date': '2026-11-17', 'activity_code': '17082', 'minutes': 60, 'weight_kg': 70, 'age': 30,
                         'calculation': {'gross_kcal': 371, 'above_rest_kcal': 301, 'met': 5.3}}],
    'estimate': {'maintenance_kcal': 2167, 'protein_reference_g': 56, 'bmi': 24.2},
    'profile': {'age': 30},
}


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tools = ToolBox(DATA, TODAY)

    def test_every_tool_returns_only_numbers_dates_and_fixed_labels(self):
        calls = [('get_period_nutrition', {'start': '2026-11-16', 'end': '2026-11-18'}), ('get_day_meals', {'date': '2026-11-17'}),
                 ('get_nutrition_review', {'start': '2026-11-16', 'end': '2026-11-18'}),
                 ('get_activity_summary', {'start': '2026-11-16', 'end': '2026-11-18'}), ('get_my_reference', {})]
        self.assertEqual({name for name, _ in calls}, {spec['name'] for spec in TOOL_SPECS})
        for name, args in calls:
            with self.subTest(tool=name):
                result = self.tools.run(name, args)
                ensure_safe_payload(result)
                text = json.dumps(result, ensure_ascii=False)
                for secret in (SECRET_FOOD, '연습 국밥', '연습 샐러드'):
                    self.assertNotIn(secret, text)

    def test_period_counts_missing_and_recorded_days(self):
        result = self.tools.run('get_period_nutrition', {'start': '2026-11-16', 'end': '2026-11-22'})
        self.assertEqual(result['days_in_period'], 3)          # 오늘(18일)까지만
        self.assertEqual(result['recorded_days'], 2)
        self.assertEqual(result['totals']['sodium']['value'], 2800)
        self.assertEqual(result['totals']['fiber']['missing_count'], 1)
        self.assertEqual(result['recorded_day_averages']['sodium']['value'], 1400)

    def test_review_and_activity_and_reference(self):
        review = self.tools.run('get_nutrition_review', {'start': '2026-11-17', 'end': '2026-11-17'})
        self.assertEqual(review['macro_status'], 'available')
        self.assertEqual(review['sodium_contributor_count'], 2)
        activity = self.tools.run('get_activity_summary', {'start': '2026-11-16', 'end': '2026-11-18'})
        self.assertEqual((activity['record_count'], activity['total_minutes'], activity['gross_kcal_estimate']), (1, 60, 371))
        self.assertEqual(activity['by_category'][0]['category'], '등산·하이킹')
        self.assertEqual(self.tools.run('get_my_reference', {})['protein_reference_g'], 56)
        self.assertFalse(ToolBox({}, TODAY).run('get_my_reference', {})['available'])

    def test_invalid_inputs_are_rejected(self):
        for name, args in [('get_period_nutrition', {'start': '2026-10-01', 'end': '2026-11-18'}),
                           ('get_period_nutrition', {'start': '2026-11-19', 'end': '2026-11-20'}),
                           ('get_day_meals', {'date': '내일'}), ('get_day_meals', {'date': '2026-11-19'}),
                           ('get_activity_summary', {'start': '2026-11-18', 'end': '2026-11-01'})]:
            with self.subTest(name=name, args=args), self.assertRaises(ToolError):
                self.tools.run(name, args)
        with self.assertRaises(ToolError):
            self.tools.run('delete_everything', {})

    def test_payload_check_blocks_free_text(self):
        for bad in ({'name': 'practice_user'}, {'items': ['연습 닉네임']}, {'Bad-Key': 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ensure_safe_payload(bad)


class FakeProviderTests(unittest.TestCase):
    def ask(self, question, data=DATA):
        return FakeProvider().answer(question, ToolBox(data, TODAY), TODAY)

    def test_sodium_this_week_uses_tool_numbers(self):
        reply = self.ask('이번 주 나트륨 어때?')
        self.assertEqual(reply.tool_calls[0]['name'], 'get_period_nutrition')
        self.assertEqual(reply.tool_calls[0]['args'], {'start': '2026-11-16', 'end': '2026-11-18'})
        self.assertIn('2,800 mg', reply.text)
        self.assertIn('3일 중 2일', reply.text)
        self.assertIn('2,000mg', reply.text)
        self.assertEqual(unknown_numbers(reply.text, '이번 주 나트륨 어때?', reply.tool_calls, TODAY), [])

    def test_protein_yesterday_and_missing_fiber(self):
        reply = self.ask('어제 단백질 충분해?')
        self.assertEqual(reply.tool_calls[0]['args'], {'start': '2026-11-17', 'end': '2026-11-17'})
        self.assertIn('55 g', reply.text)
        self.assertIn('56 g', reply.text)
        self.assertIn('어제(2026-11-17) 1일 중 1일', reply.text)   # 하루면 날짜 하나만
        fiber = self.ask('이번 주 식이섬유는?')
        self.assertIn('정보가 빠진 항목이 1개', fiber.text)  # 결측이 있으면 판단하지 않는다고 말한다
        self.assertIn('판단하지 않아요', fiber.text)

    def test_activity_and_no_records(self):
        self.assertIn('371 kcal', self.ask('이번 주 운동 얼마나 했어?').text)
        empty = self.ask('지난주 열량은?', {'records': []})
        self.assertIn('식사 기록이 없어요', empty.text)
        self.assertIn('0으로 계산하지 않아서', empty.text)


class GeminiProviderTests(unittest.TestCase):
    def test_function_call_loop_sends_only_question_and_tool_numbers(self):
        sent = []

        def post(url, body, headers, timeout):
            sent.append((url, body, headers))
            if len(sent) == 1:
                return {'candidates': [{'content': {'parts': [{'functionCall': {'name': 'get_period_nutrition', 'args': {'start': '2026-11-16', 'end': '2026-11-18'}}}]}}]}
            return {'candidates': [{'content': {'parts': [{'text': '이번 주 3일 중 2일 기록, 나트륨 합계는 2,800mg이에요.'}]}}]}

        provider = GeminiProvider('test-key-not-real', 'gemini-test', post=post)
        reply = provider.answer('이번 주 나트륨 어때?', ToolBox(DATA, TODAY), TODAY)
        self.assertEqual(reply.provider, 'gemini')
        self.assertEqual(len(sent), 2)
        url, body, headers = sent[1]
        self.assertNotIn('test-key-not-real', url)                 # 키는 URL이 아니라 헤더로
        self.assertEqual(headers['x-goog-api-key'], 'test-key-not-real')
        text = json.dumps(body, ensure_ascii=False)
        for secret in (SECRET_FOOD, '연습 국밥', '연습 샐러드'):
            self.assertNotIn(secret, text)
        self.assertEqual(unknown_numbers(reply.text, '이번 주 나트륨 어때?', reply.tool_calls, TODAY), [])

    def test_quota_and_bad_responses_raise_provider_error(self):
        def quota(*_):
            raise ProviderError('quota')
        with self.assertRaises(ProviderError):
            GeminiProvider('k', 'm', post=quota).answer('열량?', ToolBox(DATA, TODAY), TODAY)
        with self.assertRaises(ProviderError):
            GeminiProvider('k', 'm', post=lambda *_: {'candidates': []}).answer('열량?', ToolBox(DATA, TODAY), TODAY)
        with self.assertRaises(ProviderError):
            GeminiProvider('', 'm')


class SafetyTests(unittest.TestCase):
    def test_made_up_numbers_are_detected(self):
        tools = ToolBox(DATA, TODAY)
        result = tools.run('get_period_nutrition', {'start': '2026-11-16', 'end': '2026-11-18'})
        calls = [{'name': 'get_period_nutrition', 'args': {'start': '2026-11-16', 'end': '2026-11-18'}, 'result': result}]
        self.assertEqual(unknown_numbers('나트륨 합계 2,800mg, 기록일 평균 1,400mg', '', calls, TODAY), [])
        self.assertEqual(unknown_numbers('하루 3,500mg을 넘었어요', '', calls, TODAY), ['3,500'])

    def test_diagnosis_questions_are_refused_but_normal_ones_are_not(self):
        for question in ('당뇨인지 진단해줘', '혈압약 먹어도 돼?', '이 증상이면 무슨 병이야', '영양제 용량 알려줘', '임신 중인데 괜찮아?'):
            with self.subTest(question=question):
                self.assertTrue(REFUSE_PATTERNS.search(question))
        for question in ('이번 주 나트륨 어때?', '어제 단백질 충분해?', '약간 짜게 먹은 것 같아', '운동 얼마나 했어?'):
            with self.subTest(question=question):
                self.assertFalse(REFUSE_PATTERNS.search(question))

    def test_identifiers_are_removed_from_question(self):
        self.assertEqual(scrub('practice_abc 이번 주 연습닉네임 나트륨?', ['practice_abc', '연습닉네임']), '사용자 이번 주 사용자 나트륨?')

    def test_display_rule_matches_screen(self):
        self.assertEqual(fmt(949.7, 'kcal'), '950 kcal')
        self.assertEqual(fmt(41.25, 'g'), '41.3 g')   # 화면 nutrientFormat.ts와 같은 0.5 올림
        self.assertEqual(fmt(1457.1, 'mg'), '1,457 mg')
        self.assertEqual(fmt(0.04, 'g'), '0.1 미만 g')
        self.assertEqual(fmt(19.0, 'g'), '19 g')
