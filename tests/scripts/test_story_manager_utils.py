from pathlib import Path

from scripts.utils import story_manager as sm


def test_recover_commented_yaml_and_load(tmp_path, monkeypatch):
    stories_path = tmp_path / "stories.yaml"
    stories_path.write_text("# - id: S1\n#   status: todo\n", encoding="utf-8")
    monkeypatch.setattr(sm, "STORIES_PATH", stories_path)
    stories = sm.load_stories(recover_comments=True)
    assert stories and stories[0]["id"] == "S1"


def test_mark_story_status_updates(tmp_path, monkeypatch):
    stories_path = tmp_path / "stories.yaml"
    stories_path.write_text("- id: S2\n  status: todo\n", encoding="utf-8")
    monkeypatch.setattr(sm, "STORIES_PATH", stories_path)
    updated = sm.mark_story_status("S2", "done")
    assert updated is True
    loaded = sm.load_stories()
    assert loaded[0]["status"] == "done"


def test_save_stories_writes_yaml(tmp_path, monkeypatch):
    stories_path = tmp_path / "stories.yaml"
    monkeypatch.setattr(sm, "STORIES_PATH", stories_path)
    sm.save_stories([{"id": "S3", "status": "todo"}])
    assert stories_path.exists()
