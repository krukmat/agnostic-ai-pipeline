import json
import os
from pathlib import Path

import pytest

from scripts import run_qa


@pytest.mark.asyncio
async def test_run_quality_checks_main_flow(monkeypatch, tmp_path):
    # Redirect artifact dirs
    monkeypatch.setattr(run_qa, "QA_ART_DIR", tmp_path / "qa")
    monkeypatch.setattr(run_qa, "DEV_ART_DIR", tmp_path / "dev")
    run_qa.QA_ART_DIR.mkdir(parents=True, exist_ok=True)
    run_qa.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)

    # Stub helpers to avoid real execution
    monkeypatch.setattr(run_qa, "_load_qa_config", lambda: ({}, {"enabled": False}, {}))
    monkeypatch.setattr(run_qa, "load_dev_snapshot", lambda story_id: [])
    monkeypatch.setattr(run_qa, "has_any_test", lambda path: False)
    monkeypatch.setattr(run_qa, "has_any_web_test", lambda path: False)
    monkeypatch.setattr(run_qa, "run_cmd", lambda *args, **kwargs: 0)
    monkeypatch.setattr(run_qa, "log_contains_import_error", lambda *args, **kwargs: [])
    monkeypatch.setattr(run_qa, "fix_backend_test_imports", lambda *args, **kwargs: False)
    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
        def log_attempt(self, *a, **k): ...
    monkeypatch.setattr(run_qa, "get_db_context_or_default", lambda: DummyCtx())

    # Run main via run_quality_checks (captures SystemExit)
    result = run_qa.run_quality_checks(allow_no_tests=True, story="SmokeQA")
    assert result["status"] in {"pass", "no_tests"}
