import asyncio
import json
from pathlib import Path

import scripts.run_orchestrator_agent as orch
from scripts.orchestrator_runtime import load_stories as runtime_load_stories


def test_agentic_respects_max_actions(monkeypatch, tmp_path):
    orch.ART = tmp_path / "artifacts"
    orch.PLANNING = tmp_path / "planning"
    orch.ITERATIONS_DIR = orch.ART / "iterations"
    orch.ensure_dirs = lambda: (orch.ART.mkdir(parents=True, exist_ok=True), orch.PLANNING.mkdir(parents=True, exist_ok=True))

    actions_called = []

    async def fake_call_orch(client, concept, context):
        # request more actions than allowed
        return {
            "state_update": {},
            "next_actions": [
                {"tool": "RUN_DEV_STORY", "arguments": {"story_id": "S1"}},
                {"tool": "RUN_QA_STORY", "arguments": {"story_id": "S1"}},
            ],
            "termination": {"should_stop": False, "reason": ""},
        }

    async def fake_execute(role: str, payload: dict):
        actions_called.append((role, payload))
        return {"status": "ok"}

    monkeypatch.setattr(orch, "_call_orchestrator", fake_call_orch)
    monkeypatch.setattr(orch, "execute_role", fake_execute)
    monkeypatch.setattr(orch, "db_enabled", lambda: False)
    monkeypatch.setattr(orch, "DualWriteContext", None)

    asyncio.run(orch.run_agentic_orchestrator("demo", max_steps=1, max_actions_per_step=1))

    # Only one action should have been dispatched due to max_actions_per_step=1
    assert len(actions_called) == 1
    summary = json.loads((orch.ITERATIONS_DIR / "latest_orchestrator_summary.json").read_text())
    assert summary["steps"][0]["results"][0]["status"] == "ok"


def test_agentic_updates_story_state(monkeypatch, tmp_path):
    orch.ART = tmp_path / "artifacts"
    orch.PLANNING = tmp_path / "planning"
    orch.ITERATIONS_DIR = orch.ART / "iterations"
    orch.ensure_dirs = lambda: (orch.ART.mkdir(parents=True, exist_ok=True), orch.PLANNING.mkdir(parents=True, exist_ok=True))

    decisions = [
        {
            "state_update": {},
            "next_actions": [{"tool": "RUN_DEV_STORY", "arguments": {"story_id": "S1"}}],
            "termination": {"should_stop": False, "reason": ""},
        },
        {
            "state_update": {},
            "next_actions": [{"tool": "RUN_QA_STORY", "arguments": {"story_id": "S1"}}],
            "termination": {"should_stop": True, "reason": "done"},
        },
    ]

    async def fake_call_orch(client, concept, context):
        return decisions.pop(0)

    async def fake_execute(role: str, payload: dict):
        status = "ok" if role == "developer" else "failed"
        return {"status": status, "story_id": payload.get("story_id"), "error": "boom" if status != "ok" else None}

    monkeypatch.setattr(orch, "_call_orchestrator", fake_call_orch)
    monkeypatch.setattr(orch, "execute_role", fake_execute)
    monkeypatch.setattr(orch, "db_enabled", lambda: False)
    monkeypatch.setattr(orch, "DualWriteContext", None)

    asyncio.run(orch.run_agentic_orchestrator("demo", max_steps=3, max_actions_per_step=2))

    summary = json.loads((orch.ITERATIONS_DIR / "latest_orchestrator_summary.json").read_text())
    assert summary["termination"]["reason"] == "done"
    # Last step should capture failure status
    assert summary["steps"][-1]["results"][0]["status"] == "failed"
