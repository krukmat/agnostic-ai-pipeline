import os
from pathlib import Path

from scripts import run_cleanup as rc


def test_cleanup_artifacts_flush_all(tmp_path, monkeypatch, capsys):
    # Point module paths to temp
    monkeypatch.setattr(rc, "ROOT", tmp_path)
    monkeypatch.setattr(rc, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(rc, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(rc, "PROJECT", tmp_path / "project")
    monkeypatch.setattr(rc, "DEFAULTS", tmp_path / "project-defaults")
    monkeypatch.setattr(rc, "append_note", lambda msg: None)

    # Seed artifacts/planning/project/defaults
    rc.ART.mkdir()
    rc.PLANNING.mkdir()
    rc.PROJECT.mkdir()
    rc.DEFAULTS.mkdir()
    (rc.ART / "old.log").write_text("x", encoding="utf-8")
    (rc.PLANNING / "notes.md").write_text("plan", encoding="utf-8")
    (rc.PROJECT / "tmp.txt").write_text("proj", encoding="utf-8")
    (rc.DEFAULTS / "keep.txt").write_text("def", encoding="utf-8")

    monkeypatch.setenv("CLEAN_FLUSH", "1")
    rc.cleanup_artifacts_and_planning(flush_all=True)
    out = capsys.readouterr().out
    assert "[cleanup]" in out
    # Artifacts should be empty after flush
    assert not list(rc.ART.glob("**/*"))
    # Planning/project emptied then defaults restored into project
    restored = rc.PROJECT / "keep.txt"
    assert restored.exists()
