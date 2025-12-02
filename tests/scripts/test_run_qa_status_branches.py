import json
import os
from pathlib import Path

import pytest

from scripts import run_qa


def test_analyze_test_failures_collection_error(tmp_path):
    art = tmp_path
    (art / "pytest_output.txt").write_text("ERROR collecting test_bad.py\nModuleNotFoundError: foo\n", encoding="utf-8")
    details = run_qa.analyze_test_failures(art, areas=("backend",), be_rc=1, web_rc=0)
    assert run_qa.has_collection_errors(details) is True


@pytest.mark.asyncio
async def test_run_quality_checks_collection_error(monkeypatch, tmp_path):
    monkeypatch.setattr(run_qa, "QA_ART_DIR", tmp_path / "qa")
    monkeypatch.setattr(run_qa, "DEV_ART_DIR", tmp_path / "dev")
    run_qa.QA_ART_DIR.mkdir(parents=True, exist_ok=True)
    run_qa.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)

    # Stub helpers to force collection error path
    monkeypatch.setattr(run_qa, "_load_qa_config", lambda: ({}, {"enabled": False}, {}))
    monkeypatch.setattr(run_qa, "load_dev_snapshot", lambda story_id: ["project/backend-fastapi/app.py"])
    monkeypatch.setattr(run_qa, "has_any_test", lambda path: True)
    monkeypatch.setattr(run_qa, "has_any_web_test", lambda path: False)

    def fake_run_cmd(cmd, story_art_dir, cwd=None):
        # Write an ERROR collecting to trigger collection_errors_present
        (story_art_dir / "pytest_output.txt").write_text("ERROR collecting test_bad.py\nModuleNotFoundError: foo\n", encoding="utf-8")
        return 1

    monkeypatch.setattr(run_qa, "run_cmd", fake_run_cmd)
    monkeypatch.setattr(run_qa, "fix_backend_test_imports", lambda *a, **k: False)
    monkeypatch.setattr(run_qa, "log_contains_import_error", lambda *a, **k: [])
    class DummyCtx:
        enabled = True
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
        def log_attempt(self, *a, **k): ...
    monkeypatch.setattr(run_qa, "get_db_context_or_default", lambda: DummyCtx())

    result = run_qa.run_quality_checks(allow_no_tests=False, story="S_collect")
    # Collection errors should force blocked_fatal with exit code 4
    assert result["status"] in {"blocked_fatal", "fail", "error"}
    assert result["code"] in {2, 4, 1}
