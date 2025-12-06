import pytest
from pathlib import Path

from scripts import run_dev


def test_safe_write_valid(tmp_path, monkeypatch):
    # Redirect ROOT/PROJECT to temp
    root = tmp_path
    project = root / "project"
    project.mkdir()
    monkeypatch.setattr(run_dev, "ROOT", root)
    monkeypatch.setattr(run_dev, "PROJECT", project)

    rel = run_dev.safe_write("project/backend-fastapi/app/demo.py", "hello")
    assert rel == "project/backend-fastapi/app/demo.py"
    out = project / "backend-fastapi" / "app" / "demo.py"
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "hello"


def test_safe_write_rejects_escape(tmp_path, monkeypatch):
    root = tmp_path
    project = root / "project"
    project.mkdir()
    monkeypatch.setattr(run_dev, "ROOT", root)
    monkeypatch.setattr(run_dev, "PROJECT", project)
    with pytest.raises(ValueError):
        run_dev.safe_write("../outside.txt", "bad")


def test_trigger_replan_uses_requirements(monkeypatch, tmp_path):
    req_path = tmp_path / "planning" / "requirements.yaml"
    req_path.parent.mkdir(parents=True)
    req_path.write_text("meta:\n  original_request: demo concept\n", encoding="utf-8")
    monkeypatch.setattr(run_dev, "PLANNING", req_path.parent)
    monkeypatch.setattr(run_dev, "ROOT", tmp_path)

    called = {}

    def fake_run(cmd, check, cwd, env):
        called["cmd"] = cmd
        called["env"] = env
        class Dummy:
            returncode = 0
        return Dummy()

    monkeypatch.setattr(run_dev.subprocess, "run", fake_run)
    run_dev._trigger_replan()
    assert called["env"]["CONCEPT"] == "demo concept"
    assert "run_architect.py" in called["cmd"][-1]
