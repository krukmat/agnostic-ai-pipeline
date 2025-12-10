import json
from pathlib import Path

import pytest

from scripts.orchestrator.learning_store import LearningStore


def test_record_and_read(tmp_path):
    store_path = tmp_path / "learning_store.jsonl"
    store = LearningStore(path=store_path, retention_per_story=5)

    store.record_story_result(
        story_id="S1",
        phase="development",
        status="ok",
        attempt=1,
        implements=["FR1"],
    )
    store.record_story_result(
        story_id="S1",
        phase="development",
        status="failed",
        attempt=2,
        error="syntax",
        implements=["FR1"],
    )

    entries = store.get_recent_attempts("S1")
    assert len(entries) == 2
    assert entries[0]["status"] == "failed"
    assert entries[1]["status"] == "ok"
    summary = store.get_error_summary("S1")
    assert summary["syntax"] == 1
    assert summary["no_error"] == 1


def test_retention_enforced(tmp_path):
    store_path = tmp_path / "learning_store.jsonl"
    store = LearningStore(path=store_path, retention_per_story=2)
    for idx in range(4):
        store.record_story_result(
            story_id="S2",
            phase="dev",
            status="ok" if idx % 2 == 0 else "failed",
            attempt=idx + 1,
            comment=f"attempt {idx + 1}",
        )
    entries = store.get_recent_attempts("S2")
    assert len(entries) == 2
    assert entries[0]["attempt"] == 4
    assert entries[1]["attempt"] == 3


def test_empty_read_returns_empty(tmp_path):
    store = LearningStore(path=tmp_path / "learning_store.jsonl")
    assert store.get_recent_attempts("missing") == []
    assert store.get_error_summary("missing") == {}
