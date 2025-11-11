"""
Train a LoRA adapter for the Product Owner student model using the teacher dataset.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

import typer
import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)

app = typer.Typer(help="Train LoRA adapter for Product Owner student.")


def load_supervised_jsonl(path: Path) -> List[Dict[str, str]]:
    samples: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            prompt = data.get("prompt")
            response = data.get("response")
            if prompt and response:
                samples.append({"prompt": prompt, "response": response})
    return samples


@app.command()
def train(
    data_path: Path = typer.Option(
        Path("artifacts/distillation/po_teacher_supervised.jsonl"),
        help="Supervised dataset with prompt/response pairs.",
    ),
    base_model: str = typer.Option(
        "mistral-7b-instruct", help="Base model for LoRA fine-tuning."
    ),
    output_dir: Path = typer.Option(
        Path("artifacts/models/po_student_v1"), help="Output directory."
    ),
    rank: int = typer.Option(32, help="LoRA rank."),
    alpha: int = typer.Option(64, help="LoRA alpha."),
    dropout: float = typer.Option(0.05, help="LoRA dropout."),
    epochs: int = typer.Option(3, help="Number of epochs."),
    batch_size: int = typer.Option(4, help="Batch size per device."),
    lr: float = typer.Option(1e-4, help="Learning rate."),
    max_length: int = typer.Option(2048, help="Max sequence length."),
) -> None:
    samples = load_supervised_jsonl(data_path)
    if not samples:
        typer.echo(f"[train] No samples found in {data_path}")
        raise typer.Exit(code=1)

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize(sample: Dict[str, str]) -> Dict[str, Any]:
        text = sample["prompt"] + "\n\n" + sample["response"]
        tokenized = tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    ds = Dataset.from_list(samples).map(tokenize, remove_columns=["prompt", "response"])

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto",
    )

    lora_config = LoraConfig(
        r=rank,
        lora_alpha=alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    output_dir.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=1,
        num_train_epochs=epochs,
        learning_rate=lr,
        weight_decay=0.01,
        fp16=True,
        logging_steps=10,
        save_strategy="epoch",
        push_to_hub=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=ds,
        data_collator=DataCollatorForLanguageModeling(
            tokenizer, mlm=False, pad_to_multiple_of=8
        ),
    )
    trainer.train()
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    typer.echo(f"[train] LoRA adapter saved to {output_dir}")


if __name__ == "__main__":
    app()
