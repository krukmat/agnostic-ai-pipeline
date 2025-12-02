import asyncio
import json

import pytest

from scripts import run_dev


class DummyClient:
    def __init__(self, role=None, complexity=None, provider=None):
        self.provider_type = "dummy"
        self.model = "dummy"

    async def chat(self, system, user):
        return json.dumps({"path": "project/backend-fastapi/app/demo.py", "code": "print('hi')"})  # invalid shape


@pytest.mark.asyncio
async def test_implement_story_handles_no_files(monkeypatch, tmp_path):
    # Redirect paths
    monkeypatch.setattr(run_dev, "ROOT", tmp_path)
    monkeypatch.setattr(run_dev, "PROJECT", tmp_path / "project")
    monkeypatch.setattr(run_dev, "DEV_ART_DIR", tmp_path / "artifacts" / "dev")
    run_dev.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)
    (run_dev.PROJECT).mkdir(parents=True, exist_ok=True)

    # Stubs
    monkeypatch.setattr(run_dev, "load_stories", lambda: [{"id": "S1", "status": "todo", "metadata": {}}])
    monkeypatch.setattr(run_dev, "repo_tree", lambda limit=300: "project/\n")
    monkeypatch.setattr(run_dev, "get_db_context_or_default", lambda: None)
    monkeypatch.setattr(run_dev, "_load_config", lambda: ({}, {}))
    monkeypatch.setattr(run_dev, "extract_files_block", lambda resp, sid: None)
    monkeypatch.setattr(run_dev, "Client", DummyClient)
    async def fake_llm_call(story, files_ctx):
        return "{}", {"provider": "dummy", "model": "dummy"}
    monkeypatch.setattr(run_dev, "llm_call", fake_llm_call)

    res = await run_dev.implement_story("S1", retries=1)
    assert res["status"] == "error"
