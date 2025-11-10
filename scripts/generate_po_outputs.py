"""
Batch runner for Product Owner outputs based on pre-generated concept payloads.

Reads JSONL entries (concept + requirements_yaml) and iteratively executes
`scripts/run_product_owner.py`, capturing the resulting product_vision.yaml and
product_owner_review.yaml into a consolidated dataset.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional

import typer
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import PLANNING, ensure_dirs

VISION_PATH = PLANNING / "product_vision.yaml"
REVIEW_PATH = PLANNING / "product_owner_review.yaml"
REQUIREMENTS_PATH = PLANNING / "requirements.yaml"

app = typer.Typer(help="Generate Product Owner synthetic outputs (vision + review).")


def _load_entries(path: Path) -> Iterator[Dict]:
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                typer.echo(f"[warn] Skipping invalid JSONL row: {raw[:120]}...")
                continue
            yield data


def _write_requirements(requirements_yaml: str) -> None:
    REQUIREMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REQUIREMENTS_PATH.write_text(requirements_yaml.strip() + "\n", encoding="utf-8")


def _read_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def _run_product_owner(concept: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CONCEPT"] = concept
    cmd = [sys.executable, str(ROOT / "scripts" / "run_product_owner.py")]
    return subprocess.run(cmd, cwd=str(ROOT), env=env)


@app.command()
def generate(
    input_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/concepts.jsonl"),
        help="JSONL file with concept + requirements payloads.",
    ),
    output_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/product_owner_synthetic_raw.jsonl"),
        help="Destination JSONL file containing PO outputs.",
    ),
    offset: int = typer.Option(
        0, help="Number of entries to skip (useful for resumable runs)."
    ),
    limit: int = typer.Option(
        0, help="Maximum number of entries to process (0 = all remaining)."
    ),
    overwrite: bool = typer.Option(
        False, help="Overwrite the output file if it already exists."
    ),
    append: bool = typer.Option(
        False, help="Append to an existing output file instead of overwriting."
    ),
) -> None:
    """Generate Product Owner outputs for each concept payload."""

    ensure_dirs()
    if overwrite and append:
        typer.echo("[error] --overwrite and --append are mutually exclusive.")
        raise typer.Exit(code=1)

    if output_path.exists() and not (overwrite or append):
        typer.echo(
            f"[error] Output file already exists: {output_path}. "
            "Use --overwrite or --append to continue."
        )
        raise typer.Exit(code=1)

    entries = list(_load_entries(input_path))
    if offset:
        entries = entries[offset:]
    if limit and limit > 0:
        entries = entries[:limit]

    if not entries:
        typer.echo("[error] No entries to process.")
        raise typer.Exit(code=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "a" if append else "w"
    processed = 0
    failures = 0

    with output_path.open(file_mode, encoding="utf-8") as out_fh:
        for idx, entry in enumerate(entries, start=1 + offset):
            concept = entry.get("concept")
            requirements_yaml = entry.get("requirements_yaml")
            concept_id = entry.get("concept_id") or f"POCON-{idx:04d}"

            if not concept or not requirements_yaml:
                typer.echo(f"[warn] Missing data for entry {concept_id}, skipping.")
                failures += 1
                continue

            typer.echo(f"[run] ({idx}) concept_id={concept_id}")
            _write_requirements(requirements_yaml)
            started = datetime.utcnow()
            result = _run_product_owner(concept)
            duration = (datetime.utcnow() - started).total_seconds()

            vision_yaml = _read_file(VISION_PATH)
            review_yaml = _read_file(REVIEW_PATH)

            record = {
                "input": {
                    "concept_id": concept_id,
                    "concept": concept,
                    "requirements_yaml": requirements_yaml,
                    "tier": entry.get("tier"),
                    "metadata": entry.get("metadata", {}),
                },
                "output": {
                    "product_vision": vision_yaml,
                    "product_owner_review": review_yaml,
                },
                "metadata": {
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "duration_seconds": duration,
                    "exit_code": result.returncode,
                },
            }

            if result.returncode != 0 or not (vision_yaml and review_yaml):
                record["metadata"]["error"] = (
                    f"run_product_owner failed (code={result.returncode})"
                    if result.returncode != 0
                    else "Missing VISION/REVIEW output"
                )
                failures += 1

            out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            processed += 1

    typer.echo(
        f"[ok] Completed {processed} entries "
        f"(failures: {failures}) → {output_path}"
    )


if __name__ == "__main__":
    app()
