#!/usr/bin/env python3
"""CLI utility to optimize DSPy programs (BA / QA) using MIPROv2."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

import typer

from dspy_baseline.optimizers import optimize_program

app = typer.Typer(help="Optimize DSPy programs with dspy.MIPROv2.")


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    import dspy
    data: List[dspy.Example] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw = json.loads(line)
            # Convert to DSPy Example format
            # BA format: {"concept": "...", "requirements": {...}}
            if "concept" in raw and "requirements" in raw:
                example = dspy.Example(
                    concept=raw["concept"],
                    **{k: v for k, v in raw["requirements"].items()}
                ).with_inputs("concept")
                data.append(example)
            else:
                data.append(dspy.Example(**raw).with_inputs("concept"))
    return data


def _load_metric(metric_path: str) -> Callable[[Any, Any], float]:
    if ":" not in metric_path:
        raise typer.BadParameter(
            "Metric must be in the form 'module.submodule:function'"
        )
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


def _default_metric(example: Dict[str, Any], prediction: Any) -> float:
    """Fallback metric when none is provided (returns constant score)."""
    # NOTE: This is intentionally simple. Real runs should supply a proper metric.
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
    metric_path: str = typer.Option(
        None,
        "--metric",
        "-m",
        help="Metric callable path 'module:function'. Optional.",
    ),
    output_dir: Path = typer.Option(
        Path("artifacts/dspy/optimizer"),
        "--output",
        "-o",
        help="Directory where compiled program and metadata will be stored.",
    ),
    num_candidates: int = typer.Option(8, help="Number of candidates per iteration."),
    num_trials: int = typer.Option(8, help="Number of optimization trials/iterations."),
    max_bootstrapped_demos: int = typer.Option(8, help="Maximum bootstrapped demonstrations."),
    seed: int = typer.Option(0, help="Random seed for optimizer."),
) -> None:
    """Compile the selected DSPy program using the provided trainset."""
    try:
        import dspy  # noqa: F401
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise typer.Exit(
            code=1
        ) from exc

    trainset = _load_jsonl(trainset_path)
    metric = _load_metric(metric_path) if metric_path else _default_metric
    program = _load_program(role)

    # Configure DSPy with Vertex AI LM (required for MIPROv2)
    import os
    project_id = os.environ.get("GCP_PROJECT", "agnostic-pipeline-476015")
    location = os.environ.get("VERTEX_LOCATION", "us-central1")
    model_name = os.environ.get("VERTEX_MODEL", "gemini-1.5-flash")

    lm = dspy.LM(f"vertex_ai/{model_name}", project=project_id, location=location)
    dspy.configure(lm=lm)

    compiled = optimize_program(
        program=program,
        trainset=trainset,
        metric=metric,
        num_candidates=num_candidates,
        num_trials=num_trials,
        max_bootstrapped_demos=max_bootstrapped_demos,
        seed=seed,
    )

    role_dir = output_dir / role
    role_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "role": role,
        "trainset": str(trainset_path),
        "num_candidates": num_candidates,
        "num_trials": num_trials,
        "max_bootstrapped_demos": max_bootstrapped_demos,
        "seed": seed,
        "metric": metric_path or "default_constant_metric",
    }
    metadata_path = role_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    program_path = role_dir / "program.pkl"
    compiled.save(program_path)  # type: ignore[attr-defined]
    typer.echo(f"✅ Optimized program saved to {program_path}")
    typer.echo(f"📄 Metadata written to {metadata_path}")


if __name__ == "__main__":
    app()
