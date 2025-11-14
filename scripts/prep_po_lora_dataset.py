"""
Prepare supervised prompt/response pairs for Product Owner LoRA fine-tuning.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Dict, Optional

import typer

from scripts.po_prompts import build_po_prompt

app = typer.Typer(help="Build supervised dataset from teacher outputs for PO LoRA.")


def load_teacher_records(path: Path) -> List[Dict]:
    records: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


@app.command()
def build(
    input_path: Path = typer.Option(
        Path("artifacts/distillation/po_teacher_dataset.jsonl"),
        help="Teacher dataset JSONL.",
    ),
    output_path: Path = typer.Option(
        Path("artifacts/distillation/po_teacher_supervised.jsonl"),
        help="Destination JSONL with prompt/response pairs.",
    ),
    seed: int = typer.Option(42, help="Random seed for shuffling."),
    max_samples: Optional[int] = typer.Option(
        None, help="Optional limit of samples to include."
    ),
) -> None:
    records = load_teacher_records(input_path)
    if not records:
        typer.echo(f"[prep] No records found in {input_path}")
        raise typer.Exit(code=1)

    random.seed(seed)
    random.shuffle(records)
    if max_samples and max_samples > 0:
        records = records[:max_samples]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            concept = rec.get("concept", "").strip()
            requirements = rec.get("requirements_yaml", "").strip()
            vision = rec.get("teacher_product_vision", "").strip()
            review = rec.get("teacher_product_owner_review", "").strip()

            if not (concept and requirements and vision and review):
                continue

            prompt = build_po_prompt(concept, requirements, include_example=False)
            response = (
                "```yaml VISION\n"
                f"{vision}\n"
                "```\n"
                "```yaml REVIEW\n"
                f"{review}\n"
                "```"
            )

            fh.write(json.dumps({"prompt": prompt, "response": response}, ensure_ascii=False) + "\n")

    typer.echo(
        f"[prep] Wrote {len(records)} samples to {output_path}"
    )


if __name__ == "__main__":
    app()
