from __future__ import annotations

"""Dataset helper CLI extracted from run_architect.py."""

import json
from pathlib import Path
from typing import Optional

import typer
import yaml as _yaml

from scripts.generate_architect_dataset import generate as _dataset_generate
from scripts.normalize_ba_jsonl import normalize as _ba_normalize
from common import ROOT

app = typer.Typer(help="Architect dataset helper CLI")


@app.command("dataset")
def cli_dataset(
    ba_path: Path = typer.Option(..., help="BA outputs JSONL (normalized or mixed)"),
    out_train: Path = typer.Option(ROOT / "dspy_baseline/data/production/architect_train.jsonl", help="Train JSONL output"),
    out_val: Path = typer.Option(ROOT / "dspy_baseline/data/production/architect_val.jsonl", help="Validation JSONL output"),
    min_score: float = typer.Option(0.85, help="Minimum architect_metric score"),
    max_records: int = typer.Option(20, help="Desired sample count"),
    seed: int = typer.Option(42, help="Shuffle seed"),
    resume: bool = typer.Option(False, help="Append to existing JSONL files instead of overwriting"),
    metric_path: Optional[str] = typer.Option(None, help="Optional metric override 'module:function' (default architect_metric)."),
):
    _dataset_generate(
        ba_path=ba_path,
        out_train=out_train,
        out_val=out_val,
        min_score=min_score,
        max_records=max_records,
        seed=seed,
        resume=resume,
        metric_path=metric_path,
    )


@app.command("ba-normalize")
def cli_ba_normalize(
    src: Path = typer.Argument(..., help="Input BA JSONL (mixed shapes)"),
    dst: Path = typer.Argument(..., help="Output normalized BA JSONL"),
):
    _ba_normalize(src, dst)


@app.command("ba-remaining")
def cli_ba_remaining(
    ba_path: Path = typer.Option(..., help="Normalized BA JSONL path"),
    out: Path = typer.Option(..., help="Output BA JSONL excluding dataset keys"),
    subtract_train: bool = typer.Option(True, help="Subtract architect_train.jsonl"),
    subtract_val: bool = typer.Option(True, help="Subtract architect_val.jsonl"),
    subtract_gold: bool = typer.Option(True, help="Subtract architect_train/val_gold.jsonl"),
):
    base = ROOT / "dspy_baseline" / "data" / "production"
    train = base / "architect_train.jsonl"
    val = base / "architect_val.jsonl"
    gtrain = base / "architect_train_gold.jsonl"
    gval = base / "architect_val_gold.jsonl"

    def canon(yaml_str: str) -> str:
        try:
            return _yaml.safe_dump(
                _yaml.safe_load(yaml_str),
                sort_keys=True,
                allow_unicode=True,
                default_flow_style=False,
            )
        except Exception:
            return yaml_str or ""

    seen = set()
    sources = []
    if subtract_train:
        sources.append(train)
    if subtract_val:
        sources.append(val)
    if subtract_gold:
        sources.append(gtrain)
        sources.append(gval)

    for src in sources:
        if src.exists():
            with src.open(encoding="utf-8") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                        tgt = obj.get("target") or {}
                        if isinstance(tgt, dict):
                            stories_yaml = canon(tgt.get("stories_yaml", ""))
                            epics_yaml = canon(tgt.get("epics_yaml", ""))
                            architecture_yaml = canon(tgt.get("architecture_yaml", ""))
                            seen.add((stories_yaml, epics_yaml, architecture_yaml))
                    except Exception:
                        continue

    remaining = []
    with ba_path.open(encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            tgt = obj.get("target") or {}
            if isinstance(tgt, dict):
                key = (
                    canon(tgt.get("stories_yaml", "")),
                    canon(tgt.get("epics_yaml", "")),
                    canon(tgt.get("architecture_yaml", "")),
                )
                if key in seen:
                    continue
            remaining.append(obj)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for obj in remaining:
            fh.write(json.dumps(obj) + "\n")


if __name__ == "__main__":
    app()
