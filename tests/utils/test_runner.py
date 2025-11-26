from __future__ import annotations

import os
from pathlib import Path

import types

from scripts.utils.runner import (
    area_from_name,
    driver_log_name,
    normalize_rc,
    prepare_env_for_name,
    run_driver_cmd,
)


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg: str):
        self.messages.append(("info", msg))

    def warning(self, msg: str):
        self.messages.append(("warning", msg))


def test_area_from_name_mapping():
    assert area_from_name("backend_fastapi_test") == "backend"
    assert area_from_name("frontend_next_js_build") == "web"
    assert area_from_name("web_next_js_build") == "web"
    assert area_from_name("embedded_esp32_build") == "embedded"
    assert area_from_name("other") == "general"


def test_driver_log_name_and_normalize_rc():
    assert driver_log_name("backend", "fastapi", "test") == "backend_fastapi_test.log"
    assert driver_log_name("web", "next_js", "lint") == "web_next_js_lint.log"

    assert normalize_rc(0) == 0
    assert normalize_rc(None) == 0
    assert normalize_rc(5) == 5
    assert normalize_rc(1, tool_missing=True) == 127


def test_prepare_env_for_backend_adds_pythonpath(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    base = {"PYTHONPATH": "XYZ"}
    env = prepare_env_for_name("backend_fastapi_test", root, base)
    be_path = str(root / "project" / "backend-fastapi")
    assert env["PYTHONPATH"].startswith(be_path)
    assert env["PYTHONPATH"].endswith("XYZ")


def test_run_driver_cmd_success(monkeypatch, tmp_path: Path):
    # Mock subprocess.run to return rc=0 and some output
    class Result:
        returncode = 0
        stdout = "OK"
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *a, **k: Result())

    root = Path(__file__).resolve().parents[2]
    log_path = tmp_path / "backend_fastapi_test.log"
    logger = DummyLogger()
    rc = run_driver_cmd("echo hi", "backend_fastapi_test", root, log_path, logger, role="DEV")
    assert rc == 0
    assert log_path.exists()
    assert "OK" in log_path.read_text(encoding="utf-8")
    # Check that we logged RUN and DONE
    joined = "\n".join(m for _, m in logger.messages)
    assert "[DEV][backend] RUN:" in joined
    assert "[DEV][backend] DONE" in joined


def test_run_driver_cmd_file_not_found(monkeypatch, tmp_path: Path):
    def _raise(*a, **k):
        raise FileNotFoundError("tool not found")

    monkeypatch.setattr("subprocess.run", _raise)
    root = Path(__file__).resolve().parents[2]
    log_path = tmp_path / "frontend_next_js_test.log"
    logger = DummyLogger()
    rc = run_driver_cmd("jest", "frontend_next_js_test", root, log_path, logger, role="QA")
    assert rc == 127
    # Log file may not exist in this error path
    assert any("SKIP tool missing" in m for lvl, m in logger.messages)


def test_run_driver_cmd_nonzero_rc(monkeypatch, tmp_path: Path):
    class Result:
        returncode = 2
        stdout = "out"
        stderr = "err"

    monkeypatch.setattr("subprocess.run", lambda *a, **k: Result())
    root = Path(__file__).resolve().parents[2]
    log_path = tmp_path / "embedded_esp32_test.log"
    logger = DummyLogger()
    rc = run_driver_cmd("idf.py unit-test-app", "embedded_esp32_test", root, log_path, logger, role="QA")
    assert rc == 2
    txt = log_path.read_text(encoding="utf-8")
    assert "out" in txt and "err" in txt
    assert any("ERROR rc=2" in m for lvl, m in logger.messages)
