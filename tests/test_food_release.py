"""비공개 Release 식품 다운로드: 가짜 GitHub 서버와 가상 식품만 사용한다."""
import hashlib
import io
import json
import tarfile
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from backend.food_release import FoodReleaseError, fetch, package

TOKEN = 'github_pat_fake-secret-token'
SIGNATURE = 'X-Amz-Signature=fake-signed-part'


def make_archive(members: dict) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeGitHub(BaseHTTPRequestHandler):
    blob = b''
    release_status = 200
    blob_auth_seen = []

    def log_message(self, *args):
        pass

    def send_json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        port = self.server.server_address[1]
        authorized = self.headers.get('Authorization') == f'Bearer {TOKEN}'
        if self.path == '/repos/owner/food/releases/tags/v1':
            if not authorized:
                return self.send_json(401, {'message': 'Bad credentials'})
            if self.release_status != 200:
                return self.send_json(self.release_status, {'message': 'error'})
            return self.send_json(200, {'assets': [{'id': 7, 'name': 'food-data.tar.gz', 'size': len(self.blob)}]})
        if self.path == '/repos/owner/food/releases/assets/7':
            if not authorized or self.headers.get('Accept') != 'application/octet-stream':
                return self.send_json(401, {'message': 'Bad credentials'})
            self.send_response(302)
            self.send_header('Location', f'http://127.0.0.1:{port}/signed/blob?{SIGNATURE}')
            self.end_headers()
            return
        if self.path.startswith('/signed/blob'):
            type(self).blob_auth_seen.append(self.headers.get('Authorization'))
            self.send_response(200)
            self.send_header('Content-Length', str(len(self.blob)))
            self.end_headers()
            self.wfile.write(self.blob)
            return
        self.send_json(404, {'message': 'Not Found'})


class FoodReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.foods = json.dumps([{'code': 'practice-1', 'name': '연습용 음식'}], ensure_ascii=False).encode()
        self.report = json.dumps({'count': 1}).encode()
        FakeGitHub.blob = make_archive({'foods.json': self.foods, 'report.json': self.report})
        FakeGitHub.release_status = 200
        FakeGitHub.blob_auth_seen = []
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), FakeGitHub)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.api = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.dest = self.root / 'data' / 'food'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def run_fetch(self, sha=None, token=TOKEN, asset='food-data.tar.gz'):
        sha = sha or hashlib.sha256(FakeGitHub.blob).hexdigest()
        return fetch('owner/food', 'v1', asset, sha, token, self.dest, api=self.api)

    def leftovers(self):
        return [p.name for p in self.dest.parent.iterdir() if p.name.startswith('.food-release-')]

    def test_download_verifies_hash_and_places_only_expected_files(self):
        result = self.run_fetch()
        self.assertEqual(result['bytes'], len(FakeGitHub.blob))
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['foods.json', 'report.json'])
        self.assertEqual((self.dest / 'foods.json').read_bytes(), self.foods)
        self.assertEqual(self.leftovers(), [])

    def test_token_is_not_sent_to_signed_download_url(self):
        self.run_fetch()
        self.assertEqual(FakeGitHub.blob_auth_seen, [None])

    def test_hash_mismatch_places_nothing(self):
        with self.assertRaises(FoodReleaseError) as error:
            self.run_fetch(sha='0' * 64)
        self.assertIn('SHA-256', str(error.exception))
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.leftovers(), [])

    def test_existing_data_kept_when_download_fails(self):
        self.dest.mkdir(parents=True)
        (self.dest / 'foods.json').write_text('old')
        with self.assertRaises(FoodReleaseError):
            self.run_fetch(sha='0' * 64)
        self.assertEqual((self.dest / 'foods.json').read_text(), 'old')

    def test_existing_data_replaced_after_successful_download(self):
        self.dest.mkdir(parents=True)
        (self.dest / 'foods.json').write_text('old')
        (self.dest / 'stale.txt').write_text('stale')
        self.run_fetch()
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['foods.json', 'report.json'])
        self.assertEqual(self.leftovers(), [])

    def test_errors_never_contain_token_or_signed_url(self):
        cases = [
            dict(token='wrong-token'),
            dict(asset='missing.tar.gz'),
            dict(sha='0' * 64),
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(FoodReleaseError) as error:
                self.run_fetch(**case)
            message = str(error.exception)
            self.assertNotIn(TOKEN, message)
            self.assertNotIn('fake-signed-part', message)
            self.assertNotIn('127.0.0.1', message)
        FakeGitHub.release_status = 500
        with self.assertRaises(FoodReleaseError) as error:
            self.run_fetch()
        self.assertIn('HTTP 500', str(error.exception))

    def test_rejects_archive_with_unexpected_or_traversal_members(self):
        bad_sets = [
            {'foods.json': self.foods, 'report.json': self.report, '../evil.sh': b'x'},
            {'foods.json': self.foods},
            {'../foods.json': self.foods, 'report.json': self.report},
        ]
        for members in bad_sets:
            FakeGitHub.blob = make_archive(members)
            with self.subTest(members=list(members)), self.assertRaises(FoodReleaseError):
                self.run_fetch()
            self.assertFalse(self.dest.exists())
            self.assertFalse((self.root / 'data' / 'evil.sh').exists())
            self.assertEqual(self.leftovers(), [])

    def test_rejects_invalid_inputs_before_network(self):
        for kwargs in [dict(sha='abc'), dict(token=''), dict(asset='../x')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(FoodReleaseError):
                self.run_fetch(**kwargs)
        self.assertEqual(FakeGitHub.blob_auth_seen, [])

    def test_package_is_reproducible_and_fetchable(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'foods.json').write_bytes(self.foods)
        (source / 'report.json').write_bytes(self.report)
        (source / 'quarantine.jsonl').write_text('not packaged')
        first = package(source, self.root / 'out' / 'a.tar.gz')
        second = package(source, self.root / 'out' / 'b.tar.gz')
        self.assertEqual(first, second)
        FakeGitHub.blob = (self.root / 'out' / 'a.tar.gz').read_bytes()
        self.run_fetch(sha=first)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['foods.json', 'report.json'])


if __name__ == '__main__':
    unittest.main()
