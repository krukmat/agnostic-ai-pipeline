#!/usr/bin/env python3
"""CLI utility to optimize DSPy programs (BA / QA) using MIPROv2."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import dspy
import typer

from dspy_baseline.optimizers import optimize_program

app = typer.Typer(help="Optimize DSPy programs with dspy.MIPROv2.")


def _examples_from_jsonl(path: Path, role: str) -> List[dspy.Example]:
    """Load JSONL records and wrap them as dspy.Example objects."""
    examples: List[dspy.Example] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row: Dict[str, Any] = json.loads(line)

        if role == "ba" and "requirements" in row:
            payload = {"concept": row["concept"], **row["requirements"]}
            example = dspy.Example(**payload).with_inputs("concept")
        elif role == "qa":
            example = dspy.Example(**row).with_inputs(
                "story_title", "story_description", "acceptance_criteria"
            )
        else:
            example = dspy.Example(**row)
        examples.append(example)
    return examples


def _load_metric(metric_path: str) -> Callable[[Any, Any], float]:
    if ":" not in metric_path:
        raise typer.BadParameter("Metric must be in the form 'module.submodule:function'")
    module_name, func_name = metric_path.split(":", 1)
    module = importlib.import_module(module_name)
    metric = getattr(module, func_name, None)
    if metric is None:
        raise typer.BadParameter(f"Metric function '{func_name}' not found in {module_name}")
    return metric


def _load_program(role: str) -> Any:
    if role == "ba":
        from dspy_baseline.modules.ba_requirements import BARequirementsModule

        return BARequirementsModule()
    if role == "qa":
        from dspy_baseline.modules.qa_testcases import QA_PROGRAM

        return QA_PROGRAM
    raise typer.BadParameter(f"Unsupported role '{role}'. Expected 'ba' or 'qa'.")


def _default_metric(example: dspy.Example, prediction: Any, trace=None) -> float:
    """Fallback metric when none is provided (returns constant score)."""
    return 1.0


@app.command()
def main(
    role: str = typer.Option(
        ...,
        "--role",
        "-r",
        help="Program to optimize: 'ba' or 'qa'.",
    ),
    trainset_path: Path = typer.Option(
        ...,
        "--trainset",
        "-t",
        exists=True,
        readable=True,
        help="Path to JSONL trainset.",
    ),
    metric_path: Optional[str] = typer.Option(
        None,
        "--metric",
        "-m",
        help="Metric callable path 'module:function'. Optional.",
    ),
    valset_path: Optional[Path] = typer.Option(
        None,
        "--valset",
        help="Optional JSONL validation set for early stopping.",
    ),
    stop_metric_path: Optional[str] = typer.Option(
        None,
        "--stop-metric",
        help="Optional stop metric 'module:function' evaluated on the valset.",
    ),
    output_dir: Path = typer.Option(
        Path("artifacts/dspy/optimizer"),
        "--output",
        "-o",
        help="Directory where compiled program and metadata will be stored.",
    ),
    num_candidates: int = typer.Option(8, help="Number of candidates per iteration."),
    num_trials: int = typer.Option(8, help="Number of optimization trials."),
    max_bootstrapped_demos: int = typer.Option(8, help="Maximum bootstrapped demonstrations."),
    seed: int = typer.Option(0, help="Random seed for optimizer."),
    provider: str = typer.Option("vertex_ai", help="LLM provider: 'vertex_ai' or 'ollama'."),
    model: str = typer.Option("gemini-2.5-flash", help="Model name (provider-specific)."),
    ollama_base_url: str = typer.Option("http://localhost:11434", help="Ollama base URL (only used if provider=ollama)."),
) -> None:
    """Compile the selected DSPy program using the provided trainset."""
    train_examples = _examples_from_jsonl(trainset_path, role=role)
    val_examples: Optional[List[dspy.Example]] = (
        _examples_from_jsonl(valset_path, role=role) if valset_path else None
    )

    metric = _load_metric(metric_path) if metric_path else _default_metric
    stop_metric = _load_metric(stop_metric_path) if stop_metric_path else None
    program = _load_program(role)

    # Configure DSPy LM based on provider
    import os
    import dspy

    if provider == "vertex_ai":
        project_id = os.environ.get("GCP_PROJECT", "agnostic-pipeline-476015")
        location = os.environ.get("VERTEX_LOCATION", "us-central1")
        lm = dspy.LM(f"vertex_ai/{model}", project=project_id, location=location)
        typer.echo(f"🔧 Configured DSPy with Vertex AI: {model}")
    elif provider == "ollama":
        lm = dspy.LM(f"ollama/{model}", api_base=ollama_base_url)
        typer.echo(f"🔧 Configured DSPy with Ollama: {model} @ {ollama_base_url}")
    else:
        raise typer.BadParameter(f"Unsupported provider '{provider}'. Expected 'vertex_ai' or 'ollama'.")

    dspy.configure(lm=lm)

    compiled = optimize_program(
        program=program,
        trainset=train_examples,
        metric=metric,
        num_candidates=num_candidates,
        num_trials=num_trials,
        max_bootstrapped_demos=max_bootstrapped_demos,
        seed=seed,
        valset=val_examples,
        stop_metric=stop_metric,
    )

    role_dir = output_dir / role
    role_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "role": role,
        "trainset": str(trainset_path),
        "valset": str(valset_path) if valset_path else None,
        "num_candidates": num_candidates,
        "num_trials": num_trials,
        "max_bootstrapped_demos": max_bootstrapped_demos,
        "seed": seed,
        "metric": metric_path or "default_constant_metric",
        "stop_metric": stop_metric_path or None,
        "trainset_size": len(train_examples),
        "valset_size": len(val_examples) if val_examples else 0,
        "provider": provider,
        "model": model,
        "ollama_base_url": ollama_base_url if provider == "ollama" else None,
    }
    metadata_path = role_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    program_path = role_dir / "program.pkl"
    try:
        import dill
        with open(program_path, "wb") as f:
            dill.dump(compiled, f)
        typer.echo(f"✅ Optimized program saved to {program_path}")
    except Exception as e:
        typer.echo(f"⚠️  Could not serialize program: {e}")
        typer.echo(f"💡 Program is still available in memory and was optimized successfully")

    typer.echo(f"📄 Metadata written to {metadata_path}")


if __name__ == "__main__":
    app()
