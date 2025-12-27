import json

from scripts.orchestrator.feedback_loop import FeedbackCollector


def _collector(tmp_path):
    return FeedbackCollector(feedback_dir=tmp_path)


def test_records_agent_user_execution_feedback(tmp_path):
    collector = _collector(tmp_path)
    collector.record_agent_feedback("dev", "S1", {"helpful": True, "suggestions": ["x"], "errors": ["e1"]})
    collector.record_user_feedback("S1", 2, "bad")
    collector.record_execution_feedback("S1", False, "timeout", duration=3.2)

    assert len(collector.feedback_entries) == 3
    assert collector.agent_feedback["dev"][0]["helpful"] is True
    assert collector.user_feedback[0]["rating"] == 2


def test_load_feedback_from_disk(tmp_path):
    data = {
        "entries": [
            {"type": "user", "story_id": "S1", "rating": 1},
            {"type": "execution", "story_id": "S1", "success": False},
        ]
    }
    (tmp_path / "all_feedback.json").write_text(json.dumps(data))
    collector = _collector(tmp_path)
    assert len(collector.feedback_entries) == 2


def test_analyze_patterns_and_suggestions(tmp_path):
    collector = _collector(tmp_path)
    collector.record_agent_feedback("qa", "S1", {"helpful": True, "suggestions": ["add tests"], "errors": ["e1"]})
    collector.record_user_feedback("S1", 2)
    collector.record_user_feedback("S2", 5)
    collector.record_execution_feedback("S1", False, "timeout")
    collector.record_execution_feedback("S1", True)
    collector.record_execution_feedback("S1", False, "timeout")

    patterns = collector.analyze_feedback_patterns()
    assert patterns["common_errors"]["e1"] == 1
    assert patterns["common_suggestions"]["add tests"] == 1
    assert patterns["low_rating_stories"] == ["S1"]
    assert patterns["high_failure_rates"]["S1"] > 0.3

    suggestions = collector.suggest_improvements()
    assert any("recurring error" in s for s in suggestions)
    assert any("low-rated stories" in s for s in suggestions)
    assert any("failure rate" in s for s in suggestions)
    assert any("Agent feedback" in s for s in suggestions)


def test_apply_learned_rules_and_summary(tmp_path):
    collector = _collector(tmp_path)
    collector.record_execution_feedback("S1", False)
    collector.record_execution_feedback("S1", False)
    collector.record_execution_feedback("S1", False)
    collector.record_execution_feedback("S1", True)

    result = collector.apply_learned_rules()
    assert result["updated_policies"].get("parallelism_reduction") is True
    assert "auto_escalate" in result["updated_policies"]

    summary = collector.get_feedback_summary()
    assert summary["execution_feedback_count"] == 4


def test_export_feedback_report(tmp_path):
    collector = _collector(tmp_path)
    collector.record_execution_feedback("S1", True)
    report = collector.export_feedback_report()
    assert "summary" in report
    assert "patterns" in report
    assert "improvements" in report
    assert "applied_policies" in report
