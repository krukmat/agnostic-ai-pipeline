"""
Evaluate Product Owner OPTIMIZED (MIPROv2) performance on validation set.

Loads the optimized DSPy program, generates new outputs, and compares with baseline.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List

import typer
import dspy

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dspy_baseline.metrics.product_owner_metrics import product_owner_metric

app = typer.Typer(help="Evaluate optimized Product Owner model on valset.")


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
    valset_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/product_owner_val.jsonl"),
        help="Path to validation JSONL"
    ),
    program_path: Path = typer.Option(
        Path("artifacts/dspy/product_owner_optimized/product_owner/program.pkl"),
        help="Path to optimized DSPy program.pkl"
    ),
    baseline_report: Path = typer.Option(
        Path("artifacts/benchmarks/product_owner_baseline.json"),
        help="Path to baseline report for comparison"
    ),
    output_report: Path = typer.Option(
        Path("artifacts/benchmarks/product_owner_optimized.json"),
        help="Path to save optimized results"
    ),
    provider: str = typer.Option("ollama", help="LLM provider (ollama, vertex_ai)"),
    model: str = typer.Option("mistral:7b-instruct", help="Model name"),
) -> None:
    """Evaluate optimized Product Owner model and compare with baseline."""

    # Load optimized program
    if not program_path.exists():
        typer.echo(f"[error] Optimized program not found at {program_path}")
        raise typer.Exit(code=1)

    typer.echo(f"[info] Loading optimized program from {program_path}...")
    with program_path.open("rb") as f:
        optimized_program = pickle.load(f)

    # Configure DSPy LM
    if provider == "ollama":
        lm = dspy.LM("ollama_chat/" + model, api_base="http://localhost:11434", cache=False)
    elif provider == "vertex_ai":
        lm = dspy.LM(f"vertex_ai/{model}", cache=False)
    else:
        typer.echo(f"[error] Unsupported provider: {provider}")
        raise typer.Exit(code=1)

    dspy.configure(lm=lm)

    # Load validation data
    entries = _load_jsonl(valset_path)
    if not entries:
        typer.echo(f"[error] No entries found at {valset_path}")
        raise typer.Exit(code=1)

    typer.echo(f"[info] Loaded {len(entries)} validation examples")
    typer.echo(f"[info] Generating outputs with optimized model...")

    scores: List[float] = []
    detailed: List[Dict] = []

    for idx, entry in enumerate(entries, 1):
        concept_id = entry.get("input", {}).get("concept_id")
        concept = entry.get("input", {}).get("concept", "")
        requirements_yaml = entry.get("input", {}).get("requirements_yaml", "")
        tier = entry.get("input", {}).get("tier", "")

        if not requirements_yaml:
            typer.echo(f"[warn] Skipping {concept_id}: missing requirements_yaml")
            continue

        # Generate output with optimized program
        try:
            # The optimized program expects: concept, existing_vision, requirements
            result = optimized_program(
                concept=concept,
                existing_vision="",  # No existing vision for first iteration
                requirements=requirements_yaml
            )

            vision_yaml = result.vision_yaml
            review_yaml = result.review_yaml

        except Exception as e:
            typer.echo(f"[error] Failed to generate for {concept_id}: {e}")
            continue

        # Evaluate with metric
        example = ExampleWrapper(requirements_yaml)
        prediction = PredictionWrapper(vision_yaml, review_yaml)
        score = product_owner_metric(example, prediction)

        scores.append(score)
        detailed.append({
            "concept_id": concept_id,
            "score": score,
            "tier": tier,
        })

        if idx % 5 == 0:
            typer.echo(f"  [{idx}/{len(entries)}] Processed {concept_id}: score={score:.3f}")

    # Calculate statistics
    if not scores:
        typer.echo("[error] No scores computed")
        raise typer.Exit(code=1)

    avg = mean(scores)
    std = pstdev(scores) if len(scores) > 1 else 0.0

    report = {
        "model_type": "optimized",
        "program_path": str(program_path),
        "dataset": str(valset_path),
        "count": len(scores),
        "mean": avg,
        "std": std,
        "min": min(scores),
        "max": max(scores),
        "details": detailed,
    }

    # Save report
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    typer.echo("\n" + "=" * 80)
    typer.echo("OPTIMIZED MODEL RESULTS")
    typer.echo("=" * 80)
    typer.echo(f"Count: {len(scores)}")
    typer.echo(f"Mean:  {avg:.3f}")
    typer.echo(f"Std:   {std:.3f}")
    typer.echo(f"Min:   {min(scores):.3f}")
    typer.echo(f"Max:   {max(scores):.3f}")

    # Compare with baseline if available
    if baseline_report.exists():
        baseline_data = json.loads(baseline_report.read_text(encoding="utf-8"))
        baseline_mean = baseline_data.get("mean", 0.0)

        improvement = avg - baseline_mean
        improvement_pct = (improvement / baseline_mean) * 100 if baseline_mean > 0 else 0

        typer.echo("\n" + "=" * 80)
        typer.echo("COMPARISON WITH BASELINE")
        typer.echo("=" * 80)
        typer.echo(f"Baseline Mean:  {baseline_mean:.3f}")
        typer.echo(f"Optimized Mean: {avg:.3f}")
        typer.echo(f"Improvement:    {improvement:+.3f} ({improvement_pct:+.1f}%)")

        if improvement > 0.05:
            typer.echo("\n✅ Significant improvement! Model optimization is working.")
        elif improvement > 0:
            typer.echo("\n⚠️  Marginal improvement. Consider more training examples.")
        else:
            typer.echo("\n❌ No improvement or regression. Review optimization strategy.")

    typer.echo(f"\n[ok] Report saved to {output_report}")


if __name__ == "__main__":
    app()
