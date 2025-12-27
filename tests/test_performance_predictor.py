import json

import pytest

from scripts.orchestrator.performance_predictor import PerformancePredictor


def _make_predictor(tmp_path):
    history_dir = tmp_path / "iterations"
    history_dir.mkdir()
    run_dir = history_dir / "iter_1"
    run_dir.mkdir()
    payload = {
        "executions": [
            {"story_id": "S1", "duration": 12},
            {"story_id": "S1", "duration": 18},
        ]
    }
    (run_dir / "latest_orchestrator_summary.json").write_text(json.dumps(payload))
    return PerformancePredictor(history_dir=history_dir)


def test_predict_duration_uses_history(tmp_path):
    predictor = _make_predictor(tmp_path)
    assert predictor.predict_duration("S1") == 15


def test_predict_duration_metadata_estimate():
    predictor = PerformancePredictor(history_dir=None)
    estimate = predictor.predict_duration(
        "S2",
        {"lines_of_code": 200, "dependencies": [1, 2], "test_count": 3},
    )
    assert estimate == 30.0 + 20.0 + 10.0 + 6.0


def test_predict_duration_default():
    predictor = PerformancePredictor(history_dir=None)
    assert predictor.predict_duration("S3") == 60.0


def test_predict_resource_usage_parallel_safe(tmp_path):
    predictor = _make_predictor(tmp_path)
    res = predictor.predict_resource_usage("db_migrate_story")
    assert res["parallel_safe"] is False
    assert res["memory_mb"] == 128
    assert 25 <= res["cpu_percent"] <= 75


def test_train_on_execution_and_confidence():
    predictor = PerformancePredictor(history_dir=None)
    predictor.train_on_execution("S1", 10.0)
    assert predictor.get_confidence_score("S1") == pytest.approx(0.14, rel=1e-6)
    for _ in range(6):
        predictor.train_on_execution("S1", 10.0)
    assert predictor.get_confidence_score("S1") == pytest.approx(0.34, rel=1e-6)
    for _ in range(20):
        predictor.train_on_execution("S1", 10.0)
    assert predictor.get_confidence_score("S1") >= 0.6


def test_predict_batch_duration_and_batch_size(tmp_path):
    predictor = _make_predictor(tmp_path)
    total = predictor.predict_batch_duration(["S1", "S2"])
    assert total == 15 + 60
    assert predictor.get_optimal_batch_size(4, 512) == 2
