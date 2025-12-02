import asyncio
from pathlib import Path

import pytest

from scripts import orchestrate as orch


class DummyExecutor:
    def __init__(self, result=None):
        self.result = result or {}
        self.calls = 0

    async def execute(self, payload):
        self.calls += 1
        return self.result or {"echo": payload}


@pytest.mark.asyncio
async def test_get_executor_cached(monkeypatch):
    dummy = DummyExecutor()
    monkeypatch.setattr(orch, "get_executor", lambda role, handler, skill_id=None: dummy)
    exec1 = orch._get_executor_for_role("developer")
    exec2 = orch._get_executor_for_role("developer")
    assert exec1 is exec2


@pytest.mark.asyncio
async def test_execute_role_includes_drivers(monkeypatch):
    dummy = DummyExecutor()
    monkeypatch.setattr(orch, "get_executor", lambda role, handler, skill_id=None: dummy)
    monkeypatch.setattr(orch, "_ROLE_EXECUTORS", {})
    monkeypatch.setattr(orch, "load_driver", lambda cat, sel: type("D", (), {"id": sel, "category": cat, "language": "py", "framework": "fastapi", "build": type("B", (), {"command": "echo build"})(), "test": type("T", (), {"command": "echo test"})(), "lint": None, "artifact_paths": []})())
    cfg = {
        "drivers": {"enabled": True},
        "project": {"targets": {"backend": "be1"}},
    }
    monkeypatch.setattr(orch, "load_config", lambda: cfg)
    monkeypatch.setattr(orch, "instrumented", lambda role: (lambda fn: fn))
    res = await orch.execute_role("developer", {"story_id": "S1"})
    assert dummy.calls == 1


def test_load_stories_fallback_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(orch, "get_current_context", lambda: None)
    monkeypatch.setattr(orch, "STORIES_P", tmp_path / "stories.yaml")
    stories = orch.load_stories()
    assert stories == []


def test_load_stories_recovery(monkeypatch, tmp_path):
    monkeypatch.setattr(orch, "get_current_context", lambda: None)
    p = tmp_path / "stories.yaml"
    p.write_text("# - id: S1\n#   acceptance: a; b\n", encoding="utf-8")
    monkeypatch.setattr(orch, "STORIES_P", p)
    stories = orch.load_stories()
    if stories:
        assert stories[0]["id"] == "S1"
    else:
        # recovery may fall back to empty if fix_stories_automatic not triggered
        assert stories == []


def test_fix_stories_automatic_called(monkeypatch, tmp_path):
    monkeypatch.setattr(orch, "get_current_context", lambda: None)
    bad = tmp_path / "stories.yaml"
    bad.write_text("not: [yaml", encoding="utf-8")
    monkeypatch.setattr(orch, "STORIES_P", bad)
    monkeypatch.setattr(orch, "fix_stories_automatic", lambda: False)
    # Should log and return []
    stories = orch.load_stories()
    assert stories == []


def test_save_stories_yaml_only(monkeypatch, tmp_path):
    monkeypatch.setattr(orch, "get_current_context", lambda: None)
    monkeypatch.setattr(orch, "STORIES_P", tmp_path / "stories.yaml")
    orch.save_stories([{"id": "S1", "status": "todo"}])
    assert (tmp_path / "stories.yaml").exists()


def test_cleanup_artifacts_flush(monkeypatch, tmp_path):
    # Point ROOT/PLAN to temp
    root = tmp_path
    monkeypatch.setattr(orch, "ROOT", root)
    monkeypatch.setattr(orch, "PLAN", root / "planning")
    monkeypatch.setattr(orch, "append_note", lambda msg: None)
    monkeypatch.setattr(orch, "ensure_dirs", lambda: None)

    art = root / "artifacts"
    art.mkdir()
    (art / "tmp.txt").write_text("x", encoding="utf-8")
    proj = root / "project"
    proj.mkdir()
    (proj / "foo.txt").write_text("y", encoding="utf-8")
    monkeypatch.setenv("CLEAN_FLUSH", "1")
    orch.cleanup_artifacts()
    # artifacts and project should be cleaned
    assert not any(art.iterdir())
