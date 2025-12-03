import asyncio
import types
import json

import pytest
import click

from scripts import run_ba
from scripts.utils.db_logger import DbLogger


def test_load_legacy_module_failure(monkeypatch):
    monkeypatch.setattr(run_ba.importlib.util, "spec_from_file_location", lambda *a, **k: None)
    with pytest.raises(ImportError):
        run_ba._load_legacy_module()


def test_generate_requirements_legacy_db(monkeypatch, tmp_path):
    monkeypatch.setattr(run_ba, "_use_dspy", lambda: False)
    monkeypatch.setattr(run_ba, "PLANNING", tmp_path / "planning")
    run_ba.PLANNING.mkdir(parents=True, exist_ok=True)

    class DummyLegacy:
        async def generate_requirements(self, concept):
            # produce requirements.yaml
            (run_ba.PLANNING / "requirements.yaml").write_text("meta: {}", encoding="utf-8")
            return {"ok": True}

    monkeypatch.setattr(run_ba, "_load_legacy_module", lambda: DummyLegacy())

    events = []
    artifacts = []
    class DummyDB:
        enabled = True
        def log_event(self, *a, **k):
            events.append((a, k))
        def save_artifact(self, *a, **k):
            artifacts.append((a, k))

    monkeypatch.setattr(run_ba, "get_db_context_or_default", lambda: DummyDB())
    monkeypatch.setattr(run_ba, "DbLogger", lambda ctx=None: DbLogger(DummyDB()))

    result = asyncio.run(run_ba.generate_requirements("demo"))
    assert result.get("ok") is True
    assert events and artifacts  # DB paths hit


def test_generate_requirements_dspy(monkeypatch, tmp_path):
    monkeypatch.setattr(run_ba, "_use_dspy", lambda: True)
    monkeypatch.setattr(run_ba, "PLANNING", tmp_path / "planning")
    run_ba.PLANNING.mkdir(parents=True, exist_ok=True)

    called = {}
    monkeypatch.setattr(run_ba, "build_lm_for_role", lambda role: "lm")
    monkeypatch.setattr(run_ba, "dsp_generate", lambda concept, lm=None: {"requirements": [{"id": "R1"}]})
    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
    monkeypatch.setattr(run_ba, "get_db_context_or_default", lambda: DummyCtx())

    out = run_ba._run_dspy("demo concept")
    assert (run_ba.PLANNING / "requirements.yaml").exists()
    assert "requirements_path" in out


def test_generate_cli_missing_concept(monkeypatch):
    with pytest.raises(click.exceptions.Exit):
        run_ba.generate(concept=None)


def test_generate_cli_with_concept(monkeypatch):
    called = {}
    monkeypatch.setattr(run_ba, "generate_requirements", lambda concept: {"c": concept})
    monkeypatch.setattr(run_ba.asyncio, "run", lambda coro: called.setdefault("res", {"ok": True}))
    captured = []
    monkeypatch.setattr(run_ba.typer, "echo", lambda msg: captured.append(msg))
    run_ba.generate(concept="demo")
    assert captured and "ok" in json.dumps(captured[0]) or captured
