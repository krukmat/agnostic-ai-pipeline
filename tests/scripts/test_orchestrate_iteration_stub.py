import asyncio

import pytest

from scripts import orchestrate as orch


@pytest.mark.asyncio
async def test_process_iteration_basic(monkeypatch):
    stories = [{"id": "S1", "status": "todo", "metadata": {}}]
    monkeypatch.setattr(orch, "find_in_review_stories", lambda s: [])
    monkeypatch.setattr(orch, "save_stories", lambda s: None)
    monkeypatch.setattr(orch, "load_stories", lambda: stories)
    monkeypatch.setattr(orch, "load_config", lambda: {})
    async def stub_process(story, **kwargs):
        story["status"] = "done"
    monkeypatch.setattr(orch, "_process_story", stub_process)
    result = await orch._process_iteration(
        1,
        stories,
        allow_no_tests=True,
        enable_architect_intervention=False,
        status_no_tests="in_review",
        skip_qa=False,
        max_recovery_attempts=1,
    )
    assert result is True
    assert stories[0]["status"] == "done"
