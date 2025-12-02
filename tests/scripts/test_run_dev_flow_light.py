import asyncio
import json
from pathlib import Path

import pytest

from scripts import run_dev


class DummyClient:
    def __init__(self, role=None, complexity=None, provider=None):
        self.provider_type = "dummy"
        self.model = "dummy"

    async def chat(self, system: str, user: str):
        files = [{"path": "project/backend-fastapi/app/demo.py", "content": "# demo"}]
        return json.dumps({"FILES": files})


@pytest.mark.asyncio
async def test_implement_story_light(monkeypatch, tmp_path):
    # Redirect key paths
    root = tmp_path
    project = root / "project"
    artifacts = root / "artifacts"
    project.mkdir()
    artifacts.mkdir()
    (project / "backend-fastapi").mkdir()
    monkeypatch.setattr(run_dev, "ROOT", root)
    monkeypatch.setattr(run_dev, "PROJECT", project)
    monkeypatch.setattr(run_dev, "DEV_ART_DIR", artifacts / "dev")
    run_dev.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)

    # Stub stories and helpers
    monkeypatch.setattr(run_dev, "load_stories", lambda: [{"id": "S1", "status": "todo", "complexity": "simple"}])
    monkeypatch.setattr("scripts.utils.story_manager.save_stories", lambda stories: None)
    # Patch Client inside run_dev and llm module
    monkeypatch.setattr(run_dev, "Client", DummyClient)
    monkeypatch.setattr("llm.Client", DummyClient)
    monkeypatch.setattr(run_dev, "extract_files_block", lambda resp, sid: [{"path": "project/backend-fastapi/app/demo.py", "content": "# demo"}])
    monkeypatch.setattr(run_dev, "repo_tree", lambda limit=300: "project/\n")
    monkeypatch.setattr(run_dev, "_load_config", lambda: ({}, {}))
    monkeypatch.setattr(run_dev, "get_db_context_or_default", lambda: None)
    res = await run_dev.implement_story("S1", retries=1)
    assert res.get("status") == "done"
    files = list(project.rglob("*.py"))
    assert files  # at least one file written
