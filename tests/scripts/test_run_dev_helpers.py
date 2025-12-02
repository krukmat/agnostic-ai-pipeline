from pathlib import Path

import pytest

from scripts import run_dev


def test_load_stories_recovers_commented_yaml(tmp_path, monkeypatch):
    plan_dir = tmp_path / "planning"
    plan_dir.mkdir()
    stories_path = plan_dir / "stories.yaml"
    stories_path.write_text(
        "# - id: S1\n#   status: todo\n#   description: demo\n", encoding="utf-8"
    )
    monkeypatch.setattr(run_dev, "PLAN", plan_dir)
    stories = run_dev.load_stories()
    assert stories and stories[0]["id"] == "S1"


def test_pick_story_prefers_env_match(monkeypatch):
    stories = [
        {"id": "S1", "status": "done"},
        {"id": "S2", "status": "todo"},
    ]
    picked = run_dev.pick_story(stories, "S1")
    assert picked["id"] == "S1"
    picked2 = run_dev.pick_story(stories, None)
    assert picked2["id"] == "S2"


def test_repo_tree_caches_results(tmp_path, monkeypatch):
    root = tmp_path
    project = root / "project"
    project.mkdir()
    sample = project / "backend-fastapi" / "app"
    sample.mkdir(parents=True)
    (sample / "main.py").write_text("print('hi')", encoding="utf-8")

    monkeypatch.setattr(run_dev, "ROOT", root)
    # Reset cache
    monkeypatch.setattr(run_dev, "_repo_tree_cache", {"mtime": 0.0, "content": ""})

    first = run_dev.repo_tree(limit=10)
    second = run_dev.repo_tree(limit=10)
    assert first == second
    assert "project/backend-fastapi/app/main.py" in first
