import json
from pathlib import Path

from scripts import run_qa


def test_run_cmd_nonzero(tmp_path, monkeypatch):
    story_dir = tmp_path / "S1"
    story_dir.mkdir()

    class DummyRes:
        def __init__(self):
            self.stdout = "boom"
            self.returncode = 1

    monkeypatch.setattr(run_qa.subprocess, "run", lambda *a, **k: DummyRes())
    rc = run_qa.run_cmd(["pytest"], story_dir, cwd=str(tmp_path))
    assert rc == 1
    assert (story_dir / "pytest_error.txt").exists()


def test_run_cmd_file_not_found(tmp_path, monkeypatch):
    story_dir = tmp_path / "S2"
    story_dir.mkdir()

    def raise_fn(*a, **k):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(run_qa.subprocess, "run", raise_fn)
    rc = run_qa.run_cmd(["missing"], story_dir)
    assert rc == 127
    assert (story_dir / "logs.txt").exists()
