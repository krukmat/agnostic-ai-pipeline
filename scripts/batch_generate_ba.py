"""Batch generator for BA requirements using existing run_ba logic."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import typer

from common import PLANNING, ROOT
from scripts.run_ba import generate_requirements

DEFAULT_OUTPUT = ROOT / "dspy_baseline" / "data" / "production" / "ba_extra.jsonl"

app = typer.Typer(help="Generate multiple BA requirements in one go.")


def _load_concepts(concepts_file: Optional[Path], inline: List[str]) -> List[str]:
    concepts: List[str] = []
    if concepts_file:
        text = concepts_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            entry = line.strip()
            if entry:
                concepts.append(entry)
    for entry in inline:
        clean = entry.strip()
        if clean:
            concepts.append(clean)
    return concepts


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


@app.command()
def generate(
    concepts_file: Optional[Path] = typer.Option(
        None,
        "--concepts-file",
        "-f",
        help="Plain text file with one concept per line.",
    ),
    output: Path = typer.Option(
        DEFAULT_OUTPUT,
        "--output",
        "-o",
        help="JSONL file where concepts+requirements are appended.",
    ),
    concept: List[str] = typer.Option(
        [],
        "--concept",
        "-c",
        help="Provide a concept directly (can repeat).",
    ),
) -> None:
    """Generate BA requirements for all provided concepts and append to JSONL."""
    concepts = _load_concepts(concepts_file, concept)
    if not concepts:
        typer.echo("No concepts provided. Use --concept or --concepts-file.")
        raise typer.Exit(code=1)

    typer.echo(f"Generating {len(concepts)} BA requirements via DSPy…")
    for idx, entry in enumerate(concepts, start=1):
        typer.echo(f"[{idx}/{len(concepts)}] Concept: {entry}")
        asyncio.run(generate_requirements(entry))
        requirements_path = PLANNING / "requirements.yaml"
        if not requirements_path.exists():
            typer.echo("requirements.yaml missing after BA run; skipping entry.")
            continue
        requirements_yaml = requirements_path.read_text(encoding="utf-8")
        record = {
            "input": {"concept": entry},
            "requirements_yaml": requirements_yaml,
            "generated_at": datetime.utcnow()
            .replace(tzinfo=timezone.utc)
            .isoformat(),
        }
        _append_jsonl(output, record)
        typer.echo(f"  ✓ Appended to {output}")

    typer.echo("Batch BA generation completed.")


if __name__ == "__main__":
    app()
