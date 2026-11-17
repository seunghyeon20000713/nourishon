"""AI 건강 비서 API(별도 PostgreSQL 테스트 DB에서만). 테스트가 만든 가상 계정만 정리한다."""
import json
import os
import secrets
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict

from backend.api import create_app
from backend.assistant import FALLBACK_NOTICE, NUMBER_NOTICE, REFUSAL, AssistantConfig, today
from backend.assistant_providers import GeminiProvider, ProviderError, Reply
from backend.database import connect
from tests.test_api import practice_row

TEST_DSN = os.environ.get('NOURISHON_TEST_DATABASE_URL')
HEADERS = {'Origin': 'http://localhost:5173', 'X-NourishOn-Client': 'web'}
FOOD_NAME = '연습비밀음식'


class Broken:
    name = 'gemini'

    def answer(self, *_):
        raise ProviderError('quota')


class MadeUp:
    name = 'gemini'

    def answer(self, question, tools, day):
        result = tools.run('get_day_meals', {'date': day.isoformat()})
        return Reply('오늘 열량은 3,333kcal이에요.', 'gemini', [{'name': 'get_day_meals', 'args': {'date': day.isoformat()}, 'result': result}])


@unittest.skipUnless(TEST_DSN, '별도 PostgreSQL 테스트 DB 설정이 필요합니다.')
class AssistantApiTests(unittest.TestCase):
    def setUp(self):
        if conninfo_to_dict(TEST_DSN).get('dbname') != 'nourishon_test':
            raise RuntimeError('테스트 전용 DB만 허용합니다.')
        self.names = []
        self.app = create_app(rows=[practice_row('practice-1', FOOD_NAME)], database_url=TEST_DSN)
        self.app.state.assistant = AssistantConfig(provider='fake', daily_limit=3, service_daily_limit=1000)
        self.client = TestClient(self.app)
        self.client.__enter__()
        with connect(TEST_DSN) as conn:
            conn.execute('DELETE FROM auth_attempts')

    def tearDown(self):
        self.client.__exit__(None, None, None)
        with connect(TEST_DSN) as conn:
            for name in self.names:
                conn.execute('DELETE FROM users WHERE username=%s', (name,))

    def signup(self, client):
        name = 'practice_' + uuid4().hex[:12]
        self.names.append(name)
        response = client.post('/auth/register', json={'username': name, 'password': secrets.token_urlsafe(16)}, headers=HEADERS)
        self.assertEqual(response.status_code, 201)
        user = response.json()
        profile = client.get('/account/profiles').json()['profiles'][0]
        data = {'profile': dict(age=30, height_cm=170, weight_kg=70, equation_sex='female', activity='inactive', scope_confirmed=True, measured_on='2020-01-01'),
                'records': [{'id': str(uuid4()), 'date': today().isoformat(), 'kind': '점심', 'calculation': {'foods': [{'food_code': 'practice-1', 'intake_g': 150}]}}]}
        saved = client.put(f"/account/profiles/{profile['id']}/data", json={'revision': 0, 'data': data}, headers=HEADERS | {'X-CSRF-Token': user['csrf_token']})
        self.assertEqual(saved.status_code, 200, saved.text)
        return name, user['csrf_token'], profile

    def ask(self, client, csrf, profile_id, question):
        return client.post('/assistant/ask', json={'profile_id': profile_id, 'question': question}, headers=HEADERS | {'X-CSRF-Token': csrf})

    def test_answers_from_own_records_and_counts_usage(self):
        _, csrf, profile = self.signup(self.client)
        response = self.ask(self.client, csrf, profile['id'], '오늘 열량은?')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['provider'], 'fake')
        self.assertIn('300 kcal', body['answer'])            # 가상 음식 200kcal/100g × 150g
        self.assertEqual(body['tool_calls'][0]['name'], 'get_period_nutrition')
        self.assertEqual(body['remaining'], 2)
        self.assertEqual(self.client.get('/assistant/status').json()['remaining'], 2)

    def test_other_users_profile_is_not_readable(self):
        _, csrf_a, profile_a = self.signup(self.client)
        # 같은 앱에 두 번째 사용자(별도 쿠키). 앱 시작·종료(lifespan)는 첫 클라이언트만 맡는다.
        other = TestClient(self.app)
        _, csrf_b, profile_b = self.signup(other)
        # A가 B의 프로필 ID를 넣어도 읽을 수 없다(404). 사용 횟수도 늘지 않는다.
        self.assertEqual(self.ask(self.client, csrf_a, profile_b['id'], '오늘 열량은?').status_code, 404)
        self.assertEqual(self.client.get('/assistant/status').json()['remaining'], 3)
        # B 자신은 읽을 수 있다.
        self.assertEqual(self.ask(other, csrf_b, profile_b['id'], '오늘 열량은?').status_code, 200)

    def test_login_csrf_and_daily_limit(self):
        anonymous = TestClient(self.app)
        self.assertEqual(anonymous.post('/assistant/ask', json={'profile_id': str(uuid4()), 'question': '열량?'}, headers=HEADERS).status_code, 401)
        _, csrf, profile = self.signup(self.client)
        self.assertEqual(self.ask(self.client, 'wrong', profile['id'], '열량?').status_code, 403)
        for _ in range(3):
            self.assertEqual(self.ask(self.client, csrf, profile['id'], '오늘 열량은?').status_code, 200)
        limited = self.ask(self.client, csrf, profile['id'], '오늘 열량은?')
        self.assertEqual(limited.status_code, 429)
        self.assertIn('3개', limited.json()['detail'])

    def test_diagnosis_is_refused_without_tools(self):
        _, csrf, profile = self.signup(self.client)
        body = self.ask(self.client, csrf, profile['id'], '당뇨인지 진단해줘').json()
        self.assertTrue(body['refused'])
        self.assertEqual(body['answer'], REFUSAL)
        self.assertEqual(body['tool_calls'], [])

    def test_provider_failure_and_made_up_numbers_fall_back(self):
        _, csrf, profile = self.signup(self.client)
        self.app.state.assistant_provider = Broken()
        body = self.ask(self.client, csrf, profile['id'], '오늘 열량은?').json()
        self.assertEqual((body['provider'], body['notice']), ('fake', FALLBACK_NOTICE))
        self.app.state.assistant_provider = MadeUp()
        body = self.ask(self.client, csrf, profile['id'], '오늘 열량은?').json()
        self.assertEqual((body['provider'], body['notice']), ('fake', NUMBER_NOTICE))
        self.assertNotIn('3,333', body['answer'])
        with connect(TEST_DSN) as conn:
            row = conn.execute('SELECT u.fallbacks FROM assistant_usage u JOIN profiles p ON p.user_id=u.user_id WHERE p.id=%s', (profile['id'],)).fetchone()
        self.assertEqual(row['fallbacks'], 2)

    def test_gemini_mode_without_key_shows_notice_and_falls_back(self):
        # 키가 없거나(설정 실수) 무료 사용량을 넘으면 가짜 AI로 답하고 안내한다. 화면 안내는 Google 전송 문구.
        self.app.state.assistant = AssistantConfig(provider='gemini', api_key=None, daily_limit=3, service_daily_limit=1000)
        _, csrf, profile = self.signup(self.client)
        status = self.client.get('/assistant/status').json()
        self.assertEqual(status['provider'], 'gemini')
        for words in ('Google', '서비스 개선', '실제 건강정보', '이름'):
            self.assertIn(words, status['notice'])
        body = self.ask(self.client, csrf, profile['id'], '오늘 열량은?').json()
        self.assertEqual((body['provider'], body['notice']), ('fake', FALLBACK_NOTICE))

    def test_external_request_has_no_identifiers(self):
        name, csrf, profile = self.signup(self.client)
        sent = []

        def post(url, body, headers, timeout):
            sent.append(json.dumps(body, ensure_ascii=False))
            if len(sent) == 1:
                return {'candidates': [{'content': {'parts': [{'functionCall': {'name': 'get_day_meals', 'args': {'date': today().isoformat()}}}]}}]}
            return {'candidates': [{'content': {'parts': [{'text': '오늘 기록된 열량은 300kcal이에요.'}]}}]}

        self.app.state.assistant_provider = GeminiProvider('test-key', 'gemini-test', post=post)
        body = self.ask(self.client, csrf, profile['id'], f"{name} {profile['nickname']}의 오늘 열량 알려줘").json()
        self.assertEqual(body['provider'], 'gemini')
        self.assertIsNone(body['notice'])
        outbound = '\n'.join(sent)
        with connect(TEST_DSN) as conn:
            user_id = str(conn.execute('SELECT id FROM users WHERE username=%s', (name,)).fetchone()['id'])
        for secret in (name, profile['nickname'], profile['id'], user_id, FOOD_NAME, 'test-key'):
            self.assertNotIn(secret, outbound)
        self.assertIn('사용자', outbound)

    def test_usage_rows_are_deleted_with_account(self):
        name, csrf, profile = self.signup(self.client)
        self.ask(self.client, csrf, profile['id'], '오늘 열량은?')
        with connect(TEST_DSN) as conn:
            conn.execute('DELETE FROM users WHERE username=%s', (name,))
            self.assertIsNone(conn.execute('SELECT 1 FROM assistant_usage u JOIN profiles p ON p.user_id=u.user_id WHERE p.id=%s', (profile['id'],)).fetchone())
            self.assertEqual(conn.execute("SELECT count(*) AS n FROM assistant_usage u LEFT JOIN users x ON x.id=u.user_id WHERE x.id IS NULL").fetchone()['n'], 0)


if __name__ == '__main__':
    unittest.main()
