from pathlib import Path

from scripts.utils import orchestrator_facade as facade


def test_resolve_story_env_match(monkeypatch):
    stories = [
        {"id": "S1", "status": "todo"},
        {"id": "S2", "status": "todo"},
    ]
    monkeypatch.setattr(facade, "load_stories_from_planning", lambda p=None: stories)
    s = facade.resolve_story("s2")
    assert s["id"] == "S2"


def test_resolve_story_first_todo(monkeypatch):
    stories = [
        {"id": "S1", "status": "todo"},
        {"id": "S2", "status": "done"},
    ]
    monkeypatch.setattr(facade, "load_stories_from_planning", lambda p=None: stories)
    s = facade.resolve_story(None)
    assert s["id"] == "S1"


def test_ensure_artifact_dir(tmp_path):
    out = facade.ensure_artifact_dir(tmp_path, "S1")
    assert out.exists()
    assert out.name == "S1"


def test_write_report_files(tmp_path):
    story_dir = tmp_path / "qa" / "S1"
    report = {"status": "pass", "story": "S1"}
    out = facade.write_report_files(report, story_dir, last_report_dir=tmp_path / "qa")
    assert out.exists()
    assert (tmp_path / "qa" / "last_report.json").exists()


def test_log_attempt_safe_noop(monkeypatch):
    class Dummy:
        enabled = False
    dummy = Dummy()
    facade.log_attempt_safe(dummy, story_id="S1", role="qa", status="success")
    assert True  # no exception
