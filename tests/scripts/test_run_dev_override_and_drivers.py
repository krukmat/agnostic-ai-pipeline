import asyncio
import json
from pathlib import Path

import pytest

from scripts import run_dev


class DummyCtx:
    def __init__(self):
        self.events = []
        self.attempts = []
        self.enabled = True

    def log_event(self, *a, **k):
        self.events.append((a, k))

    def save_artifact(self, *a, **k):
        pass

    def log_attempt(self, **kwargs):
        self.attempts.append(kwargs)


class DummyClient:
    def __init__(self, role=None, complexity=None):
        self.role = role
        self.complexity = complexity
        self.provider_type = "dummy"
        self.model = "dummy"
        self.provider_options = {}
        self.cli_command = []

    async def chat(self, system, user):
        return json.dumps({"path": "project/backend-fastapi/app/demo.py", "code": "print('hi')"})


def _setup_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(run_dev, "ROOT", tmp_path)
    monkeypatch.setattr(run_dev, "PLAN", tmp_path / "planning")
    monkeypatch.setattr(run_dev, "PROJECT", tmp_path / "project")
    monkeypatch.setattr(run_dev, "DEV_ART_DIR", tmp_path / "artifacts" / "dev")
    run_dev.PLAN.mkdir(parents=True, exist_ok=True)
    run_dev.PROJECT.mkdir(parents=True, exist_ok=True)
    run_dev.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)


@pytest.mark.asyncio
async def test_implement_story_model_override(monkeypatch, tmp_path):
    _setup_paths(tmp_path, monkeypatch)
    story = {
        "id": "S1",
        "status": "todo",
        "metadata": {"model_override": {"provider": "codex_cli", "model": "demo"}},
    }
    (run_dev.PLAN / "stories.yaml").write_text(json.dumps([story]), encoding="utf-8")

    monkeypatch.setattr(run_dev, "load_stories", lambda: [story])
    monkeypatch.setattr(run_dev, "repo_tree", lambda limit=300: "project/\n")
    monkeypatch.setattr(run_dev, "extract_files_block", lambda resp, sid: [{"path": "project/app.py", "content": "print('x')"}])
    monkeypatch.setattr(run_dev, "_load_config", lambda: ({}, {}))
    monkeypatch.setattr(run_dev, "Client", DummyClient)
    monkeypatch.setattr("llm.Client", DummyClient)
    monkeypatch.setattr(run_dev, "get_db_context_or_default", lambda: DummyCtx())
    res = await run_dev.implement_story("S1", retries=1)
    assert res["status"] == "done"
    assert res["written"]


@pytest.mark.asyncio
async def test_implement_story_runs_drivers(monkeypatch, tmp_path):
    _setup_paths(tmp_path, monkeypatch)
    story = {"id": "S2", "status": "todo"}
    (run_dev.PLAN / "stories.yaml").write_text(json.dumps([story]), encoding="utf-8")

    monkeypatch.setattr(run_dev, "load_stories", lambda: [story])
    monkeypatch.setattr(run_dev, "repo_tree", lambda limit=300: "project/\n")
    monkeypatch.setattr(run_dev, "extract_files_block", lambda resp, sid: [{"path": "project/app.py", "content": "print('x')"}])
    monkeypatch.setattr(run_dev, "Client", DummyClient)
    monkeypatch.setattr("llm.Client", DummyClient)
    monkeypatch.setattr(run_dev, "get_db_context_or_default", lambda: DummyCtx())

    def fake_load_driver(area, sel):
        return type("Drv", (), {
            "id": sel,
            "category": area,
            "language": "py",
            "framework": "fastapi",
            "build": type("B", (), {"command": "echo build"})(),
            "test": type("T", (), {"command": "echo test"})(),
            "lint": type("L", (), {"command": "echo lint"})(),
            "artifact_paths": [],
        })()

    monkeypatch.setattr(run_dev, "load_driver", fake_load_driver)
    monkeypatch.setattr(run_dev, "run_driver_cmd", lambda *a, **k: 0)
    monkeypatch.setattr(run_dev, "_resolve_targets", lambda cfg: {"backend": "be1", "frontend": "fe1"})
    monkeypatch.setattr(run_dev, "_embedded_detection", lambda *a, **k: None)
    monkeypatch.setattr(run_dev, "_scaffold_templates", lambda *a, **k: None)
    monkeypatch.setattr(run_dev, "_load_config", lambda: ({}, {"enabled": True, "templates": {"apply": True}}))

    res = await run_dev.implement_story("S2", retries=1)
    summary = run_dev.DEV_ART_DIR / "S2" / "run-"
    assert res["status"] == "done"
    assert any((run_dev.DEV_ART_DIR / "S2").glob("run-*/dev_summary.json"))
