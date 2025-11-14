"""
Evaluate Product Owner baseline/student models using the supervised prompt template.
Ensures YAML output, computes product_owner_metric, and stores inference artifacts.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List, Optional, Tuple

import torch
import typer
from peft import PeftModel
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)

from dspy_baseline.metrics.product_owner_metrics import product_owner_metric
from scripts.po_format import extract_vision_review
from scripts.po_prompts import build_po_prompt

app = typer.Typer(help="Evaluate Product Owner baseline or student models.")


@dataclass
class ExampleWrapper:
    requirements: str


@dataclass
class PredictionWrapper:
    vision_yaml: str
    review_yaml: str


def load_dataset(path: Path, max_samples: Optional[int], seed: int) -> List[Dict]:
    records: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    if not records:
        raise ValueError(f"No records found in {path}")

    random.seed(seed)
    random.shuffle(records)
    if max_samples:
        records = records[:max_samples]
    return records


def prepare_generation_model(
    base_model: str,
    adapter_path: Optional[Path],
    load_4bit: bool,
    compute_dtype: str,
) -> Tuple[AutoTokenizer, AutoModelForCausalLM]:
    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: Dict[str, object] = {"device_map": "auto"}
    if load_4bit:
        dtype = torch.bfloat16 if compute_dtype == "bfloat16" else torch.float16
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )
        model_kwargs.update(
            quantization_config=quant_config,
            torch_dtype=dtype,
        )
    else:
        model_kwargs["torch_dtype"] = torch.float16 if torch.cuda.is_available() else torch.float32

    model = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)
    if adapter_path:
        model = PeftModel.from_pretrained(model, str(adapter_path))
    model.eval()

    return tokenizer, model


def generate_response(
    tokenizer: AutoTokenizer,
    model: AutoModelForCausalLM,
    prompt: str,
    temperature: float,
    top_p: float,
    max_new_tokens: int,
    retries: int,
) -> Tuple[str, str, str, int]:
    attempt = 0
    final_text = ""
    while attempt <= retries:
        attempt += 1
        forced_prompt = prompt
        if attempt > 1:
            forced_prompt = (
                prompt
                + "\n\nREMINDER: Respond ONLY with the two fenced YAML blocks (VISION, REVIEW). "
                "Regenerate now."
            )

        inputs = tokenizer(
            forced_prompt,
            return_tensors="pt",
            padding=True,
        )
        input_ids = inputs["input_ids"].to(model.device)
        attention_mask = inputs["attention_mask"].to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                do_sample=temperature > 0,
                temperature=temperature,
                top_p=top_p,
                max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.eos_token_id,
            )

        generated = outputs[0][input_ids.shape[-1]:]
        final_text = tokenizer.decode(generated, skip_special_tokens=True).strip()
        vision_yaml, review_yaml = extract_vision_review(final_text)
        if vision_yaml and review_yaml:
            return final_text, vision_yaml, review_yaml, attempt

    return final_text, "", "", attempt


@app.command()
def evaluate(
    dataset_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/product_owner_val.jsonl"),
        help="Validation dataset with requirements_yaml entries.",
    ),
    output_dir: Path = typer.Option(
        Path("inference_results"),
        help="Directory where evaluation JSON files are stored.",
    ),
    base_model: str = typer.Option(
        "Qwen/Qwen2.5-7B-Instruct",
        help="Base model identifier (HF Hub).",
    ),
    adapter_path: Optional[Path] = typer.Option(
        None,
        help="Path to LoRA adapter produced by train_po_lora.py (omit for baseline).",
    ),
    tag: str = typer.Option(
        "student",
        help="Label for output file names (e.g., baseline, student).",
    ),
    max_samples: int = typer.Option(
        20,
        help="Number of validation records to evaluate.",
    ),
    seed: int = typer.Option(42, help="Random seed for sampling."),
    temperature: float = typer.Option(0.2, help="Generation temperature."),
    top_p: float = typer.Option(0.9, help="Top-p nucleus sampling."),
    max_new_tokens: int = typer.Option(900, help="Max new tokens to generate."),
    retries: int = typer.Option(1, help="Retries if YAML format is missing."),
    load_4bit: bool = typer.Option(False, help="Load base model in 4-bit mode."),
    bnb_compute_dtype: str = typer.Option(
        "float16",
        help="Compute dtype for bitsandbytes (float16|bfloat16).",
    ),
) -> None:
    """Run inference and metric evaluation for the Product Owner student."""

    records = load_dataset(dataset_path, max_samples, seed)
    tokenizer, model = prepare_generation_model(
        base_model=base_model,
        adapter_path=adapter_path,
        load_4bit=load_4bit,
        compute_dtype=bnb_compute_dtype,
    )

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{tag}_{timestamp}.json"

    typer.echo(f"[info] Evaluating {len(records)} samples; saving to {out_path}")

    scores: List[float] = []
    per_case: List[Dict] = []
    failures = 0

    for idx, entry in enumerate(records, start=1):
        payload = entry.get("input", {})
        concept_id = payload.get("concept_id") or entry.get("concept_id") or f"sample-{idx}"
        tier = payload.get("tier") or entry.get("tier")
        concept = payload.get("concept") or entry.get("concept") or ""
        requirements = payload.get("requirements_yaml") or entry.get("requirements_yaml") or ""

        prompt = build_po_prompt(concept, requirements, include_example=True)
        response, vision_yaml, review_yaml, attempts = generate_response(
            tokenizer,
            model,
            prompt,
            temperature=temperature,
            top_p=top_p,
            max_new_tokens=max_new_tokens,
            retries=retries,
        )

        status = "ok"
        score = None
        if vision_yaml and review_yaml:
            example = ExampleWrapper(requirements)
            prediction = PredictionWrapper(vision_yaml, review_yaml)
            score = product_owner_metric(example, prediction)
            scores.append(score)
        else:
            status = "format_error"
            failures += 1

        per_case.append(
            {
                "concept_id": concept_id,
                "tier": tier,
                "status": status,
                "attempts": attempts,
                "score": score,
                "vision_yaml": vision_yaml,
                "review_yaml": review_yaml,
                "raw_response": response,
            }
        )

        typer.echo(
            f"[{idx}/{len(records)}] {concept_id} -> {status}"
            + (f" score={score:.3f}" if score is not None else "")
        )

    summary = {
        "model": base_model,
        "adapter_path": str(adapter_path) if adapter_path else None,
        "timestamp": timestamp,
        "dataset": str(dataset_path),
        "total_samples": len(records),
        "valid_samples": len(scores),
        "failed_samples": failures,
        "metrics": {},
        "results": per_case,
    }

    if scores:
        summary["metrics"] = {
            "mean": mean(scores),
            "std": pstdev(scores) if len(scores) > 1 else 0.0,
            "min": min(scores),
            "max": max(scores),
        }

    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"[done] Results saved to {out_path}")
    if failures:
        typer.echo(f"[warn] {failures} samples failed to produce valid YAML.")


if __name__ == "__main__":
    app()
