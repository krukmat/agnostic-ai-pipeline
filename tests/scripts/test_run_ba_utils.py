from pathlib import Path
import yaml
import pytest

from scripts import run_ba


def test_use_dspy_flag(monkeypatch):
    monkeypatch.setattr(run_ba, "load_config_base", lambda: {"features": {"use_dspy_ba": False}})
    assert run_ba._use_dspy() is False
    monkeypatch.setattr(run_ba, "load_config_base", lambda: {"features": {"use_dspy_ba": True}})
    assert run_ba._use_dspy() is True


def test_run_dspy_writes_requirements(tmp_path, monkeypatch):
    # Redirect planning dir
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run_ba, "PLANNING", planning)
    monkeypatch.setattr(run_ba, "ensure_dirs", lambda: None)
    # Stub DSPy generator and LM builder
    monkeypatch.setattr(run_ba, "build_lm_for_role", lambda role: None)
    monkeypatch.setattr(run_ba, "dsp_generate", lambda concept, lm=None: {"requirements": {"title": "t"}})
    res = run_ba._run_dspy("demo")
    req_file = run_ba.PLANNING / "requirements.yaml"
    assert req_file.exists()
    data = yaml.safe_load(req_file.read_text(encoding="utf-8"))
    assert data["meta"]["original_request"] == "demo"
    assert res["requirements_path"].endswith("requirements.yaml")


@pytest.mark.asyncio
async def test_generate_requirements_legacy(monkeypatch, tmp_path):
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run_ba, "PLANNING", planning)
    monkeypatch.setattr(run_ba, "_use_dspy", lambda: False)
    monkeypatch.setattr(run_ba, "ensure_dirs", lambda: None)

    class DummyLegacy:
        async def generate_requirements(self, concept):
            out = planning / "requirements.yaml"
            out.write_text("title: legacy", encoding="utf-8")
            return {"legacy": True}

    monkeypatch.setattr(run_ba, "_load_legacy_module", lambda: DummyLegacy())
    monkeypatch.setattr(run_ba, "get_db_context_or_default", lambda: None)

    res = await run_ba.generate_requirements("legacy concept")
    assert res.get("legacy") is True
    assert (planning / "requirements.yaml").exists()
