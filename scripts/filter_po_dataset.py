"""
Score and filter Product Owner synthetic outputs using product_owner_metric.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dspy_baseline.metrics.product_owner_metrics import product_owner_metric

app = typer.Typer(help="Filter PO synthetic dataset based on metric threshold.")


@dataclass
class ExampleWrapper:
    requirements: str


@dataclass
class PredictionWrapper:
    vision_yaml: str
    review_yaml: str


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data.append(json.loads(line))
    return data


@app.command()
def filter(
    input_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/product_owner_synthetic_raw.jsonl")
    ),
    output_path: Path = typer.Option(
        Path(
            "artifacts/synthetic/product_owner/product_owner_synthetic_filtered.jsonl"
        )
    ),
    report_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/product_owner_scores.json")
    ),
    threshold: float = typer.Option(
        0.70, help="Minimum score (0-1) to keep an example."
    ),
) -> None:
    """Score each entry with product_owner_metric and filter by threshold."""

    entries = _load_jsonl(input_path)
    if not entries:
        typer.echo(f"[error] No entries found at {input_path}")
        raise typer.Exit(code=1)

    kept: List[Dict[str, Any]] = []
    raw_scores: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    for entry in entries:
        concept_id = entry.get("input", {}).get("concept_id")
        requirements_yaml = entry.get("input", {}).get("requirements_yaml")
        vision_yaml = entry.get("output", {}).get("product_vision")
        review_yaml = entry.get("output", {}).get("product_owner_review")
        error = entry.get("metadata", {}).get("error")

        if error or not (requirements_yaml and vision_yaml and review_yaml):
            failures.append(
                {"concept_id": concept_id, "reason": error or "missing output"}
            )
            continue

        example = ExampleWrapper(requirements=requirements_yaml)
        prediction = PredictionWrapper(
            vision_yaml=vision_yaml,
            review_yaml=review_yaml,
        )
        score = product_owner_metric(example, prediction, trace=None)

        record = {
            **entry,
            "score": score,
        }
        raw_scores.append({"concept_id": concept_id, "score": score})
        if score >= threshold:
            kept.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for item in kept:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    report = {
        "input_file": str(input_path),
        "output_file": str(output_path),
        "threshold": threshold,
        "total_entries": len(entries),
        "kept_entries": len(kept),
        "dropped_entries": len(entries) - len(kept),
        "failed_entries": failures,
        "scores": raw_scores,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    typer.echo(
        f"[ok] Scored {len(entries)} entries → kept {len(kept)} "
        f"(threshold={threshold})"
    )
    if failures:
        typer.echo(f"[warn] {len(failures)} entries skipped due to errors.")


if __name__ == "__main__":
    app()
