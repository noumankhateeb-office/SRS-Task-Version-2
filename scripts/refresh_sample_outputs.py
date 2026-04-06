"""
Refresh task outputs for all sample JSON files using the current task generator.

This keeps the training outputs aligned with the latest task schema:
- multiple detailed tasks per FR
- task-level acceptance criteria
- descriptions that explain how the work should be performed
"""

from __future__ import annotations

import json
from pathlib import Path

from generate_samples import generate_tasks_for_fr


def refresh_outputs(samples_dir: Path) -> int:
    """Rewrite the `output` section for every sample JSON file."""
    updated = 0

    for path in sorted(samples_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        input_payload = data.get("input", {})
        title = input_payload.get("title", "Unknown Project")
        technologies = input_payload.get("technologies", [])
        frs = input_payload.get("functional_requirements", {})

        new_output = {}
        for fr_id, fr_data in frs.items():
            new_output[fr_id] = generate_tasks_for_fr(
                fr_id,
                fr_data.get("title", fr_id),
                title,
                technologies,
                fr_data,
            )

        data["output"] = new_output
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        updated += 1

    return updated


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    samples_dir = project_root / "data" / "training"
    updated = refresh_outputs(samples_dir)
    print(f"Updated outputs for {updated} sample files")


if __name__ == "__main__":
    main()
