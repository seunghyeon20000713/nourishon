import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from backend.collect_food_api import collect, fetch_page, load_key, parse_response


def response_bytes(items, category="연습분류"):
    return json.dumps({"header": {"resultCode": "00"}, "body": {
        "pageNo": 1, "totalCount": len(items), "items": items,
    }}).encode()


class CollectFoodApiTests(unittest.TestCase):
    def test_key_decoding_preserves_plus(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            for value in ("practice%2Bkey%3D", "practice+key="):
                path.write_text(f'DATA_GO_KR_SERVICE_KEY="{value}"\n')
                self.assertEqual(load_key(path), "practice+key=")

    def test_invalid_responses_do_not_expose_server_text(self):
        for raw in (b'<error>secret-value</error>', b'{"header":{"resultCode":"30","message":"secret-value"}}', b'{}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError) as error:
                parse_response(raw)
            self.assertNotIn("secret-value", str(error.exception))

    def test_save_original_and_sanitized_manifest(self):
        items = [{"FOOD_CD": "practice-1", "FOOD_CAT1_NM": "연습분류",
                  "SERVING_SIZE": "100g"}]
        raw = response_bytes(items)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            with patch("backend.collect_food_api.fetch_page", return_value=(raw, {"totalCount": 1}, items)):
                report = collect("practice-secret", ["연습분류"], 20, 1, output)
            self.assertEqual(report["unique_food_codes"], 1)
            self.assertFalse(report["full_collection_complete"])
            self.assertEqual((output / "category-01-page-1.json").read_bytes(), raw)
            self.assertNotIn("practice-secret", (output / "manifest.json").read_text())
            with self.assertRaises(FileExistsError):
                collect("practice-secret", ["연습분류"], 20, 1, output)

    def test_partial_failure_is_recorded_and_previous_raw_preserved(self):
        items = [{"FOOD_CD": "practice-1"}]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            with patch("backend.collect_food_api.fetch_page", side_effect=[
                (b'{}', {"totalCount": 1}, items), ValueError("실패")
            ]):
                with self.assertRaises(ValueError):
                    collect("practice-secret", ["가", "나"], 20, 1, output)
            report = json.loads((output / "manifest.json").read_text())
            self.assertEqual(report["collection_status"], "failed")
            self.assertEqual(len(report["requests"]), 1)
            self.assertTrue((output / "category-01-page-1.json").is_file())

    def test_http_exception_does_not_expose_url_or_key(self):
        error = HTTPError("https://example.invalid/?secret=practice-secret", 403, "practice-secret", {}, None)
        with patch("backend.collect_food_api.urlopen", side_effect=error):
            with self.assertRaises(ValueError) as caught:
                fetch_page("practice-secret", "연습분류", 1, 20)
        self.assertNotIn("practice-secret", str(caught.exception))

    def test_category_mismatch_and_key_echo_are_rejected(self):
        for raw in (response_bytes([{"FOOD_CAT1_NM": "다른분류"}]), b'practice-secret'):
            with self.subTest(raw=raw), patch("backend.collect_food_api.urlopen") as request:
                request.return_value.__enter__.return_value.read.return_value = raw
                with self.assertRaises(ValueError):
                    fetch_page("practice-secret", "연습분류", 1, 20)

    def test_duplicate_codes_are_not_silently_merged(self):
        items = [{"FOOD_CD": "same", "FOOD_CAT1_NM": "연습분류"}] * 2
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            with patch("backend.collect_food_api.fetch_page", return_value=(b'{}', {"totalCount": 2}, items)):
                with self.assertRaises(ValueError):
                    collect("practice-secret", ["연습분류"], 20, 1, output)
            self.assertEqual(json.loads((output / "manifest.json").read_text())["collection_status"], "failed")
