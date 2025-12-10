"""Tests for Task 2: Planner CoT Integration

Integrates ChainOfThoughtTracker into OrchestratorPlanner.
Tests that planner logs all decisions to CoT tracker.

TDD approach - tests written first.
"""
import tempfile
from pathlib import Path
import pytest
from unittest.mock import Mock

from scripts.orchestrator.cot_tracker import ChainOfThoughtTracker
from scripts.orchestrator.state_machine import PipelinePhase, PipelineState, StateMachine
from scripts.orchestrator.story_dag import StoryDAG
from scripts.orchestrator.policy_engine import PolicyEngine
from scripts.orchestrator.planner import OrchestratorPlanner


@pytest.fixture
def temp_dir():
    """Temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {
        "max_parallel_stories": 3,
        "retry_policies": {
            "dev": {"max_attempts": 3},
            "qa": {"max_attempts": 2},
        },
    }


@pytest.fixture
def state_machine():
    """Create state machine for tests."""
    sm = StateMachine("test_concept", Path(tempfile.mkdtemp()))
    return sm


@pytest.fixture
def dag():
    """Create story DAG for tests."""
    dag = StoryDAG()
    dag.add_story("S1", {"priority": "P1"}, [])
    dag.add_story("S2", {"priority": "P1"}, ["S1"])
    return dag


@pytest.fixture
def policy_engine(mock_config):
    """Create policy engine."""
    return PolicyEngine(mock_config)


@pytest.fixture
def cot_tracker(temp_dir):
    """Create CoT tracker."""
    return ChainOfThoughtTracker(output_dir=temp_dir)


@pytest.fixture
def planner(state_machine, dag, policy_engine, mock_config, cot_tracker):
    """Create planner with CoT tracker."""
    planner = OrchestratorPlanner(state_machine, dag, policy_engine, mock_config)
    planner.cot_tracker = cot_tracker
    return planner


# ==============================================================================
# TEST SUITE 1: Tracker Initialization
# ==============================================================================

class TestPlannerTrackerInitialization:
    """Test planner initializes CoT tracker correctly."""

    def test_planner_initializes_cot_tracker(self, planner, cot_tracker):
        """Planner has CoT tracker initialized."""
        assert hasattr(planner, "cot_tracker")
        assert planner.cot_tracker is not None
        assert isinstance(planner.cot_tracker, ChainOfThoughtTracker)

    def test_tracker_output_dir_created(self, planner, temp_dir):
        """Tracker output directory exists."""
        assert planner.cot_tracker.output_dir.exists()


# ==============================================================================
# TEST SUITE 2: State Transition Logging
# ==============================================================================

class TestStateTransitionLogging:
    """Test CoT logging for state transitions."""

    def test_log_init_to_requirements_transition(self, planner, state_machine):
        """Log state transition in _plan_init."""
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.INIT,
            has_requirements=True,
            total_stories=2,
        )

        # Simulate transition logging
        planner.cot_tracker.log_state_transition(
            from_phase="INIT",
            to_phase="REQUIREMENTS",
            reason="requirements_ready"
        )

        assert planner.cot_tracker.get_thought_count() == 1
        thought = planner.cot_tracker.thoughts[0]
        assert thought.kind == "transition"
        assert thought.layer == "state_machine"

    def test_log_requirements_to_planning_transition(self, planner):
        """Log transition from REQUIREMENTS to PLANNING."""
        planner.cot_tracker.log_state_transition(
            from_phase="REQUIREMENTS",
            to_phase="PLANNING",
            reason="stories_generated"
        )

        assert planner.cot_tracker.get_thought_count() == 1
        thought = planner.cot_tracker.thoughts[0]
        assert thought.output == "PLANNING"


# ==============================================================================
# TEST SUITE 3: DAG Decision Logging
# ==============================================================================

class TestDAGDecisionLogging:
    """Test CoT logging for DAG batch decisions."""

    def test_log_dag_batch_selection(self, planner):
        """Log DAG batch selection decision."""
        ready_stories = ["S1", "S2", "S3"]
        selected_batch = ["S1", "S2"]

        planner.cot_tracker.log_dag_decision(
            ready_stories=ready_stories,
            batch=selected_batch,
            reason="dependency_order"
        )

        assert planner.cot_tracker.get_thought_count() == 1
        thought = planner.cot_tracker.thoughts[0]
        assert thought.layer == "dag"
        assert thought.output == selected_batch

    def test_log_multiple_dag_decisions(self, planner):
        """Log multiple DAG decisions over time."""
        # First batch
        planner.cot_tracker.log_dag_decision(
            ["S1", "S2"], ["S1"], "first_batch"
        )
        # Second batch
        planner.cot_tracker.log_dag_decision(
            ["S2", "S3"], ["S2"], "second_batch"
        )

        assert planner.cot_tracker.get_thought_count() == 2
        by_layer = planner.cot_tracker.get_thoughts_by_layer()
        assert by_layer["dag"] == 2


# ==============================================================================
# TEST SUITE 4: Policy Evaluation Logging
# ==============================================================================

class TestPolicyEvaluationLogging:
    """Test CoT logging for policy engine decisions."""

    def test_log_policy_evaluation_matched(self, planner):
        """Log policy evaluation when condition matches."""
        planner.cot_tracker.log_policy_evaluation(
            policy_name="max_retries_policy",
            condition="attempts >= 3",
            matched=True,
            context={"story_id": "S1", "attempts": 3}
        )

        assert planner.cot_tracker.get_thought_count() == 1
        thought = planner.cot_tracker.thoughts[0]
        assert thought.layer == "policy"
        assert thought.output is True

    def test_log_policy_evaluation_not_matched(self, planner):
        """Log policy evaluation when condition doesn't match."""
        planner.cot_tracker.log_policy_evaluation(
            policy_name="max_retries_policy",
            condition="attempts >= 3",
            matched=False,
            context={"story_id": "S1", "attempts": 1}
        )

        assert planner.cot_tracker.get_thought_count() == 1
        thought = planner.cot_tracker.thoughts[0]
        assert thought.output is False


# ==============================================================================
# TEST SUITE 5: Escalation Decision Logging
# ==============================================================================

class TestEscalationDecisionLogging:
    """Test CoT logging for escalation decisions."""

    def test_log_escalation_to_architect(self, planner):
        """Log escalation decision."""
        planner.cot_tracker.log_escalation_decision(
            story_id="S1",
            action="escalate_to_architect",
            reason="repeated_failures"
        )

        assert planner.cot_tracker.get_thought_count() == 1
        thought = planner.cot_tracker.thoughts[0]
        assert thought.kind == "escalation"
        assert thought.output == "escalate_to_architect"
        assert thought.details["story_id"] == "S1"

    def test_log_multiple_escalations(self, planner):
        """Log multiple escalation decisions."""
        planner.cot_tracker.log_escalation_decision("S1", "escalate_to_architect", "failure")
        planner.cot_tracker.log_escalation_decision("S2", "escalate_to_architect", "timeout")

        assert planner.cot_tracker.get_thought_count() == 2
        thoughts = planner.cot_tracker.thoughts
        assert thoughts[0].details["story_id"] == "S1"
        assert thoughts[1].details["story_id"] == "S2"


# ==============================================================================
# TEST SUITE 6: Planner Decision Logging
# ==============================================================================

class TestPlannerDecisionLogging:
    """Test CoT logging for planner decisions."""

    def test_log_dev_action_selection(self, planner):
        """Log planner decision for dev action."""
        planner.cot_tracker.log_planner_decision(
            decision_type="story_execution",
            alternatives=["retry", "escalate", "fail"],
            chosen="retry",
            confidence=1.0
        )

        assert planner.cot_tracker.get_thought_count() == 1
        thought = planner.cot_tracker.thoughts[0]
        assert thought.layer == "planner"
        assert thought.output == "retry"
        assert len(thought.inputs["alternatives"]) == 3

    def test_log_phase_transition_decision(self, planner):
        """Log phase transition decision."""
        planner.cot_tracker.log_planner_decision(
            decision_type="phase_transition",
            alternatives=["PLANNING", "DEVELOPMENT", "INTEGRATION"],
            chosen="DEVELOPMENT",
            confidence=1.0
        )

        thought = planner.cot_tracker.thoughts[0]
        assert thought.message
        assert "DEVELOPMENT" in str(thought.output)


# ==============================================================================
# TEST SUITE 7: Export CoT Reasoning
# ==============================================================================

class TestExportCOTReasoning:
    """Test export_cot_reasoning() method."""

    def test_export_cot_reasoning_returns_dict(self, planner, temp_dir):
        """export_cot_reasoning() returns dict with exports."""
        # Log some decisions
        planner.cot_tracker.log_state_transition("INIT", "REQUIREMENTS", "test")
        planner.cot_tracker.log_dag_decision(["S1"], ["S1"], "test")
        planner.cot_tracker.log_policy_evaluation("policy", "cond", True, {})

        # Export
        result = planner.export_cot_reasoning(output_dir=temp_dir)

        assert isinstance(result, dict)
        assert "thought_count" in result
        assert "jsonl_path" in result
        assert "markdown_path" in result
        assert result["thought_count"] == 3

    def test_export_files_created(self, planner, temp_dir):
        """export_cot_reasoning() creates JSONL and Markdown files."""
        planner.cot_tracker.log_state_transition("A", "B", "test")

        result = planner.export_cot_reasoning(output_dir=temp_dir)

        jsonl_path = result["jsonl_path"]
        md_path = result["markdown_path"]

        assert Path(jsonl_path).exists()
        assert Path(md_path).exists()

    def test_export_empty_tracker(self, planner, temp_dir):
        """export_cot_reasoning() works with empty tracker."""
        result = planner.export_cot_reasoning(output_dir=temp_dir)

        assert result["thought_count"] == 0


# ==============================================================================
# TEST SUITE 8: Integration Tests
# ==============================================================================

class TestPlannerCOTIntegration:
    """Integration tests for planner + CoT tracker."""

    def test_full_planning_cycle_with_cot(self, planner, state_machine):
        """Full planning cycle logs to CoT tracker."""
        # Simulate planning cycle
        planner.cot_tracker.log_state_transition("INIT", "REQUIREMENTS", "start")
        planner.cot_tracker.log_dag_decision(["S1", "S2"], ["S1"], "batch")
        planner.cot_tracker.log_policy_evaluation("retry_policy", "attempts < 3", True, {})
        planner.cot_tracker.log_planner_decision("exec", ["run", "skip"], "run", 1.0)

        assert planner.cot_tracker.get_thought_count() == 4
        by_layer = planner.cot_tracker.get_thoughts_by_layer()
        assert by_layer["state_machine"] == 1
        assert by_layer["dag"] == 1
        assert by_layer["policy"] == 1
        assert by_layer["planner"] == 1

    def test_coherence_checks_dont_interfere_with_cot(self, planner):
        """Coherence checks and CoT tracking coexist."""
        # Log a decision
        planner.cot_tracker.log_state_transition("A", "B", "test")

        # Coherence checks (don't add to CoT)
        # This should not affect CoT tracker
        initial_count = planner.cot_tracker.get_thought_count()

        # Log another decision
        planner.cot_tracker.log_policy_evaluation("p", "c", True, {})

        assert planner.cot_tracker.get_thought_count() == initial_count + 1

    def test_statistics_across_planning_phases(self, planner):
        """Statistics work across multiple phases."""
        # Simulate multiple phases - log_state_transition uses to_phase as phase
        planner.cot_tracker.log_state_transition("INIT", "REQUIREMENTS", "start")
        planner.cot_tracker.log_state_transition("REQUIREMENTS", "PLANNING", "req_done")
        planner.cot_tracker.log_state_transition("PLANNING", "DEVELOPMENT", "planning_done")

        by_phase = planner.cot_tracker.get_thoughts_by_phase()
        assert len(by_phase) == 3
        assert "REQUIREMENTS" in by_phase
        assert "PLANNING" in by_phase
        assert "DEVELOPMENT" in by_phase
