import unittest

from src.evaluate import (
    analyze_prediction,
    build_recommendations,
    summarize_run,
)


class EvaluationAnalysisTests(unittest.TestCase):
    def test_analyze_prediction_reports_expected_metrics(self):
        input_payload = {
            "title": "Example Platform",
            "functional_requirements": {
                "FR-01": {"title": "User Authentication", "requirements": ["Users must sign in."]},
                "FR-02": {"title": "Audit Trail", "requirements": ["System must log user actions."]},
            },
        }
        expected_output = {
            "FR-01": [
                {
                    "title": "Build Authentication API",
                    "description": "Create login and session endpoints.",
                    "type": "backend",
                    "related_requirement": "FR-01",
                    "acceptance_criteria": ["Login validates credentials."],
                }
            ],
            "FR-02": [
                {
                    "title": "Implement Audit Log Persistence",
                    "description": "Store access and change events with actor details.",
                    "type": "database",
                    "related_requirement": "FR-02",
                    "acceptance_criteria": ["Audit records are persisted."],
                }
            ],
        }
        generated_tasks = [
            {
                "title": "Build Authentication API",
                "description": "Create secure login endpoints with validation and session handling.",
                "type": "backend",
                "related_requirement": "FR-01",
                "acceptance_criteria": ["Login validates credentials."],
            }
        ]

        result = analyze_prediction(
            "eval_example.json",
            input_payload,
            expected_output,
            generated_tasks,
        )

        self.assertEqual(result["source_file"], "eval_example.json")
        self.assertEqual(result["generated_task_count"], 1)
        self.assertEqual(result["expected_task_count"], 2)
        self.assertEqual(result["missing_requirement_ids"], ["FR-02"])
        self.assertGreaterEqual(result["fr_coverage_rate"], 0.5)
        self.assertEqual(result["acceptance_criteria_coverage"], 1.0)

    def test_summary_and_recommendations_flag_weak_run(self):
        file_results = [
            {
                "source_file": "eval_01.json",
                "fr_count": 4,
                "expected_task_count": 12,
                "generated_task_count": 5,
                "fr_coverage_rate": 0.5,
                "keyword_recall_avg": 0.3,
                "count_alignment_avg": 0.25,
                "generic_task_rate": 0.4,
                "acceptance_criteria_coverage": 0.5,
            }
        ]

        summary = summarize_run(file_results)
        recommendations = build_recommendations(summary, file_results)

        self.assertLess(summary["overall_quality_score"], 0.6)
        self.assertTrue(recommendations)
        self.assertTrue(
            any("holdout files" in recommendation or "coverage" in recommendation.lower()
                for recommendation in recommendations)
        )


if __name__ == "__main__":
    unittest.main()
