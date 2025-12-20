import os

from scripts import orchestrate as orch


def test_check_and_activate_waiting_stories():
    stories = [
        {"id": "S1", "status": "quality_gate_waiting"},
        {"id": "S2", "status": "todo"},
    ]
    activated = orch.check_and_activate_waiting_stories(stories, "S9")
    assert activated == ["S1"]
    assert stories[0]["status"] == "todo"


def test_analyze_qa_failure_severity_paths(monkeypatch):
    # Critical path
    crit = {"backend": {"errors": [{"error": "ModuleNotFoundError", "type": "environment_fail"}]}}
    out = orch.analyze_qa_failure_severity(crit)
    assert out["severity"] in {"blocked_fatal", "force_applicable"}

    # Force-applicable path
    force = {"backend": {"errors": [{"error": "coverage missing", "type": "pytest_failure", "test": "pytest_execution"}]}}
    out2 = orch.analyze_qa_failure_severity(force)
    assert out2["severity"] == "force_applicable"

    # Test-only path
    test_only = {"backend": {"errors": [{"error": "assert failed", "type": "other"}]}}
    out3 = orch.analyze_qa_failure_severity(test_only)
    assert out3["severity"] in {"test_only", "standard"}


def test_analyze_failure_and_suggest_model(monkeypatch):
    story = {"metadata": {"model_history": [{"provider": "p1", "model": "m1"}], "last_failure_reason": "blocked_dev"}}
    cfg = {
        "roles": {"dev": {"backup_models": [
            {"provider": "p1", "model": "m1", "specialties": ["structured_output"], "reason": "tried"},
            {"provider": "p2", "model": "m2", "specialties": ["structured_output"], "reason": "alt", "cost_tier": "free"},
        ]}},
        "pipeline": {"model_fallback": {"allow_cost_increase": False, "prefer_local": True}},
    }
    suggestion = orch.analyze_failure_and_suggest_model(story, cfg)
    assert suggestion["provider"] == "p2"
