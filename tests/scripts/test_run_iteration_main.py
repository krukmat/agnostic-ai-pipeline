from pathlib import Path

from scripts import run_iteration as ri


def test_main_skips_steps_with_flags(monkeypatch, tmp_path):
    # Point module globals to temp
    monkeypatch.setattr(ri, "ROOT", tmp_path)
    monkeypatch.setattr(ri, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(ri, "PROJECT", tmp_path / "project")
    ri.PLANNING.mkdir()
    ri.PROJECT.mkdir()
    # Seed stories.yaml for derived loops
    stories = "- id: S1\n  status: todo\n- id: S2\n  status: todo\n"
    (ri.PLANNING / "stories.yaml").write_text(stories, encoding="utf-8")

    # Stub ensure_dirs and orchestrator to avoid external calls
    monkeypatch.setattr(ri, "ensure_dirs", lambda: None)
    calls = []

    async def fake_orchestrator(concept, max_steps, max_actions_per_step):
        calls.append((concept, max_steps, max_actions_per_step))

    monkeypatch.setattr(ri, "run_agentic_orchestrator", fake_orchestrator)

    rc = ri.main([
        "--concept", "demo",
        "--iteration-name", "iter-test",
        "--skip-ba",
        "--skip-po",
        "--skip-plan",
    ])
    assert rc == 0
    # Should run orchestrator once
    assert calls
    # Snapshot should exist
    snap = tmp_path / "artifacts" / "iterations" / "iter-test" / "summary.json"
    assert snap.exists()
