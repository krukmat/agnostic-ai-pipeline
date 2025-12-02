import asyncio
import pytest

# Skip if FastAPI stack is unavailable; this test only checks loop plumbing.
pytest.importorskip("fastapi")

from scripts import orchestrate as orch


async def _stub_execute_role(role, payload):
    if role == "developer":
        return {"status": "done", "story_id": payload.get("story_id")}
    if role == "qa":
        return {"status": "pass", "story_id": payload.get("story_id"), "report": {"status": "pass"}}
    if role == "architect":
        return {"status": "ok"}
    if role == "business_analyst":
        return {"status": "ok"}
    if role == "product_owner":
        return {"status": "ok"}
    return {"status": "unknown"}


def test_orchestrator_loop_stop(monkeypatch, tmp_path):
    # Stub stories.yaml with one todo
    stories = [{"id": "S1", "status": "todo", "description": "x"}]
    monkeypatch.setattr(orch, "ensure_dirs", lambda: None)
    monkeypatch.setenv("MAX_LOOPS", "1")
    monkeypatch.setenv("ALLOW_NO_TESTS", "1")

    # Stub helpers
    monkeypatch.setattr(orch, "load_stories", lambda: stories)
    monkeypatch.setattr(orch, "save_stories", lambda s: None)
    monkeypatch.setattr(orch, "execute_role", _stub_execute_role)
    monkeypatch.setattr(orch, "cleanup_artifacts", lambda: None)
    monkeypatch.setattr(orch, "append_note", lambda msg: None)
    monkeypatch.setattr(orch, "db_enabled", lambda: False)

    # Run a single iteration directly to avoid nested asyncio.run
    asyncio.run(orch._process_iteration(1, stories, allow_no_tests=True, enable_architect_intervention=False, status_no_tests="in_review", skip_qa=False, max_recovery_attempts=1))
