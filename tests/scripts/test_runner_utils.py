import subprocess
from pathlib import Path

import pytest

from scripts.utils import runner


def test_area_from_name():
    assert runner.area_from_name("backend_demo") == "backend"
    assert runner.area_from_name("frontend_ui") == "web"
    assert runner.area_from_name("web_app") == "web"
    assert runner.area_from_name("embedded_fw") == "embedded"
    assert runner.area_from_name("misc") == "general"


def test_prepare_env_for_backend(tmp_path, monkeypatch):
    root = tmp_path
    project = root / "project" / "backend-fastapi"
    project.mkdir(parents=True)
    env = runner.prepare_env_for_name("backend_driver", root, base={"PYTHONPATH": ""})
    assert str(project) in env["PYTHONPATH"]


def test_normalize_rc():
    assert runner.normalize_rc(0) == 0
    assert runner.normalize_rc(None) == 0
    assert runner.normalize_rc("3") == 3
    assert runner.normalize_rc("x") == 1
    assert runner.normalize_rc(0, tool_missing=True) == 127


def test_run_driver_cmd_missing_tool(tmp_path, monkeypatch, caplog):
    root = tmp_path
    log_path = root / "out.log"
    # Force FileNotFoundError by using a non-existent executable
    rc = runner.run_driver_cmd("nonexistent_cmd_xyz123", "backend_demo", root, log_path, logger=_DummyLogger())
    assert rc == 127


class _DummyLogger:
    def info(self, msg):  # pragma: no cover - simple stub
        pass
    def warning(self, msg):
        pass
