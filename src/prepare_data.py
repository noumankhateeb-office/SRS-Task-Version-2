"""
Data Preparation Module
========================
Loads training data from a directory of JSON files or a JSONL file,
formats it for causal-instruct LoRA training, tokenizes prompt/response
pairs, and creates HuggingFace datasets.
"""

import json
import logging
from pathlib import Path
from typing import Any

from datasets import Dataset
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_INPUT_LENGTH = 1024
MAX_TARGET_LENGTH = 1536
MAX_SEQUENCE_LENGTH = MAX_INPUT_LENGTH + MAX_TARGET_LENGTH + 1
LEGACY_DATA_PATH_NAME = "samples"
DEFAULT_DATA_PATH_NAME = "training"

INSTRUCTION_PREFIX = (
    "You are a senior software planning assistant.\n"
    "Generate implementation-ready development tasks for the provided functional requirement.\n"
    "Return ONLY a valid JSON array with no markdown fences or commentary.\n"
    "Each task object must contain exactly these keys: "
    "title, description, priority, type, related_requirement, acceptance_criteria.\n"
    "Allowed priority values: high, medium, low.\n"
    "Allowed type values: design, frontend, backend, database, testing, security, integration, devops, general.\n"
    "Use only the task types relevant to the requirement; do not force every type for every requirement.\n"
    "Keep tasks concise, concrete, and directly tied to the requirement.\n\n"
    "SRS JSON:\n"
)
RESPONSE_PREFIX = "\n\nTasks JSON:\n"

CONTEXT_LIST_FIELDS = (
    "technologies",
    "actors",
    "modules",
    "scope",
    "constraints",
)


def build_fr_prompt_input(
    srs_json: dict[str, Any],
    fr_id: str,
    fr_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the compact per-FR prompt payload used for both training and inference.

    The prompt includes the single functional requirement plus the highest-signal
    document context that often influences implementation planning.
    """
    payload: dict[str, Any] = {
        "title": srs_json.get("title", ""),
        "description": srs_json.get("description", ""),
        "fr_id": fr_id,
        "fr": fr_data,
    }

    for field_name in CONTEXT_LIST_FIELDS:
        value = srs_json.get(field_name)
        if value:
            payload[field_name] = value

    system_attributes = srs_json.get("system_attributes") or {}
    if system_attributes:
        payload["system_attributes"] = system_attributes

    operating_environment = srs_json.get("operating_environment") or {}
    if operating_environment:
        payload["operating_environment"] = operating_environment

    non_functional_requirements = srs_json.get("non_functional_requirements") or {}
    if non_functional_requirements:
        payload["non_functional_requirements"] = {
            req_id: req_data.get("title", "")
            for req_id, req_data in non_functional_requirements.items()
            if isinstance(req_data, dict)
        }

    return payload


def build_prompt_text(input_payload: dict[str, Any]) -> str:
    """Build the user prompt text used for both training and inference."""
    if isinstance(input_payload, dict):
        serialized_payload = json.dumps(input_payload, separators=(",", ":"))
    else:
        serialized_payload = str(input_payload)
    return INSTRUCTION_PREFIX + serialized_payload + RESPONSE_PREFIX


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_training_data(data_path: str | Path) -> list[dict[str, Any]]:
    """
    Load training data from a directory of JSON files or a single JSONL file.

    Supports two formats:
    - **Directory**: Reads all .json files in the directory. Each file must
      be a JSON object with 'input' and 'output' fields.
    - **JSONL file**: Reads a single file where each line is a JSON object
      with 'input' and 'output' fields.

    Args:
        data_path: Path to a directory of JSON files or a single JSONL file.

    Returns:
        List of parsed training examples.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If no valid examples are found.
    """
    data_path = Path(data_path)

    if not data_path.exists():
        fallback_path = _resolve_legacy_training_path(data_path)
        if fallback_path is not None:
            logger.warning(
                "Training data path %s not found. Falling back to legacy path %s.",
                data_path,
                fallback_path,
            )
            data_path = fallback_path

    if not data_path.exists():
        raise FileNotFoundError(f"Training data path not found: {data_path}")

    if data_path.is_dir() and data_path.name == LEGACY_DATA_PATH_NAME:
        fallback_path = _resolve_legacy_training_path(data_path)
        if fallback_path is not None:
            legacy_files = list(data_path.glob("*.json"))
            fallback_files = list(fallback_path.glob("*.json"))
            if not legacy_files and fallback_files:
                logger.warning(
                    "Legacy training directory %s is empty. Using %s instead.",
                    data_path,
                    fallback_path,
                )
                data_path = fallback_path

    if data_path.is_dir():
        return _load_from_directory(data_path)
    else:
        return _load_from_jsonl(data_path)


def _load_from_directory(dir_path: Path) -> list[dict[str, Any]]:
    """
    Load training examples from individual JSON files in a directory.

    Each file contains a full SRS project with multiple FRs. This function
    splits each file into **per-FR training pairs** so that each training
    example is small enough for the configured input token limit.

    Input for each pair:
        {"title": "...", "technologies": [...], "fr_id": "FR-01", "fr": {...}}
    Output for each pair:
        [{"title": ..., "description": ..., "priority": ..., "type": ..., ...}]

    Args:
        dir_path: Path to directory containing .json files.

    Returns:
        List of per-FR training examples.
    """
    json_files = sorted(dir_path.glob("*.json"))

    if not json_files:
        raise ValueError(f"No .json files found in {dir_path}")

    data: list[dict[str, Any]] = []
    errors = 0
    files_loaded = 0

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                entry = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning("%s: Invalid JSON (%s), skipping.", file_path.name, e)
            errors += 1
            continue

        if "input" not in entry or "output" not in entry:
            logger.warning(
                "%s: Missing 'input' or 'output' field, skipping.", file_path.name
            )
            errors += 1
            continue

        # Split into per-FR training pairs
        per_fr_pairs = _split_into_fr_pairs(entry, file_path.name)
        data.extend(per_fr_pairs)
        files_loaded += 1
        logger.debug("Loaded %s: %d FR pairs", file_path.name, len(per_fr_pairs))

    if not data:
        raise ValueError(
            f"No valid training examples found in {dir_path}. "
            f"{errors} files had errors."
        )

    logger.info(
        "Loaded %d per-FR training pairs from %d files in %s/ (%d errors skipped)",
        len(data), files_loaded, dir_path.name, errors,
    )

    return data


def _resolve_legacy_training_path(data_path: Path) -> Path | None:
    """Support both `data/samples` and `data/training` during the migration."""
    parts = list(data_path.parts)
    if not parts:
        return None

    if parts[-1] == DEFAULT_DATA_PATH_NAME:
        legacy_path = Path(*parts[:-1], LEGACY_DATA_PATH_NAME)
        if legacy_path.exists():
            return legacy_path

    if parts[-1] == LEGACY_DATA_PATH_NAME:
        modern_path = Path(*parts[:-1], DEFAULT_DATA_PATH_NAME)
        if modern_path.exists():
            return modern_path

    return None


def _split_into_fr_pairs(
    entry: dict[str, Any], filename: str
) -> list[dict[str, Any]]:
    """
    Split a multi-FR training file into individual per-FR training pairs.

    Each pair has a compact input (project context + single FR) and the
    corresponding output tasks for that FR.

    Args:
        entry: Full training file with 'input' and 'output'.
        filename: Source filename for logging.

    Returns:
        List of {"input": {...}, "output": [...]} pairs, one per FR.
    """
    inp = entry["input"]
    out = entry["output"]
    frs = inp.get("functional_requirements", {})

    pairs: list[dict[str, Any]] = []

    # Output keyed by FR-ID  (e.g. {"FR-01": [...], "FR-02": [...]})
    if isinstance(out, dict):
        for fr_id, fr_data in frs.items():
            fr_tasks = out.get(fr_id, [])
            if not fr_tasks:
                continue
            pairs.append({
                "input": build_fr_prompt_input(inp, fr_id, fr_data),
                "output": fr_tasks,
                "source_document": filename,
            })
    # Legacy: output is a flat list of tasks
    elif isinstance(out, list):
        # Try to group tasks by related_requirement
        tasks_by_fr: dict[str, list] = {}
        for task in out:
            req = task.get("related_requirement", "")
            tasks_by_fr.setdefault(req, []).append(task)

        for fr_id, fr_data in frs.items():
            fr_tasks = tasks_by_fr.get(fr_id, [])
            if not fr_tasks:
                continue
            pairs.append({
                "input": build_fr_prompt_input(inp, fr_id, fr_data),
                "output": fr_tasks,
                "source_document": filename,
            })

    if not pairs:
        logger.warning("%s: Could not extract per-FR pairs, using whole file.", filename)
        entry = dict(entry)
        entry["source_document"] = filename
        pairs.append(entry)

    return pairs


def _load_from_jsonl(file_path: Path) -> list[dict[str, Any]]:
    """
    Load training examples from a JSONL file (one JSON per line).

    Args:
        file_path: Path to the JSONL file.

    Returns:
        List of parsed training examples.
    """
    data: list[dict[str, Any]] = []
    errors = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("Line %d: Invalid JSON (%s), skipping.", line_num, e)
                errors += 1
                continue

            if "input" not in entry or "output" not in entry:
                logger.warning(
                    "Line %d: Missing 'input' or 'output' field, skipping.", line_num
                )
                errors += 1
                continue

            if "source_document" not in entry:
                entry["source_document"] = f"{file_path.name}:line-{line_num}"
            data.append(entry)

    if not data:
        raise ValueError(
            f"No valid training examples found in {file_path}. "
            f"{errors} lines had errors."
        )

    logger.info(
        "Loaded %d examples from %s (%d errors skipped)",
        len(data), file_path.name, errors,
    )

    return data


# ---------------------------------------------------------------------------
# Data Formatting
# ---------------------------------------------------------------------------

def format_examples(data: list[dict[str, Any]]) -> dict[str, list[str]]:
    """
    Convert raw training data into prompt/response text pairs.

    The input becomes an instruction prompt with serialized SRS JSON.
    The target is the tasks array serialized as JSON.

    Args:
        data: List of training examples with 'input' and 'output' fields.

    Returns:
        Dictionary with 'input_text' and 'target_text' lists.
    """
    inputs: list[str] = []
    targets: list[str] = []

    for entry in data:
        inputs.append(build_prompt_text(entry["input"]))

        # Serialize tasks output
        if isinstance(entry["output"], (list, dict)):
            target_text = json.dumps(entry["output"], separators=(",", ":"))
        else:
            target_text = str(entry["output"])

        targets.append(target_text)

    return {"input_text": inputs, "target_text": targets}


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

def tokenize_dataset(dataset: Dataset, tokenizer: AutoTokenizer) -> Dataset:
    """
    Tokenize the dataset for model training.

    Builds causal language-model examples where the prompt tokens are masked
    out in the labels and only the target task JSON contributes to the loss.

    Padding is intentionally deferred to the data collator so batches are
    padded only to the longest example they actually contain.

    Args:
        dataset: HuggingFace Dataset with 'input_text' and 'target_text' columns.
        tokenizer: Causal LM tokenizer instance.

    Returns:
        Tokenized dataset ready for training.
    """

    def _tokenize_fn(examples: dict[str, list[str]]) -> dict[str, Any]:
        batch_input_ids: list[list[int]] = []
        batch_attention_mask: list[list[int]] = []
        batch_labels: list[list[int]] = []
        eos_tokens = (
            [tokenizer.eos_token_id]
            if tokenizer.eos_token_id is not None
            else []
        )

        for input_text, target_text in zip(
            examples["input_text"],
            examples["target_text"],
            strict=True,
        ):
            prompt_ids = tokenizer(
                input_text,
                max_length=MAX_INPUT_LENGTH,
                truncation=True,
                add_special_tokens=True,
            )["input_ids"]
            target_ids = tokenizer(
                target_text,
                max_length=MAX_TARGET_LENGTH,
                truncation=True,
                add_special_tokens=False,
            )["input_ids"]

            input_ids = (prompt_ids + target_ids + eos_tokens)[:MAX_SEQUENCE_LENGTH]
            labels = ([-100] * len(prompt_ids) + target_ids + eos_tokens)[
                :MAX_SEQUENCE_LENGTH
            ]
            attention_mask = [1] * len(input_ids)

            batch_input_ids.append(input_ids)
            batch_attention_mask.append(attention_mask)
            batch_labels.append(labels)

        return {
            "input_ids": batch_input_ids,
            "attention_mask": batch_attention_mask,
            "labels": batch_labels,
        }

    tokenized = dataset.map(
        _tokenize_fn,
        batched=True,
        remove_columns=dataset.column_names,
        desc="Tokenizing dataset",
    )

    return tokenized


def prepare_datasets(
    train_data_path: str | Path,
    eval_data_path: str | Path,
    model_name: str = MODEL_NAME,
) -> tuple[Dataset, Dataset, AutoTokenizer]:
    """
    Full data preparation pipeline.

    Loads separate training and evaluation data, formats it, and tokenizes it.

    Args:
        train_data_path: Path to the training data directory or JSONL file.
        eval_data_path: Path to the evaluation data directory or JSONL file.
        model_name: HuggingFace model name for tokenizer.

    Returns:
        Tuple of (train_dataset, val_dataset, tokenizer).
    """
    logger.info("=" * 60)
    logger.info("DATA PREPARATION")
    logger.info("=" * 60)

    train_raw = load_training_data(train_data_path)
    eval_raw = load_training_data(eval_data_path)

    if not train_raw:
        raise ValueError(
            "Training dataset is empty. "
            "Add more training data to your data/training/ directory."
        )

    if not eval_raw:
        raise ValueError(
            "Evaluation dataset is empty. "
            "Add holdout data to your data/evaluation/ directory."
        )

    logger.info("Loaded separate datasets: %d train / %d evaluation examples", len(train_raw), len(eval_raw))

    train_dataset_raw = Dataset.from_dict(format_examples(train_raw))
    val_dataset_raw = Dataset.from_dict(format_examples(eval_raw))

    # Load tokenizer
    logger.info("Loading tokenizer: %s", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Tokenize both splits
    train_dataset = tokenize_dataset(train_dataset_raw, tokenizer)
    val_dataset = tokenize_dataset(val_dataset_raw, tokenizer)

    logger.info("Data preparation complete!")

    return train_dataset, val_dataset, tokenizer


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    project_root = Path(__file__).parent.parent
    train_data_path = project_root / "data" / "training"
    eval_data_path = project_root / "data" / "evaluation"

    if len(sys.argv) >= 2:
        train_data_path = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        eval_data_path = Path(sys.argv[2])

    if not train_data_path.exists():
        logger.error("Training data path not found: %s", train_data_path)
        logger.info("Add training JSON files to: data/training/")
        sys.exit(1)
    if not eval_data_path.exists():
        logger.error("Evaluation data path not found: %s", eval_data_path)
        logger.info("Add evaluation JSON files to: data/evaluation/")
        sys.exit(1)

    train_ds, val_ds, tok = prepare_datasets(train_data_path, eval_data_path)

    print(f"\nTrain dataset: {len(train_ds)} examples")
    print(f"Val dataset:   {len(val_ds)} examples")
    print(f"Columns:       {train_ds.column_names}")
