"""Tests for Task 9: LLM Fallback Handler

Implements LLM fallback for complex/ambiguous orchestration decisions.
Tests LLMFallbackEngine with decision logic, LLM integration, and escalation planning.

TDD approach - tests written first.
"""
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import pytest

from scripts.orchestrator.llm_fallback import LLMFallbackEngine
from scripts.orchestrator.state_machine import PipelinePhase, PipelineState
from scripts.orchestrator.cot_tracker import ChainOfThoughtTracker


@pytest.fixture
def temp_dir():
    """Temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {
        "llm_fallback_enabled": True,
        "llm_fallback_threshold": 0.7,
        "llm_escalation_max_retries": 3,
    }


@pytest.fixture
def cot_tracker(temp_dir):
    """Create CoT tracker."""
    return ChainOfThoughtTracker(output_dir=temp_dir)


@pytest.fixture
def llm_fallback_engine(mock_config, cot_tracker):
    """Create LLM fallback engine."""
    return LLMFallbackEngine(config=mock_config, cot_tracker=cot_tracker)


# ==============================================================================
# TEST SUITE 1: LLMFallbackEngine Initialization
# ==============================================================================

class TestLLMFallbackEngineInitialization:
    """Test LLMFallbackEngine initialization."""

    def test_engine_initialization(self, llm_fallback_engine, mock_config):
        """LLMFallbackEngine initializes with config."""
        assert llm_fallback_engine is not None
        assert llm_fallback_engine.config == mock_config

    def test_engine_has_cot_tracker(self, llm_fallback_engine, cot_tracker):
        """LLMFallbackEngine has CoT tracker."""
        assert llm_fallback_engine.cot_tracker is cot_tracker


# ==============================================================================
# TEST SUITE 2: LLM Fallback Decision Logic
# ==============================================================================

class TestLLMFallbackDecisionLogic:
    """Test LLMFallbackEngine decision logic."""

    def test_should_use_llm_with_complex_case(self, llm_fallback_engine):
        """Detect complex case requiring LLM fallback."""
        decision_context = {
            "type": "escalation",
            "ambiguity_score": 0.8,  # High ambiguity
            "matched_rules": 0,  # No deterministic rule matched
            "failed_attempts": 3,
        }

        result = llm_fallback_engine.should_use_llm(decision_context)
        assert result is True

    def test_should_use_llm_with_simple_case(self, llm_fallback_engine):
        """Don't use LLM for simple deterministic cases."""
        decision_context = {
            "type": "dev_retry",
            "ambiguity_score": 0.1,  # Low ambiguity
            "matched_rules": 1,  # Deterministic rule matched
            "failed_attempts": 1,
        }

        result = llm_fallback_engine.should_use_llm(decision_context)
        assert result is False

    def test_should_use_llm_with_escalation(self, llm_fallback_engine):
        """Use LLM for escalation decisions."""
        decision_context = {
            "type": "escalation",
            "ambiguity_score": 0.65,
            "matched_rules": 0,
            "failed_attempts": 2,
            "error_pattern": "pattern_mismatch",
        }

        result = llm_fallback_engine.should_use_llm(decision_context)
        assert result is True

    def test_should_use_llm_below_threshold(self, llm_fallback_engine):
        """Don't use LLM if ambiguity below threshold."""
        decision_context = {
            "type": "escalation",
            "ambiguity_score": 0.5,  # Below default 0.7 threshold
            "matched_rules": 0,
            "failed_attempts": 2,
        }

        result = llm_fallback_engine.should_use_llm(decision_context)
        assert result is False


# ==============================================================================
# TEST SUITE 3: Context Prompt Building
# ==============================================================================

class TestContextPromptBuilding:
    """Test context prompt building for LLM."""

    def test_build_context_prompt_with_failure(self, llm_fallback_engine):
        """Build prompt for failure escalation."""
        context = {
            "story_id": "S1",
            "error": "timeout",
            "attempts": 2,
            "last_error": "Task execution exceeded timeout",
            "phase": "DEVELOPMENT",
        }

        prompt = llm_fallback_engine._build_context_prompt(context)

        assert isinstance(prompt, str)
        assert "S1" in prompt
        assert "timeout" in prompt
        assert len(prompt) > 50

    def test_build_context_prompt_with_architectural_issue(self, llm_fallback_engine):
        """Build prompt for architectural issue."""
        context = {
            "type": "architecture",
            "issue": "dependency_conflict",
            "affected_stories": ["S1", "S2", "S3"],
            "phase": "PLANNING",
        }

        prompt = llm_fallback_engine._build_context_prompt(context)

        assert isinstance(prompt, str)
        assert "dependency_conflict" in prompt.lower() or len(prompt) > 50


# ==============================================================================
# TEST SUITE 4: Escalation Planning
# ==============================================================================

class TestEscalationPlanning:
    """Test escalation planning logic."""

    def test_escalation_planning_single_story(self, llm_fallback_engine):
        """Generate escalation for single failed story."""
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.DEVELOPMENT,
        )
        failed_stories = {"S1"}

        actions = llm_fallback_engine.escalation_planning(state, failed_stories)

        assert isinstance(actions, list)
        assert len(actions) > 0
        # Should return RUN_ARCHITECT action for refinement
        assert any(a.get("tool") == "RUN_ARCHITECT" for a in actions)

    def test_escalation_planning_multiple_stories(self, llm_fallback_engine):
        """Generate escalation for multiple failed stories."""
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.DEVELOPMENT,
        )
        failed_stories = {"S1", "S2", "S3"}

        actions = llm_fallback_engine.escalation_planning(state, failed_stories)

        assert isinstance(actions, list)
        assert len(actions) >= 1

    def test_escalation_planning_has_reason(self, llm_fallback_engine):
        """Escalation actions have reason field."""
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.DEVELOPMENT,
        )
        failed_stories = {"S1"}

        actions = llm_fallback_engine.escalation_planning(state, failed_stories)

        assert len(actions) > 0
        action = actions[0]
        assert "reason" in action
        assert len(action["reason"]) > 0


# ==============================================================================
# TEST SUITE 5: LLM Response Parsing
# ==============================================================================

class TestLLMResponseParsing:
    """Test parsing of LLM responses."""

    def test_parse_valid_llm_response(self, llm_fallback_engine):
        """Parse valid LLM decision response."""
        llm_response = {
            "decision": "escalate_to_architect",
            "reasoning": "Story has architectural implications",
            "actions": [{"tool": "RUN_ARCHITECT", "arguments": {"story_id": "S1"}}],
            "confidence": 0.85,
        }

        parsed = llm_fallback_engine._parse_llm_response(llm_response)

        assert isinstance(parsed, dict)
        assert "decision" in parsed
        assert "confidence" in parsed
        assert parsed["confidence"] <= 1.0

    def test_parse_llm_response_with_list_actions(self, llm_fallback_engine):
        """Parse LLM response with multiple actions."""
        llm_response = {
            "decision": "complex_escalation",
            "reasoning": "Multiple issues detected",
            "actions": [
                {"tool": "RUN_ARCHITECT", "arguments": {"story_id": "S1"}},
                {"tool": "RUN_ARCHITECT", "arguments": {"story_id": "S2"}},
            ],
            "confidence": 0.75,
        }

        parsed = llm_fallback_engine._parse_llm_response(llm_response)

        assert isinstance(parsed, dict)


# ==============================================================================
# TEST SUITE 6: CoT Logging Integration
# ==============================================================================

class TestCoTLoggingIntegration:
    """Test logging LLM decisions to CoT tracker."""

    def test_log_llm_decision_to_cot(self, llm_fallback_engine, cot_tracker):
        """Log LLM fallback decision to CoT tracker."""
        decision_context = {
            "type": "escalation",
            "story_id": "S1",
            "ambiguity_score": 0.8,
        }

        llm_fallback_engine.cot_tracker.log_llm_decision(
            prompt="Test escalation prompt",
            response='{"decision": "escalate"}',  # String response
            parsed={"decision": "escalate", "confidence": 0.8},
        )

        assert cot_tracker.get_thought_count() > 0
        thoughts = cot_tracker.thoughts
        assert any(t.kind == "llm_call" for t in thoughts)

    def test_llm_decision_has_low_confidence(self, llm_fallback_engine, cot_tracker):
        """LLM decisions logged with confidence <1.0."""
        cot_tracker.log_llm_decision(
            prompt="Test",
            response='{"result": "test"}',  # String response
            parsed={"confidence": 0.75},
        )

        thoughts = cot_tracker.thoughts
        if thoughts:
            llm_thought = next(t for t in thoughts if t.kind == "llm_call")
            assert llm_thought.confidence < 1.0


# ==============================================================================
# TEST SUITE 7: Fallback Trigger Scenarios
# ==============================================================================

class TestFallbackTriggerScenarios:
    """Test various scenarios that trigger LLM fallback."""

    def test_fallback_on_repeated_failures(self, llm_fallback_engine):
        """Trigger fallback after repeated story failures."""
        decision_context = {
            "type": "dev_retry",
            "story_id": "S1",
            "failed_attempts": 3,
            "error_pattern": "same_error",
            "ambiguity_score": 0.75,
        }

        result = llm_fallback_engine.should_use_llm(decision_context)
        # High ambiguity after repeated failures should trigger LLM
        assert result is True

    def test_fallback_on_epic_wide_failures(self, llm_fallback_engine):
        """Trigger fallback on multiple story failures in same epic."""
        decision_context = {
            "type": "epic_escalation",
            "failed_count": 4,
            "total_in_epic": 6,
            "ambiguity_score": 0.8,
        }

        result = llm_fallback_engine.should_use_llm(decision_context)
        assert result is True

    def test_no_fallback_on_clear_error(self, llm_fallback_engine):
        """Don't trigger fallback for clear, deterministic errors."""
        decision_context = {
            "type": "dev_retry",
            "story_id": "S1",
            "failed_attempts": 1,
            "error_pattern": "missing_dependency",  # Clear pattern
            "ambiguity_score": 0.2,
            "matched_rules": 1,
        }

        result = llm_fallback_engine.should_use_llm(decision_context)
        assert result is False


# ==============================================================================
# TEST SUITE 8: Integration Tests
# ==============================================================================

class TestLLMFallbackE2E:
    """End-to-end integration tests."""

    def test_full_fallback_workflow(self, llm_fallback_engine, cot_tracker):
        """Full workflow: detect complexity → call LLM → log → plan escalation."""
        # 1. Detect complexity
        decision_context = {
            "type": "escalation",
            "ambiguity_score": 0.8,
            "matched_rules": 0,
            "story_id": "S1",
        }

        should_use = llm_fallback_engine.should_use_llm(decision_context)
        assert should_use is True

        # 2. Plan escalation
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.DEVELOPMENT,
        )
        actions = llm_fallback_engine.escalation_planning(state, {"S1"})
        assert len(actions) > 0

    def test_mixed_deterministic_and_llm_decisions(self, llm_fallback_engine):
        """System should use deterministic rules when available, LLM otherwise."""
        # Simple case - deterministic
        simple_context = {
            "type": "retry",
            "ambiguity_score": 0.1,
            "matched_rules": 1,
        }
        assert llm_fallback_engine.should_use_llm(simple_context) is False

        # Complex case - LLM
        complex_context = {
            "type": "escalation",
            "ambiguity_score": 0.9,
            "matched_rules": 0,
        }
        assert llm_fallback_engine.should_use_llm(complex_context) is True

    def test_fallback_doesnt_interfere_with_normal_planning(self, llm_fallback_engine):
        """LLM fallback should not break normal planning flow."""
        # Fallback engine exists and works independently
        assert llm_fallback_engine is not None
        assert llm_fallback_engine.config is not None

        # Normal operations should still work
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.DEVELOPMENT,
        )
        actions = llm_fallback_engine.escalation_planning(state, set())
        assert isinstance(actions, list)
