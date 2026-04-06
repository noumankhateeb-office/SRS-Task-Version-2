"""
Evaluation Script
=================
Runs the trained model against the holdout evaluation dataset and writes
prediction artifacts plus a quality report.

Usage:
    python src/evaluate.py
    python src/evaluate.py --eval-data data/evaluation --adapter models/srs-task-adapter
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from generate import DEFAULT_ADAPTER_PATH, TaskGenerator

logger = logging.getLogger(__name__)

DEFAULT_EVAL_DATA_PATH = Path(__file__).parent.parent / "data" / "evaluation"
DEFAULT_RESULTS_DIR = Path(__file__).parent.parent / "evaluation_results"

STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "that", "this", "your", "their",
    "must", "shall", "should", "will", "able", "allow", "allows", "system", "data",
    "management", "platform", "portal", "support", "supports", "module", "service",
    "user", "users", "task", "tasks",
}


def _flatten_expected_output(output_payload: Any) -> list[dict[str, Any]]:
    """Flatten expected output tasks into a single list."""
    if isinstance(output_payload, dict):
        tasks: list[dict[str, Any]] = []
        for value in output_payload.values():
            if isinstance(value, list):
                tasks.extend(task for task in value if isinstance(task, dict))
        return tasks
    if isinstance(output_payload, list):
        return [task for task in output_payload if isinstance(task, dict)]
    return []


def _group_tasks_by_requirement(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group tasks by related requirement ID."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        requirement_id = str(task.get("related_requirement", "-")).strip() or "-"
        grouped[requirement_id].append(task)
    return dict(grouped)


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _extract_keywords(text: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9]+", text.lower())
        if len(token) >= 4 and token not in STOPWORDS
    }
    return tokens


def _count_duplicate_titles(tasks: list[dict[str, Any]]) -> int:
    normalized_titles = [
        _normalize_text(str(task.get("title", "")))
        for task in tasks
        if str(task.get("title", "")).strip()
    ]
    title_counts = Counter(normalized_titles)
    return sum(count - 1 for title, count in title_counts.items() if title and count > 1)


def _is_generic_task(task: dict[str, Any]) -> bool:
    title = str(task.get("title", "")).strip().lower()
    description = str(task.get("description", "")).strip().lower()

    if not title or title.startswith("task "):
        return True
    if title in {"generated output", "backend task", "frontend task", "database task", "testing task"}:
        return True
    if len(description) < 40:
        return True
    return False


def _keyword_recall(expected_tasks: list[dict[str, Any]], generated_tasks: list[dict[str, Any]]) -> float:
    expected_keywords: set[str] = set()
    generated_keywords: set[str] = set()

    for task in expected_tasks:
        expected_keywords.update(_extract_keywords(str(task.get("title", ""))))

    for task in generated_tasks:
        generated_keywords.update(_extract_keywords(str(task.get("title", ""))))
        generated_keywords.update(_extract_keywords(str(task.get("description", ""))))

    if not expected_keywords:
        return 1.0

    matched = len(expected_keywords & generated_keywords)
    return matched / len(expected_keywords)


def _count_alignment_score(expected_count: int, generated_count: int) -> float:
    if expected_count <= 0 and generated_count <= 0:
        return 1.0
    if expected_count <= 0:
        return 0.0
    return max(0.0, 1 - (abs(generated_count - expected_count) / expected_count))


def analyze_prediction(
    source_filename: str,
    input_payload: dict[str, Any],
    expected_output: Any,
    generated_tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare generated tasks to the expected holdout output for one file."""
    expected_tasks = _flatten_expected_output(expected_output)
    expected_by_fr = {
        fr_id: tasks
        for fr_id, tasks in (expected_output.items() if isinstance(expected_output, dict) else [])
    }
    generated_by_fr = _group_tasks_by_requirement(generated_tasks)

    fr_ids = list((input_payload.get("functional_requirements") or {}).keys())
    missing_frs = [fr_id for fr_id in fr_ids if not generated_by_fr.get(fr_id)]

    per_fr_metrics: list[dict[str, Any]] = []
    keyword_recalls: list[float] = []
    alignment_scores: list[float] = []

    for fr_id in fr_ids:
        expected_fr_tasks = expected_by_fr.get(fr_id, [])
        generated_fr_tasks = generated_by_fr.get(fr_id, [])
        keyword_recall = _keyword_recall(expected_fr_tasks, generated_fr_tasks)
        alignment_score = _count_alignment_score(
            len(expected_fr_tasks),
            len(generated_fr_tasks),
        )
        keyword_recalls.append(keyword_recall)
        alignment_scores.append(alignment_score)
        per_fr_metrics.append(
            {
                "fr_id": fr_id,
                "expected_tasks": len(expected_fr_tasks),
                "generated_tasks": len(generated_fr_tasks),
                "keyword_recall": round(keyword_recall, 3),
                "count_alignment": round(alignment_score, 3),
            }
        )

    generated_type_distribution = Counter(
        str(task.get("type", "general")).strip().lower() or "general"
        for task in generated_tasks
    )
    expected_type_distribution = Counter(
        str(task.get("type", "general")).strip().lower() or "general"
        for task in expected_tasks
    )

    acceptance_criteria_tasks = sum(
        1 for task in generated_tasks if task.get("acceptance_criteria")
    )
    generic_task_count = sum(1 for task in generated_tasks if _is_generic_task(task))

    return {
        "source_file": source_filename,
        "project_title": input_payload.get("title", source_filename),
        "fr_count": len(fr_ids),
        "expected_task_count": len(expected_tasks),
        "generated_task_count": len(generated_tasks),
        "fr_coverage_rate": round(
            (len(fr_ids) - len(missing_frs)) / len(fr_ids), 3
        ) if fr_ids else 0.0,
        "missing_requirement_ids": missing_frs,
        "avg_tasks_per_fr": round(
            len(generated_tasks) / len(fr_ids), 3
        ) if fr_ids else 0.0,
        "keyword_recall_avg": round(statistics.mean(keyword_recalls), 3) if keyword_recalls else 0.0,
        "count_alignment_avg": round(statistics.mean(alignment_scores), 3) if alignment_scores else 0.0,
        "duplicate_title_count": _count_duplicate_titles(generated_tasks),
        "generic_task_count": generic_task_count,
        "generic_task_rate": round(generic_task_count / len(generated_tasks), 3) if generated_tasks else 0.0,
        "acceptance_criteria_coverage": round(
            acceptance_criteria_tasks / len(generated_tasks), 3
        ) if generated_tasks else 0.0,
        "generated_type_distribution": dict(generated_type_distribution),
        "expected_type_distribution": dict(expected_type_distribution),
        "per_requirement": per_fr_metrics,
    }


def summarize_run(file_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a run-level summary from per-file metrics."""
    if not file_results:
        return {
            "file_count": 0,
            "overall_quality_score": 0.0,
        }

    fr_counts = [result["fr_count"] for result in file_results]
    generated_counts = [result["generated_task_count"] for result in file_results]
    expected_counts = [result["expected_task_count"] for result in file_results]
    coverage_rates = [result["fr_coverage_rate"] for result in file_results]
    keyword_recalls = [result["keyword_recall_avg"] for result in file_results]
    alignment_scores = [result["count_alignment_avg"] for result in file_results]
    generic_rates = [result["generic_task_rate"] for result in file_results]
    acceptance_coverages = [result["acceptance_criteria_coverage"] for result in file_results]

    overall_quality_score = (
        (statistics.mean(coverage_rates) * 0.30)
        + (statistics.mean(keyword_recalls) * 0.30)
        + (statistics.mean(alignment_scores) * 0.20)
        + (statistics.mean(acceptance_coverages) * 0.10)
        + ((1 - statistics.mean(generic_rates)) * 0.10)
    )

    return {
        "file_count": len(file_results),
        "total_functional_requirements": sum(fr_counts),
        "total_expected_tasks": sum(expected_counts),
        "total_generated_tasks": sum(generated_counts),
        "avg_fr_coverage_rate": round(statistics.mean(coverage_rates), 3),
        "avg_keyword_recall": round(statistics.mean(keyword_recalls), 3),
        "avg_count_alignment": round(statistics.mean(alignment_scores), 3),
        "avg_acceptance_criteria_coverage": round(statistics.mean(acceptance_coverages), 3),
        "avg_generic_task_rate": round(statistics.mean(generic_rates), 3),
        "overall_quality_score": round(overall_quality_score, 3),
    }


def build_recommendations(summary: dict[str, Any], file_results: list[dict[str, Any]]) -> list[str]:
    """Generate practical improvement recommendations from report metrics."""
    recommendations: list[str] = []

    if summary.get("avg_fr_coverage_rate", 0) < 0.95:
        recommendations.append(
            "Generated tasks did not cover every requirement consistently. Tighten per-FR generation constraints and add a post-generation check that every FR produces at least one task."
        )
    if summary.get("avg_keyword_recall", 0) < 0.65:
        recommendations.append(
            "Generated tasks are missing too much requirement-specific language. Expand prompt context with more FR details and add more domain-specific examples to training."
        )
    if summary.get("avg_count_alignment", 0) < 0.60:
        recommendations.append(
            "Task volume per requirement is drifting away from the reference output. Rebalance the training set so multi-step requirements consistently map to multiple implementation tasks."
        )
    if summary.get("avg_generic_task_rate", 0) > 0.15:
        recommendations.append(
            "Too many generated tasks look generic. Increase dataset realism and enforce richer task descriptions with specific deliverables, validations, and system context."
        )
    if summary.get("avg_acceptance_criteria_coverage", 0) < 0.95:
        recommendations.append(
            "Some generated tasks are missing acceptance criteria. Add stricter output validation and reject or repair tasks that do not include definition-of-done bullets."
        )

    high_gap_files = [
        result["source_file"]
        for result in file_results
        if result.get("keyword_recall_avg", 0) < 0.55 or result.get("fr_coverage_rate", 0) < 0.85
    ]
    if high_gap_files:
        recommendations.append(
            "Review the weakest holdout files manually and add similar domains to training: "
            + ", ".join(high_gap_files[:5])
        )

    if not recommendations:
        recommendations.append(
            "Evaluation metrics look healthy. Next improvement should focus on human review scoring and regression tracking across multiple trained model versions."
        )

    return recommendations


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_markdown_report(
    summary: dict[str, Any],
    file_results: list[dict[str, Any]],
    recommendations: list[str],
    adapter_path: Path,
    eval_data_path: Path,
) -> str:
    lines = [
        "# Evaluation Report",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Adapter path: `{adapter_path}`",
        f"- Evaluation data: `{eval_data_path}`",
        "",
        "## Summary",
        "",
        f"- Files evaluated: {summary.get('file_count', 0)}",
        f"- Total FRs: {summary.get('total_functional_requirements', 0)}",
        f"- Expected tasks: {summary.get('total_expected_tasks', 0)}",
        f"- Generated tasks: {summary.get('total_generated_tasks', 0)}",
        f"- Average FR coverage: {summary.get('avg_fr_coverage_rate', 0):.3f}",
        f"- Average keyword recall: {summary.get('avg_keyword_recall', 0):.3f}",
        f"- Average count alignment: {summary.get('avg_count_alignment', 0):.3f}",
        f"- Acceptance criteria coverage: {summary.get('avg_acceptance_criteria_coverage', 0):.3f}",
        f"- Generic task rate: {summary.get('avg_generic_task_rate', 0):.3f}",
        f"- Overall quality score: {summary.get('overall_quality_score', 0):.3f}",
        "",
        "## Recommendations",
        "",
    ]

    for recommendation in recommendations:
        lines.append(f"- {recommendation}")

    lines.extend(["", "## File Breakdown", ""])

    for result in file_results:
        lines.extend(
            [
                f"### {result['source_file']}",
                "",
                f"- Project title: {result['project_title']}",
                f"- FR coverage: {result['fr_coverage_rate']:.3f}",
                f"- Keyword recall: {result['keyword_recall_avg']:.3f}",
                f"- Count alignment: {result['count_alignment_avg']:.3f}",
                f"- Expected vs generated tasks: {result['expected_task_count']} / {result['generated_task_count']}",
                f"- Duplicate titles: {result['duplicate_title_count']}",
                f"- Generic task rate: {result['generic_task_rate']:.3f}",
                f"- Acceptance criteria coverage: {result['acceptance_criteria_coverage']:.3f}",
            ]
        )
        if result["missing_requirement_ids"]:
            lines.append(
                "- Missing requirement IDs: " + ", ".join(result["missing_requirement_ids"])
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def evaluate_dataset(
    eval_data_path: Path,
    adapter_path: Path,
    results_root: Path,
    limit: int | None = None,
) -> Path:
    """Run the model on the evaluation dataset and write report artifacts."""
    eval_files = sorted(eval_data_path.glob("*.json"))
    if limit is not None:
        eval_files = eval_files[:limit]

    if not eval_files:
        raise ValueError(f"No evaluation files found in {eval_data_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = results_root / f"run_{timestamp}"
    predictions_dir = run_dir / "predictions"
    predictions_dir.mkdir(parents=True, exist_ok=True)

    generator = TaskGenerator(adapter_path=adapter_path)
    generator.load_model()

    file_results: list[dict[str, Any]] = []

    for eval_file in eval_files:
        logger.info("Evaluating %s", eval_file.name)
        payload = json.loads(eval_file.read_text(encoding="utf-8"))
        input_payload = payload.get("input", {})
        expected_output = payload.get("output", {})
        generated_tasks = generator.generate_from_json(input_payload)

        prediction_record = {
            "source_file": eval_file.name,
            "project_title": input_payload.get("title", eval_file.stem),
            "generated_tasks": generated_tasks,
        }
        _write_json(predictions_dir / eval_file.name, prediction_record)

        file_results.append(
            analyze_prediction(
                eval_file.name,
                input_payload,
                expected_output,
                generated_tasks,
            )
        )

    summary = summarize_run(file_results)
    recommendations = build_recommendations(summary, file_results)

    report_payload = {
        "metadata": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "adapter_path": str(adapter_path),
            "evaluation_data_path": str(eval_data_path),
            "results_dir": str(run_dir),
        },
        "summary": summary,
        "recommendations": recommendations,
        "files": file_results,
    }

    _write_json(run_dir / "summary.json", report_payload)
    (run_dir / "report.md").write_text(
        _build_markdown_report(summary, file_results, recommendations, adapter_path, eval_data_path),
        encoding="utf-8",
    )

    logger.info("Evaluation report written to %s", run_dir)
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the model against the holdout evaluation dataset and write a quality report.",
    )
    parser.add_argument(
        "--eval-data",
        type=Path,
        default=DEFAULT_EVAL_DATA_PATH,
        help="Path to the holdout evaluation dataset directory.",
    )
    parser.add_argument(
        "--adapter",
        type=Path,
        default=DEFAULT_ADAPTER_PATH,
        help="Path to the trained LoRA adapter directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory where evaluation results should be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for number of evaluation files to process.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = evaluate_dataset(
        eval_data_path=args.eval_data,
        adapter_path=args.adapter,
        results_root=args.output_dir,
        limit=args.limit,
    )
    print(f"Evaluation report saved to {run_dir}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    main()
