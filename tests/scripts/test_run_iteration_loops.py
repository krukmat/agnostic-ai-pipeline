from pathlib import Path
import yaml
from scripts import run_iteration


def test_derived_loops_from_stories(tmp_path, monkeypatch):
    # Prepare stories.yaml with two TODO items
    planning = tmp_path / "planning"
    planning.mkdir()
    stories = [
        {"id": "S1", "status": "todo"},
        {"id": "S2", "status": "todo"},
    ]
    (planning / "stories.yaml").write_text(yaml.safe_dump(stories, sort_keys=False), encoding="utf-8")

    # Patch module paths and helpers
    monkeypatch.setattr(run_iteration, "PLANNING", planning)
    monkeypatch.setattr(run_iteration, "ensure_dirs", lambda: None)

    commands = []

    def fake_run(cmd, env=None):
        commands.append((cmd, dict(env) if env else {}))
        return 0

    monkeypatch.setattr(run_iteration, "run_command", fake_run)
    monkeypatch.setattr(run_iteration, "snapshot_iteration", lambda *args, **kwargs: None)

    # Skip BA/PO/plan to avoid concept requirement
    env = {
        "SKIP_BA": "1",
        "SKIP_PO": "1",
        "SKIP_PLAN": "1",
    }
    monkeypatch.setenv("SKIP_BA", "1")
    monkeypatch.setenv("SKIP_PO", "1")
    monkeypatch.setenv("SKIP_PLAN", "1")

    exit_code = run_iteration.main([])
    assert exit_code == 0

    # Last command should be make loop with MAX_LOOPS=2 (from stories)
    loop_cmd, loop_env = commands[-1]
    assert loop_cmd == ["make", "loop"]
    assert loop_env.get("MAX_LOOPS") == "2"
