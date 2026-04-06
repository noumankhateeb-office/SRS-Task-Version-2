"""
Training Script
================
Fine-tunes FLAN-T5-base with LoRA (Low-Rank Adaptation) for
SRS JSON → Development Tasks generation.

Usage:
    python src/train.py                            # Uses default data path
    python src/train.py --data data/training       # Custom data path
    python src/train.py --epochs 15 --batch-size 2
"""

import argparse
import logging
import sys
from pathlib import Path

import torch
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)
from peft import LoraConfig, TaskType, get_peft_model

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from prepare_data import prepare_datasets, MODEL_NAME, MAX_TARGET_LENGTH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DATA_PATH = Path(__file__).parent.parent / "data" / "training"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "models" / "srs-task-adapter"

LORA_CONFIG = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q", "v"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.SEQ_2_SEQ_LM,
)


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
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Apply LoRA
    logger.info("Applying LoRA configuration (r=%d, alpha=%d)", LORA_CONFIG.r, LORA_CONFIG.lora_alpha)
    model = get_peft_model(model, LORA_CONFIG)

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
    epochs: int = 15,
    batch_size: int = 4,
    learning_rate: float = 3e-4,
    gradient_accumulation_steps: int = 2,
) -> Seq2SeqTrainingArguments:
    """
    Create training arguments for Seq2SeqTrainer.

    Args:
        output_dir: Directory to save model checkpoints.
        epochs: Number of training epochs.
        batch_size: Per-device batch size.
        learning_rate: Learning rate for AdamW optimizer.
        gradient_accumulation_steps: Steps to accumulate gradients.

    Returns:
        Configured Seq2SeqTrainingArguments.
    """
    return Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_steps=50,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        predict_with_generate=True,
        generation_max_length=MAX_TARGET_LENGTH,
        fp16=False,
        report_to="none",
        remove_unused_columns=False,
    )


# ---------------------------------------------------------------------------
# Main Training Function
# ---------------------------------------------------------------------------

def train(
    data_path: Path = DEFAULT_DATA_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    epochs: int = 15,
    batch_size: int = 4,
    learning_rate: float = 3e-4,
) -> None:
    """
    Run the full training pipeline.

    Args:
        data_path: Path to training data directory (JSON files) or JSONL file.
        output_dir: Directory to save the trained LoRA adapter.
        epochs: Number of training epochs.
        batch_size: Per-device batch size.
        learning_rate: Learning rate.
    """
    logger.info("=" * 60)
    logger.info("SRS → TASKS MODEL TRAINING")
    logger.info("=" * 60)

    # Detect device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Device: %s", device)

    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        logger.info("GPU: %s (%.1f GB)", gpu_name, gpu_mem)

    # Prepare data
    train_dataset, val_dataset, tokenizer = prepare_datasets(data_path)

    # Setup model
    model, _ = setup_model()

    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
        label_pad_token_id=-100,
    )

    # Training arguments
    training_args = get_training_args(
        output_dir=output_dir,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
    )

    # Trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
        data_collator=data_collator,
    )

    # Train
    logger.info("Starting training...")
    logger.info("  Epochs: %d", epochs)
    logger.info("  Batch size: %d", batch_size)
    logger.info("  Learning rate: %s", learning_rate)
    logger.info("  Train examples: %d", len(train_dataset))
    logger.info("  Val examples: %d", len(val_dataset))

    train_result = trainer.train()

    # Log results
    logger.info("Training complete!")
    logger.info("  Train loss: %.4f", train_result.training_loss)
    logger.info(
        "  Train time: %.1f seconds",
        train_result.metrics.get("train_runtime", 0),
    )

    # Save the LoRA adapter
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
        description="Fine-tune FLAN-T5-base with LoRA for SRS → Tasks generation."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to training data directory or JSONL file.",
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
        default=15,
        help="Number of training epochs (default: 15).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Per-device batch size (default: 4, reduce if OOM).",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=3e-4,
        help="Learning rate (default: 3e-4).",
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
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )
