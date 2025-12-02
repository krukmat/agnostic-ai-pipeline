import os
import time
import types
from pathlib import Path

import pytest


def _fresh_cleanup_module(tmp_path: Path):
    """Reload run_cleanup with paths pointed to a temp root."""
    from importlib import import_module, reload
    import scripts.run_cleanup as rc

    # Point module-level paths to temp
    rc.ROOT = tmp_path
    rc.ART = tmp_path / "artifacts"
    rc.PLANNING = tmp_path / "planning"
    rc.PROJECT = tmp_path / "project"
    rc.DEFAULTS = tmp_path / "project-defaults"
    rc.NOTES_P = rc.PLANNING / "notes.md"
    return rc


def test_cleanup_removes_old_artifacts(tmp_path, monkeypatch):
    rc = _fresh_cleanup_module(tmp_path)
    rc.ART.mkdir(parents=True)
    old_file = rc.ART / "old.txt"
    old_file.write_text("stale", encoding="utf-8")
    # Set mtime to 2 days ago
    two_days = 2 * 24 * 60 * 60
    os.utime(old_file, (time.time() - two_days, time.time() - two_days))

    # Force retention 0 days so anything is removed
    monkeypatch.setenv("ARTIFACT_RETENTION_DAYS", "0")
    rc.cleanup_artifacts_and_planning(flush_all=False)

    assert not old_file.exists()
    # Notes file should be created if cleanup occurred
    assert rc.NOTES_P.exists()


def test_cleanup_flush_all_recreates_defaults(tmp_path):
    rc = _fresh_cleanup_module(tmp_path)
    # Seed project-defaults with a template file
    rc.DEFAULTS.mkdir(parents=True)
    template = rc.DEFAULTS / "README.md"
    template.write_text("template", encoding="utf-8")

    # Project contains a file that should be removed then recreated from defaults
    rc.PROJECT.mkdir(parents=True)
    project_file = rc.PROJECT / "README.md"
    project_file.write_text("old", encoding="utf-8")

    rc.cleanup_artifacts_and_planning(flush_all=True)

    # After flush_all, project README should exist and match template content
    assert project_file.exists()
    assert project_file.read_text(encoding="utf-8") == "template"
