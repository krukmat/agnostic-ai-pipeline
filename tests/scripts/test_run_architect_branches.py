import asyncio
import json
from pathlib import Path

import pytest

from scripts import run_architect as ra


class DummyCtx:
    def __init__(self):
        self.events = []
        self.artifacts = []
        self.enabled = True

    def log_event(self, *a, **k):
        self.events.append((a, k))

    def save_artifact(self, *a, **k):
        self.artifacts.append((a, k))

    def log_attempt(self, *a, **k):
        pass


class DummyClient:
    def __init__(self, role=None, complexity=None):
        self.role = role
        self.complexity = complexity
        self.provider_type = "dummy"
        self.model = "dummy"
        self.temperature = 0.2
        self.max_tokens = 512

    async def chat(self, system=None, user=None):
        # Return minimal stories/architecture payload
        return json.dumps({
            "stories": [{"id": "S1", "status": "todo", "description": "demo"}],
            "architecture": {"services": []},
        })


@pytest.mark.asyncio
async def test_run_architect_job_happy(monkeypatch, tmp_path):
    # Redirect paths
    monkeypatch.setattr(ra, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(ra, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(ra, "ROOT", tmp_path)
    ra.PLANNING.mkdir(parents=True, exist_ok=True)
    ra.ART.mkdir(parents=True, exist_ok=True)
    (ra.PLANNING / "requirements.yaml").write_text("meta:\n  original_request: demo\n", encoding="utf-8")
    (ra.PLANNING / "stories.yaml").write_text("", encoding="utf-8")

    monkeypatch.setattr(ra, "Client", DummyClient)
    monkeypatch.setattr(ra, "get_db_context_or_default", lambda: DummyCtx())
    def fake_save_text(path, content):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
    monkeypatch.setattr(ra, "save_text", fake_save_text)

    result = await ra.run_architect_job(concept="demo", architect_mode="normal", story_id="", detail_level="medium", iteration_count=1, force_tier=None)
    assert "outputs" in result
    assert (ra.PLANNING / "stories.yaml").exists()
    assert (ra.PLANNING / "architecture.yaml").exists()


def test_get_architect_prompt_override(tmp_path, monkeypatch):
    override = tmp_path / "override.md"
    override.write_text("OVERRIDE", encoding="utf-8")
    cfg = {"features": {"architect": {"use_optimized_prompt": True, "prompt_override_file": str(override)}}}
    monkeypatch.setattr(ra, "_load_config", lambda: cfg)
    prompt = ra.get_architect_prompt("normal", "medium")
    assert "OVERRIDE" in prompt


def test_extract_original_concept_empty():
    assert ra.extract_original_concept("") == ""
    text = json.dumps({"meta": {"original_request": "Build X"}})
    assert ra.extract_original_concept(text) == "Build X"
