"""
Inference Script (Full Pipeline)
=================================
Runs the complete SRS to tasks pipeline:
  1. Accept input (PDF, text file, raw text, or pre-parsed JSON)
  2. Extract text from PDF (if applicable)
  3. Stage 1: Parse SRS text to structured JSON
  4. Stage 2: Feed JSON to fine-tuned Qwen with LoRA to generate tasks
  5. Output validated tasks as JSON
"""

import argparse
import json
import logging
import re
import sys
from collections.abc import Iterator
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from pdf_parser import extract_text_from_file
from prepare_data import (
    MODEL_NAME,
    MAX_INPUT_LENGTH,
    MAX_TARGET_LENGTH,
    build_fr_prompt_input,
    build_prompt_text,
)
from srs_to_json import parse_srs

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ADAPTER_PATH = Path(__file__).parent.parent / "models" / "srs-task-adapter"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "output"

GENERATION_CONFIG = {
    "max_new_tokens": MAX_TARGET_LENGTH,
    "do_sample": False,
    "repetition_penalty": 1.05,
}

ALLOWED_PRIORITIES = {"high", "medium", "low"}
ALLOWED_TYPES = {
    "design",
    "frontend",
    "backend",
    "database",
    "testing",
    "security",
    "integration",
    "devops",
    "general",
}


# ---------------------------------------------------------------------------
# Model Loading
# ---------------------------------------------------------------------------

class TaskGenerator:
    """
    Generates development tasks from SRS documents.

    Combines the SRS parser (Stage 1) with the fine-tuned Qwen
    model (Stage 2) for end-to-end task generation.
    """

    def __init__(
        self,
        adapter_path: str | Path = DEFAULT_ADAPTER_PATH,
        base_model: str = MODEL_NAME,
    ):
        self.adapter_path = Path(adapter_path)
        self.base_model = base_model
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load_model(self) -> None:
        """Load the base model with the trained LoRA adapter."""
        logger.info("Loading base model: %s", self.base_model)

        torch_dtype = torch.float32
        if torch.cuda.is_available():
            torch_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            torch_dtype=torch_dtype,
        )

        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"

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

        self.model.config.pad_token_id = self.tokenizer.pad_token_id
        self.model = self.model.to(self.device)
        self.model.eval()

        logger.info("Model loaded on device: %s", self.device)

    def generate_from_pdf(self, pdf_path: str | Path) -> list[dict]:
        """Generate tasks from an SRS PDF file."""
        logger.info("Processing PDF: %s", pdf_path)
        raw_text = extract_text_from_file(pdf_path)
        logger.info("Extracted %d characters from PDF", len(raw_text))
        return self.generate_from_text(raw_text)

    def generate_from_text(self, srs_text: str) -> list[dict]:
        """Generate tasks from raw SRS text."""
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
        """Generate tasks from a structured SRS JSON."""
        final_tasks: list[dict] = []

        for event in self.iter_generate_from_json(srs_json):
            if event.get("event") == "complete":
                final_tasks = event.get("tasks", [])

        return final_tasks

    def iter_generate_from_json(self, srs_json: dict) -> Iterator[dict]:
        """Generate tasks from a structured SRS JSON and emit progress events."""
        if self.model is None:
            self.load_model()

        frs = srs_json.get("functional_requirements", {})

        if not frs:
            logger.warning("No functional requirements found in SRS JSON.")
            yield {
                "event": "complete",
                "message": "No functional requirements found in the SRS.",
                "task_count": 0,
                "tasks": [],
                "total_requirements": 0,
            }
            return

        total_requirements = len(frs)
        logger.info(
            "Stage 2: Generating tasks for %d FRs (per-FR processing)...",
            total_requirements,
        )

        yield {
            "event": "stage",
            "stage": "generate",
            "message": f"Generating tasks for {total_requirements} requirements...",
            "total_requirements": total_requirements,
        }

        all_tasks: list[dict] = []

        for index, (fr_id, fr_data) in enumerate(frs.items(), start=1):
            fr_input = build_fr_prompt_input(srs_json, fr_id, fr_data)
            fr_title = fr_data.get("title", "").strip() or "Untitled Requirement"
            input_text = build_prompt_text(fr_input)

            logger.info(
                "  Processing %s: %s (%d chars)",
                fr_id,
                fr_title,
                len(input_text),
            )

            yield {
                "event": "progress",
                "stage": "generate",
                "message": f"Generating tasks for {fr_id}: {fr_title}",
                "current_requirement": index,
                "total_requirements": total_requirements,
                "requirement_id": fr_id,
                "requirement_title": fr_title,
                "total_task_count": len(all_tasks),
            }

            inputs = self.tokenizer(
                input_text,
                max_length=MAX_INPUT_LENGTH,
                truncation=True,
                return_tensors="pt",
            ).to(self.device)

            generation_kwargs = dict(GENERATION_CONFIG)
            generation_kwargs["pad_token_id"] = self.tokenizer.pad_token_id
            generation_kwargs["eos_token_id"] = self.tokenizer.eos_token_id

            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    **generation_kwargs,
                )

            prompt_length = inputs["input_ids"].shape[1]
            generated_ids = output_ids[0][prompt_length:]
            raw_output = self.tokenizer.decode(
                generated_ids,
                skip_special_tokens=True,
            ).strip()
            logger.debug("  Raw output for %s: %s", fr_id, raw_output[:300])

            fr_tasks = self._parse_output(raw_output)

            for task in fr_tasks:
                if task.get("related_requirement", "-") == "-":
                    task["related_requirement"] = fr_id

            all_tasks.extend(fr_tasks)
            batch_count = len(fr_tasks)

            yield {
                "event": "task_batch",
                "stage": "generate",
                "message": (
                    f"Generated {batch_count} task"
                    f"{'' if batch_count == 1 else 's'} for {fr_id}"
                ),
                "current_requirement": index,
                "total_requirements": total_requirements,
                "requirement_id": fr_id,
                "requirement_title": fr_title,
                "generated_task_count": batch_count,
                "total_task_count": len(all_tasks),
                "tasks": fr_tasks,
            }

        logger.info(
            "Generated %d total tasks across %d FRs",
            len(all_tasks),
            total_requirements,
        )
        yield {
            "event": "complete",
            "message": (
                f"Generated {len(all_tasks)} tasks across "
                f"{total_requirements} requirements."
            ),
            "task_count": len(all_tasks),
            "tasks": all_tasks,
            "total_requirements": total_requirements,
        }

    @staticmethod
    def _normalize_enum(value: str, allowed_values: set[str], default: str) -> str:
        cleaned = str(value or "").strip().lower()
        if cleaned in allowed_values:
            return cleaned
        for allowed in allowed_values:
            if allowed in cleaned:
                return allowed
        return default

    @staticmethod
    def _parse_output(raw_output: str) -> list[dict]:
        """Parse and validate the model's raw text output into task dicts."""
        try:
            result = json.loads(raw_output)
            if isinstance(result, list):
                return TaskGenerator._normalize_tasks(result)
            if isinstance(result, dict):
                return TaskGenerator._normalize_tasks([result])
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"\[.*\]", raw_output, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if isinstance(result, list):
                    return TaskGenerator._normalize_tasks(result)
            except json.JSONDecodeError:
                pass

        json_match = re.search(r"\{.*\}", raw_output, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if isinstance(result, dict):
                    return TaskGenerator._normalize_tasks([result])
            except json.JSONDecodeError:
                pass

        recovered_tasks = TaskGenerator._recover_tasks_from_text(raw_output)
        if recovered_tasks:
            return recovered_tasks

        logger.warning("Could not parse model output as JSON. Raw output: %s", raw_output)
        return [
            {
                "title": "Generated Output",
                "description": raw_output,
                "priority": "medium",
                "type": "general",
                "related_requirement": "-",
                "acceptance_criteria": [],
            }
        ]

    @staticmethod
    def _recover_tasks_from_text(raw_output: str) -> list[dict]:
        """Recover task-like structures from malformed JSON-ish model output."""
        key_pattern = re.compile(
            r'["\']?(title|description|priority|type|related_requirement|acceptance_criteria)["\']?\s*:\s*',
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
        """Clean a field value extracted from malformed JSON-like text."""
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
    def _normalize_acceptance_criteria(value) -> list[str]:
        """Normalize acceptance criteria into a clean list of strings."""
        if value is None:
            return []

        if isinstance(value, list):
            items = value
        else:
            text = str(value).strip()
            if not text:
                return []
            items = re.split(r"\n+|(?<=\.)\s+(?=[A-Z0-9-])|;\s*", text)

        cleaned_items: list[str] = []
        for item in items:
            cleaned = str(item).strip()
            cleaned = re.sub(r"^\s*[-*•]\s+", "", cleaned)
            cleaned = cleaned.strip(" \t\r\n,[]{}")
            if cleaned:
                cleaned_items.append(cleaned)

        return list(dict.fromkeys(cleaned_items))

    @staticmethod
    def _normalize_tasks(items: list) -> list[dict]:
        """Normalize a list of items into proper task dictionaries."""
        tasks = []
        for i, item in enumerate(items):
            if isinstance(item, dict):
                task = {
                    "title": str(item.get("title", f"Task {i + 1}")).strip() or f"Task {i + 1}",
                    "description": str(item.get("description", "")).strip(),
                    "priority": TaskGenerator._normalize_enum(
                        str(item.get("priority", "medium")),
                        ALLOWED_PRIORITIES,
                        "medium",
                    ),
                    "type": TaskGenerator._normalize_enum(
                        str(item.get("type", "general")),
                        ALLOWED_TYPES,
                        "general",
                    ),
                    "related_requirement": str(item.get("related_requirement", "-")).strip() or "-",
                    "acceptance_criteria": TaskGenerator._normalize_acceptance_criteria(
                        item.get("acceptance_criteria", [])
                    ),
                }
                tasks.append(task)
            elif isinstance(item, str) and item.strip():
                tasks.append(
                    {
                        "title": item.strip()[:100],
                        "description": item.strip(),
                        "priority": "medium",
                        "type": "general",
                        "related_requirement": "-",
                        "acceptance_criteria": [],
                    }
                )
        return tasks


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

def format_tasks(tasks: list[dict]) -> str:
    """Format tasks for console display."""
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
        acceptance = task.get("acceptance_criteria", [])

        lines.append(f"  [{i}] {title}")
        lines.append(f"      Type: {task_type} | Priority: {priority} | Req: {req}")
        lines.append(f"      {desc}")
        for criterion in acceptance:
            lines.append(f"      - {criterion}")
        lines.append("")

    lines.append(f"{'='*70}")
    return "\n".join(lines)


def save_tasks(tasks: list[dict], output_path: Path) -> None:
    """Save generated tasks to a JSON file."""
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

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pdf", type=Path, help="Path to SRS PDF file.")
    input_group.add_argument("--file", type=Path, help="Path to SRS text/markdown file.")
    input_group.add_argument("--input", type=str, help="Raw SRS text string.")
    input_group.add_argument("--json", type=Path, help="Path to pre-parsed SRS JSON file.")

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

    print(format_tasks(tasks))

    if not args.no_save:
        save_tasks(tasks, args.output)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    main()
