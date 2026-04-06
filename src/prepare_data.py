"""
Data Preparation Module
========================
Loads training data from a directory of JSON files or a JSONL file,
formats it for FLAN-T5 seq2seq training, tokenizes input/target pairs,
and creates HuggingFace datasets.
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

MODEL_NAME = "google/flan-t5-base"
MAX_INPUT_LENGTH = 512
MAX_TARGET_LENGTH = 1024

INSTRUCTION_PREFIX = (
    "Generate development tasks as JSON from this software requirements specification:\n\n"
)

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
        raise FileNotFoundError(f"Training data path not found: {data_path}")

    if data_path.is_dir():
        return _load_from_directory(data_path)
    else:
        return _load_from_jsonl(data_path)


def _load_from_directory(dir_path: Path) -> list[dict[str, Any]]:
    """
    Load training examples from individual JSON files in a directory.

    Each file contains a full SRS project with multiple FRs. This function
    splits each file into **per-FR training pairs** so that each training
    example is small enough for T5's 512-token input limit.

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
            })

    if not pairs:
        logger.warning("%s: Could not extract per-FR pairs, using whole file.", filename)
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
    Convert raw training data into input-target text pairs for T5.

    The input gets an instruction prefix and the SRS JSON is serialized.
    The target is the tasks array serialized as JSON.

    Args:
        data: List of training examples with 'input' and 'output' fields.

    Returns:
        Dictionary with 'input_text' and 'target_text' lists.
    """
    inputs: list[str] = []
    targets: list[str] = []

    for entry in data:
        # Serialize SRS JSON input
        if isinstance(entry["input"], dict):
            input_json = json.dumps(entry["input"], separators=(",", ":"))
        else:
            input_json = str(entry["input"])

        input_text = INSTRUCTION_PREFIX + input_json
        inputs.append(input_text)

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

    Pads inputs to MAX_INPUT_LENGTH and targets to MAX_TARGET_LENGTH.
    Replaces padding token IDs with -100 in labels so they are ignored
    during loss computation.

    Args:
        dataset: HuggingFace Dataset with 'input_text' and 'target_text' columns.
        tokenizer: T5 tokenizer instance.

    Returns:
        Tokenized dataset ready for training.
    """

    def _tokenize_fn(examples: dict[str, list[str]]) -> dict[str, Any]:
        model_inputs = tokenizer(
            examples["input_text"],
            max_length=MAX_INPUT_LENGTH,
            truncation=True,
            padding="max_length",
        )

        labels = tokenizer(
            text_target=examples["target_text"],
            max_length=MAX_TARGET_LENGTH,
            truncation=True,
            padding="max_length",
        )

        # Replace padding token IDs with -100 (ignored by loss function)
        model_inputs["labels"] = [
            [
                token_id if token_id != tokenizer.pad_token_id else -100
                for token_id in label
            ]
            for label in labels["input_ids"]
        ]

        return model_inputs

    tokenized = dataset.map(
        _tokenize_fn,
        batched=True,
        remove_columns=dataset.column_names,
        desc="Tokenizing dataset",
    )

    return tokenized


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def prepare_datasets(
    data_path: str | Path,
    val_split: float = 0.2,
    model_name: str = MODEL_NAME,
) -> tuple[Dataset, Dataset, AutoTokenizer]:
    """
    Full data preparation pipeline.

    Loads data, formats it, tokenizes, and splits into train/validation.

    Args:
        data_path: Path to the JSONL training data file.
        val_split: Fraction of data to use for validation (0.0 - 1.0).
        model_name: HuggingFace model name for tokenizer.

    Returns:
        Tuple of (train_dataset, val_dataset, tokenizer).
    """
    logger.info("=" * 60)
    logger.info("DATA PREPARATION")
    logger.info("=" * 60)

    # Load raw data (supports directory of JSONs or single JSONL)
    raw_data = load_training_data(data_path)

    if len(raw_data) < 2:
        raise ValueError(
            f"Need at least 2 examples for train/val split, got {len(raw_data)}. "
            "Add more training data to your data/samples/ directory."
        )

    # Format into text pairs
    formatted = format_examples(raw_data)
    dataset = Dataset.from_dict(formatted)

    # Split into train/validation
    split = dataset.train_test_split(test_size=val_split, seed=42)
    logger.info(
        "Split: %d train / %d validation examples",
        len(split["train"]),
        len(split["test"]),
    )

    # Load tokenizer
    logger.info("Loading tokenizer: %s", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Tokenize both splits
    train_dataset = tokenize_dataset(split["train"], tokenizer)
    val_dataset = tokenize_dataset(split["test"], tokenizer)

    logger.info("Data preparation complete!")

    return train_dataset, val_dataset, tokenizer


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    project_root = Path(__file__).parent.parent
    data_path = project_root / "data" / "samples"

    if len(sys.argv) >= 2:
        data_path = Path(sys.argv[1])

    if not data_path.exists():
        logger.error("Data path not found: %s", data_path)
        logger.info("Add training JSON files to: data/samples/")
        sys.exit(1)

    train_ds, val_ds, tok = prepare_datasets(data_path)

    print(f"\nTrain dataset: {len(train_ds)} examples")
    print(f"Val dataset:   {len(val_ds)} examples")
    print(f"Columns:       {train_ds.column_names}")
