import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api import create_app
from backend.prepare_food_sample import NUTRIENTS


def practice_row(code, name):
    return {**{key: 0 for key in NUTRIENTS}, "FOOD_CD": code, "FOOD_NM": name,
            "NUT_CON_SRTR_QUA": "100g", "SRC_NM": "가상 자료", "CRTR_YMD": None,
            "DATA_PROD_NM": "연습용", "UPDATE_DATE": "2026-11-05",
            "ENERC": 200, "PROT": 10, "FIBTG": None}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.rows = [practice_row("practice-1", "연습용 두부"),
                     practice_row("practice-2", "연습용 두부"),
                     practice_row("practice-3", "다른 식품")]
        self.client = TestClient(create_app(rows=self.rows))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_profile_endpoint_and_private_validation(self):
        payload = dict(age=30, height_cm=170, weight_kg=70, equation_sex='female',
                       activity='inactive', scope_confirmed=True)
        response = self.client.post('/profile/estimate', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['maintenance_kcal'], 2167)
        response = self.client.post('/profile/estimate', json=payload | {'private_note':'practice-private-marker'})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('practice-private-marker', response.text)

    def test_health_and_docs(self):
        self.assertEqual(self.client.get("/health").json()["food_count"], 3)
        self.assertEqual(self.client.get("/docs").status_code, 200)
        schema = self.client.get("/openapi.json").json()
        self.assertIn("/meals/calculate", schema["paths"])

    def test_search_pagination_and_projection(self):
        data = self.client.get("/foods", params={"q": " 두부 ", "offset": 1, "limit": 1}).json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["items"][0]["food_code"], "practice-2")
        self.assertEqual(len(data["items"]), 1)
        self.assertNotIn("ENERC", data["items"][0])
        self.assertEqual(self.client.get("/foods", params={"q": "미일치"}).json()["total"], 0)

    def test_invalid_search_parameters(self):
        for params in ({"q": " "}, {"q": "두부", "limit": 101}, {"q": "두부", "offset": -1}, {}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get("/foods", params=params).status_code, 422)

    def test_meal_calculation_preserves_missing_zero_and_source_row(self):
        response = self.client.post("/meals/calculate", json={"entries": [
            {"food_code": "practice-2", "intake_g": 150},
            {"food_code": "practice-1", "intake_g": 50}]})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["totals"]["energy"]["known_total"], 400)
        self.assertIsNone(data["totals"]["fiber"]["known_total"])
        self.assertEqual(data["totals"]["sugar"]["known_total"], 0)
        self.assertEqual([f["source_row_number"] for f in data["foods"]], [2, 1])

    def test_invalid_meal_inputs_and_body_not_echoed(self):
        bodies = [{"entries": []}, {"entries": [{"food_code": "practice-1"}]},
                  {"entries": [{"food_code": "practice-1", "intake_g": 100}], "private_note": "private-example"}]
        bodies += [{"entries": [{"food_code": "practice-1", "intake_g": value}]}
                   for value in (-1, "150", True, "private-example")]
        for body in bodies:
            with self.subTest(body=body):
                response = self.client.post("/meals/calculate", json=body)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn("private-example", response.text)

    def test_nonfinite_numbers_are_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            response = self.client.post("/meals/calculate",
                content='{"entries":[{"food_code":"practice-1","intake_g":' + value + ']}',
                headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 422)

    def test_unknown_code_and_zero_intake(self):
        unknown = self.client.post("/meals/calculate", json={"entries": [
            {"food_code": "unknown", "intake_g": 100}]})
        self.assertEqual(unknown.status_code, 404)
        zero = self.client.post("/meals/calculate", json={"entries": [
            {"food_code": "practice-1", "intake_g": 0}]})
        self.assertEqual(zero.json()["totals"]["energy"]["known_total"], 0)

    def test_missing_data_does_not_start_with_fake_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                with TestClient(create_app(data_path=Path(tmp) / "foods.json")):
                    pass
