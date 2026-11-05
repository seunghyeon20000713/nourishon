import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.collect_all_food_api import collect_all, validate_page


def page_response(page, total=3, codes=None):
    codes = codes if codes is not None else (["practice-1", "practice-2"] if page == 1 else ["practice-3"])
    items = [{"FOOD_CD": code, "DB_GRP_NM": "가상", "SERVING_SIZE": "100g",
              "FOOD_CAT1_NM": "연습분류"} for code in codes]
    body = {"totalCount": total, "pageNo": page, "items": items}
    raw = json.dumps({"header": {"resultCode": "00"}, "body": body}).encode()
    return raw, body, items


class CollectAllFoodApiTests(unittest.TestCase):
    def test_complete_and_revalidate_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            with patch("backend.collect_all_food_api.fetch_page", side_effect=lambda key, category, page, size: page_response(page)) as fetch:
                report = collect_all("fake-key", output, size=2, delay=0, workers=2)
            self.assertTrue(report["full_collection_complete"])
            self.assertEqual(report["received_count"], 3)
            self.assertEqual(report["unique_food_codes"], 3)
            self.assertTrue(all(call.args[1] is None for call in fetch.call_args_list))
            with patch("backend.collect_all_food_api.fetch_page") as fetch:
                collect_all("fake-key", output, size=2, delay=0)
                fetch.assert_not_called()
            self.assertNotIn("fake-key", (output / "manifest.json").read_text())

    def test_failure_then_resume_only_missing_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            def fail_second(key, category, page, size):
                if page == 2:
                    raise ValueError("가상 연결 실패")
                return page_response(page)
            with patch("backend.collect_all_food_api.fetch_page", side_effect=fail_second), patch("backend.collect_all_food_api.time.sleep"):
                with self.assertRaises(ValueError):
                    collect_all("fake-key", output, size=2)
            report = json.loads((output / "manifest.json").read_text())
            self.assertFalse(report["full_collection_complete"])
            self.assertEqual(len(report["requests"]), 1)
            with patch("backend.collect_all_food_api.fetch_page", return_value=page_response(2)) as fetch:
                report = collect_all("fake-key", output, size=2, delay=0)
            self.assertTrue(report["full_collection_complete"])
            self.assertEqual(fetch.call_args.args[2], 2)
            self.assertEqual(fetch.call_count, 1)

    def test_changed_total_and_duplicate_codes_block_completion(self):
        for second in (page_response(2, total=4, codes=["practice-3", "practice-4"]),
                       page_response(2, codes=["practice-1"])):
            with self.subTest(second=second), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "run"
                with patch("backend.collect_all_food_api.fetch_page", side_effect=[page_response(1), second]):
                    with self.assertRaises(ValueError):
                        collect_all("fake-key", output, size=2, delay=0)
                self.assertFalse(json.loads((output / "manifest.json").read_text())["full_collection_complete"])

    def test_tampered_raw_blocks_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            with patch("backend.collect_all_food_api.fetch_page", side_effect=lambda k, c, p, s: page_response(p)):
                collect_all("fake-key", output, size=2, delay=0)
            (output / "page-00001.json").write_bytes(b'changed')
            with self.assertRaises(ValueError):
                collect_all("fake-key", output, size=2, delay=0)

    def test_orphan_page_is_verified_and_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            def stop_after_first(k, c, p, s):
                if p == 2:
                    raise ValueError("가상 중단")
                return page_response(p)
            with patch("backend.collect_all_food_api.fetch_page", side_effect=stop_after_first), patch("backend.collect_all_food_api.time.sleep"):
                with self.assertRaises(ValueError):
                    collect_all("fake-key", output, size=2)
            (output / "page-00002.json").write_bytes(page_response(2)[0])
            with patch("backend.collect_all_food_api.fetch_page") as fetch:
                self.assertTrue(collect_all("fake-key", output, size=2, delay=0)["full_collection_complete"])
                fetch.assert_not_called()

    def test_wrong_page_short_response_and_missing_code_are_rejected(self):
        for response, page in ((page_response(1), 2), (page_response(1, codes=["practice-1"]), 1),
                               (page_response(1, codes=["", "practice-2"]), 1)):
            with self.subTest(page=page), self.assertRaises(ValueError):
                validate_page(response[0], page, 2, 3)

    def test_changed_page_size_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            with patch("backend.collect_all_food_api.fetch_page", side_effect=lambda k, c, p, s: page_response(p)):
                collect_all("fake-key", output, size=2, delay=0)
            with self.assertRaises(ValueError):
                collect_all("fake-key", output, size=3, delay=0)
