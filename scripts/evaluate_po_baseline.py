"""
Evaluate Product Owner baseline performance on a given dataset (e.g., validation set).
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List

import typer

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dspy_baseline.metrics.product_owner_metrics import product_owner_metric

app = typer.Typer(help="Compute aggregate metrics for Product Owner outputs.")


class ExampleWrapper:
    def __init__(self, requirements: str) -> None:
        self.requirements = requirements


class PredictionWrapper:
    def __init__(self, vision_yaml: str, review_yaml: str) -> None:
        self.vision_yaml = vision_yaml
        self.review_yaml = review_yaml


def _load_jsonl(path: Path) -> List[Dict]:
    data: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data.append(json.loads(line))
    return data


@app.command()
def evaluate(
    input_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/product_owner_val.jsonl")
    ),
    report_path: Path = typer.Option(
        Path("artifacts/benchmarks/product_owner_baseline.json")
    ),
    recompute_scores: bool = typer.Option(
        True, help="Recompute metric even if 'score' field exists."
    ),
) -> None:
    entries = _load_jsonl(input_path)
    if not entries:
        typer.echo(f"[error] No entries found at {input_path}")
        raise typer.Exit(code=1)

    scores: List[float] = []
    detailed: List[Dict] = []

    for entry in entries:
        concept_id = entry.get("input", {}).get("concept_id")
        requirements = entry.get("input", {}).get("requirements_yaml")
        vision_yaml = entry.get("output", {}).get("product_vision")
        review_yaml = entry.get("output", {}).get("product_owner_review")

        if not (requirements and vision_yaml and review_yaml):
            typer.echo(f"[warn] Skipping {concept_id}: missing fields.")
            continue

        if recompute_scores or "score" not in entry:
            example = ExampleWrapper(requirements)
            prediction = PredictionWrapper(vision_yaml, review_yaml)
            score = product_owner_metric(example, prediction)
        else:
            score = entry["score"]

        scores.append(score)
        detailed.append(
            {
                "concept_id": concept_id,
                "score": score,
                "tier": entry.get("input", {}).get("tier"),
            }
        )

    avg = mean(scores)
    std = pstdev(scores) if len(scores) > 1 else 0.0
    report = {
        "dataset": str(input_path),
        "count": len(scores),
        "mean": avg,
        "std": std,
        "min": min(scores),
        "max": max(scores),
        "details": detailed,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    typer.echo(
        f"[ok] Evaluated {len(scores)} records. "
        f"Mean={avg:.3f} Std={std:.3f} Min={min(scores):.3f} Max={max(scores):.3f}"
    )


if __name__ == "__main__":
    app()
