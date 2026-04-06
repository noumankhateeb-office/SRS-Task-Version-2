import unittest
from pathlib import Path

from src.srs_to_json import parse_srs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / "samples"


class SRSParserTests(unittest.TestCase):
    def test_markdown_sample_extracts_acceptance_and_out_of_scope(self):
        text = (SAMPLES_DIR / "sample_srs_taskmanager.md").read_text(encoding="utf-8")
        srs = parse_srs(text).to_dict()

        self.assertEqual(srs["title"], "Task Management Application")
        self.assertIn("React", srs["technologies"])
        self.assertEqual(len(srs["functional_requirements"]), 4)
        self.assertEqual(len(srs["non_functional_requirements"]), 2)

        fr1 = srs["functional_requirements"]["FR-01"]
        self.assertEqual(len(fr1["acceptance_criteria"]), 5)
        self.assertNotIn("**Acceptance Criteria**:", fr1["requirements"])
        self.assertIn("Native mobile applications (iOS/Android)", srs["out_of_scope"])
        self.assertNotIn("Native mobile applications (iOS/Android)", srs["system_attributes"]["maintainability"])

    def test_plain_erp_sample_extracts_sections_and_requirements(self):
        text = (SAMPLES_DIR / "sample_srs_erp.md").read_text(encoding="utf-8")
        srs = parse_srs(text).to_dict()

        self.assertEqual(srs["title"], "Enterprise Resource Planning (ERP) System")
        self.assertIn("React", srs["technologies"])
        self.assertIn("Node.js", srs["technologies"])
        self.assertEqual(len(srs["functional_requirements"]), 30)
        self.assertEqual(srs["functional_requirements"]["FR-01"]["title"], "User Authentication")
        self.assertGreaterEqual(
            len(srs["functional_requirements"]["FR-01"]["requirements"]),
            4,
        )
        self.assertEqual(
            srs["operating_environment"]["deployment"],
            "Cloud-based infrastructure (AWS, Azure, or Google Cloud).",
        )
        self.assertIn("responsive", " ".join(srs["external_interfaces"]["user_interface"]).lower())
        self.assertIn(
            "Mobile applications (iOS/Android) will not be developed in the initial release",
            srs["out_of_scope"],
        )


if __name__ == "__main__":
    unittest.main()
