import json

from scripts.orchestrator.analytics_engine import AnalyticsEngine


def _make_engine(tmp_path):
    history_dir = tmp_path / "iterations"
    history_dir.mkdir()

    exec1 = {
        "timestamp": "t1",
        "status": "ok",
        "duration": 10,
        "executions": [
            {"tool": "RUN_DEV", "status": "ok", "duration": 4},
            {"tool": "RUN_QA", "status": "failed", "duration": 2, "error": "timeout"},
        ],
        "phases": [
            {"phase": "REQUIREMENTS", "duration": 2, "status": "ok"},
            {"phase": "DEVELOPMENT", "duration": 8, "status": "failed"},
        ],
    }
    exec2 = {
        "timestamp": "t2",
        "status": "failed",
        "duration": 20,
        "executions": [
            {"tool": "RUN_DEV", "status": "failed", "duration": 7, "error": "compile"},
            {"tool": "RUN_DEV", "status": "ok", "duration": 5},
        ],
        "phases": [
            {"phase": "DEVELOPMENT", "duration": 15, "status": "failed"},
            {"phase": "INTEGRATION", "duration": 5, "status": "ok"},
        ],
    }

    for idx, payload in enumerate((exec1, exec2), start=1):
        run_dir = history_dir / f"iter_{idx}"
        run_dir.mkdir()
        (run_dir / "latest_orchestrator_summary.json").write_text(json.dumps(payload))

    return AnalyticsEngine(history_dir=history_dir)


def test_story_patterns_counts(tmp_path):
    engine = _make_engine(tmp_path)
    patterns = engine.get_story_patterns()
    assert patterns["story"]["count"] == 4
    assert patterns["story"]["success_rate"] == 0.5
    assert patterns["story"]["avg_duration"] == 4.5
    assert patterns["story"]["common_errors"] == ["timeout", "compile"]


def test_bottleneck_analysis_detects_slow_and_failures(tmp_path):
    engine = _make_engine(tmp_path)
    bottlenecks = engine.get_bottleneck_analysis()
    assert any(b["bottleneck_type"] == "slow_phase" for b in bottlenecks)
    assert any(b["bottleneck_type"] == "high_failure_rate" for b in bottlenecks)


def test_role_performance(tmp_path):
    engine = _make_engine(tmp_path)
    perf = engine.get_role_performance("dev")
    assert perf["count"] == 3
    assert perf["success_rate"] == 2 / 3
    assert perf["avg_duration"] == 16 / 3
    assert perf["error_distribution"]["compile"] == 1


def test_execution_timeline(tmp_path):
    engine = _make_engine(tmp_path)
    timeline = engine.get_execution_timeline()
    assert timeline[0]["execution_count"] == 2
    assert timeline[0]["success_rate"] == 0.5
    assert timeline[1]["execution_count"] == 2


def test_predict_success_probability(tmp_path):
    engine = _make_engine(tmp_path)
    prob = engine.predict_success_probability({"story_type": "story", "complexity": 10, "dependencies": [1, 2]})
    assert 0.1 <= prob <= 1.0
    assert prob == 0.5 * 0.9 * 0.92


def test_trend_analysis(tmp_path):
    engine = _make_engine(tmp_path)
    trend = engine.get_trend_analysis()
    assert trend["overall_trend"] == "stable"
    assert trend["trend_direction"] == "flat"
    assert trend["success_rate_change"] == 0.0


def test_export_summary(tmp_path):
    engine = _make_engine(tmp_path)
    summary = engine.export_summary()
    assert summary["execution_count"] == 2
    assert "story_patterns" in summary
    assert "bottlenecks" in summary
