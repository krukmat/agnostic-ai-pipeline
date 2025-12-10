import json
from pathlib import Path

import pytest

from scripts.orchestrator import cot_analytics


def _sample_entry(phase="PLANNING", layer="planner", kind="decision", **overrides):
    base = {
        "timestamp": "2025-12-10T10:00:00Z",
        "phase": phase,
        "layer": layer,
        "kind": kind,
        "message": "sample message",
        "details": {},
        "inputs": {},
        "reasoning_steps": [],
        "output": None,
        "confidence": 0.9,
    }
    base.update(overrides)
    return base


def test_load_thoughts_handles_missing(tmp_path):
    missing = tmp_path / "missing.jsonl"
    assert cot_analytics.load_thoughts(missing) == []


def test_load_thoughts_parses_jsonl(tmp_path):
    path = tmp_path / "thoughts.jsonl"
    path.write_text(json.dumps(_sample_entry()) + "\n")
    thoughts = cot_analytics.load_thoughts(path)
    assert len(thoughts) == 1
    assert thoughts[0]["phase"] == "PLANNING"


def test_aggregate_thoughts_counts_and_low_confidence():
    entries = [
        _sample_entry(phase="PLANNING", confidence=0.8),
        _sample_entry(phase="DEVELOPMENT", layer="llm", kind="llm_call", confidence=0.5),
        _sample_entry(phase="INTEGRATION", kind="escalation", details={"story_id": "S1"}, confidence=0.7),
    ]
    summary = cot_analytics.aggregate_thoughts(entries, low_conf_threshold=0.75)
    assert summary.total_entries == 3
    assert summary.phases["PLANNING"] == 1
    assert summary.layers["llm"] == 1
    assert summary.kinds["escalation"] == 1
    assert summary.escalations["by_story"]["S1"] == 1
    assert summary.average_confidence > 0
    assert len(summary.low_confidence_entries) == 2  # 0.5 and 0.7


def test_generate_reports_creates_files(tmp_path):
    input_path = tmp_path / "thoughts.jsonl"
    entries = [
        _sample_entry(),
        _sample_entry(kind="escalation", details={"story_id": "S2"}, confidence=0.6),
    ]
    input_path.write_text("\n".join(json.dumps(e) for e in entries))

    output_dir = tmp_path / "out"
    summary = cot_analytics.generate_reports(
        input_path=input_path,
        output_dir=output_dir,
        low_conf_threshold=0.7,
    )

    json_report = output_dir / "analytics.json"
    md_report = output_dir / "analytics.md"
    assert json_report.exists()
    assert md_report.exists()

    data = json.loads(json_report.read_text())
    assert data["total_entries"] == 2
    assert data["escalations"]["by_story"]["S2"] == 1
    assert "Chain of Thought Analytics Summary" in md_report.read_text()
    assert summary.low_confidence_entries  # ensure summary returned same info
