import asyncio
from copy import deepcopy
from typing import List, Tuple, Dict

from scripts import run_iteration


def test_run_iteration_invokes_agentic_with_args(monkeypatch):
    calls: List[Tuple[str, int, int]] = []
    snapshots: List[Tuple[str, str, int, bool]] = []

    async def fake_agentic(concept: str, max_steps: int, max_actions_per_step: int):
        calls.append((concept, max_steps, max_actions_per_step))

    def fake_snapshot(name: str, concept: str, loops: int, allow: bool):
        snapshots.append((name, concept, loops, allow))

    monkeypatch.setattr(run_iteration, "run_agentic_orchestrator", fake_agentic)
    monkeypatch.setattr(run_iteration, "snapshot_iteration", fake_snapshot)
    monkeypatch.setattr(run_iteration, "ensure_dirs", lambda: None)

    rc = run_iteration.main(["--concept", "demo", "--loops", "2", "--iteration-name", "iter-x"])
    assert rc == 0
    assert calls == [("demo", 2, 2)]
    assert snapshots == [("iter-x", "demo", 2, False)]


def test_run_iteration_uses_default_concept_and_derived_loops(monkeypatch, tmp_path):
    # Seed stories to derive loops
    planning = tmp_path / "planning"
    planning.mkdir()
    stories_yaml = "- id: S1\n  status: todo\n- id: S2\n  status: todo\n"
    (planning / "stories.yaml").write_text(stories_yaml, encoding="utf-8")

    monkeypatch.setattr(run_iteration, "PLANNING", planning)
    monkeypatch.setattr(run_iteration, "PROJECT", tmp_path / "project")
    monkeypatch.setattr(run_iteration, "ROOT", tmp_path)
    monkeypatch.setattr(run_iteration, "ensure_dirs", lambda: None)

    calls: List[Tuple[str, int, int]] = []

    async def fake_agentic(concept: str, max_steps: int, max_actions_per_step: int):
        calls.append((concept, max_steps, max_actions_per_step))

    monkeypatch.setattr(run_iteration, "run_agentic_orchestrator", fake_agentic)
    monkeypatch.setattr(run_iteration, "snapshot_iteration", lambda *a, **k: None)
    monkeypatch.setenv("SKIP_BA", "1")

    rc = run_iteration.main([])
    assert rc == 0
    # default concept applied, max_steps derived from stories (2)
    assert calls == [("agentic-adhoc", 2, 2)]
