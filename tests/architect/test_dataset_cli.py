from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from scripts.architect import dataset_cli


runner = CliRunner()


def test_dataset_command_calls_generate(tmp_path: Path):
    with patch("scripts.architect.dataset_cli._dataset_generate") as mock_gen:
        result = runner.invoke(
            dataset_cli.app,
            [
                "dataset",
                "--ba-path",
                str(tmp_path / "ba.jsonl"),
                "--max-records",
                "10",
            ],
        )
        assert result.exit_code == 0
        mock_gen.assert_called_once()
        args, kwargs = mock_gen.call_args
        assert kwargs["max_records"] == 10


def test_ba_normalize_command(tmp_path: Path):
    with patch("scripts.architect.dataset_cli._ba_normalize") as mock_norm:
        result = runner.invoke(
            dataset_cli.app,
            ["ba-normalize", str(tmp_path / "in.jsonl"), str(tmp_path / "out.jsonl")],
        )
        assert result.exit_code == 0
        mock_norm.assert_called_once_with(Path(tmp_path / "in.jsonl"), Path(tmp_path / "out.jsonl"))


def test_ba_remaining_filters_seen(tmp_path: Path, monkeypatch):
    # Point ROOT to tmp so base dataset files live in tmp path
    monkeypatch.setattr(dataset_cli, "ROOT", tmp_path)

    base = tmp_path / "dspy_baseline" / "data" / "production"
    base.mkdir(parents=True)
    train = base / "architect_train.jsonl"

    seen_entry = {
        "target": {
            "stories_yaml": "- id: S1",
            "epics_yaml": "- E1",
            "architecture_yaml": "name: arch",
        }
    }
    # Canonical form will match
    train.write_text(json.dumps(seen_entry) + "\n", encoding="utf-8")

    ba_path = tmp_path / "ba.jsonl"
    keep_entry = {
        "target": {
            "stories_yaml": "- id: S2",
            "epics_yaml": "- E2",
            "architecture_yaml": "name: other",
        }
    }
    ba_entries = [seen_entry, keep_entry]
    ba_path.write_text("\n".join(json.dumps(e) for e in ba_entries), encoding="utf-8")

    out_path = tmp_path / "out.jsonl"
    result = runner.invoke(
        dataset_cli.app,
        ["ba-remaining", "--ba-path", str(ba_path), "--out", str(out_path)],
    )
    assert result.exit_code == 0
    out_lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(out_lines) == 1
    assert json.loads(out_lines[0])["target"]["stories_yaml"] == "- id: S2"
