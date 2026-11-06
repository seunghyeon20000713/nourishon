"""가상 HTTPS 주소·임시 빌드·별도 테스트 DB로 배포 경계를 검증한다."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.api import create_app
from backend.settings import load_settings
from tests.test_api import practice_row

ENV = {'NOURISHON_ENV':'staging', 'NOURISHON_ALLOWED_ORIGINS':'https://preview.example.com',
       'NOURISHON_DATABASE_URL':'postgresql://tester:dummy-secret@db.example.com/test?sslmode=require',
       'NOURISHON_FOOD_DATA_PATH':'/srv/food/foods.json','NOURISHON_FRONTEND_DIST':'/srv/frontend/dist'}

class DeploymentTests(unittest.TestCase):
    def test_external_settings_fail_closed_without_secret_output(self):
        for name in ENV:
            values=ENV.copy();values.pop(name)
            if name=='NOURISHON_ENV':continue
            with self.subTest(name=name),patch.dict(os.environ,values,clear=True),self.assertRaises(ValueError) as error:
                load_settings()
            self.assertNotIn('dummy-secret',str(error.exception))
        for origin in ['http://preview.example.com','https://localhost','https://*.example.com','https://preview.example.com/path','https://user:secret@preview.example.com']:
            with self.subTest(origin=origin),patch.dict(os.environ,ENV|{'NOURISHON_ALLOWED_ORIGINS':origin},clear=True),self.assertRaises(ValueError):load_settings()
        with patch.dict(os.environ,ENV,clear=True):
            settings=load_settings()
            self.assertTrue(settings.secure_cookie)
            self.assertEqual(settings.cookie_name,'__Host-nourishon_session')
            self.assertNotIn('dummy-secret',repr(settings))
        with patch.dict(os.environ,ENV|{'NOURISHON_DATABASE_URL':'postgresql://user:private-marker@db.example.com/test'},clear=True),self.assertRaises(ValueError) as error:load_settings()
        self.assertNotIn('private-marker',str(error.exception))

    def test_same_origin_web_and_forbidden_paths(self):
        from backend.web import create_web_app
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'assets').mkdir();(root/'index.html').write_text('practice-ui')
            (root/'assets/app.js').write_text('/* practice */');(root/'.env').write_text('do-not-serve-this')
            api=create_app(rows=[practice_row('practice-1','가상 식품')])
            with TestClient(create_web_app(api=api,frontend_path=root)) as client:
                self.assertEqual(client.get('/').text,'practice-ui')
                self.assertEqual(client.get('/assets/app.js').status_code,200)
                self.assertEqual(client.get('/api/foods',params={'q':'가상'}).json()['total'],1)
                self.assertEqual(client.get('/api/unknown').status_code,404)
                for path in ['/.env','/.git/config','/data/foods.json','/assets/.env','/backend/settings.py']:
                    self.assertEqual(client.get(path).status_code,404)
                    self.assertNotIn('do-not-serve-this',client.get(path).text)
                self.assertEqual(client.get('/api/ready').status_code,503)
                self.assertEqual(client.get('/api/auth/me').headers['cache-control'],'no-store')
                limited=client.post('/api/auth/register',content=b'x'*2_000_001,headers={'Content-Type':'application/json'})
                self.assertEqual(limited.status_code,413)
                self.assertEqual(limited.headers['cache-control'],'no-store')

    def test_external_host_and_origin_guard(self):
        with patch.dict(os.environ,ENV,clear=True):
            settings=load_settings()
            app=create_app(rows=[practice_row('p','가상')],settings=settings,database_url=None)
            with TestClient(app,base_url='https://preview.example.com') as client:
                self.assertEqual(client.get('/health').status_code,200)
                self.assertEqual(client.get('/docs').status_code,404)
                self.assertEqual(client.get('/health',headers={'host':'untrusted.example.com'}).status_code,400)
                response=client.post('/auth/register',json={'username':'practice','password':'abcd'},headers={'Origin':'https://untrusted.example.com','X-NourishOn-Client':'web'})
                self.assertEqual(response.status_code,403)
