"""화면용 운동 이름표(frontend/src/activityGuide.ts)가 서버 운동 코드와 정확히 같은지 확인한다.

서버에 운동을 추가하고 번역표를 빠뜨리면 화면에 공식 긴 이름이 그대로 나오므로, 양쪽 목록을 테스트로 맞춘다(2026-11-17).
"""
import re
import unittest
from pathlib import Path

from backend.activity_log import ACTIVITIES

GUIDE = Path(__file__).resolve().parents[1] / 'frontend/src/activityGuide.ts'


class ActivityGuideTests(unittest.TestCase):
    def setUp(self):
        text = GUIDE.read_text(encoding='utf-8')
        body = text[text.index('ACTIVITY_GUIDE'):text.index('\n}\n')]
        self.entries = re.findall(r"'(\d{5})': \{ label: '([^']+)', hint: '([^']*)' \}", body)

    def test_every_server_code_has_plain_name_and_no_extra(self):
        guide_codes = [code for code, _, _ in self.entries]
        self.assertEqual(len(guide_codes), len(set(guide_codes)), '번역표에 중복 코드가 있습니다.')
        self.assertEqual(len(ACTIVITIES), 28)
        self.assertEqual(set(guide_codes), set(ACTIVITIES))

    def test_demo_list_matches_server_codes_and_met(self):
        # 체험판(Sites)은 서버 없이 demoData.json 목록을 쓴다. 코드·MET·분류가 서버와 같아야 한다.
        import json
        demo = json.loads((GUIDE.parent / 'demoData.json').read_text(encoding='utf-8'))['activities']
        self.assertEqual({item['code']: (item['met'], item['category']) for item in demo},
                         {code: (item['met'], item['category']) for code, item in ACTIVITIES.items()})

    def test_plain_names_avoid_imperial_units_and_met(self):
        for code, label, hint in self.entries:
            with self.subTest(code=code):
                self.assertTrue(label.strip())
                self.assertNotRegex(label + hint, r'mph|MET')


if __name__ == '__main__':
    unittest.main()
