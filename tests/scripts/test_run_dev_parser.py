import json
from pathlib import Path

import pytest

from scripts import run_dev


def test_extract_files_block_parses_code_field(tmp_path, monkeypatch):
    # Redirect artifact directory to temp to avoid touching real project
    monkeypatch.setattr(run_dev, "DEV_ART_DIR", tmp_path)
    payload = {
        "path": "project/backend-fastapi/app/demo.py",
        "code": "```python\nprint('hi')\n```",
    }
    text = json.dumps(payload)
    files = run_dev.extract_files_block(text, "S1")
    assert files and files[0]["path"].endswith("demo.py")
    assert files[0]["content"] == "print('hi')"
    assert (tmp_path / "S1" / "last_raw.txt").exists()


@pytest.mark.asyncio
async def test_implement_story_returns_error_on_missing_files(tmp_path, monkeypatch):
    # Point everything to temp directories
    root = tmp_path
    project = root / "project"
    project.mkdir()
    monkeypatch.setattr(run_dev, "ROOT", root)
    monkeypatch.setattr(run_dev, "PROJECT", project)
    monkeypatch.setattr(run_dev, "DEV_ART_DIR", root / "artifacts" / "dev")
    run_dev.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)

    # Stub supporting calls
    monkeypatch.setattr(run_dev, "load_stories", lambda: [{"id": "S1", "status": "todo"}])
    monkeypatch.setattr(run_dev, "repo_tree", lambda limit=300: "project/\n")
    monkeypatch.setattr(run_dev, "get_db_context_or_default", lambda: None)
    monkeypatch.setattr(run_dev, "extract_files_block", lambda resp, sid: None)
    monkeypatch.setattr(run_dev, "_load_config", lambda: ({}, {}))

    async def fake_llm_call(story, files_ctx):
        return "{}", {"provider": "dummy", "model": "dummy"}

    monkeypatch.setattr(run_dev, "llm_call", fake_llm_call)

    result = await run_dev.implement_story("S1", retries=1)
    assert result["status"] == "error"
    assert result["story_id"] == "S1"
    # No files should be written under project/
    assert not list(project.rglob("*.py"))
