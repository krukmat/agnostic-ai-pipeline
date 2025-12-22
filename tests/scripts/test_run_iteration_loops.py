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

    calls = []

    async def fake_orchestrator(concept, max_steps, max_actions_per_step):
        calls.append(
            {
                "concept": concept,
                "max_steps": max_steps,
                "max_actions_per_step": max_actions_per_step,
            }
        )

    monkeypatch.setattr(run_iteration, "run_agentic_orchestrator", fake_orchestrator)
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

    assert calls
    assert calls[0]["max_steps"] == 2
