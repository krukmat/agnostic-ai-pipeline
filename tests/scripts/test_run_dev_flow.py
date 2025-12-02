import json
import pathlib
from typing import Any, Dict

import pytest

# Minimal story fixture
STORY = {
    "id": "S_dev_test",
    "title": "Sample",
    "description": "Do something",
    "acceptance": ["ok"],
    "complexity": "simple",
}


class DummyClient:
    def __init__(self, role="dev", complexity=None, provider=None):
        self.provider_type = provider or "dummy"
        self.model = "dummy-model"
        self.chat_calls = []

    async def chat(self, system: str, user: str):
        self.chat_calls.append((system, user))
        # Return a minimal FILES payload writing one file
        files = [{"path": "project/backend-fastapi/app/demo.py", "content": "# demo\n"}]
        return json.dumps({"FILES": files})


@pytest.mark.asyncio
@pytest.mark.skip(reason="Integration-heavy dev flow; skip in fast coverage sweep")
async def test_run_dev_writes_files(monkeypatch, tmp_path, caplog):
    # Point project/artifacts to temp dirs
    root = tmp_path
    project_dir = root / "project"
    artifacts_dir = root / "artifacts"
    project_dir.mkdir(parents=True)
    (project_dir / "backend-fastapi").mkdir(parents=True)
    (artifacts_dir / "dev").mkdir(parents=True)

    # Patch module-level ROOT, PROJECT, and ARTIFACTS
    import scripts.run_dev as mod
    mod.ROOT = root
    mod.PROJECT = project_dir
    mod.ARTIFACTS_ROOT = artifacts_dir

    # Stub load_stories to return our story
    monkeypatch.setattr(mod, "load_stories", lambda: [STORY.copy()])
    # Stub save_stories to capture updated story (module exposes save_stories inside scripts.utils.story_manager)
    saved: Dict[str, Any] = {}
    monkeypatch.setattr("scripts.utils.story_manager.save_stories", lambda stories: saved.setdefault("stories", stories))

    # Stub Client to avoid real LLM
    monkeypatch.setattr(mod, "Client", DummyClient)

    # Stub file context helper to return minimal tree
    monkeypatch.setattr(mod, "repo_tree", lambda limit=300: "project/\n")

    result = await mod.implement_story(story_id="S_dev_test", retries=1)
    assert result.get("status") == "done"

    # File should be written
    out_file = project_dir / "backend-fastapi" / "app" / "demo.py"
    assert out_file.exists()
    assert "# demo" in out_file.read_text(encoding="utf-8")

    # Story should be marked done in saved stories
    assert saved["stories"][0]["status"] == "done"
