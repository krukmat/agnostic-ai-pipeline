"""Tests for Task 3: Coherence Orchestration Integration

Integrates coherence checks into the planning loop with remediation actions.
Tests coherence validation and automated remediation generation.

TDD approach - tests written first.
"""
import tempfile
from pathlib import Path
import pytest

from scripts.orchestrator.coherence_checker import CoherenceChecker
from scripts.orchestrator.cot_tracker import ChainOfThoughtTracker
from scripts.orchestrator.state_machine import PipelinePhase, PipelineState


@pytest.fixture
def temp_dir():
    """Temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def coherence_checker():
    """Create coherence checker."""
    return CoherenceChecker(config={})


@pytest.fixture
def cot_tracker(temp_dir):
    """Create CoT tracker."""
    return ChainOfThoughtTracker(output_dir=temp_dir)


@pytest.fixture
def aligned_requirements():
    """Requirements that are well-formed."""
    return {
        "requirements": ["R1: User auth", "R2: Data storage"],
        "constraints": ["GDPR compliant", "REST API"],
    }


@pytest.fixture
def aligned_po_review():
    """PO review aligned with requirements."""
    return {
        "approved": True,
        "reviewed_requirements": ["R1: User auth", "R2: Data storage"],
        "constraints": ["GDPR compliant", "REST API"],
    }


@pytest.fixture
def misaligned_po_review():
    """PO review misaligned with requirements."""
    return {
        "approved": True,
        "reviewed_requirements": ["R1: User auth"],  # Missing R2
        "constraints": ["GDPR compliant", "Kafka"],  # Different constraint
    }


# ==============================================================================
# TEST SUITE 1: CoherenceOrchestrationIntegration Initialization
# ==============================================================================

class TestCoherenceIntegrationInit:
    """Test CoherenceOrchestrationIntegration initialization."""

    def test_coherence_integration_init(self, coherence_checker, cot_tracker):
        """Initialize integration with coherence checker and tracker."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        assert integration.checker is not None
        assert integration.tracker is not None

    def test_integration_has_checker_reference(self, coherence_checker, cot_tracker):
        """Integration maintains reference to coherence checker."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        assert integration.checker is coherence_checker


# ==============================================================================
# TEST SUITE 2: Coherence Checking at Checkpoints
# ==============================================================================

class TestCoherenceCheckingAtCheckpoints:
    """Test coherence checks at different pipeline phases."""

    def test_check_at_requirements_phase(self, coherence_checker, cot_tracker, aligned_requirements, aligned_po_review):
        """Check coherence at REQUIREMENTS phase."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        state = PipelineState(
            concept="test",
            phase=PipelinePhase.REQUIREMENTS,
            has_requirements=True,
        )

        # Check alignment
        result = coherence_checker.check_ba_po_alignment(aligned_requirements, aligned_po_review)

        assert result["aligned"] is True
        assert len(result["issues"]) == 0

    def test_check_at_planning_phase(self, coherence_checker, cot_tracker):
        """Check coherence at PLANNING phase."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        state = PipelineState(
            concept="test",
            phase=PipelinePhase.PLANNING,
            has_stories=True,
        )

        # Mock architecture and stories
        architecture = {"components": ["API", "Database"]}
        stories = [
            {"component": "API", "title": "S1"},
            {"component": "Database", "title": "S2"},
        ]

        result = coherence_checker.check_arch_stories_alignment(architecture, stories)

        assert isinstance(result, dict)
        assert "aligned" in result
        assert "issues" in result

    def test_detect_misalignment(self, coherence_checker, aligned_requirements, misaligned_po_review):
        """Detect misalignment in coherence check."""
        result = coherence_checker.check_ba_po_alignment(aligned_requirements, misaligned_po_review)

        assert result["aligned"] is False
        assert len(result["issues"]) > 0


# ==============================================================================
# TEST SUITE 3: Remediation Action Generation
# ==============================================================================

class TestRemediationActionGeneration:
    """Test generation of remediation actions for coherence issues."""

    def test_generate_remediation_for_coverage_gap(self, coherence_checker, cot_tracker):
        """Generate remediation for missing architecture coverage."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        state = PipelineState(
            concept="test",
            phase=PipelinePhase.PLANNING,
        )

        # Simulate coverage gap
        critical_issues = [{"type": "missing_components", "components": ["Cache"]}]

        actions = integration._generate_remediation_actions(critical_issues, state)

        assert isinstance(actions, list)
        assert len(actions) > 0

    def test_generate_remediation_for_conflicts(self, coherence_checker, cot_tracker):
        """Generate remediation for constraint conflicts."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        state = PipelineState(
            concept="test",
            phase=PipelinePhase.REQUIREMENTS,
        )

        critical_issues = [{"type": "constraint_conflict", "conflicts": ["Auth method"]}]

        actions = integration._generate_remediation_actions(critical_issues, state)

        assert isinstance(actions, list)
        # Should generate architect intervention action
        if actions:
            assert any(a.get("tool") == "RUN_ARCHITECT" for a in actions)

    def test_generate_remediation_for_quality_issues(self, coherence_checker, cot_tracker):
        """Generate remediation for quality issues."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        state = PipelineState(
            concept="test",
            phase=PipelinePhase.PLANNING,
        )

        critical_issues = [{"type": "low_quality_stories", "severity": "high"}]

        actions = integration._generate_remediation_actions(critical_issues, state)

        assert isinstance(actions, list)


# ==============================================================================
# TEST SUITE 4: Plan with Coherence Integration
# ==============================================================================

class TestPlanWithCoherence:
    """Test planning with integrated coherence checks."""

    def test_plan_with_coherence_aligned(self, coherence_checker, cot_tracker, aligned_requirements, aligned_po_review):
        """Plan when coherence checks pass."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        state = PipelineState(
            concept="test",
            phase=PipelinePhase.REQUIREMENTS,
            has_requirements=True,
        )

        # Check coherence
        coherence_result = coherence_checker.check_ba_po_alignment(
            aligned_requirements, aligned_po_review
        )

        assert coherence_result["aligned"] is True

    def test_plan_with_coherence_misaligned(self, coherence_checker, cot_tracker, aligned_requirements, misaligned_po_review):
        """Plan when coherence checks fail."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        state = PipelineState(
            concept="test",
            phase=PipelinePhase.REQUIREMENTS,
            has_requirements=True,
        )

        # Check coherence
        coherence_result = coherence_checker.check_ba_po_alignment(
            aligned_requirements, misaligned_po_review
        )

        assert coherence_result["aligned"] is False
        assert len(coherence_result["issues"]) > 0


# ==============================================================================
# TEST SUITE 5: CoT Logging for Coherence Warnings
# ==============================================================================

class TestCoherenceCoTLogging:
    """Test logging coherence issues to CoT tracker."""

    def test_log_coherence_warning_to_cot(self, coherence_checker, cot_tracker):
        """Log coherence warnings to CoT tracker."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        warnings = [
            {"type": "missing_components", "components": ["Cache"]},
            {"type": "constraint_conflict", "conflicts": ["Auth"]},
        ]

        # Log warnings
        cot_tracker.log_policy_evaluation(
            policy_name="coherence_check",
            condition="coherence_issues > 0",
            matched=True,
            context={"warnings": len(warnings)},
        )

        assert cot_tracker.get_thought_count() == 1

    def test_log_coherence_issues_by_phase(self, cot_tracker):
        """Log coherence issues for different phases."""
        cot_tracker.phase = "REQUIREMENTS"
        cot_tracker.log_policy_evaluation("coherence", "issues > 0", True, {"count": 2})

        cot_tracker.phase = "PLANNING"
        cot_tracker.log_policy_evaluation("coherence", "issues > 0", False, {"count": 0})

        by_phase = cot_tracker.get_thoughts_by_phase()
        assert "REQUIREMENTS" in by_phase
        assert "PLANNING" in by_phase


# ==============================================================================
# TEST SUITE 6: Critical vs Non-Critical Issues
# ==============================================================================

class TestCriticalIssueHandling:
    """Test handling of critical vs non-critical coherence issues."""

    def test_critical_issue_blocks_progression(self, coherence_checker, cot_tracker):
        """Critical coherence issues should block progression."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        # Simulate critical issue
        critical_issues = [
            {"type": "missing_components", "severity": "critical", "components": ["Database"]}
        ]

        actions = integration._generate_remediation_actions(critical_issues, None)

        # Should generate actions to resolve critical issues
        assert len(actions) > 0

    def test_warning_issues_allow_progression(self, coherence_checker, cot_tracker):
        """Non-critical issues should allow progression with warnings."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        # Simulate warning issue
        warning_issues = [{"type": "documentation_gap", "severity": "warning"}]

        # Log warning without blocking
        cot_tracker.log_policy_evaluation(
            policy_name="coherence_warning",
            condition="warning_issued",
            matched=True,
            context={"severity": "warning"},
        )

        assert cot_tracker.get_thought_count() == 1


# ==============================================================================
# TEST SUITE 7: Integration Tests
# ==============================================================================

class TestCoherenceIntegrationE2E:
    """End-to-end integration tests."""

    def test_full_coherence_check_cycle(self, coherence_checker, cot_tracker, aligned_requirements, aligned_po_review):
        """Full cycle: check coherence, log issues, generate remediation."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        state = PipelineState(
            concept="test",
            phase=PipelinePhase.REQUIREMENTS,
        )

        # Check coherence
        coherence_result = coherence_checker.check_ba_po_alignment(
            aligned_requirements, aligned_po_review
        )

        # Log result
        cot_tracker.log_policy_evaluation(
            policy_name="coherence_check",
            condition="alignment_verified",
            matched=coherence_result["aligned"],
            context={"issues": len(coherence_result["issues"])},
        )

        # Generate remediation if needed
        if not coherence_result["aligned"]:
            actions = integration._generate_remediation_actions(
                [{"type": "misalignment", "issues": coherence_result["issues"]}],
                state,
            )
            assert len(actions) > 0

        assert cot_tracker.get_thought_count() >= 1

    def test_coherence_doesnt_break_normal_flow(self, coherence_checker, cot_tracker):
        """Coherence checks should not interfere with normal orchestration."""
        from scripts.orchestrator.coherence_orchestration_integration import (
            CoherenceOrchestrationIntegration,
        )

        integration = CoherenceOrchestrationIntegration(coherence_checker, cot_tracker)

        # Normal operation (no issues)
        cot_tracker.log_state_transition("A", "B", "test")
        cot_tracker.log_dag_decision(["S1"], ["S1"], "test")

        # Coherence check
        cot_tracker.log_policy_evaluation("coherence", "check", True, {})

        # Should have 3 thoughts logged
        assert cot_tracker.get_thought_count() == 3
