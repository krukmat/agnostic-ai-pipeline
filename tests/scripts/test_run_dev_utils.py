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
