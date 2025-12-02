import os
import time

from scripts import run_cleanup as rc


def test_cleanup_artifacts_deletes_pyc_and_empty_dirs(tmp_path, monkeypatch, capsys):
    # Point paths to temp
    monkeypatch.setattr(rc, "ROOT", tmp_path)
    art = tmp_path / "artifacts"
    art.mkdir()
    old_file = art / "old.pyc"
    old_file.write_text("x", encoding="utf-8")
    # Make file appear old
    os.utime(old_file, (time.time() - 10 * 24 * 3600, time.time() - 10 * 24 * 3600))
    # __pycache__ dir
    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "mod.pyc").write_text("x", encoding="utf-8")

    monkeypatch.setattr(rc, "ART", art)
    monkeypatch.setattr(rc, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(rc, "PROJECT", tmp_path / "project")
    monkeypatch.setattr(rc, "DEFAULTS", tmp_path / "project-defaults")
    monkeypatch.setattr(rc, "append_note", lambda msg: None)
    monkeypatch.setenv("ARTIFACT_RETENTION_DAYS", "1")

    rc.cleanup_artifacts_and_planning(flush_all=False)
    out = capsys.readouterr().out
    assert "cleanup" in out
    assert not old_file.exists() or old_file.stat().st_size == 0
