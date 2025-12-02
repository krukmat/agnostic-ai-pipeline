import asyncio
from pathlib import Path

import pytest

from scripts import orchestrate as orch


@pytest.mark.asyncio
async def test_run_architect_for_review_uses_execute_role(monkeypatch, tmp_path):
    called = {}

    async def fake_execute(role, payload):
        called["payload"] = payload
        return {"status": "ok"}

    monkeypatch.setenv("CONCEPT", "Demo concept")
    monkeypatch.setattr(orch, "execute_role", fake_execute)
    res = await orch.run_architect_for_review({"id": "S1", "metadata": {"last_failure_reason": "x"}}, iteration_count=2)
    assert res["status"] == "ok"
    assert called["payload"]["detail_level"] == "maximum"
    assert called["payload"]["story_id"] == "S1"


def test_next_todo_batch_and_find_in_review():
    stories = [
        {"id": "S1", "status": "todo"},
        {"id": "S2", "status": "in_review"},
        {"id": "S3", "status": "todo"},
    ]
    batch = orch.next_todo_batch(stories, batch_size=1)
    assert batch == [{"id": "S1", "status": "todo"}]
    rev = orch.find_in_review_stories(stories)
    assert rev == [{"id": "S2", "status": "in_review"}]


def test_append_note_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(orch, "NOTES_P", tmp_path / "notes.md")
    orch.append_note("hello")
    assert (tmp_path / "notes.md").exists()
    assert "hello" in (tmp_path / "notes.md").read_text()
