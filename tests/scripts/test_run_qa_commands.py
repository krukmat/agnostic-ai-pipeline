import types
from pathlib import Path

from scripts import run_qa


def test_matches_area():
    assert run_qa._matches_area("project/backend-fastapi/app.py", run_qa.BACKEND_PREFIX)
    assert not run_qa._matches_area("other/path", run_qa.BACKEND_PREFIX)


def test_run_cmd_success(tmp_path, monkeypatch):
    story_dir = tmp_path / "S1"
    story_dir.mkdir()

    class DummyRes:
        def __init__(self):
            self.stdout = "ok"
            self.returncode = 0

    monkeypatch.setattr(run_qa.subprocess, "run", lambda *a, **k: DummyRes())
    rc = run_qa.run_cmd(["echo", "hi"], story_dir, cwd=str(tmp_path))
    assert rc == 0
    assert (story_dir / "echo_output.txt").exists()
    assert (story_dir / "logs.txt").exists()


def test_run_cmd_missing(tmp_path, monkeypatch):
    story_dir = tmp_path / "S2"
    story_dir.mkdir()
    def raise_fn(*a, **k):
        raise FileNotFoundError("missing")
    monkeypatch.setattr(run_qa.subprocess, "run", raise_fn)
    rc = run_qa.run_cmd(["missing_cmd"], story_dir)
    assert rc == 127
    assert (story_dir / "logs.txt").exists()
