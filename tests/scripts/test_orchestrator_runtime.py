import asyncio
from pathlib import Path

import scripts.orchestrator_runtime as rt


class DummyExecutor:
    def __init__(self):
        self.calls = 0
        self.payloads = []

    async def execute(self, payload):
        self.calls += 1
        self.payloads.append(payload)
        return {"echo": payload}


def test_execute_role_uses_executor(monkeypatch):
    dummy = DummyExecutor()
    monkeypatch.setattr(rt, "get_executor", lambda role, handler, skill_id=None: dummy)
    monkeypatch.setattr(rt, "_ROLE_EXECUTORS", {})
    monkeypatch.setattr(rt, "instrumented", lambda role: (lambda fn: fn))
    monkeypatch.setattr(rt, "load_config", lambda: {})
    res = asyncio.run(rt.execute_role("developer", {"a": 1}))
    assert res["echo"]["a"] == 1
    assert dummy.calls == 1


def test_execute_role_includes_drivers(monkeypatch):
    dummy = DummyExecutor()
    monkeypatch.setattr(rt, "get_executor", lambda role, handler, skill_id=None: dummy)
    monkeypatch.setattr(rt, "_ROLE_EXECUTORS", {})
    monkeypatch.setattr(
        rt,
        "load_driver",
        lambda cat, sel: type(
            "D",
            (),
            {
                "id": sel,
                "category": cat,
                "language": "py",
                "framework": "fastapi",
                "build": type("B", (), {"command": "echo build"})(),
                "test": type("T", (), {"command": "echo test"})(),
                "lint": None,
                "artifact_paths": [],
            },
        )(),
    )
    cfg = {"drivers": {"enabled": True}, "project": {"targets": {"backend": "be1"}}}
    monkeypatch.setattr(rt, "load_config", lambda: cfg)
    monkeypatch.setattr(rt, "instrumented", lambda role: (lambda fn: fn))
    asyncio.run(rt.execute_role("developer", {"story_id": "S1"}))
    assert dummy.calls == 1
    assert dummy.payloads[0]["drivers"]["backend"]["id"] == "be1"


def test_load_stories_uses_planning(tmp_path, monkeypatch):
    planning = tmp_path / "planning"
    planning.mkdir()
    stories_path = planning / "stories.yaml"
    stories_path.write_text("- id: S1\n  status: todo\n", encoding="utf-8")
    monkeypatch.setattr(rt, "PLANNING", planning, raising=False)
    stories = rt.load_stories()
    assert stories and stories[0]["id"] == "S1"
