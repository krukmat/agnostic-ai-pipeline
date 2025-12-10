"""
End-to-end tests for Orchestrator V2 Phase 3.

Comprehensive test coverage for all Phase 3 modules:
- Performance Predictor
- Domain Rules Engine
- Analytics Engine
- Parallelism Scheduler
- Cache Manager
- Feedback Loop
- Advanced CoT
- Adaptive Policy Engine
"""

import pytest
import tempfile
from pathlib import Path
import json
from unittest.mock import Mock, patch

# Phase 3 imports
from scripts.orchestrator.performance_predictor import PerformancePredictor
from scripts.orchestrator.domain_rules import DomainRulesEngine
from scripts.orchestrator.analytics_engine import AnalyticsEngine
from scripts.orchestrator.parallelism_scheduler import ParallelismScheduler
from scripts.orchestrator.cache_manager import CacheManager
from scripts.orchestrator.feedback_loop import FeedbackCollector
from scripts.orchestrator.advanced_cot import AdvancedChainOfThought
from scripts.orchestrator.adaptive_policy_engine import AdaptivePolicyEngine


class TestPerformancePredictor:
    """Tests for Performance Predictor module."""

    @pytest.fixture
    def predictor(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield PerformancePredictor(history_dir=temp_dir)

    def test_predict_duration_default(self, predictor):
        """Test default duration prediction."""
        duration = predictor.predict_duration("S1")
        assert duration == 60.0  # Default fallback

    def test_predict_duration_with_metadata(self, predictor):
        """Test duration prediction with complexity metadata."""
        metadata = {
            "lines_of_code": 500,
            "dependencies": ["api", "db"],
            "test_count": 10,
        }
        duration = predictor.predict_duration("S2", metadata)
        assert duration > 30.0  # Should be > base

    def test_train_on_execution(self, predictor):
        """Test online learning from actual execution."""
        predictor.train_on_execution("S3", 45.0)
        predictor.train_on_execution("S3", 50.0)
        predictor.train_on_execution("S3", 48.0)

        duration = predictor.predict_duration("S3")
        assert 47.0 < duration < 49.0  # Average of trainings

    def test_confidence_score(self, predictor):
        """Test confidence scoring based on data points."""
        # No data: very low confidence
        conf1 = predictor.get_confidence_score("S1")
        assert conf1 < 0.2

        # Add samples and check confidence increases
        for i in range(5):
            predictor.train_on_execution("S2", 60.0)
        conf2 = predictor.get_confidence_score("S2")
        assert 0.2 < conf2 < 0.4

    def test_predict_batch_duration(self, predictor):
        """Test batch duration prediction."""
        stories = ["S1", "S2", "S3"]
        total = predictor.predict_batch_duration(stories)
        assert total > 0
        assert total >= 60.0  # At least 3 stories * 20s base

    def test_resource_usage_prediction(self, predictor):
        """Test resource requirement prediction."""
        resources = predictor.predict_resource_usage("S1")
        assert "memory_mb" in resources
        assert "cpu_percent" in resources
        assert "parallel_safe" in resources
        assert resources["memory_mb"] > 0
        assert resources["cpu_percent"] > 0


class TestDomainRulesEngine:
    """Tests for Domain Rules Engine."""

    @pytest.fixture
    def rules_engine(self):
        return DomainRulesEngine(domain_name="backend")

    def test_register_custom_check(self, rules_engine):
        """Test registering a custom rule."""
        def custom_check(output):
            return {"passed": True, "message": "Custom check passed"}

        rules_engine.register_check(
            name="custom_test",
            description="Test custom rule",
            severity="high",
            check_function=custom_check,
            applies_to=["RUN_DEV"],
        )

        assert "custom_test" in rules_engine.rules

    def test_validate_api_endpoints(self, rules_engine):
        """Test API endpoint validation."""
        output = {
            "endpoints": [
                "/api/v1/users",
                "/api/v2/products",
                "invalid/endpoint",
            ]
        }
        result = rules_engine.validate_output("RUN_ARCHITECT", output)
        assert not result["passed"]
        assert result["severity"] == "high"

    def test_validate_migrations(self, rules_engine):
        """Test database migration validation."""
        output = {
            "migrations": [
                {"name": "001_init", "up": "CREATE TABLE...", "down": "DROP TABLE..."},
                {"name": "002_alter", "up": "ALTER TABLE..."},  # Missing down
            ]
        }
        result = rules_engine.validate_output("RUN_DEV", output)
        assert not result["passed"]

    def test_get_applicable_rules(self, rules_engine):
        """Test context-aware rule selection."""
        context = {"domain": "backend", "tool": "RUN_DEV"}
        rules = rules_engine.get_applicable_rules(context)
        assert len(rules) > 0
        assert all("RUN_DEV" in r.applies_to for r in rules)

    def test_rules_summary(self, rules_engine):
        """Test rules summary generation."""
        summary = rules_engine.get_rules_summary()
        assert summary["domain"] == "backend"
        assert summary["total_rules"] > 0
        assert "severity_breakdown" in summary


class TestAnalyticsEngine:
    """Tests for Analytics Engine."""

    @pytest.fixture
    def analytics(self):
        temp_dir = Path(tempfile.mkdtemp())
        return AnalyticsEngine(history_dir=temp_dir)

    def test_story_patterns(self, analytics):
        """Test story pattern analysis."""
        patterns = analytics.get_story_patterns()
        assert isinstance(patterns, dict)
        # Empty history should return empty patterns
        assert len(patterns) == 0

    def test_bottleneck_analysis(self, analytics):
        """Test bottleneck detection."""
        bottlenecks = analytics.get_bottleneck_analysis()
        assert isinstance(bottlenecks, list)

    def test_role_performance(self, analytics):
        """Test role performance metrics."""
        perf = analytics.get_role_performance("dev")
        assert "success_rate" in perf
        assert "avg_duration" in perf
        assert "count" in perf

    def test_execution_timeline(self, analytics):
        """Test execution timeline generation."""
        timeline = analytics.get_execution_timeline()
        assert isinstance(timeline, list)

    def test_success_probability(self, analytics):
        """Test success probability prediction."""
        metadata = {
            "story_type": "story",
            "complexity": 5,
            "dependencies": [],
        }
        prob = analytics.predict_success_probability(metadata)
        assert 0.1 <= prob <= 1.0

    def test_trend_analysis(self, analytics):
        """Test trend analysis."""
        trends = analytics.get_trend_analysis()
        assert "overall_trend" in trends
        assert trends["overall_trend"] in ["improving", "degrading", "stable", "insufficient_data"]


class TestParallelismScheduler:
    """Tests for Parallelism Scheduler."""

    @pytest.fixture
    def scheduler(self):
        return ParallelismScheduler(min_parallelism=1, max_parallelism=10)

    @patch('psutil.cpu_percent', return_value=50.0)
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_safe_parallelism(self, mock_disk, mock_mem, mock_cpu, scheduler):
        """Test safe parallelism calculation."""
        mock_mem.return_value = Mock(percent=50.0)
        mock_disk.return_value = Mock(percent=50.0)

        parallelism = scheduler.get_safe_parallelism()
        assert 1 <= parallelism <= 10

    @patch('psutil.cpu_percent', return_value=90.0)
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_should_throttle(self, mock_disk, mock_mem, mock_cpu, scheduler):
        """Test throttling under stress."""
        mock_mem.return_value = Mock(percent=85.0)
        mock_disk.return_value = Mock(percent=75.0)

        should_throttle = scheduler.should_throttle()
        assert should_throttle is True

    def test_record_execution(self, scheduler):
        """Test execution result recording."""
        scheduler.record_execution(success=True)
        scheduler.record_execution(success=False)

        assert scheduler.recent_successes == 1
        assert scheduler.recent_errors == 1

    def test_adaptive_parallelism_step(self, scheduler):
        """Test adaptive parallelism adjustment."""
        scheduler.recent_successes = 9
        scheduler.recent_errors = 1  # 10% error rate

        new_parallelism = scheduler.adaptive_parallelism_step()
        assert 1 <= new_parallelism <= 10


class TestCacheManager:
    """Tests for Cache Manager."""

    @pytest.fixture
    def cache(self):
        temp_dir = Path(tempfile.mkdtemp())
        return CacheManager(cache_dir=temp_dir)

    def test_cache_set_and_get(self, cache):
        """Test basic cache operations."""
        cache.set("test_key", {"data": "value"})
        result = cache.get("test_key")
        assert result == {"data": "value"}

    def test_cache_miss(self, cache):
        """Test cache miss."""
        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_invalidation(self, cache):
        """Test cache invalidation."""
        cache.set("predict:S1", {"duration": 60})
        cache.set("predict:S2", {"duration": 90})

        count = cache.invalidate("predict:*")
        assert count >= 2

    def test_cache_stats(self, cache):
        """Test cache statistics."""
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["hits"] >= 2
        assert stats["misses"] >= 1
        assert stats["hit_rate"] > 0


class TestFeedbackLoop:
    """Tests for Feedback Loop."""

    @pytest.fixture
    def feedback(self):
        temp_dir = Path(tempfile.mkdtemp())
        return FeedbackCollector(feedback_dir=temp_dir)

    def test_record_agent_feedback(self, feedback):
        """Test agent feedback recording."""
        feedback.record_agent_feedback(
            role="dev",
            story_id="S1",
            feedback={"helpful": True, "suggestions": ["Add tests"]}
        )

        summary = feedback.get_feedback_summary()
        assert summary["agent_feedback_count"] > 0

    def test_record_user_feedback(self, feedback):
        """Test user feedback recording."""
        feedback.record_user_feedback(
            story_id="S1",
            rating=4,
            comment="Good implementation"
        )

        summary = feedback.get_feedback_summary()
        assert summary["user_feedback_count"] > 0

    def test_analyze_feedback_patterns(self, feedback):
        """Test feedback pattern analysis."""
        feedback.record_agent_feedback("dev", "S1", {"errors": ["TypeError"]})
        feedback.record_agent_feedback("dev", "S2", {"errors": ["TypeError"]})

        patterns = feedback.analyze_feedback_patterns()
        assert "common_errors" in patterns
        assert "TypeError" in patterns["common_errors"]

    def test_suggest_improvements(self, feedback):
        """Test improvement suggestions."""
        feedback.record_agent_feedback("dev", "S1", {"errors": ["Error A"]})
        suggestions = feedback.suggest_improvements()
        assert len(suggestions) > 0


class TestAdvancedChainOfThought:
    """Tests for Advanced CoT Logging."""

    @pytest.fixture
    def cot(self):
        temp_dir = Path(tempfile.mkdtemp())
        return AdvancedChainOfThought(output_dir=temp_dir)

    def test_start_and_end_chain(self, cot):
        """Test chain lifecycle."""
        cot.start_chain(step=1, phase="DEVELOPMENT")
        cot.log_decision("Select S1", "priority_rule", 0.95)
        chain = cot.end_chain()

        assert chain["step"] == 1
        assert chain["phase"] == "DEVELOPMENT"
        assert len(chain["reasoning"]) > 0

    def test_sub_chains(self, cot):
        """Test nested sub-chains."""
        cot.start_chain(1, "DEVELOPMENT")
        sub_id = cot.start_sub_chain("ready_check")
        cot.log_decision("Check ready", "deps", 0.9, sub_chain_id=sub_id)
        chain = cot.end_chain()

        assert sub_id in chain["sub_chains"]

    def test_alternative_analysis(self, cot):
        """Test alternative option analysis."""
        cot.start_chain(1, "DEVELOPMENT")
        alts = {
            "S1": {"score": 0.8, "reason": "Ready"},
            "S2": {"score": 0.6, "reason": "Blocked"},
        }
        cot.log_alternative_analysis(alts, "S1")
        chain = cot.end_chain()

        assert len(chain["reasoning"]) > 0

    def test_constraint_checking(self, cot):
        """Test constraint evaluation."""
        cot.start_chain(1, "DEVELOPMENT")
        cot.log_constraint_check("max_retries", True, "Within limit")
        chain = cot.end_chain()

        assert len(chain["constraints"]) > 0

    def test_decision_tree_export(self, cot):
        """Test decision tree export."""
        cot.start_chain(1, "DEVELOPMENT")
        cot.log_decision("Choose S1", "rule", 0.9)
        cot.end_chain()

        tree = cot.export_decision_tree()
        assert "total_chains" in tree
        assert tree["total_chains"] > 0


class TestAdaptivePolicyEngine:
    """Tests for Adaptive Policy Engine."""

    @pytest.fixture
    def policy(self):
        return AdaptivePolicyEngine()

    def test_dynamic_escalation(self, policy):
        """Test dynamic escalation thresholds."""
        context = {"role": "dev", "attempts": 3, "errors": []}
        result = policy.evaluate_dynamic_escalation("S1", context)
        # May or may not escalate depending on success rate
        assert result is None or isinstance(result, str)

    def test_learn_retry_limit(self, policy):
        """Test retry limit learning."""
        retry_limit = policy.learn_optimal_retry_limit("dev", "story_type")
        assert 2 <= retry_limit <= 4

    def test_parallelism_adjustment(self, policy):
        """Test parallelism factor adjustment."""
        factor = policy.adjust_parallelism_factor(0.2)  # Low stress
        assert factor > 1.0

        factor = policy.adjust_parallelism_factor(0.9)  # High stress
        assert factor < 1.0

    def test_record_execution_result(self, policy):
        """Test execution recording."""
        policy.record_execution_result("dev", "story", True)

        # Success rate should increase
        initial_rate = policy.role_success_rates.get("dev", 0.5)
        assert initial_rate > 0.5

    def test_policy_recommendations(self, policy):
        """Test policy export."""
        recs = policy.get_policy_recommendations()
        assert "role_success_rates" in recs
        assert "escalation_thresholds" in recs
        assert "retry_limits" in recs


class TestPhase3Integration:
    """Integration tests for Phase 3 components."""

    def test_all_components_importable(self):
        """Test all Phase 3 components are importable."""
        from scripts.orchestrator import (
            PerformancePredictor,
            DomainRulesEngine,
            AnalyticsEngine,
            ParallelismScheduler,
            CacheManager,
            FeedbackCollector,
            AdvancedChainOfThought,
            AdaptivePolicyEngine,
        )

        assert PerformancePredictor is not None
        assert DomainRulesEngine is not None
        assert AnalyticsEngine is not None
        assert ParallelismScheduler is not None
        assert CacheManager is not None
        assert FeedbackCollector is not None
        assert AdvancedChainOfThought is not None
        assert AdaptivePolicyEngine is not None

    def test_phase2_backward_compatibility(self):
        """Test Phase 2 components still work."""
        from scripts.orchestrator import (
            CoherenceChecker,
            ChainOfThoughtLogger,
            ExecutionOptimizer,
        )

        assert CoherenceChecker is not None
        assert ChainOfThoughtLogger is not None
        assert ExecutionOptimizer is not None

    def test_phase1_backward_compatibility(self):
        """Test Phase 1 components still work."""
        from scripts.orchestrator import (
            StateMachine,
            StoryDAG,
            PolicyEngine,
            OrchestratorPlanner,
        )

        assert StateMachine is not None
        assert StoryDAG is not None
        assert PolicyEngine is not None
        assert OrchestratorPlanner is not None
