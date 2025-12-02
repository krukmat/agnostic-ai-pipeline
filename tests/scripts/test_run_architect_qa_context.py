from pathlib import Path
import json
from scripts import run_architect


def test_extract_qa_failure_context_no_report(tmp_path, monkeypatch):
    monkeypatch.setattr(run_architect, "ROOT", tmp_path)
    # Ensure artifacts/qa/last_report.json missing
    ctx = run_architect.extract_qa_failure_context("S1")
    assert "No QA report available" in ctx


def test_extract_qa_failure_context_other_story(tmp_path, monkeypatch):
    monkeypatch.setattr(run_architect, "ROOT", tmp_path)
    qa_dir = tmp_path / "artifacts" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "story_context": "S2",
        "failure_details": {"backend": {"errors": [{"test": "t1", "error": "boom"}]}},
    }
    (qa_dir / "last_report.json").write_text(json.dumps(report), encoding="utf-8")
    ctx = run_architect.extract_qa_failure_context("S1")
    assert "correspond to S2" in ctx
