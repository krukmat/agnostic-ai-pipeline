import asyncio

import pytest

from scripts import orchestrate as orch


@pytest.mark.asyncio
async def test_process_story_respects_recovery_budget(monkeypatch):
    story = {"id": "S1", "metadata": {"recovery_attempts": 2}, "status": "todo"}
    monkeypatch.setattr(orch, "get_current_context", lambda: None)
    monkeypatch.setattr(orch, "append_note", lambda msg: None)
    # Should exit early without calling execute_role
    called = {"dev": 0}
    async def fake_execute(role, payload):
        called["dev"] += 1
        return {"status": "ok"}
    monkeypatch.setattr(orch, "execute_role", fake_execute)
    await orch._process_story(
        story,
        allow_no_tests=True,
        status_no_tests="in_review",
        skip_qa=True,
        max_recovery_attempts=2,
        config={},
    )
    assert story["status"] == "blocked_recovery_budget"
    assert called["dev"] == 0


@pytest.mark.asyncio
async def test_process_story_dev_only_skip_qa(monkeypatch):
    story = {"id": "S2", "metadata": {}, "status": "todo"}
    monkeypatch.setattr(orch, "get_current_context", lambda: None)
    monkeypatch.setattr(orch, "append_note", lambda msg: None)
    async def fake_execute(role, payload):
        if role == "developer":
            return {"status": "ok", "model_info": {"provider": "p", "model": "m"}}
        return {"status": "pass", "report": {"status": "pass"}}
    monkeypatch.setattr(orch, "execute_role", fake_execute)
    await orch._process_story(
        story,
        allow_no_tests=True,
        status_no_tests="in_review",
        skip_qa=True,
        max_recovery_attempts=3,
        config={},
    )
    assert story["status"] in {"in_review", "done", "done_no_tests"}
