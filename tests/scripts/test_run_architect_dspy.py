import asyncio
from types import SimpleNamespace

import pytest
import yaml

from scripts import run_architect as ra


class DummyDB:
    def __init__(self):
        self.enabled = True
        self.events = []
        self.artifacts = []
        self.synced = []

    def log_event(self, *args, **kwargs):
        self.events.append((args, kwargs))

    def save_artifact(self, *args, **kwargs):
        self.artifacts.append((args, kwargs))

    def create_stories_from_list(self, stories):
        self.synced.append(stories)


@pytest.mark.asyncio
async def test_run_architect_job_dspy_db_sync(monkeypatch, tmp_path):
    monkeypatch.setattr(ra, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(ra, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(ra, "ROOT", tmp_path)
    ra.PLANNING.mkdir(parents=True, exist_ok=True)
    ra.ART.mkdir(parents=True, exist_ok=True)
    (ra.PLANNING / "requirements.yaml").write_text("meta: {}", encoding="utf-8")

    # Force DSPy branch and stub heavy components
    monkeypatch.setattr(ra, "_use_dspy_architect", lambda: True)

    async def _fake_classify(content):
        return "simple"

    monkeypatch.setattr(ra, "classify_complexity_with_llm", _fake_classify)
    monkeypatch.setattr(ra, "convert_stories_epics_to_yaml", lambda raw: ("- id: S1\n  status: todo\n", "- epic: E1\n"))
    monkeypatch.setattr(ra, "sanitize_yaml_block", lambda value: value)
    monkeypatch.setattr(ra, "normalize_status", lambda stories: stories)

    class FakeStoriesModule:
        def __call__(self, **kwargs):
            return SimpleNamespace(stories_epics_json="{}")

    class FakeArchitectureModule:
        def __call__(self, **kwargs):
            return SimpleNamespace(architecture_yaml="services: []")

    monkeypatch.setattr(ra, "StoriesEpicsModule", FakeStoriesModule)
    monkeypatch.setattr(ra, "ArchitectureModule", FakeArchitectureModule)

    db_ctx = DummyDB()
    monkeypatch.setattr(ra, "get_db_context_or_default", lambda: db_ctx)
    monkeypatch.setattr(ra, "ensure_dirs", lambda: None)

    result = await ra.run_architect_job(concept="demo", architect_mode="normal")

    assert result["mode"] == "dspy"
    saved = (ra.PLANNING / "stories.yaml").read_text(encoding="utf-8")
    assert "- id: S1" in saved
    assert db_ctx.artifacts and db_ctx.synced  # DB writes and create_stories_from_list executed


@pytest.mark.asyncio
async def test_architect_main_normalizes_and_logs(monkeypatch, tmp_path):
    monkeypatch.setattr(ra, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(ra, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(ra, "ROOT", tmp_path)
    ra.PLANNING.mkdir(parents=True, exist_ok=True)

    db_ctx = DummyDB()
    monkeypatch.setattr(ra, "get_db_context_or_default", lambda: db_ctx)
    monkeypatch.setenv("ARCHITECT_MODE", "normal")
    monkeypatch.setenv("CONCEPT", "demo")
    monkeypatch.setenv("ITERATION_COUNT", "bad")  # trigger ValueError path
    monkeypatch.setattr(ra, "ensure_dirs", lambda: None)
    monkeypatch.setattr(ra, "load_config_base", lambda: {"defaults": {"complexity": "simple"}})

    async def fake_run_architect_job(**kwargs):
        ra.PLANNING.mkdir(parents=True, exist_ok=True)
        (ra.PLANNING / "stories.yaml").write_text("- id: S1\n", encoding="utf-8")
        (ra.PLANNING / "epics.yaml").write_text("- epic: E1\n", encoding="utf-8")
        (ra.PLANNING / "architecture.yaml").write_text("services: []\n", encoding="utf-8")
        (ra.PLANNING / "prd.yaml").write_text("name: demo\n", encoding="utf-8")
        return {"mode": "test", "outputs": {"stories": str(ra.PLANNING / "stories.yaml")}}

    monkeypatch.setattr(ra, "run_architect_job", fake_run_architect_job)

    await ra.main()

    saved = yaml.safe_load((ra.PLANNING / "stories.yaml").read_text(encoding="utf-8"))
    assert saved[0]["status"] == "todo" and saved[0]["complexity"] == "simple"
    assert db_ctx.artifacts  # artifacts persisted
    assert any(evt for evt in db_ctx.events)
