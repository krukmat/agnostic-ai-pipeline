import json

from scripts.orchestrator.optimizer import ExecutionOptimizer


def _make_optimizer(tmp_path, history):
    history_dir = tmp_path / "iterations"
    history_dir.mkdir()
    for idx, entry in enumerate(history, start=1):
        run_dir = history_dir / f"iter_{idx}"
        run_dir.mkdir()
        (run_dir / "latest_orchestrator_summary.json").write_text(json.dumps(entry))
    return ExecutionOptimizer(history_dir=history_dir)


def test_get_optimal_parallelism_defaults(tmp_path):
    optimizer = ExecutionOptimizer(history_dir=tmp_path / "missing")
    assert optimizer.get_optimal_parallelism() == 3


def test_get_optimal_parallelism_uses_best_efficiency(tmp_path):
    history = [
        {"status": "success", "max_parallel": 2, "duration": 10},
        {"status": "success", "max_parallel": 4, "duration": 18},
        {"status": "failed", "max_parallel": 8, "duration": 5},
    ]
    optimizer = _make_optimizer(tmp_path, history)
    assert optimizer.get_optimal_parallelism() == 4


def test_get_optimal_backoff_default_and_linear(tmp_path):
    optimizer = ExecutionOptimizer(history_dir=tmp_path / "empty")
    assert optimizer.get_optimal_backoff("dev") == {"type": "exponential", "base": 60}

    history = [
        {"status": "failed", "dev_failures": [{"retries": 1, "succeeded": False}]},
        {"status": "failed", "dev_failures": [{"retries": 2, "succeeded": False}]},
    ]
    optimizer = _make_optimizer(tmp_path, history)
    assert optimizer.get_optimal_backoff("dev") == {"type": "linear", "base": 120}


def test_get_optimal_backoff_exponential(tmp_path):
    history = [
        {"status": "failed", "qa_failures": [{"retries": 1, "succeeded": True}]},
        {"status": "failed", "qa_failures": [{"retries": 2, "succeeded": True}]},
    ]
    optimizer = _make_optimizer(tmp_path, history)
    assert optimizer.get_optimal_backoff("qa") == {"type": "exponential", "base": 60}


def test_execution_metrics_and_cache(tmp_path):
    history = [
        {"status": "success", "duration": 10},
        {"status": "failed", "duration": 20},
    ]
    optimizer = _make_optimizer(tmp_path, history)
    metrics = optimizer.get_execution_metrics()
    assert metrics["total_executions"] == 2
    assert metrics["successful_executions"] == 1
    assert metrics["avg_duration"] == 15

    cached = optimizer.get_execution_metrics()
    assert cached is metrics

    optimizer.record_execution({"status": "success", "duration": 5})
    updated = optimizer.get_execution_metrics()
    assert updated["total_executions"] == 3
