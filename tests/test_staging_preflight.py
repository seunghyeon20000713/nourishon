"""외부 서버에 접속하지 않고 배포 사전 검사 CLI의 식품 확인·비밀값 비노출을 검사한다."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tests.test_api import practice_row

class StagingPreflightTests(unittest.TestCase):
    def test_full_food_preflight_and_bad_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);food=root/'foods.json';dist=root/'dist'
            (dist/'assets').mkdir(parents=True)
            (dist/'index.html').write_text('practice-screen')
            (dist/'assets/app.js').write_text('/* practice */')
            food.write_text(json.dumps([practice_row('a','가상 사전 검사 식품')]))
            report=root/'report.json';report.write_text(json.dumps({'status':'completed','output_count':1}))
            env={**os.environ,'NOURISHON_ENV':'staging','NOURISHON_ALLOWED_ORIGINS':'https://test.example.com',
                 'NOURISHON_DATABASE_URL':'postgresql://practice:private-preflight-marker@db.example.com/test?sslmode=require',
                 'NOURISHON_FOOD_DATA_PATH':str(food),'NOURISHON_FRONTEND_DIST':str(dist)}
            command=[sys.executable,'-B','scripts/check-staging.py','--check-food']
            result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('전체 식품 검증 통과',result.stdout)
            self.assertIn('실제 DB 연결은 검사하지 않았습니다',result.stdout)
            self.assertNotIn('private-preflight-marker',result.stdout+result.stderr)
            report.write_text(json.dumps({'status':'completed','output_count':2}))
            result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=15)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('private-preflight-marker',result.stdout+result.stderr)
