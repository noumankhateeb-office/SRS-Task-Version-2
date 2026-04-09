"""
Training Script
================
Fine-tunes Qwen2.5-1.5B-Instruct with LoRA (Low-Rank Adaptation) for
SRS JSON to development task generation.

Usage:
    python src/train.py
    python src/train.py --data data/training --eval-data data/evaluation
    python src/train.py --epochs 5 --batch-size 1
"""

import argparse
import logging
import sys
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from prepare_data import MODEL_NAME, prepare_datasets

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DATA_PATH = Path(__file__).parent.parent / "data" / "training"
DEFAULT_EVAL_DATA_PATH = Path(__file__).parent.parent / "data" / "evaluation"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "models" / "srs-task-adapter"

LORA_CONFIG = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_data_collator(tokenizer: AutoTokenizer):
    """Pad each batch to its longest example instead of a global max length."""

    pad_token_id = tokenizer.pad_token_id

    def collate(features: list[dict]) -> dict[str, torch.Tensor]:
        max_length = max(len(feature["input_ids"]) for feature in features)

        batch_input_ids: list[list[int]] = []
        batch_attention_mask: list[list[int]] = []
        batch_labels: list[list[int]] = []

        for feature in features:
            pad_length = max_length - len(feature["input_ids"])
            batch_input_ids.append(feature["input_ids"] + ([pad_token_id] * pad_length))
            batch_attention_mask.append(feature["attention_mask"] + ([0] * pad_length))
            batch_labels.append(feature["labels"] + ([-100] * pad_length))

        return {
            "input_ids": torch.tensor(batch_input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(batch_attention_mask, dtype=torch.long),
            "labels": torch.tensor(batch_labels, dtype=torch.long),
        }

    return collate


# ---------------------------------------------------------------------------
# Training Setup
# ---------------------------------------------------------------------------

def setup_model(model_name: str = MODEL_NAME) -> tuple:
    """
    Load the base model and apply LoRA configuration.

    Args:
        model_name: HuggingFace model identifier.

    Returns:
        Tuple of (model, tokenizer).
    """
    logger.info("Loading base model: %s", model_name)

    torch_dtype = torch.float32
    if torch.cuda.is_available():
        torch_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch_dtype,
        low_cpu_mem_usage=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.use_cache = False

    # Apply LoRA
    logger.info(
        "Applying LoRA configuration (r=%d, alpha=%d)",
        LORA_CONFIG.r,
        LORA_CONFIG.lora_alpha,
    )
    model = get_peft_model(model, LORA_CONFIG)
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()

    # Log trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_pct = 100 * trainable_params / total_params

    logger.info(
        "Trainable parameters: %s / %s (%.2f%%)",
        f"{trainable_params:,}",
        f"{total_params:,}",
        trainable_pct,
    )

    return model, tokenizer


def get_training_args(
    output_dir: Path,
    epochs: int = 5,
    batch_size: int = 1,
    learning_rate: float = 2e-4,
    gradient_accumulation_steps: int = 1,
) -> TrainingArguments:
    """
    Create training arguments for causal LM fine-tuning.

    Args:
        output_dir: Directory to save model checkpoints.
        epochs: Number of training epochs.
        batch_size: Per-device batch size.
        learning_rate: Learning rate for AdamW optimizer.
        gradient_accumulation_steps: Steps to accumulate gradients.

    Returns:
        Configured TrainingArguments.
    """
    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    use_fp16 = torch.cuda.is_available() and not use_bf16

    return TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_steps=20,
        logging_steps=1,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        greater_is_better=False,
        bf16=use_bf16,
        fp16=use_fp16,
        report_to="none",
        remove_unused_columns=False,
        gradient_checkpointing=True,
    )


# ---------------------------------------------------------------------------
# Main Training Function
# ---------------------------------------------------------------------------

def train(
    data_path: Path = DEFAULT_DATA_PATH,
    eval_data_path: Path = DEFAULT_EVAL_DATA_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    epochs: int = 5,
    batch_size: int = 1,
    learning_rate: float = 2e-4,
    gradient_accumulation_steps: int = 1,
) -> None:
    """
    Run the full training pipeline.

    Args:
        data_path: Path to training data directory (JSON files) or JSONL file.
        eval_data_path: Path to holdout evaluation data directory or JSONL file.
        output_dir: Directory to save the trained LoRA adapter.
        epochs: Number of training epochs.
        batch_size: Per-device batch size.
        learning_rate: Learning rate.
        gradient_accumulation_steps: Number of mini-batches to accumulate before an optimizer step.
        no_eval: Whether to disable evaluation and validation data generation.
    """
    logger.info("=" * 60)
    logger.info("SRS TO TASKS MODEL TRAINING")
    logger.info("=" * 60)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Device: %s", device)

    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        logger.info("GPU: %s (%.1f GB)", gpu_name, gpu_mem)

    train_dataset, val_dataset, tokenizer = prepare_datasets(
        data_path,
        eval_data_path,
    )

    model, _ = setup_model()
    data_collator = _build_data_collator(tokenizer)

    training_args = get_training_args(
        output_dir=output_dir,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        gradient_accumulation_steps=gradient_accumulation_steps,
    )

    if eval_data_path is None:
        training_args.eval_strategy = "no"
        training_args.save_strategy = "epoch"
        val_dataset = None

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        data_collator=data_collator,
    )

    logger.info("Starting training...")
    logger.info("  Epochs: %d", epochs)
    logger.info("  Batch size: %d", batch_size)
    logger.info("  Gradient accumulation: %d", gradient_accumulation_steps)
    logger.info("  Learning rate: %s", learning_rate)
    logger.info("  Train examples: %d", len(train_dataset))
    if val_dataset is not None:
        logger.info("  Eval examples: %d", len(val_dataset))
    else:
        logger.info("  Eval examples: 0 (disabled)")

    train_result = trainer.train()

    logger.info("Training complete!")
    logger.info("  Train loss: %.4f", train_result.training_loss)
    logger.info(
        "  Train time: %.1f seconds",
        train_result.metrics.get("train_runtime", 0),
    )

    logger.info("Saving LoRA adapter to: %s", output_dir)
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("Adapter saved to: %s", output_dir)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fine-tune Qwen2.5-1.5B-Instruct with LoRA for SRS to tasks generation."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to training data directory or JSONL file.",
    )
    parser.add_argument(
        "--eval-data",
        type=Path,
        default=DEFAULT_EVAL_DATA_PATH,
        help="Path to holdout evaluation data directory or JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save trained model adapter.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=5,
        help="Number of training epochs (default: 5).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Per-device batch size (default: 1, reduce if OOM).",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=2e-4,
        help="Learning rate (default: 2e-4).",
    )
    parser.add_argument(
        "--grad-accum",
        type=int,
        default=1,
        help="Gradient accumulation steps (default: 1 for 8GB-class GPUs).",
    )
    parser.add_argument(
        "--no-eval",
        action="store_true",
        help="Disable evaluation logic during training.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    args = parse_args()

    train(
        data_path=args.data,
        eval_data_path=None if args.no_eval else args.eval_data,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        gradient_accumulation_steps=args.grad_accum,
    )
