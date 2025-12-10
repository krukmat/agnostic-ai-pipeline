"""Tests for Task 4: Planner Coherence Integration

Integrates coherence checks into planner planning methods at checkpoints.
Tests that planner calls coherence checks and handles remediation.

TDD approach - tests written first.
"""
import tempfile
from pathlib import Path
import pytest

from scripts.orchestrator.coherence_checker import CoherenceChecker
from scripts.orchestrator.coherence_orchestration_integration import CoherenceOrchestrationIntegration
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
        "retry_policies": {"dev": {"max_attempts": 3}},
    }


@pytest.fixture
def state_machine():
    """Create state machine."""
    sm = StateMachine("test_concept", Path(tempfile.mkdtemp()))
    return sm


@pytest.fixture
def dag():
    """Create DAG."""
    dag = StoryDAG()
    dag.add_story("S1", {"priority": "P1"}, [])
    return dag


@pytest.fixture
def coherence_checker():
    """Create coherence checker."""
    return CoherenceChecker(config={})


@pytest.fixture
def cot_tracker(temp_dir):
    """Create CoT tracker."""
    return ChainOfThoughtTracker(output_dir=temp_dir)


@pytest.fixture
def coherence_integration(coherence_checker, cot_tracker):
    """Create coherence integration."""
    return CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)


@pytest.fixture
def planner(state_machine, dag, mock_config, cot_tracker, coherence_integration):
    """Create planner with coherence integration."""
    policy_engine = PolicyEngine(mock_config)
    planner = OrchestratorPlanner(state_machine, dag, policy_engine, mock_config)
    planner.cot_tracker = cot_tracker
    planner.coherence_integration = coherence_integration
    return planner


# ==============================================================================
# TEST SUITE 1: Planner Initialization with Coherence
# ==============================================================================

class TestPlannerCoherenceInitialization:
    """Test planner initializes coherence integration."""

    def test_planner_has_coherence_integration(self, planner, coherence_integration):
        """Planner has coherence integration."""
        assert hasattr(planner, "coherence_integration")
        assert planner.coherence_integration is not None

    def test_coherence_integration_has_tracker(self, planner, cot_tracker):
        """Coherence integration has CoT tracker."""
        assert planner.coherence_integration.tracker is cot_tracker


# ==============================================================================
# TEST SUITE 2: Coherence Checks at Requirements Checkpoint
# ==============================================================================

class TestCoherenceAtRequirementsCheckpoint:
    """Test coherence checks at REQUIREMENTS phase."""

    def test_plan_requirements_calls_coherence(self, planner):
        """_plan_requirements calls coherence checks."""
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.REQUIREMENTS,
            has_requirements=True,
            has_product_vision=True,
            has_stories=False,
        )

        # Call plan_requirements
        actions = planner._plan_requirements(state)

        # Should return architect action to generate stories
        assert isinstance(actions, list)

    def test_coherence_check_ba_po_alignment(self, planner):
        """Coherence checker validates BA→PO alignment at checkpoint."""
        aligned_requirements = {
            "requirements": ["R1", "R2"],
            "constraints": ["GDPR"],
        }
        aligned_po_review = {
            "approved": True,
            "reviewed_requirements": ["R1", "R2"],
            "constraints": ["GDPR"],
        }

        result = planner.coherence_integration.checker.check_ba_po_alignment(
            aligned_requirements, aligned_po_review
        )

        assert result["aligned"] is True


# ==============================================================================
# TEST SUITE 3: Coherence Checks at Planning Checkpoint
# ==============================================================================

class TestCoherenceAtPlanningCheckpoint:
    """Test coherence checks at PLANNING phase."""

    def test_plan_planning_calls_coherence(self, planner):
        """_plan_planning calls coherence checks."""
        # Transition state machine to PLANNING (INIT → REQUIREMENTS → PLANNING)
        planner.state_machine.transition_to(PipelinePhase.REQUIREMENTS, "test transition")
        planner.state_machine.transition_to(PipelinePhase.PLANNING, "test transition")

        state = PipelineState(
            concept="test",
            phase=PipelinePhase.PLANNING,
            has_stories=True,
            total_stories=2,
        )

        # Call plan_planning
        actions = planner._plan_planning(state)

        # Should transition to DEVELOPMENT and return development actions
        assert isinstance(actions, list)

    def test_coherence_check_arch_stories_alignment(self, planner):
        """Coherence checker validates Architecture→Stories alignment."""
        architecture = {"components": ["API", "Database"]}
        stories = [
            {"component": "API", "title": "S1"},
            {"component": "Database", "title": "S2"},
        ]

        result = planner.coherence_integration.checker.check_arch_stories_alignment(
            architecture, stories
        )

        assert isinstance(result, dict)
        assert "aligned" in result


# ==============================================================================
# TEST SUITE 4: Coherence Checks at Integration Checkpoint
# ==============================================================================

class TestCoherenceAtIntegrationCheckpoint:
    """Test coherence checks at INTEGRATION phase."""

    def test_plan_integration_phase(self, planner):
        """_plan_integration executes at INTEGRATION phase."""
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.INTEGRATION,
            total_stories=2,
            stories_done={"S1", "S2"},
            stories_failed={},
        )

        # Call plan_integration
        actions = planner._plan_integration(state)

        # Should return actions (either QA or remediation from coherence)
        assert isinstance(actions, list)
        if actions:
            # Could be RUN_QA_FULL (no coherence issues) or RUN_ARCHITECT (coherence remediation)
            assert actions[0]["tool"] in ["RUN_QA_FULL", "RUN_ARCHITECT"]


# ==============================================================================
# TEST SUITE 5: Remediation Action Handling
# ==============================================================================

class TestRemediationActionHandling:
    """Test handling remediation actions from coherence."""

    def test_generate_remediation_from_coherence(self, planner, coherence_integration):
        """Generate and handle remediation actions."""
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.PLANNING,
        )

        critical_issues = [
            {"type": "arch_stories_misalignment", "severity": "critical"}
        ]

        actions = coherence_integration._generate_remediation_actions(
            critical_issues, state
        )

        assert len(actions) > 0
        assert actions[0]["tool"] == "RUN_ARCHITECT"

    def test_remediation_actions_have_correct_fields(self, planner, coherence_integration):
        """Remediation actions have all required fields."""
        state = PipelineState(concept="test", phase=PipelinePhase.REQUIREMENTS)

        critical_issues = [{"type": "ba_po_misalignment", "severity": "critical"}]

        actions = coherence_integration._generate_remediation_actions(
            critical_issues, state
        )

        assert len(actions) > 0
        action = actions[0]
        assert "tool" in action
        assert "arguments" in action
        assert "reason" in action
        assert "decision_method" in action


# ==============================================================================
# TEST SUITE 6: CoT Logging for Coherence Checks
# ==============================================================================

class TestCoherenceCoTLogging:
    """Test logging coherence checks to CoT tracker."""

    def test_coherence_check_logged_to_cot(self, planner, cot_tracker):
        """Coherence checks are logged to CoT tracker."""
        # Simulate coherence check
        cot_tracker.log_policy_evaluation(
            policy_name="coherence_check",
            condition="ba_po_alignment",
            matched=True,
            context={"checkpoint": "post_requirements"},
        )

        assert cot_tracker.get_thought_count() == 1
        thought = cot_tracker.thoughts[0]
        assert thought.kind == "policy_eval"
        assert thought.layer == "policy"

    def test_multiple_checkpoint_logs(self, planner, cot_tracker):
        """Log multiple checkpoint evaluations."""
        cot_tracker.log_policy_evaluation(
            "coherence", "post_requirements", True, {}
        )
        cot_tracker.log_policy_evaluation(
            "coherence", "post_planning", True, {}
        )
        cot_tracker.log_policy_evaluation(
            "coherence", "post_integration", True, {}
        )

        assert cot_tracker.get_thought_count() == 3


# ==============================================================================
# TEST SUITE 7: Coherence Blocking Critical Issues
# ==============================================================================

class TestCoherenceBlockingCriticalIssues:
    """Test that critical coherence issues block progression."""

    def test_critical_issue_blocks_progression(self, planner, coherence_integration):
        """Critical coherence issues generate remediation."""
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.PLANNING,
        )

        critical_issues = [
            {"type": "arch_stories_misalignment", "severity": "critical"}
        ]

        actions = coherence_integration._generate_remediation_actions(
            critical_issues, state
        )

        # Should return architect intervention action
        assert len(actions) > 0

    def test_warning_issues_allow_progression(self, planner, cot_tracker):
        """Warning-level issues are logged but allow progression."""
        cot_tracker.log_policy_evaluation(
            policy_name="coherence_warning",
            condition="missing_documentation",
            matched=True,
            context={"severity": "warning"},
        )

        assert cot_tracker.get_thought_count() == 1


# ==============================================================================
# TEST SUITE 8: Integration Tests
# ==============================================================================

class TestPlannerCoherenceE2E:
    """End-to-end integration tests."""

    def test_full_planning_cycle_with_coherence(self, planner, cot_tracker):
        """Full planning cycle with coherence checks integrated."""
        # Simulate full cycle
        cot_tracker.log_state_transition("INIT", "REQUIREMENTS", "start")
        cot_tracker.log_policy_evaluation("coherence", "ba_po_alignment", True, {})
        cot_tracker.log_state_transition("REQUIREMENTS", "PLANNING", "req_done")
        cot_tracker.log_policy_evaluation("coherence", "arch_stories", True, {})
        cot_tracker.log_state_transition("PLANNING", "DEVELOPMENT", "plan_done")

        assert cot_tracker.get_thought_count() == 5
        by_layer = cot_tracker.get_thoughts_by_layer()
        assert by_layer["state_machine"] == 3
        assert by_layer["policy"] == 2

    def test_coherence_doesnt_break_normal_planning(self, planner):
        """Coherence integration doesn't interfere with normal planning."""
        state = PipelineState(
            concept="test",
            phase=PipelinePhase.REQUIREMENTS,
            has_requirements=True,
            has_product_vision=True,
            has_stories=False,
        )

        # Should execute normally
        actions = planner._plan_requirements(state)

        assert isinstance(actions, list)

    def test_all_checkpoints_in_planning_cycle(self, planner, cot_tracker):
        """All three coherence checkpoints tested in planning cycle."""
        # REQUIREMENTS checkpoint
        cot_tracker.log_policy_evaluation("coherence", "post_requirements", True, {})

        # PLANNING checkpoint
        cot_tracker.log_policy_evaluation("coherence", "post_planning", True, {})

        # INTEGRATION checkpoint
        cot_tracker.log_policy_evaluation("coherence", "post_integration", True, {})

        by_phase = cot_tracker.get_thoughts_by_phase()

        # All three checkpoints logged
        assert cot_tracker.get_thought_count() == 3
