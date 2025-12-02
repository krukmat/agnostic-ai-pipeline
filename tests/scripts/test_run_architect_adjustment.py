from scripts import run_architect


def test_try_programmatic_adjustment_high(monkeypatch):
    stories = [
        {"id": "S1", "acceptance": ["A1"], "metadata": {}},
        {"id": "S2", "acceptance": []},
    ]

    monkeypatch.setattr(run_architect, "_load_stories_with_content", lambda: ("", stories))
    ok = run_architect.try_programmatic_adjustment("S1", "high")
    assert ok is True
    assert len(stories[0]["acceptance"]) > 1
