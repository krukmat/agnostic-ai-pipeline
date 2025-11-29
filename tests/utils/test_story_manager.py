from __future__ import annotations

from pathlib import Path

import yaml

from scripts.utils import story_manager


def test_load_stories_returns_empty_when_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(story_manager, "STORIES_PATH", tmp_path / "stories.yaml")
    assert story_manager.load_stories() == []


def test_save_and_load_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(story_manager, "STORIES_PATH", tmp_path / "stories.yaml")
    sample = [{"id": "S1", "status": "todo"}]
    story_manager.save_stories(sample)
    loaded = story_manager.load_stories()
    assert loaded == sample


def test_mark_story_status_updates_and_persists(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(story_manager, "STORIES_PATH", tmp_path / "stories.yaml")
    story_manager.save_stories([{"id": "S1", "status": "todo"}])
    ok = story_manager.mark_story_status("S1", "doing")
    assert ok is True
    loaded = story_manager.load_stories()
    assert loaded[0]["status"] == "doing"


def test_mark_story_status_returns_false_when_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(story_manager, "STORIES_PATH", tmp_path / "stories.yaml")
    story_manager.save_stories([{"id": "S1", "status": "todo"}])
    ok = story_manager.mark_story_status("S2", "doing")
    assert ok is False
    assert story_manager.load_stories()[0]["status"] == "todo"


def test_mark_story_todo(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(story_manager, "STORIES_PATH", tmp_path / "stories.yaml")
    story_manager.save_stories([{"id": "S1", "status": "doing"}])
    assert story_manager.mark_story_todo("S1") is True
    assert story_manager.load_stories()[0]["status"] == "todo"


def test_recover_commented_yaml(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(story_manager, "STORIES_PATH", tmp_path / "stories.yaml")
    commented = """
    # - id: S1
    #   status: todo
    """
    (tmp_path / "stories.yaml").write_text(commented, encoding="utf-8")
    loaded = story_manager.load_stories(recover_comments=True)
    assert loaded == [{"id": "S1", "status": "todo"}]


def test_load_stories_dict_wrapper(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(story_manager, "STORIES_PATH", tmp_path / "stories.yaml")
    data = {"stories": [{"id": "S1", "status": "todo"}]}
    (tmp_path / "stories.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    assert story_manager.load_stories() == data["stories"]
