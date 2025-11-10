"""
Split Product Owner filtered dataset into train/validation sets.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import typer

app = typer.Typer(help="Split filtered PO dataset into train/val JSONL files.")


def _load_jsonl(path: Path) -> List[Dict]:
    entries: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def _write_jsonl(path: Path, entries: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


@app.command()
def split(
    input_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/product_owner_synthetic_filtered.jsonl")
    ),
    train_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/product_owner_train.jsonl")
    ),
    val_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/product_owner_val.jsonl")
    ),
    val_ratio: float = typer.Option(
        0.2, help="Portion of dataset to allocate to validation."
    ),
    seed: int = typer.Option(42, help="Random seed for reproducible splits."),
    stratify_tier: bool = typer.Option(
        True, help="Maintain tier distribution when splitting."
    ),
) -> None:
    entries = _load_jsonl(input_path)
    if not entries:
        typer.echo(f"[error] No entries found at {input_path}")
        raise typer.Exit(code=1)

    rng = random.Random(seed)
    train_entries: List[Dict] = []
    val_entries: List[Dict] = []

    if stratify_tier:
        tiers: Dict[str, List[Dict]] = defaultdict(list)
        for entry in entries:
            tier = entry.get("input", {}).get("tier", "unknown")
            tiers[tier].append(entry)

        for tier, bucket in tiers.items():
            rng.shuffle(bucket)
            val_count = max(1, int(len(bucket) * val_ratio))
            val_entries.extend(bucket[:val_count])
            train_entries.extend(bucket[val_count:])
    else:
        rng.shuffle(entries)
        val_count = int(len(entries) * val_ratio)
        val_entries = entries[:val_count]
        train_entries = entries[val_count:]

    _write_jsonl(train_path, train_entries)
    _write_jsonl(val_path, val_entries)

    typer.echo(
        "[ok] Split complete: "
        f"train={len(train_entries)} val={len(val_entries)} (val_ratio={val_ratio})"
    )


if __name__ == "__main__":
    app()
