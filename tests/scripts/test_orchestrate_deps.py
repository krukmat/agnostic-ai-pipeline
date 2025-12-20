import asyncio

import pytest

from scripts import orchestrate as orch


def test_dependency_activation():
    stories = [
        {"id": "S1", "status": "quality_gate_waiting"},
        {"id": "S2", "status": "todo"},
    ]
    activated = orch.check_and_activate_waiting_stories(stories, "S9")
    assert activated == ["S1"]
    assert stories[0]["status"] == "todo"


def test_analyze_qa_failure_severity_collection_error():
    details = {"backend": {"errors": [{"error": "error collecting test_demo", "type": "pytest_collection_error"}]}}
    out = orch.analyze_qa_failure_severity(details)
    assert out["severity"] in {"blocked_fatal", "test_only"}


def test_analyze_qa_failure_severity_force_applicable():
    details = {"backend": {"errors": [{"error": "coverage missing", "type": "pytest_failure", "test": "pytest_execution"}]}}
    out = orch.analyze_qa_failure_severity(details)
    assert out["severity"] in {"force_applicable", "test_only", "standard"}


@pytest.mark.asyncio
async def test_process_iteration_architect_retry(monkeypatch):
    # Force an in_review story and architect retry
    stories = [{"id": "S1", "status": "in_review", "metadata": {}, "priority": "P1"}]

    async def fake_run_architect(story, iteration_count):
        return {"status": "ok"}

    monkeypatch.setattr(orch, "run_architect_for_review", fake_run_architect)
    monkeypatch.setattr(orch, "save_stories", lambda s: None)
    monkeypatch.setattr(orch, "load_stories", lambda: stories)
    monkeypatch.setattr(orch, "append_note", lambda msg: None)
    monkeypatch.setattr(orch, "load_config", lambda: {})
    async def fake_process_story(*args, **kwargs):
        return None
    monkeypatch.setattr(orch, "_process_story", fake_process_story)
    res = await orch._process_iteration(
        1,
        stories,
        allow_no_tests=True,
        enable_architect_intervention=True,
        status_no_tests="in_review",
        skip_qa=False,
        max_recovery_attempts=1,
    )
    assert res is True
