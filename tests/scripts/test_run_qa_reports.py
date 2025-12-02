import json
from pathlib import Path

from scripts import run_qa


def test_run_quality_checks_generates_report(monkeypatch, tmp_path):
    monkeypatch.setattr(run_qa, "QA_ART_DIR", tmp_path / "qa")
    monkeypatch.setattr(run_qa, "DEV_ART_DIR", tmp_path / "dev")
    run_qa.QA_ART_DIR.mkdir(parents=True, exist_ok=True)
    run_qa.DEV_ART_DIR.mkdir(parents=True, exist_ok=True)

    # No changes => run full but stub to pass
    monkeypatch.setattr(run_qa, "load_dev_snapshot", lambda story_id: [])
    monkeypatch.setattr(run_qa, "_load_qa_config", lambda: ({}, {"enabled": False}, {}))
    monkeypatch.setattr(run_qa, "has_any_test", lambda path: False)
    monkeypatch.setattr(run_qa, "has_any_web_test", lambda path: False)
    monkeypatch.setattr(run_qa, "run_cmd", lambda *a, **k: 0)
    monkeypatch.setattr(run_qa, "log_contains_import_error", lambda *a, **k: [])
    monkeypatch.setattr(run_qa, "fix_backend_test_imports", lambda *a, **k: False)

    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
        def log_attempt(self, *a, **k): ...
    monkeypatch.setattr(run_qa, "get_db_context_or_default", lambda: DummyCtx())

    report = run_qa.run_quality_checks(allow_no_tests=True, story="Sreport")
    # Report files should be written
    assert (run_qa.QA_ART_DIR / "Sreport" / "report.json").exists()
    data = json.loads((run_qa.QA_ART_DIR / "Sreport" / "report.json").read_text(encoding="utf-8"))
    assert data.get("status") in {"pass", "no_tests"}
