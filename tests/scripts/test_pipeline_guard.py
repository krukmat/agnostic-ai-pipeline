import json
from pathlib import Path

import yaml

from scripts.checks import pipeline_guard
from scripts.utils import story_manager


def _patch_paths(tmp_path, monkeypatch):
    planning = tmp_path / "planning"
    artifacts = tmp_path / "artifacts"
    qa_dir = artifacts / "qa"
    planning.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(pipeline_guard, "PLANNING", planning)
    monkeypatch.setattr(pipeline_guard, "ART", artifacts)
    monkeypatch.setattr(pipeline_guard, "GUARD_REPORT", qa_dir / "pipeline_guard.json")
    monkeypatch.setattr(story_manager, "PLANNING", planning)
    monkeypatch.setattr(story_manager, "STORIES_PATH", planning / "stories.yaml")

    def _ensure_dirs():
        planning.mkdir(parents=True, exist_ok=True)
        artifacts.mkdir(parents=True, exist_ok=True)
        qa_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(pipeline_guard, "ensure_dirs", _ensure_dirs)
    return planning, artifacts


def test_guard_fails_when_po_not_approved(tmp_path, monkeypatch):
    planning, _ = _patch_paths(tmp_path, monkeypatch)
    (planning / "product_owner_review.yaml").write_text("status: needs_adjustment\n", encoding="utf-8")
    result = pipeline_guard.run_guard(check_architecture=False, allow_empty_stories=True)
    assert not result.passed
    assert any("status" in issue for issue in result.issues)


def test_guard_detects_missing_implements(tmp_path, monkeypatch):
    planning, _ = _patch_paths(tmp_path, monkeypatch)
    (planning / "product_owner_review.yaml").write_text("status: approved\n", encoding="utf-8")
    (planning / "requirements.yaml").write_text(
        yaml.safe_dump({"functional_requirements": [{"id": "FR001"}]}),
        encoding="utf-8",
    )
    (planning / "stories.yaml").write_text(
        yaml.safe_dump([{"id": "S1", "title": "Story without implements"}]),
        encoding="utf-8",
    )

    result = pipeline_guard.run_guard(check_architecture=False, allow_empty_stories=False)
    assert not result.passed
    assert any("implements" in issue for issue in result.issues)


def test_guard_passes_with_complete_artifacts(tmp_path, monkeypatch):
    planning, artifacts = _patch_paths(tmp_path, monkeypatch)
    (planning / "product_owner_review.yaml").write_text("status: approved\n", encoding="utf-8")
    (planning / "architecture.yaml").write_text("backend: {}\n", encoding="utf-8")
    (planning / "epics.yaml").write_text(yaml.safe_dump([{"id": "E1"}]), encoding="utf-8")
    (planning / "requirements.yaml").write_text(
        yaml.safe_dump({"functional_requirements": [{"id": "FR001"}]}),
        encoding="utf-8",
    )
    (planning / "stories.yaml").write_text(
        yaml.safe_dump([{"id": "S1", "implements": ["FR001"]}]),
        encoding="utf-8",
    )

    result = pipeline_guard.run_guard(check_architecture=True, allow_empty_stories=False)
    assert result.passed
    report_path = artifacts / "qa" / "pipeline_guard.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report.get("passed") is True
