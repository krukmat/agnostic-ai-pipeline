import json
from types import SimpleNamespace

import pytest

from scripts import run_qa


def test_run_cmd_returncode_127(tmp_path, monkeypatch):
    story_dir = tmp_path / "S127"
    story_dir.mkdir()

    class DummyRes:
        def __init__(self):
            self.stdout = "cmd not found"
            self.returncode = 127

    monkeypatch.setattr(run_qa.subprocess, "run", lambda *a, **k: DummyRes())
    rc = run_qa.run_cmd(["missing"], story_dir, cwd=str(tmp_path))
    assert rc == 127
    # Error file should be written for non-zero return code
    assert (story_dir / "missing_error.txt").exists()


def test_run_cmd_generic_exception(tmp_path, monkeypatch):
    story_dir = tmp_path / "SERR"
    story_dir.mkdir()

    def boom(*a, **k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(run_qa.subprocess, "run", boom)
    rc = run_qa.run_cmd(["whatever"], story_dir)
    assert rc == 1


def test_run_quality_checks_embedded_driver(monkeypatch, tmp_path):
    # Redirect artifact directories
    monkeypatch.setattr(run_qa, "QA_ART_DIR", tmp_path / "qa")
    monkeypatch.setattr(run_qa, "DEV_ART_DIR", tmp_path / "dev")
    run_qa.QA_ART_DIR.mkdir(parents=True, exist_ok=True)
    run_qa.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)

    # Config enables drivers only for embedded
    cfg = {"drivers": {"embedded": {"run_test": True}}}
    drv_cfg = {"enabled": True}
    targets = {"embedded": "emb1"}
    monkeypatch.setattr(run_qa, "_load_qa_config", lambda: (cfg, drv_cfg, targets))

    # No backend/web tests
    monkeypatch.setattr(run_qa, "load_dev_snapshot", lambda story_id: [])
    monkeypatch.setattr(run_qa, "has_any_test", lambda path: False)
    monkeypatch.setattr(run_qa, "has_any_web_test", lambda path: False)
    monkeypatch.setattr(run_qa, "run_cmd", lambda *a, **k: 0)

    class DummyDriver(SimpleNamespace):
        def __init__(self):
            super().__init__(id="emb1", framework="esp-idf", test=SimpleNamespace(command="echo emb"))

    monkeypatch.setattr(run_qa, "load_driver", lambda area, name: DummyDriver())
    monkeypatch.setattr(run_qa, "has_idf", lambda: (True, "ok"))

    class DummyProc:
        def __init__(self):
            self.returncode = 0
            self.stdout = "ok"
            self.stderr = ""

    monkeypatch.setattr(run_qa.subprocess, "run", lambda *a, **k: DummyProc())

    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
        def log_attempt(self, *a, **k): ...

    monkeypatch.setattr(run_qa, "get_db_context_or_default", lambda: DummyCtx())

    result = run_qa.run_quality_checks(allow_no_tests=True, story="S_emb")
    assert result["status"] in {"pass", "no_tests"}
    # Embedded log should have been created
    assert any(p.name.startswith("embedded_") for p in (tmp_path / "qa" / "S_emb").glob("embedded_*"))


def test_run_quality_checks_strict_fail(monkeypatch, tmp_path):
    monkeypatch.setattr(run_qa, "QA_ART_DIR", tmp_path / "qa")
    monkeypatch.setattr(run_qa, "DEV_ART_DIR", tmp_path / "dev")
    run_qa.QA_ART_DIR.mkdir(parents=True, exist_ok=True)
    run_qa.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(run_qa, "_load_qa_config", lambda: ({}, {"enabled": False}, {}))
    monkeypatch.setattr(run_qa, "load_dev_snapshot", lambda story_id: ["project/backend-fastapi/app.py"])
    monkeypatch.setattr(run_qa, "has_any_test", lambda path: True)
    monkeypatch.setattr(run_qa, "has_any_web_test", lambda path: False)
    # Backend command fails (rc=1), no collection errors written
    monkeypatch.setattr(run_qa, "run_cmd", lambda *a, **k: 1)
    monkeypatch.setattr(run_qa, "fix_backend_test_imports", lambda *a, **k: False)
    monkeypatch.setattr(run_qa, "log_contains_import_error", lambda *a, **k: [])

    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
        def log_attempt(self, *a, **k): ...

    monkeypatch.setattr(run_qa, "get_db_context_or_default", lambda: DummyCtx())

    result = run_qa.run_quality_checks(allow_no_tests=False, story="S_fail")
    assert result["status"] in {"fail", "blocked_fatal", "error"}
    assert result["code"] in {2, 4, 1}
