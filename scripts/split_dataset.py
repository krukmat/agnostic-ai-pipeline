#!/usr/bin/env python3
"""Split JSONL dataset into train/val sets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import typer

app = typer.Typer()


@app.command()
def main(
    input_path: Path = typer.Option(..., "--input", exists=True),
    train_path: Path = typer.Option(Path("artifacts/synthetic/ba_train_v1.jsonl"), "--train"),
    val_path: Path = typer.Option(Path("artifacts/synthetic/ba_val_v1.jsonl"), "--val"),
    split: float = typer.Option(0.8, help="Train ratio (0-1)."),
):
    rows: List[str] = [line for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    train_count = int(len(rows) * split)
    train_rows = rows[:train_count]
    val_rows = rows[train_count:]

    train_path.parent.mkdir(parents=True, exist_ok=True)
    val_path.parent.mkdir(parents=True, exist_ok=True)

    train_path.write_text("\n".join(train_rows) + "\n", encoding="utf-8")
    val_path.write_text("\n".join(val_rows) + "\n", encoding="utf-8")

    typer.echo(
        f"Dataset split -> train: {len(train_rows)} ({train_path}), val: {len(val_rows)} ({val_path})"
    )


if __name__ == "__main__":
    app()
