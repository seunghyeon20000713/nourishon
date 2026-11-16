"""외부 DB 준비 스크립트의 입력 검사. 실제 DB에 접속하지 않는다."""
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('prepare_staging_db', Path(__file__).resolve().parents[1] / 'scripts/prepare-staging-db.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class PrepareStagingDbTests(unittest.TestCase):
    def test_rejects_unsafe_owner_connections_without_leaking_secret(self):
        cases = [
            'postgresql://owner:secret-marker@db.example.com/neondb',                      # SSL 없음
            'postgresql://owner:secret-marker@localhost/neondb?sslmode=require',           # 로컬
            'host=/tmp/socket user=owner password=secret-marker dbname=neondb sslmode=require',
            'postgresql://nourishon_app:secret-marker@db.example.com/neondb?sslmode=require',  # 앱 역할
            'not a valid secret-marker conninfo ===',
        ]
        for dsn in cases:
            with self.subTest(dsn=dsn.split('secret-marker')[0]), self.assertRaises(module.PrepareError) as error:
                module.check_owner_dsn(dsn)
            self.assertNotIn('secret-marker', str(error.exception))

    def test_accepts_remote_ssl_owner_connection(self):
        options = module.check_owner_dsn('postgresql://neondb_owner:x@ep-test.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
        self.assertEqual(options['dbname'], 'neondb')

    def test_missing_env_exits_nonzero(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(module.main([]), 1)


if __name__ == '__main__':
    unittest.main()
