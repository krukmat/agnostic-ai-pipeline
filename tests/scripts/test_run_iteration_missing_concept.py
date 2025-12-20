from scripts import run_iteration


def test_run_iteration_requires_concept_when_ba_enabled(monkeypatch):
    calls = []

    def fake_run(cmd, env=None):
        calls.append((cmd, env))
        return 0

    monkeypatch.setattr(run_iteration, "run_command", fake_run)
    monkeypatch.setattr(run_iteration, "snapshot_iteration", lambda *a, **k: None)
    # ensure skip flags are off
    exit_code = run_iteration.main([])
    assert exit_code == 1
    assert calls == []
