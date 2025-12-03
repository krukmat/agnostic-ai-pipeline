import asyncio
import json
from pathlib import Path

import pytest

from scripts import run_dev
import common


def test_try_recover_empty_returns_none():
    assert run_dev._try_recover_commented_yaml("") is None


def test_load_stories_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(run_dev, "PLAN", tmp_path)
    assert run_dev.load_stories() == []


def test_repo_tree_uses_cache(tmp_path, monkeypatch):
    root = tmp_path
    project = root / "project"
    project.mkdir(parents=True, exist_ok=True)
    (project / "a.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(run_dev, "ROOT", root)
    monkeypatch.setattr(run_dev, "_repo_tree_cache", {"mtime": 0.0, "content": ""})
    first = run_dev.repo_tree(limit=10)
    second = run_dev.repo_tree(limit=10)
    assert first == second


@pytest.mark.asyncio
async def test_llm_call_missing_provider(monkeypatch, tmp_path):
    # Prepare prompt files and env
    monkeypatch.setattr(run_dev, "DEV_PROMPT", tmp_path / "developer.md")
    run_dev.DEV_PROMPT.write_text("base prompt", encoding="utf-8")
    monkeypatch.setenv("REQUIRE_TESTS", "0")

    # Force model_override path with unknown provider to trigger ValueError
    story = {"id": "S1", "metadata": {"model_override": {"provider": "missing", "model": "x"}}}

    class DummyClient:
        def __init__(self, role=None, complexity=None):
            pass

    monkeypatch.setattr(run_dev, "Client", DummyClient)
    monkeypatch.setattr(run_dev, "get_db_context_or_default", lambda: None)
    monkeypatch.setattr(common, "load_config", lambda: {})  # llm_call imports from common.load_config

    with pytest.raises(ValueError):
        await run_dev.llm_call(story, files_ctx="tree")


@pytest.mark.asyncio
async def test_llm_call_require_tests_prompt(monkeypatch, tmp_path):
    # Prepare prompts
    monkeypatch.setattr(run_dev, "DEV_PROMPT", tmp_path / "developer.md")
    run_dev.DEV_PROMPT.write_text("base", encoding="utf-8")
    extra_prompt = tmp_path / "tests_prompt.md"
    extra_prompt.write_text("MANDATORY TESTS BLOCK", encoding="utf-8")
    monkeypatch.setenv("REQUIRE_TESTS", "1")
    monkeypatch.setenv("TESTS_ENFORCEMENT_PROMPT_FILE", str(extra_prompt))

    captured = {}

    class DummyClient:
        def __init__(self, role=None, complexity=None):
            self.provider_type = "p"
            self.model = "m"
            self.temperature = 0.0
            self.max_tokens = 1

        async def chat(self, system, user):
            captured["system"] = system
            captured["user"] = user
            return '{"path": "project/demo.txt", "code": "print(1)"}'

    import llm
    monkeypatch.setattr(llm, "Client", DummyClient)
    monkeypatch.setattr(run_dev, "get_db_context_or_default", lambda: None)
    monkeypatch.setattr(common, "load_config", lambda: {"providers": {"p": {"type": "p"}}})

    resp, model_info = await run_dev.llm_call({"id": "S1", "metadata": {}}, files_ctx="tree")
    assert "MANDATORY TESTS BLOCK" in captured["system"]
    assert model_info["provider"] == "p"
    assert resp


@pytest.mark.asyncio
async def test_implement_story_llm_failure(monkeypatch, tmp_path):
    # Redirect paths
    planning = tmp_path / "planning"
    planning.mkdir()
    monkeypatch.setattr(run_dev, "PLAN", planning)
    monkeypatch.setattr(run_dev, "ROOT", tmp_path)
    monkeypatch.setattr(run_dev, "PROJECT", tmp_path / "project")
    monkeypatch.setattr(run_dev, "DEV_ART_DIR", tmp_path / "artifacts")
    run_dev.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run_dev, "DEV_PROMPT", tmp_path / "developer.md")
    run_dev.DEV_PROMPT.write_text("prompt", encoding="utf-8")

    # Seed stories
    (planning / "stories.yaml").write_text("- id: S1\n  status: todo\n", encoding="utf-8")

    # Stub helpers
    monkeypatch.setattr(run_dev, "_load_config", lambda: ({}, {}))
    monkeypatch.setattr(run_dev, "_resolve_targets", lambda cfg: {})
    monkeypatch.setattr(run_dev, "_embedded_detection", lambda *a, **k: None)
    monkeypatch.setattr(run_dev, "_scaffold_templates", lambda *a, **k: None)
    monkeypatch.setattr(run_dev, "get_db_context_or_default", lambda: None)

    async def fake_llm_call(story, ctx):
        return None, {"provider": "p", "model": "m"}

    monkeypatch.setattr(run_dev, "llm_call", fake_llm_call)

    result = await run_dev.implement_story(retries=1)
    assert result["status"] == "error"
    assert result["model_info"]["provider"] == "p"

@pytest.mark.asyncio
async def test_implement_story_writes_and_drivers(monkeypatch, tmp_path):
    planning = tmp_path / "planning"
    planning.mkdir()
    monkeypatch.setattr(run_dev, "PLAN", planning)
    monkeypatch.setattr(run_dev, "ROOT", tmp_path)
    monkeypatch.setattr(run_dev, "DEV_ART_DIR", tmp_path / "artifacts")
    run_dev.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run_dev, "DEV_PROMPT", tmp_path / "developer.md")
    run_dev.DEV_PROMPT.write_text("prompt", encoding="utf-8")

    (planning / "stories.yaml").write_text("- id: S1\n  status: todo\n", encoding="utf-8")

    monkeypatch.setattr(run_dev, "_load_config", lambda: ({"drivers": {"enabled": True}}, {"enabled": True}))
    monkeypatch.setattr(run_dev, "_resolve_targets", lambda cfg: {"backend": "be1", "frontend": "fe1"})
    monkeypatch.setattr(run_dev, "_embedded_detection", lambda *a, **k: None)
    monkeypatch.setattr(run_dev, "_scaffold_templates", lambda *a, **k: None)

    class DummyDriver:
        def __init__(self, id):
            self.id = id
            self.framework = "esp-idf"
            self.templates = []
            self.test = types.SimpleNamespace(command="echo test")
            self.lint = types.SimpleNamespace(command="echo lint")
            self.build = types.SimpleNamespace(command="echo build")

    monkeypatch.setattr(run_dev, "load_driver", lambda cat, sel: DummyDriver(sel))
    monkeypatch.setattr(run_dev, "run_driver_cmd", lambda *a, **k: 0)
    monkeypatch.setattr(run_dev, "has_idf", lambda: (True, "ok"))
    monkeypatch.setattr(run_dev, "has_west", lambda: (False, "missing"))
    def _fake_safe_write(rel, cnt):
        path = tmp_path / "project" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(cnt, encoding="utf-8")
        return f"project/{rel}"
    monkeypatch.setattr(run_dev, "safe_write", _fake_safe_write)

    async def fake_llm_call(story, ctx):
        return json.dumps({"path": "demo.txt", "code": "print(1)"}), {"provider": "p", "model": "m"}

    monkeypatch.setattr(run_dev, "llm_call", fake_llm_call)
    monkeypatch.setattr(run_dev, "get_db_context_or_default", lambda: None)

    result = await run_dev.implement_story(retries=1)
    assert result["status"] == "done"
    assert (tmp_path / "project" / "demo.txt").exists()
    # dev_summary should be written
    summary = list((tmp_path / "artifacts" / "S1").rglob("dev_summary.json"))
    assert summary

@pytest.mark.asyncio
async def test_implement_story_no_stories(monkeypatch):
    monkeypatch.setattr(run_dev, "load_stories", lambda: [])
    monkeypatch.setattr(run_dev, "_load_config", lambda: ({}, {}))
    monkeypatch.setattr(run_dev, "_resolve_targets", lambda cfg: {})
    monkeypatch.setattr(run_dev, "_embedded_detection", lambda *a, **k: None)
    monkeypatch.setattr(run_dev, "_scaffold_templates", lambda *a, **k: None)
    with pytest.raises(SystemExit):
        await run_dev.implement_story(retries=1)
