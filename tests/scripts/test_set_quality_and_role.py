import os
import sys
import yaml
import json
from pathlib import Path

import pytest


def _write_config(path: Path, roles: dict) -> None:
    cfg = {"roles": roles}
    path.write_text(json.dumps(cfg), encoding="utf-8")


def test_set_quality_updates_all_roles(tmp_path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    _write_config(cfg_path, {"ba": {}, "architect": {}, "dev": {}, "qa": {}})

    monkeypatch.setenv("CONFIG_PATH", str(cfg_path))
    argv = ["--profile", "low"]
    # invoke via module to avoid subprocess
    from scripts import set_quality

    # patch sys.argv for argparse
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[2]))
    monkeypatch.setattr(sys, "argv", ["set_quality.py", *argv])
    set_quality.main()

    updated = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    for role_cfg in updated["roles"].values():
        assert role_cfg["temperature"] == 0.05
        assert role_cfg["max_tokens"] == 1536
    captured = capsys.readouterr().out
    assert "quality=low" in captured


def test_set_role_updates_specific_role(tmp_path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    _write_config(cfg_path, {"dev": {"provider": "ollama", "model": "old-model"}})
    monkeypatch.setenv("CONFIG_PATH", str(cfg_path))

    from scripts import set_role

    exit_code = set_role.main(["--role", "dev", "--provider", "vertex_sdk", "--model", "gemini"])
    assert exit_code == 0
    updated = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    dev_cfg = updated["roles"]["dev"]
    assert dev_cfg["provider"] == "vertex_sdk"
    assert dev_cfg["model"] == "gemini"
    assert "updated dev" in capsys.readouterr().out


def test_split_po_dataset_stratified(tmp_path):
    from scripts import split_po_dataset

    data = [
        {"input": {"tier": "simple"}, "id": 1},
        {"input": {"tier": "simple"}, "id": 2},
        {"input": {"tier": "medium"}, "id": 3},
        {"input": {"tier": "medium"}, "id": 4},
    ]
    input_path = tmp_path / "input.jsonl"
    with input_path.open("w", encoding="utf-8") as fh:
        for row in data:
            fh.write(json.dumps(row) + "\n")

    train_path = tmp_path / "train.jsonl"
    val_path = tmp_path / "val.jsonl"

    split_po_dataset.split(
        input_path=input_path,
        train_path=train_path,
        val_path=val_path,
        val_ratio=0.25,
        seed=123,
        stratify_tier=True,
    )

    train = [json.loads(line) for line in train_path.read_text(encoding="utf-8").splitlines()]
    val = [json.loads(line) for line in val_path.read_text(encoding="utf-8").splitlines()]

    # Expect one from each tier in val (stratified) because max(1, len*t) => 1 each
    assert len(val) == 2
    tiers_val = sorted([row["input"]["tier"] for row in val])
    assert tiers_val == ["medium", "simple"]
    assert len(train) == 2
