import unittest

from fastapi.testclient import TestClient

from src.server import app


class SampleSrsEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_sample_library_returns_expected_entries(self):
        response = self.client.get("/sample-srs")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["status"], "success")
        samples = payload["samples"]
        self.assertTrue(samples)

        sample_ids = {sample["id"] for sample in samples}
        self.assertIn("sample_srs_erp", sample_ids)
        self.assertIn("sample_srs_procurement_portal", sample_ids)
        self.assertIn("sample_srs_university_portal", sample_ids)
        self.assertIn("sample_srs_field_service", sample_ids)

    def test_individual_sample_endpoint_returns_text(self):
        response = self.client.get("/sample-srs/sample_srs_procurement_portal")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["status"], "success")
        sample = payload["sample"]
        self.assertEqual(sample["id"], "sample_srs_procurement_portal")
        self.assertIn("Procurement and Vendor Management Portal", sample["title"])
        self.assertIn("Purchase Requisition Submission", sample["text"])


if __name__ == "__main__":
    unittest.main()
