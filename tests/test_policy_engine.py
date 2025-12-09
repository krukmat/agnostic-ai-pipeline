"""Tests for Policy Engine."""

import pytest
from scripts.orchestrator.policy_engine import PolicyEngine


class TestPolicyEngine:
    """Test PolicyEngine class."""

    def test_retry_allowed(self):
        """Test retry policy evaluation."""
        config = {
            "pipeline": {
                "retry_policies": {
                    "dev": {"max_attempts": 3, "backoff": "exponential"}
                }
            }
        }
        engine = PolicyEngine(config)
        assert engine.should_retry("dev", 0) is True
        assert engine.should_retry("dev", 2) is True
        assert engine.should_retry("dev", 3) is False

    def test_backoff_exponential(self):
        """Test exponential backoff."""
        config = {
            "pipeline": {
                "retry_policies": {
                    "dev": {"backoff": "exponential"}
                }
            }
        }
        engine = PolicyEngine(config)
        assert engine.get_backoff_delay("dev", 1) == 60
        assert engine.get_backoff_delay("dev", 2) == 120
        assert engine.get_backoff_delay("dev", 3) == 240

    def test_escalation_same_error(self):
        """Test escalation on repeated same error."""
        config = {
            "pipeline": {
                "escalation_policies": [
                    {
                        "condition": "dev_attempts >= 3 AND same_error_pattern",
                        "action": "architect_refine",
                        "reason": "Repeated error"
                    }
                ]
            }
        }
        engine = PolicyEngine(config)

        action = engine.evaluate_escalation(
            "S1", 3,
            ["ImportError", "ImportError", "ImportError"],
            {}
        )
        assert action == "architect_refine"

    def test_no_escalation_different_errors(self):
        """Test no escalation with different errors."""
        config = {
            "pipeline": {
                "escalation_policies": [
                    {
                        "condition": "dev_attempts >= 3 AND same_error_pattern",
                        "action": "architect_refine",
                        "reason": "Repeated error"
                    }
                ]
            }
        }
        engine = PolicyEngine(config)

        action = engine.evaluate_escalation(
            "S1", 3,
            ["ImportError", "SyntaxError", "NameError"],
            {}
        )
        assert action is None

    def test_max_parallel_stories(self):
        """Test resource policy for parallelism."""
        config = {
            "pipeline": {
                "resource_policies": {
                    "max_parallel_stories": 5
                }
            }
        }
        engine = PolicyEngine(config)
        assert engine.get_max_parallel_stories() == 5

    def test_timeout(self):
        """Test timeout policy."""
        config = {
            "pipeline": {
                "resource_policies": {
                    "dev_timeout": 300,
                    "qa_timeout": 600
                }
            }
        }
        engine = PolicyEngine(config)
        assert engine.get_timeout("dev") == 300
        assert engine.get_timeout("qa") == 600
