import unittest

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


if __name__ == "__main__":
    unittest.main()
