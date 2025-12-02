import asyncio

from scripts import orchestrate as orch


def test_main_short_circuit(monkeypatch, tmp_path):
    # Short-circuit main by limiting MAX_LOOPS and stubbing helpers
    monkeypatch.setenv("MAX_LOOPS", "1")
    monkeypatch.setenv("ALLOW_NO_TESTS", "1")
    monkeypatch.setattr(orch, "cleanup_artifacts", lambda: None)
    stories = [{"id": "S1", "status": "todo"}]
    monkeypatch.setattr(orch, "load_stories", lambda: stories)
    monkeypatch.setattr(orch, "save_stories", lambda s: None)
    async def fake_process_iteration(idx, stories, **kwargs):
        # mark story done to exit loop
        for s in stories:
            s["status"] = "done"
        return False
    monkeypatch.setattr(orch, "_process_iteration", fake_process_iteration)
    # Call async main; it calls _process_iteration stub which returns False to exit
    import asyncio
    asyncio.run(orch.main())
