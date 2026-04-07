import unittest
import json
from unittest.mock import patch

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

    def test_generate_tasks_stream_text_returns_progress_events(self):
        class StubDoc:
            def to_dict(self):
                return {
                    "functional_requirements": {
                        "FR-01": {
                            "title": "User Login",
                            "requirements": ["Users can sign in with email and password."],
                        }
                    },
                    "non_functional_requirements": {},
                }

        class StubGenerator:
            def iter_generate_from_json(self, _srs_json):
                yield {
                    "event": "stage",
                    "stage": "generate",
                    "message": "Generating tasks for 1 requirements...",
                    "total_requirements": 1,
                }
                yield {
                    "event": "progress",
                    "stage": "generate",
                    "message": "Generating tasks for FR-01: User Login",
                    "current_requirement": 1,
                    "total_requirements": 1,
                    "requirement_id": "FR-01",
                    "requirement_title": "User Login",
                    "total_task_count": 0,
                }
                yield {
                    "event": "task_batch",
                    "stage": "generate",
                    "message": "Generated 1 task for FR-01",
                    "current_requirement": 1,
                    "total_requirements": 1,
                    "requirement_id": "FR-01",
                    "requirement_title": "User Login",
                    "generated_task_count": 1,
                    "total_task_count": 1,
                    "tasks": [
                        {
                            "title": "Build Login API",
                            "description": "Create secure login and session endpoints.",
                            "priority": "high",
                            "type": "backend",
                            "related_requirement": "FR-01",
                            "acceptance_criteria": ["Users can authenticate successfully."],
                        }
                    ],
                }
                yield {
                    "event": "complete",
                    "message": "Generated 1 tasks across 1 requirements.",
                    "task_count": 1,
                    "tasks": [
                        {
                            "title": "Build Login API",
                            "description": "Create secure login and session endpoints.",
                            "priority": "high",
                            "type": "backend",
                            "related_requirement": "FR-01",
                            "acceptance_criteria": ["Users can authenticate successfully."],
                        }
                    ],
                    "total_requirements": 1,
                }

        with patch("src.server.parse_srs", return_value=StubDoc()):
            with patch("src.server.get_generator", return_value=StubGenerator()):
                response = self.client.post(
                    "/generate-tasks-stream-text",
                    json={"text": "### FR-01: User Login"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/x-ndjson", response.headers["content-type"])

        events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
        self.assertGreaterEqual(len(events), 4)
        self.assertEqual(events[0]["stage"], "parse")
        self.assertEqual(events[1]["stage"], "parse_complete")
        self.assertEqual(events[-1]["event"], "complete")
        self.assertEqual(events[-1]["task_count"], 1)


if __name__ == "__main__":
    unittest.main()
