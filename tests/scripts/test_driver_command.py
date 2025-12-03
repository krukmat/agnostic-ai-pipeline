from pathlib import Path

from scripts.utils.driver_command import DriverCommand


def test_driver_command_execute(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    calls = {}

    def fake_run(cmd, name, root, logf, log, role):
        calls["cmd"] = cmd
        logf.write_text("ok", encoding="utf-8")
        return 0

    monkeypatch.setattr("scripts.utils.driver_command.run_driver_cmd", fake_run)
    dc = DriverCommand("backend", "be1", "test", "echo hi", log_dir)
    rc = dc.execute()
    assert rc == 0
    assert (log_dir / "backend_be1_test.log").exists()
    assert calls["cmd"] == "echo hi"


def test_driver_command_empty(tmp_path):
    dc = DriverCommand("backend", "be1", "test", "", tmp_path)
    rc = dc.execute()
    assert rc == 0
