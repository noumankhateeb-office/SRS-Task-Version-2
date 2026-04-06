import unittest
import json
from pathlib import Path

from src.generate import TaskGenerator


class TaskOutputTests(unittest.TestCase):
    def test_normalize_tasks_preserves_task_acceptance_criteria(self):
        tasks = TaskGenerator._normalize_tasks(
            [
                {
                    "title": "Implement User Authentication Backend Services",
                    "description": "Build the backend services for user authentication.",
                    "priority": "high",
                    "type": "backend",
                    "related_requirement": "FR-01",
                    "acceptance_criteria": [
                        "Validation rules are enforced",
                        "Audit logging is implemented",
                    ],
                }
            ]
        )

        self.assertEqual(len(tasks), 1)
        self.assertEqual(
            tasks[0]["acceptance_criteria"],
            ["Validation rules are enforced", "Audit logging is implemented"],
        )

    def test_erp_sample_uses_task_level_acceptance_criteria_only(self):
        sample_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "training"
            / "51_enterprise_erp.json"
        )
        data = json.loads(sample_path.read_text(encoding="utf-8"))

        functional_requirements = data["input"]["functional_requirements"]
        self.assertTrue(functional_requirements)
        for fr_data in functional_requirements.values():
            self.assertNotIn("acceptance_criteria", fr_data)
            self.assertTrue(fr_data.get("requirements"))

        output = data["output"]
        self.assertTrue(output)
        for tasks in output.values():
            self.assertTrue(tasks)
            for task in tasks:
                self.assertTrue(task.get("acceptance_criteria"))

    def test_legacy_project_management_sample_is_upgraded_to_richer_schema(self):
        sample_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "training"
            / "07_project_management.json"
        )
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        input_payload = data["input"]

        self.assertIn("description", input_payload)
        self.assertIn("actors", input_payload)
        self.assertIn("user_classes", input_payload)
        self.assertIn("constraints", input_payload)
        self.assertIn("operating_environment", input_payload)
        self.assertIn("non_functional_requirements", input_payload)
        self.assertIn("system_attributes", input_payload)

        for fr_data in input_payload["functional_requirements"].values():
            self.assertNotIn("acceptance_criteria", fr_data)

        for tasks in data["output"].values():
            for task in tasks:
                self.assertTrue(task.get("acceptance_criteria"))


if __name__ == "__main__":
    unittest.main()
