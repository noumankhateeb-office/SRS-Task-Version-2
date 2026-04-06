"""
Inference Script (Full Pipeline)
=================================
Runs the complete SRS → Tasks pipeline:
  1. Accept input (PDF, text file, raw text, or pre-parsed JSON)
  2. Extract text from PDF (if applicable)
  3. Stage 1: Parse SRS text → structured JSON
  4. Stage 2: Feed JSON to fine-tuned FLAN-T5 → generate tasks
  5. Output validated tasks as JSON

Usage:
    python src/generate.py --pdf path/to/srs.pdf
    python src/generate.py --file path/to/srs.txt
    python src/generate.py --input "The system shall..."
    python src/generate.py --json path/to/srs.json
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from pdf_parser import extract_text_from_file
from srs_to_json import parse_srs
from prepare_data import MODEL_NAME, INSTRUCTION_PREFIX, MAX_TARGET_LENGTH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ADAPTER_PATH = Path(__file__).parent.parent / "models" / "srs-task-adapter"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Generation parameters
GENERATION_CONFIG = {
    "max_new_tokens": MAX_TARGET_LENGTH,
    "num_beams": 4,
    "early_stopping": True,
    "no_repeat_ngram_size": 3,
    "length_penalty": 1.0,
}


# ---------------------------------------------------------------------------
# Model Loading
# ---------------------------------------------------------------------------

class TaskGenerator:
    """
    Generates development tasks from SRS documents.

    Combines the SRS parser (Stage 1) with the fine-tuned FLAN-T5
    model (Stage 2) for end-to-end task generation.
    """

    def __init__(
        self,
        adapter_path: str | Path = DEFAULT_ADAPTER_PATH,
        base_model: str = MODEL_NAME,
    ):
        """
        Initialize the task generator.

        Args:
            adapter_path: Path to the trained LoRA adapter directory.
            base_model: HuggingFace model identifier for the base model.
        """
        self.adapter_path = Path(adapter_path)
        self.base_model = base_model
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load_model(self) -> None:
        """Load the base model with the trained LoRA adapter."""
        logger.info("Loading base model: %s", self.base_model)
        base_model = AutoModelForSeq2SeqLM.from_pretrained(self.base_model)

        if self.adapter_path.exists():
            logger.info("Loading LoRA adapter from: %s", self.adapter_path)
            self.model = PeftModel.from_pretrained(base_model, str(self.adapter_path))
        else:
            logger.warning(
                "Adapter not found at %s. Using base model without fine-tuning. "
                "Run train.py first for better results.",
                self.adapter_path,
            )
            self.model = base_model

        self.model = self.model.to(self.device)
        self.model.eval()

        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)

        logger.info("Model loaded on device: %s", self.device)

    def generate_from_pdf(self, pdf_path: str | Path) -> list[dict]:
        """
        Generate tasks from an SRS PDF file.

        Full pipeline: PDF → text → JSON → tasks.

        Args:
            pdf_path: Path to the SRS PDF file.

        Returns:
            List of generated task dictionaries.
        """
        logger.info("Processing PDF: %s", pdf_path)

        # Step 1: Extract text
        raw_text = extract_text_from_file(pdf_path)
        logger.info("Extracted %d characters from PDF", len(raw_text))

        return self.generate_from_text(raw_text)

    def generate_from_text(self, srs_text: str) -> list[dict]:
        """
        Generate tasks from raw SRS text.

        Pipeline: text → JSON (Stage 1) → tasks (Stage 2).

        Args:
            srs_text: Raw SRS document text.

        Returns:
            List of generated task dictionaries.
        """
        # Stage 1: Parse SRS → structured JSON
        logger.info("Stage 1: Parsing SRS text to structured JSON...")
        srs_doc = parse_srs(srs_text)
        srs_json = srs_doc.to_dict()

        logger.info(
            "Parsed: %d FRs, %d NFRs",
            len(srs_json.get("functional_requirements", {})),
            len(srs_json.get("non_functional_requirements", {})),
        )

        return self.generate_from_json(srs_json)

    def generate_from_json(self, srs_json: dict) -> list[dict]:
        """
        Generate tasks from a structured SRS JSON.

        Processes each Functional Requirement (FR) individually to match
        the per-FR training format. This avoids token truncation and
        produces much better results.

        Args:
            srs_json: Structured SRS dictionary.

        Returns:
            List of generated task dictionaries (aggregated from all FRs).
        """
        if self.model is None:
            self.load_model()

        title = srs_json.get("title", "")
        techs = srs_json.get("technologies", [])
        frs = srs_json.get("functional_requirements", {})

        if not frs:
            logger.warning("No functional requirements found in SRS JSON.")
            return []

        logger.info(
            "Stage 2: Generating tasks for %d FRs (per-FR processing)...",
            len(frs),
        )

        all_tasks: list[dict] = []

        for fr_id, fr_data in frs.items():
            # Build compact per-FR input (matches training data format)
            fr_input = {
                "title": title,
                "technologies": techs,
                "fr_id": fr_id,
                "fr": fr_data,
            }

            input_text = INSTRUCTION_PREFIX + json.dumps(
                fr_input, separators=(",", ":")
            )

            logger.info(
                "  Processing %s: %s (%d chars)",
                fr_id,
                fr_data.get("title", ""),
                len(input_text),
            )

            # Tokenize
            inputs = self.tokenizer(
                input_text,
                max_length=512,
                truncation=True,
                return_tensors="pt",
            ).to(self.device)

            # Generate
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    **GENERATION_CONFIG,
                )

            # Decode
            raw_output = self.tokenizer.decode(
                output_ids[0], skip_special_tokens=True
            )
            logger.debug("  Raw output for %s: %s", fr_id, raw_output[:300])

            # Parse tasks for this FR
            fr_tasks = self._parse_output(raw_output)

            # Ensure related_requirement is set
            for task in fr_tasks:
                if task.get("related_requirement", "-") == "-":
                    task["related_requirement"] = fr_id

            all_tasks.extend(fr_tasks)

        logger.info("Generated %d total tasks across %d FRs", len(all_tasks), len(frs))
        return all_tasks

    @staticmethod
    def _parse_output(raw_output: str) -> list[dict]:
        """
        Parse and validate the model's raw text output into task dicts.

        Args:
            raw_output: Raw text from model generation.

        Returns:
            List of validated task dictionaries.
        """
        # Try to parse as JSON directly
        try:
            result = json.loads(raw_output)
            if isinstance(result, list):
                return TaskGenerator._normalize_tasks(result)
            if isinstance(result, dict):
                return TaskGenerator._normalize_tasks([result])
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in the output
        json_match = re.search(r"\[.*\]", raw_output, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if isinstance(result, list):
                    return TaskGenerator._normalize_tasks(result)
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in the output
        json_match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if isinstance(result, dict):
                    return TaskGenerator._normalize_tasks([result])
            except json.JSONDecodeError:
                pass

        # Model returned plain text — wrap it as a task
        recovered_tasks = TaskGenerator._recover_tasks_from_text(raw_output)
        if recovered_tasks:
            return recovered_tasks

        logger.warning("Could not parse model output as JSON. Raw output: %s", raw_output)
        return [{"title": "Generated Output", "description": raw_output, "priority": "medium", "type": "general"}]

    @staticmethod
    def _recover_tasks_from_text(raw_output: str) -> list[dict]:
        """
        Recover task-like structures from malformed JSON-ish model output.
        """
        key_pattern = re.compile(
            r'["\']?(title|description|priority|type|related_requirement)["\']?\s*:\s*',
            re.IGNORECASE,
        )
        matches = list(key_pattern.finditer(raw_output))
        if not matches:
            return []

        recovered_items: list[dict] = []
        current_item: dict[str, str] = {}

        for index, match in enumerate(matches):
            key = match.group(1).lower()
            next_start = matches[index + 1].start() if index + 1 < len(matches) else len(raw_output)
            raw_value = raw_output[match.end():next_start]
            cleaned_value = TaskGenerator._clean_recovered_value(raw_value)

            if key == "title" and current_item:
                recovered_items.append(current_item)
                current_item = {}

            current_item[key] = cleaned_value

        if current_item:
            recovered_items.append(current_item)

        return TaskGenerator._normalize_tasks(recovered_items)

    @staticmethod
    def _clean_recovered_value(value: str) -> str:
        """
        Clean a field value extracted from malformed JSON-like text.
        """
        text = value.strip()
        if not text:
            return ""

        if text[0] in {"'", '"'}:
            quote_char = text[0]
            chars: list[str] = []
            escaped = False

            for char in text[1:]:
                if escaped:
                    chars.append(char)
                    escaped = False
                    continue

                if char == "\\":
                    escaped = True
                    continue

                if char == quote_char:
                    break

                chars.append(char)

            text = "".join(chars)
        else:
            text = re.split(r"[\],}]", text, maxsplit=1)[0]

        text = text.replace("\\n", "\n").replace("\\t", "\t")
        text = text.replace('\\"', '"').replace("\\'", "'")
        text = re.sub(r"\s+", " ", text).strip(" \t\r\n,[]{}")
        return text

    @staticmethod
    def _normalize_tasks(items: list) -> list[dict]:
        """
        Normalize a list of items into proper task dictionaries.

        Handles cases where the model outputs strings, partial dicts,
        or other non-standard formats.

        Args:
            items: List of items (may be dicts, strings, or mixed).

        Returns:
            List of properly structured task dicts.
        """
        tasks = []
        for i, item in enumerate(items):
            if isinstance(item, dict):
                # Ensure minimum required fields
                task = {
                    "title": str(item.get("title", f"Task {i + 1}")).strip() or f"Task {i + 1}",
                    "description": str(item.get("description", "")).strip(),
                    "priority": str(item.get("priority", "medium")).strip().lower() or "medium",
                    "type": str(item.get("type", "general")).strip().lower() or "general",
                    "related_requirement": str(item.get("related_requirement", "-")).strip() or "-",
                }
                tasks.append(task)
            elif isinstance(item, str) and item.strip():
                # Convert plain string into a task dict
                tasks.append({
                    "title": item.strip()[:100],
                    "description": item.strip(),
                    "priority": "medium",
                    "type": "general",
                    "related_requirement": "-",
                })
            # Skip None, empty strings, etc.
        return tasks


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

def format_tasks(tasks: list[dict]) -> str:
    """
    Format tasks for console display.

    Args:
        tasks: List of task dictionaries.

    Returns:
        Formatted string for display.
    """
    lines: list[str] = []
    lines.append(f"\n{'='*70}")
    lines.append(f"  GENERATED TASKS ({len(tasks)} total)")
    lines.append(f"{'='*70}\n")

    for i, task in enumerate(tasks, start=1):
        title = task.get("title", "Untitled")
        desc = task.get("description", "No description")
        priority = task.get("priority", "medium").upper()
        task_type = task.get("type", "unknown")
        req = task.get("related_requirement", "-")

        lines.append(f"  [{i}] {title}")
        lines.append(f"      Type: {task_type} | Priority: {priority} | Req: {req}")
        lines.append(f"      {desc}")
        lines.append("")

    lines.append(f"{'='*70}")

    return "\n".join(lines)


def save_tasks(tasks: list[dict], output_path: Path) -> None:
    """
    Save generated tasks to a JSON file.

    Args:
        tasks: List of task dictionaries.
        output_path: Path to save the JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(tasks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Tasks saved to: %s", output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate development tasks from an SRS document.",
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--pdf", type=Path, help="Path to SRS PDF file."
    )
    input_group.add_argument(
        "--file", type=Path, help="Path to SRS text/markdown file."
    )
    input_group.add_argument(
        "--input", type=str, help="Raw SRS text string."
    )
    input_group.add_argument(
        "--json", type=Path, help="Path to pre-parsed SRS JSON file."
    )

    # Options
    parser.add_argument(
        "--adapter",
        type=Path,
        default=DEFAULT_ADAPTER_PATH,
        help="Path to trained LoRA adapter directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "tasks.json",
        help="Path to save generated tasks JSON.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save tasks to file (console output only).",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point for CLI usage."""
    args = parse_args()

    generator = TaskGenerator(adapter_path=args.adapter)

    # Determine input source and generate
    if args.pdf:
        tasks = generator.generate_from_pdf(args.pdf)
    elif args.file:
        raw_text = extract_text_from_file(args.file)
        tasks = generator.generate_from_text(raw_text)
    elif args.input:
        tasks = generator.generate_from_text(args.input)
    elif args.json:
        srs_json = json.loads(args.json.read_text(encoding="utf-8"))
        tasks = generator.generate_from_json(srs_json)
    else:
        logger.error("No input provided.")
        sys.exit(1)

    # Display results
    print(format_tasks(tasks))

    # Save to file
    if not args.no_save:
        save_tasks(tasks, args.output)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    main()
