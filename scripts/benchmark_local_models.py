#!/usr/bin/env python3
"""Benchmark local Ollama models for BA role quality/perf."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

import typer

import yaml

app = typer.Typer(help="Benchmark local Ollama models for BA role quality/perf.")

PROMPT_TEMPLATE = """You are a Business Analyst generating software requirements.\nCONCEPT: {concept}\nProvide structured YAML with fields: title, description, functional_requirements (list of id/description/priority), non_functional_requirements, constraints.\n"""


def _load_dataset(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _run_ollama(model: str, prompt: str, timeout: int = 60) -> str:
    result = subprocess.run(
        ["ollama", "run", model, prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _score_output(output: str) -> float:
    try:
        data = yaml.safe_load(output)
    except Exception:
        return 0.0
    if not isinstance(data, dict):
        return 0.0
    fr = data.get("functional_requirements")
    if not isinstance(fr, list) or len(fr) < 2:
        return 0.0
    return 1.0


@app.command()
def main(
    models: List[str] = typer.Option(..., "--models", help="Models to benchmark"),
    dataset: Path = typer.Option(..., "--dataset", exists=True),
    output: Path = typer.Option(Path("artifacts/benchmarks/local_models_baseline.json"), "--output"),
):
    examples = _load_dataset(dataset)
    results = {}
    for model in models:
        typer.echo(f"Benchmarking {model}...")
        scores = []
        start = time.time()
        try:
            for ex in examples:
                prompt = PROMPT_TEMPLATE.format(concept=ex["concept"])
                output_text = _run_ollama(model, prompt)
                scores.append(_score_output(output_text))
        except Exception as exc:
            typer.echo(f"Error benchmarking {model}: {exc}")
            continue
        elapsed = time.time() - start
        results[model] = {
            "avg_score": round(sum(scores) / len(scores), 3),
            "elapsed_sec": round(elapsed, 2),
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    typer.echo(f"Results written to {output}")


if __name__ == "__main__":
    app()
