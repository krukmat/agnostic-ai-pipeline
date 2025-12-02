import asyncio

import pytest

from scripts import orchestrate as orch


class DummyCtx:
    def __init__(self):
        self.enabled = True
        self.events = []
        self.attempts = []
        self.meta_updates = []
        self.status_updates = []

    def log_event(self, *a, **k):
        self.events.append((a, k))

    def log_attempt(self, **kwargs):
        self.attempts.append(kwargs)

    def update_story_status(self, sid, status):
        self.status_updates.append((sid, status))

    def update_story_metadata(self, sid, meta):
        self.meta_updates.append((sid, meta))

    def save_artifact(self, *a, **k):
        pass


@pytest.mark.asyncio
async def test_process_story_success(monkeypatch):
    story = {"id": "S1", "metadata": {}, "status": "todo"}
    monkeypatch.setattr(orch, "get_current_context", lambda: DummyCtx())
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
        skip_qa=False,
        max_recovery_attempts=2,
        config={},
    )
    assert story["status"] in {"done", "in_review", "done_no_tests"}


@pytest.mark.asyncio
async def test_process_story_recovery_budget(monkeypatch):
    story = {"id": "S2", "metadata": {"recovery_attempts": 3}, "status": "todo"}
    ctx = DummyCtx()
    monkeypatch.setattr(orch, "get_current_context", lambda: ctx)
    monkeypatch.setattr(orch, "append_note", lambda msg: None)
    async def fake_execute(role, payload):
        return {"status": "ok"}
    monkeypatch.setattr(orch, "execute_role", fake_execute)
    await orch._process_story(
        story,
        allow_no_tests=True,
        status_no_tests="in_review",
        skip_qa=False,
        max_recovery_attempts=2,
        config={},
    )
    assert story["status"] == "blocked_recovery_budget"


@pytest.mark.asyncio
async def test_process_story_qa_fail_force_applicable(monkeypatch):
    story = {"id": "S3", "metadata": {}, "priority": "P1", "status": "todo"}
    ctx = DummyCtx()
    monkeypatch.setattr(orch, "get_current_context", lambda: ctx)
    monkeypatch.setattr(orch, "append_note", lambda msg: None)
    async def fake_execute(role, payload):
        if role == "developer":
            return {"status": "ok", "model_info": {"provider": "p", "model": "m"}}
        return {"status": "fail", "report": {"status": "fail", "failure_details": {"backend": {"errors": [{"error": "coverage", "type": "pytest_failure"}]}}}}
    monkeypatch.setattr(orch, "execute_role", fake_execute)
    await orch._process_story(
        story,
        allow_no_tests=False,
        status_no_tests="in_review",
        skip_qa=False,
        max_recovery_attempts=2,
        config={
            "roles": {"dev": {"backup_models": [{"provider": "p2", "model": "m2", "specialties": ["structured_output"], "reason": "alt", "cost_tier": "free"}]}},
            "pipeline": {"model_fallback": {"allow_cost_increase": False, "prefer_local": True}},
        },
    )
    assert story["status"] in {"in_review", "in_review_tests", "blocked_fatal", "in_review_retry", "blocked_quality_issues"}
