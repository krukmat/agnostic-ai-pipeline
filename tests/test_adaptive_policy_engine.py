import pytest

from scripts.orchestrator.adaptive_policy_engine import AdaptivePolicyEngine


def test_evaluate_dynamic_escalation_uses_success_rate():
    engine = AdaptivePolicyEngine()
    engine.role_success_rates["dev"] = 0.5
    context = {"role": "dev", "attempts": 2, "errors": ["fail"]}
    reason = engine.evaluate_dynamic_escalation("S1", context)
    assert reason is not None

    context = {"role": "dev", "attempts": 1, "errors": ["fail"]}
    assert engine.evaluate_dynamic_escalation("S1", context) is None


def test_learn_optimal_retry_limit_clamps_by_role():
    engine = AdaptivePolicyEngine()
    engine.story_type_failure_patterns["api"] = ["x"] * 6
    assert engine.learn_optimal_retry_limit("dev", "api") == 2

    engine.story_type_failure_patterns["low"] = []
    assert engine.learn_optimal_retry_limit("dev", "low") == 4

    engine.story_type_failure_patterns["qa"] = ["x"] * 3
    assert engine.learn_optimal_retry_limit("qa", "qa") == 2

    engine.story_type_failure_patterns["arch"] = ["x"] * 10
    assert engine.learn_optimal_retry_limit("architect", "arch") == 1


def test_adjust_parallelism_factor_sets_current():
    engine = AdaptivePolicyEngine()
    assert engine.adjust_parallelism_factor(0.9) == 0.5
    assert engine.parallelism_factors["current"] == 0.5
    assert engine.adjust_parallelism_factor(0.2) == 1.5


def test_should_escalate_immediately_uses_failure_rate():
    engine = AdaptivePolicyEngine()
    engine.story_type_failure_patterns["api"] = ["x"] * 11
    assert engine.should_escalate_immediately("api_story", 2) is True
    assert engine.should_escalate_immediately("api_story", 1) is False


def test_get_optimal_backoff_strategy_adjusts_by_success_rate():
    engine = AdaptivePolicyEngine()
    engine.role_success_rates["dev"] = 0.95
    assert engine.get_optimal_backoff_strategy("dev") == {"type": "exponential", "base": 30}

    engine.role_success_rates["qa"] = 0.8
    assert engine.get_optimal_backoff_strategy("qa")["type"] == "exponential"

    engine.role_success_rates["architect"] = 0.6
    strat = engine.get_optimal_backoff_strategy("architect")
    assert strat["type"] == "linear"
    assert strat["base"] == 45.0


def test_record_execution_result_updates_rates_and_trims_failures():
    engine = AdaptivePolicyEngine()
    engine.record_execution_result("dev", "api", success=True)
    assert engine.role_success_rates["dev"] == pytest.approx(0.82, rel=1e-6)

    engine.record_execution_result("dev", "api", success=False, error_type="fail")
    assert engine.role_success_rates["dev"] == pytest.approx(0.738, rel=1e-6)

    for idx in range(22):
        engine.record_execution_result("dev", "api", success=False, error_type=f"e{idx}")
    assert len(engine.story_type_failure_patterns["api"]) == 20
    assert engine.story_type_failure_patterns["api"][0] == "e2"
    assert engine.story_type_failure_patterns["api"][-1] == "e21"


def test_recommendations_and_reset():
    engine = AdaptivePolicyEngine()
    engine.escalation_thresholds["dev"] = 5
    recs = engine.get_policy_recommendations()
    assert "timestamp" in recs
    assert recs["escalation_thresholds"]["dev"] == 5

    engine.reset_to_base_policies()
    assert engine.escalation_thresholds["dev"] == 2
    assert engine.retry_limits["qa"] == 2


def test_export_policy_snapshot_contains_failures():
    engine = AdaptivePolicyEngine()
    engine.record_execution_result("qa", "ui", success=False, error_type="timeout")
    snapshot = engine.export_policy_snapshot()
    assert snapshot["story_type_failures"]["ui"] == ["timeout"]
