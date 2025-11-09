#!/usr/bin/env python3
"""Fine-tune Mistral-7B-Instruct with LoRA for BA role.

Based on: docs/fase8_finetuning_plan.md
"""

import json
import logging
from pathlib import Path
from typing import Optional

import torch
import typer
import yaml
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

app = typer.Typer(help="Fine-tune Mistral-7B-Instruct with LoRA for BA role")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def format_example_for_instruction_tuning(example: dict) -> str:
    """Format example for Mistral instruction tuning format.

    Uses [INST]...[/INST] format for Mistral-Instruct models.
    """
    concept = example["concept"]
    requirements = example["requirements"]

    # Serialize requirements to YAML
    requirements_yaml = yaml.safe_dump(
        requirements,
        allow_unicode=True,
        default_flow_style=False
    )

    # Mistral Instruct format
    prompt = f"""[INST] You are a Business Analyst. Generate detailed business requirements for the following concept:

Concept: {concept}

Generate a structured requirements document with:
- title: A clear, concise title for the project
- description: A detailed description of the project (minimum 50 characters)
- functional_requirements: A list of functional requirements (minimum 2), each with:
  - id: Unique identifier (format: FR001, FR002, etc.)
  - description: Detailed description of the requirement
  - priority: Priority level (High, Medium, Low)
- non_functional_requirements: A list of non-functional requirements (minimum 2), each with:
  - id: Unique identifier (format: NFR001, NFR002, etc.)
  - description: Detailed description of the requirement
  - priority: Priority level (High, Medium, Low)
- constraints: A list of constraints (minimum 2), each with:
  - id: Unique identifier (format: C001, C002, etc.)
  - description: Detailed description of the constraint
  - priority: Priority level (High, Medium, Low)
[/INST]

{requirements_yaml}"""

    return prompt


def load_and_prepare_datasets(
    train_path: Path,
    val_path: Path,
    tokenizer,
    max_length: int = 2048,
    train_limit: Optional[int] = None,
    val_limit: Optional[int] = None,
) -> tuple[Dataset, Dataset]:
    """Load JSONL datasets and prepare for training."""
    logger.info(f"Loading train dataset from {train_path}")

    # Load train dataset
    train_examples = []
    for line in train_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            train_examples.append(json.loads(line))

    if train_limit and train_limit > 0:
        train_examples = train_examples[:train_limit]
        logger.info(
            "Applying train limit: %s examples (requested %s)",
            len(train_examples),
            train_limit,
        )
    logger.info(f"Loaded {len(train_examples)} training examples")

    # Load validation dataset
    logger.info(f"Loading validation dataset from {val_path}")
    val_examples = []
    for line in val_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            val_examples.append(json.loads(line))

    if val_limit and val_limit > 0:
        val_examples = val_examples[:val_limit]
        logger.info(
            "Applying val limit: %s examples (requested %s)",
            len(val_examples),
            val_limit,
        )
    logger.info(f"Loaded {len(val_examples)} validation examples")

    # Format examples for instruction tuning
    def format_for_training(examples):
        formatted = []
        for ex in examples:
            text = format_example_for_instruction_tuning(ex)
            formatted.append({"text": text})
        return formatted

    train_formatted = format_for_training(train_examples)
    val_formatted = format_for_training(val_examples)

    # Create HuggingFace datasets
    train_dataset = Dataset.from_list(train_formatted)
    val_dataset = Dataset.from_list(val_formatted)

    # Tokenize
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding=False,  # Will be done by data collator
        )

    logger.info("Tokenizing datasets...")
    train_dataset = train_dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
        desc="Tokenizing train set"
    )

    val_dataset = val_dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
        desc="Tokenizing validation set"
    )

    return train_dataset, val_dataset


@app.command()
def main(
    train: Path = typer.Option(
        ...,
        "--train",
        "-t",
        help="Path to training JSONL dataset",
        exists=True,
        readable=True,
    ),
    val: Path = typer.Option(
        ...,
        "--val",
        "-v",
        help="Path to validation JSONL dataset",
        exists=True,
        readable=True,
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output directory for fine-tuned model (LoRA adapters)",
    ),
    base_model: str = typer.Option(
        "mistralai/Mistral-7B-Instruct-v0.1",
        "--base-model",
        "-m",
        help="Base model ID from Hugging Face",
    ),
    epochs: int = typer.Option(
        3,
        "--epochs",
        "-e",
        help="Number of training epochs",
    ),
    learning_rate: float = typer.Option(
        2e-4,
        "--lr",
        help="Learning rate",
    ),
    batch_size: int = typer.Option(
        1,
        "--batch-size",
        "-b",
        help="Per-device train batch size (CPU limitation)",
    ),
    grad_accum_steps: int = typer.Option(
        8,
        "--grad-accum",
        help="Gradient accumulation steps (simulates larger batch)",
    ),
    lora_r: int = typer.Option(
        8,
        "--lora-r",
        help="LoRA rank (r)",
    ),
    lora_alpha: int = typer.Option(
        32,
        "--lora-alpha",
        help="LoRA alpha (scaling factor)",
    ),
    lora_dropout: float = typer.Option(
        0.1,
        "--lora-dropout",
        help="LoRA dropout",
    ),
    max_length: int = typer.Option(
        2048,
        "--max-length",
        help="Maximum sequence length",
    ),
    train_limit: Optional[int] = typer.Option(
        None,
        "--train-limit",
        help="Limit number of training examples (smoke tests)",
    ),
    val_limit: Optional[int] = typer.Option(
        None,
        "--val-limit",
        help="Limit number of validation examples (smoke tests)",
    ),
    max_steps: Optional[int] = typer.Option(
        None,
        "--max-steps",
        help="Override total training steps (smoke tests)",
    ),
    quantization: str = typer.Option(
        "bnb4",
        "--quantization",
        help="Quantization mode: 'bnb4', 'bf16', or 'fp32'",
    ),
    seed: int = typer.Option(
        42,
        "--seed",
        help="Random seed for reproducibility",
    ),
) -> None:
    """Fine-tune Mistral-7B-Instruct with LoRA for BA role."""

    logger.info("=" * 80)
    logger.info("FASE 8.4: Fine-Tuning LoRA - Mistral-7B-Instruct (BA Role)")
    logger.info("=" * 80)

    # Set seed
    torch.manual_seed(seed)

    # 1. Load tokenizer
    logger.info(f"Loading tokenizer from {base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"  # Fix for llama-based models

    quantization = quantization.lower()
    if quantization not in {"bnb4", "bf16", "fp32"}:
        raise typer.BadParameter("Quantization must be one of: bnb4, bf16, fp32")

    # 2. Load model
    if quantization == "bnb4":
        logger.info(f"Loading model {base_model} with 4-bit quantization (bitsandbytes)...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        try:
            model = AutoModelForCausalLM.from_pretrained(
                base_model,
                quantization_config=bnb_config,
                device_map="cpu",  # Force CPU
                trust_remote_code=True,
            )
        except ImportError as exc:
            raise typer.BadParameter(
                "bitsandbytes 4-bit quantization is not available in this environment. "
                "Install a GPU-enabled bitsandbytes or rerun with --quantization bf16."
            ) from exc
    else:
        dtype = torch.bfloat16 if quantization == "bf16" else torch.float32
        logger.info(
            "Loading model %s without bitsandbytes (dtype=%s)...",
            base_model,
            dtype,
        )
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            device_map="cpu",
            trust_remote_code=True,
        )

    # 3. Apply LoRA configuration
    logger.info(f"Applying LoRA configuration (r={lora_r}, alpha={lora_alpha})...")

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        bias="none",
        inference_mode=False,
    )

    model = get_peft_model(model, lora_config)

    # Print trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(
        f"Trainable params: {trainable_params:,} / {total_params:,} "
        f"({100 * trainable_params / total_params:.2f}%)"
    )

    # 4. Load and prepare datasets
    train_dataset, val_dataset = load_and_prepare_datasets(
        train_path=train,
        val_path=val,
        tokenizer=tokenizer,
        max_length=max_length,
        train_limit=train_limit,
        val_limit=val_limit,
    )

    # 5. Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Causal LM (not masked)
    )

    # 6. Training arguments
    logger.info("Configuring training arguments...")

    output.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        # Output
        output_dir=str(output),
        overwrite_output_dir=True,

        # Training
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum_steps,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_steps=10,
        max_grad_norm=1.0,
        max_steps=max_steps if max_steps is not None else -1,

        # Optimization
        optim="adamw_torch",  # AdamW (torch native, no 8-bit)
        lr_scheduler_type="cosine",

        # Evaluation
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",

        # Hardware
        use_cpu=True,
        dataloader_num_workers=0,

        # Logging
        logging_dir=str(output / "logs"),
        logging_steps=10,
        save_total_limit=2,

        # Misc
        seed=seed,
        fp16=False,  # No FP16 on CPU
        report_to="none",  # No W&B/TensorBoard
        remove_unused_columns=False,
    )

    # 7. Trainer
    logger.info("Initializing Trainer...")

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
    )

    # 8. Train
    logger.info("=" * 80)
    logger.info("Starting training...")
    logger.info(f"  Train examples: {len(train_dataset)}")
    logger.info(f"  Val examples: {len(val_dataset)}")
    logger.info(f"  Epochs: {epochs}")
    logger.info(f"  Batch size (effective): {batch_size * grad_accum_steps}")
    logger.info(f"  Learning rate: {learning_rate}")
    logger.info(f"  Estimated time: 1.5-2.5 hours (CPU)")
    logger.info("=" * 80)

    trainer.train()

    # 9. Save LoRA adapters
    logger.info("=" * 80)
    logger.info(f"Saving LoRA adapters to {output}...")
    model.save_pretrained(str(output))
    tokenizer.save_pretrained(str(output))

    # Save training info
    info = {
        "base_model": base_model,
        "train_dataset": str(train),
        "val_dataset": str(val),
        "train_examples": len(train_dataset),
        "val_examples": len(val_dataset),
        "epochs": epochs,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "grad_accum_steps": grad_accum_steps,
        "effective_batch_size": batch_size * grad_accum_steps,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "lora_dropout": lora_dropout,
        "max_length": max_length,
        "seed": seed,
        "train_limit": train_limit,
        "val_limit": val_limit,
        "max_steps": max_steps,
        "quantization": quantization,
        "trainable_params": trainable_params,
        "total_params": total_params,
        "trainable_percentage": 100 * trainable_params / total_params,
    }

    (output / "training_info.json").write_text(
        json.dumps(info, indent=2), encoding="utf-8"
    )

    logger.info("=" * 80)
    logger.info("✅ Fine-tuning completed!")
    logger.info(f"📁 LoRA adapters saved to: {output}")
    logger.info(f"📊 Training info: {output / 'training_info.json'}")
    logger.info("=" * 80)
    logger.info("\n🚀 Next steps:")
    logger.info("  1. Evaluate model on validation set")
    logger.info("  2. Compare with baseline and optimized models (3-way)")
    logger.info("  3. If score ≥ 90%, integrate into pipeline")
    logger.info("=" * 80)


if __name__ == "__main__":
    app()
