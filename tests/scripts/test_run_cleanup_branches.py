import os
import time
import shutil

import pytest

from tests.scripts.test_run_cleanup import _fresh_cleanup_module


def test_cleanup_no_old_files_message(tmp_path, capsys, monkeypatch):
    rc = _fresh_cleanup_module(tmp_path)
    # Ensure no files are removed so the "No old files" branch is hit
    monkeypatch.setenv("ARTIFACT_RETENTION_DAYS", "30")
    rc.cleanup_artifacts_and_planning(flush_all=False)
    out = capsys.readouterr().out
    assert "No old files to clean." in out


def test_cleanup_pyc_and_pycache_warning(tmp_path, capsys, monkeypatch):
    rc = _fresh_cleanup_module(tmp_path)
    rc.ROOT.mkdir(parents=True, exist_ok=True)
    rc.ART.mkdir(parents=True, exist_ok=True)

    # Create an old .pyc file to trigger removal
    stale_pyc = rc.ROOT / "module.pyc"
    stale_pyc.write_text("bytecode", encoding="utf-8")
    old = time.time() - (2 * 60 * 60)
    os.utime(stale_pyc, (old, old))

    # Create __pycache__ directory and force shutil.rmtree to raise to exercise warning path
    cache_dir = rc.ROOT / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "x.pyc").write_text("x", encoding="utf-8")

    original_rmtree = shutil.rmtree

    def flaky_rmtree(path):
        if path == cache_dir:
            raise OSError("cannot remove")
        return original_rmtree(path)

    monkeypatch.setattr(shutil, "rmtree", flaky_rmtree)

    rc.cleanup_artifacts_and_planning(flush_all=False)
    out = capsys.readouterr().out
    # pyc removed, warning for __pycache__ emitted
    assert not stale_pyc.exists()
    assert "Warning: Could not remove __pycache__" in out


def test_cleanup_flush_all_skips_gitkeep_and_dirs(tmp_path, capsys, monkeypatch):
    rc = _fresh_cleanup_module(tmp_path)
    rc.DEFAULTS.mkdir(parents=True, exist_ok=True)
    (rc.DEFAULTS / "template.txt").write_text("content", encoding="utf-8")
    (rc.DEFAULTS / "skip.pyc").write_text("ignore", encoding="utf-8")

    rc.PLANNING.mkdir(parents=True, exist_ok=True)
    (rc.PLANNING / ".gitkeep").write_text("", encoding="utf-8")
    (rc.PLANNING / "tmp.txt").write_text("tmp", encoding="utf-8")

    rc.PROJECT.mkdir(parents=True, exist_ok=True)
    subdir = rc.PROJECT / "to_remove"
    subdir.mkdir()
    (subdir / "file.txt").write_text("data", encoding="utf-8")

    rc.cleanup_artifacts_and_planning(flush_all=True)
    out = capsys.readouterr().out
    # .gitkeep preserved, subdir removed, defaults copied without .pyc
    assert (rc.PLANNING / ".gitkeep").exists()
    assert not subdir.exists()
    assert (rc.PROJECT / "template.txt").exists()
    assert not (rc.PROJECT / "skip.pyc").exists()
    assert "[cleanup]" in out
