import asyncio
import json
from types import SimpleNamespace

import scripts.run_orchestrator_agent as orch


def test_update_story_state_marks_done_and_failed():
    stories = {}
    results = [
        {"tool": "RUN_DEV_STORY", "status": "ok", "story_id": "S1"},
        {"tool": "RUN_QA_STORY", "status": "failed", "story_id": "S2", "error": "boom"},
    ]
    orch._update_story_state(stories, results)
    assert stories["S1"]["status"] == "done"
    assert stories["S2"]["status"] == "failed"
    assert stories["S2"]["last_error"] == "boom"


def test_call_orchestrator_repairs_invalid_json(monkeypatch):
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, system: str, user: str):
            calls["n"] += 1
            if calls["n"] == 1:
                return "not json"
            return json.dumps(
                {"state_update": {}, "next_actions": [], "termination": {"should_stop": True, "reason": ""}}
            )

    ctx = json.dumps({"foo": "bar"})
    result = asyncio.run(orch._call_orchestrator(FakeClient(), "concept", ctx))
    assert result.get("termination", {}).get("should_stop") is True
    assert calls["n"] == 2  # repair path used


def test_run_agentic_orchestrator_creates_summary(monkeypatch, tmp_path):
    # Redirect artifacts/planning to temp
    orch.ART = tmp_path / "artifacts"
    orch.PLANNING = tmp_path / "planning"
    orch.ITERATIONS_DIR = orch.ART / "iterations"

    def fake_ensure_dirs():
        orch.ART.mkdir(parents=True, exist_ok=True)
        orch.PLANNING.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(orch, "ensure_dirs", fake_ensure_dirs)

    async def fake_call_orchestrator(client, concept, context):
        return {"state_update": {}, "next_actions": [], "termination": {"should_stop": True, "reason": "done"}}

    async def fake_execute_role(role: str, payload: dict):
        return {"status": "ok"}

    monkeypatch.setattr(orch, "_call_orchestrator", fake_call_orchestrator)
    monkeypatch.setattr(orch, "execute_role", fake_execute_role)
    monkeypatch.setattr(orch, "db_enabled", lambda: False)
    monkeypatch.setattr(orch, "DualWriteContext", None)

    asyncio.run(orch.run_agentic_orchestrator("demo", max_steps=2, max_actions_per_step=1))

    summary_path = orch.ITERATIONS_DIR / "latest_orchestrator_summary.json"
    assert summary_path.exists()
    data = json.loads(summary_path.read_text())
    assert data["termination"]["reason"] == "done"


def test_build_context_includes_qa_and_dev(monkeypatch, tmp_path):
    # Seed artifacts
    art = tmp_path / "artifacts"
    qa_dir = art / "qa"
    qa_dir.mkdir(parents=True)
    (qa_dir / "last_report.json").write_text(json.dumps({"status": "ok", "stories": []}), encoding="utf-8")
    dev_dir = art / "dev" / "S99"
    dev_dir.mkdir(parents=True)
    (dev_dir / "error.txt").write_text("boom", encoding="utf-8")

    # point globals
    orch.ART = art
    orch.PLANNING = tmp_path / "planning"
    orch.PLANNING.mkdir()
    orch.ITERATIONS_DIR = art / "iterations"

    ctx = orch._build_context(
        "demo",
        actions=[{"tool": "X"}],
        limits={"max_steps": 1, "max_actions_per_step": 1, "step": 1},
        stories_state={},
    )
    data = json.loads(ctx)
    assert data["qa_summary"]["status"] == "ok"
    assert data["dev_errors"]["S99"] == "boom"


def test_dispatch_actions_skips_unknown_tool(monkeypatch):
    actions = [{"tool": "UNKNOWN", "arguments": {"foo": "bar"}}]
    results = asyncio.run(orch._dispatch_actions(actions))
    assert results[0]["status"] == "skipped"
    assert results[0]["error"] == "unknown_tool"
