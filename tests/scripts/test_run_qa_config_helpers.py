import json
from pathlib import Path

from scripts import run_qa


def test_load_qa_config_handles_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(run_qa, "ROOT", tmp_path)
    cfg, drv, targets = run_qa._load_qa_config()
    assert cfg == {}
    assert drv == {}
    assert targets == {}


def test_load_dev_snapshot_warns_on_bad_json(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(run_qa, "DEV_ART_DIR", tmp_path)
    story_dir = tmp_path / "S1"
    story_dir.mkdir()
    (story_dir / "files.json").write_text("not-json", encoding="utf-8")
    out = run_qa.load_dev_snapshot("S1")
    assert out == []


def test_has_any_test_and_web(tmp_path):
    py_dir = tmp_path / "backend-fastapi" / "tests"
    py_dir.mkdir(parents=True)
    (py_dir / "test_demo.py").write_text("x", encoding="utf-8")
    assert run_qa.has_any_test(py_dir.parent)

    web_dir = tmp_path / "web-express" / "tests"
    web_dir.mkdir(parents=True)
    (web_dir / "demo.test.js").write_text("x", encoding="utf-8")
    assert run_qa.has_any_web_test(web_dir.parent)
