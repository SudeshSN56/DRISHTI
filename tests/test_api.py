import unittest
from fastapi.testclient import TestClient

from api.main import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")

    def test_model_info(self):
        response = self.client.get("/api/model/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("model_name", data)
        self.assertIn("default_classes", data)
        self.assertIn("all_classes", data)
        self.assertIn("person", data["default_classes"])

    def test_model_classes(self):
        response = self.client.get("/api/model/classes")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertIn("car", data)

    def test_sample_videos(self):
        response = self.client.get("/api/model/sample-videos")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_list_runs(self):
        response = self.client.get("/api/runs")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_nonexistent_run_returns_404(self):
        response = self.client.get("/api/runs/nonexistent_run_12345")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
