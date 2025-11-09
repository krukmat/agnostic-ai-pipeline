#!/usr/bin/env python3
"""Filter synthetic dataset by score and structural checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import typer

app = typer.Typer()


def _valid_example(row: Dict[str, object], min_score: float) -> bool:
    if row.get("score", 0) < min_score:
        return False
    reqs = row.get("requirements", {})
    fr = reqs.get("functional_requirements", []) if isinstance(reqs, dict) else []
    nfr = reqs.get("non_functional_requirements", []) if isinstance(reqs, dict) else []
    return len(fr) >= 3 and len(nfr) >= 2


@app.command()
def main(
    input_path: Path = typer.Option(..., "--input", exists=True),
    output_path: Path = typer.Option(Path("artifacts/synthetic/ba_synthetic_filtered.jsonl"), "--output"),
    min_score: float = typer.Option(0.7, "--min-score"),
    min_examples: int = typer.Option(100, "--min-examples"),
):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    filtered = [row for row in rows if _valid_example(row, min_score)]

    if len(filtered) < min_examples:
        typer.echo(
            f"Warning: only {len(filtered)} examples meet criteria (<{min_examples}). Adjusting threshold."
        )
        filtered = rows[:min_examples]

    with output_path.open("w", encoding="utf-8") as fh:
        for row in filtered:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    typer.echo(f"Filtered dataset -> {output_path} ({len(filtered)} examples)")


if __name__ == "__main__":
    app()
