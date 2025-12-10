"""Coherence Orchestration Integration

Integrates coherence checking into the planning loop with remediation actions.
Extends CoherenceChecker with planning capabilities.
"""
from typing import Dict, List, Optional
from logger import logger

from .coherence_checker import CoherenceChecker
from .cot_tracker import ChainOfThoughtTracker


class CoherenceOrchestrationIntegration:
    """Integrates coherence checks with planning and remediation."""

    def __init__(self, checker: CoherenceChecker, tracker: Optional[ChainOfThoughtTracker] = None):
        """Initialize integration with coherence checker and optional CoT tracker."""
        self.checker = checker
        self.tracker = tracker
        logger.debug("[coherence_integration] Initialized CoherenceOrchestrationIntegration")

    def plan_with_coherence(self, state: "PipelineState") -> List[Dict]:
        """Execute planning with integrated coherence checks.

        Returns list of planning actions.
        """
        from .state_machine import PipelinePhase

        logger.debug(f"[coherence_integration] Planning with coherence checks for phase: {state.phase.value}")

        # Determine checkpoint based on phase
        checkpoint = self._get_checkpoint_for_phase(state.phase)

        if not checkpoint:
            # No coherence check for this phase
            return []

        # Run coherence checks
        coherence_issues = self._check_coherence_at_checkpoint(checkpoint, state)

        # Log coherence check to CoT
        if self.tracker:
            self.tracker.log_policy_evaluation(
                policy_name="coherence_check",
                condition=f"coherence_check_{checkpoint}",
                matched=len(coherence_issues) == 0,
                context={
                    "checkpoint": checkpoint,
                    "issues_found": len(coherence_issues),
                },
            )

        # Handle critical issues
        if coherence_issues:
            critical_issues = [i for i in coherence_issues if i.get("severity") == "critical"]

            if critical_issues:
                logger.warning(f"[coherence_integration] Critical coherence issues: {critical_issues}")

                # Generate remediation actions
                actions = self._generate_remediation_actions(critical_issues, state)

                if actions:
                    logger.info(f"[coherence_integration] Generated {len(actions)} remediation actions")
                    return actions

        return []

    def _get_checkpoint_for_phase(self, phase: "PipelinePhase") -> Optional[str]:
        """Determine coherence checkpoint for phase.

        Returns checkpoint name or None if no check needed.
        """
        from .state_machine import PipelinePhase

        checkpoints = {
            PipelinePhase.REQUIREMENTS: "post_requirements",
            PipelinePhase.PLANNING: "post_planning",
            PipelinePhase.DEVELOPMENT: None,  # No coherence check in development
            PipelinePhase.INTEGRATION: "post_integration",
        }

        return checkpoints.get(phase)

    def _check_coherence_at_checkpoint(self, checkpoint: str, state: "PipelineState") -> List[Dict]:
        """Run coherence checks for specific checkpoint.

        Returns list of issues found.
        """
        from pathlib import Path

        issues = []

        if checkpoint == "post_requirements":
            # Check BA→PO alignment
            ba_output = self._load_artifact("planning/requirements.yaml")
            po_output = self._load_artifact("planning/product_owner_review.yaml")

            if ba_output and po_output:
                result = self.checker.check_ba_po_alignment(ba_output, po_output)

                if not result["aligned"]:
                    issues.append({
                        "type": "ba_po_misalignment",
                        "severity": "critical" if len(result["issues"]) > 2 else "warning",
                        "issues": result["issues"],
                    })

        elif checkpoint == "post_planning":
            # Check Architecture→Stories alignment
            arch_output = self._load_artifact("planning/architecture.yaml")
            stories_output = self._load_artifact("planning/stories.yaml")

            if arch_output and stories_output:
                result = self.checker.check_arch_stories_alignment(arch_output, stories_output)

                if not result["aligned"]:
                    issues.append({
                        "type": "arch_stories_misalignment",
                        "severity": "critical" if len(result["issues"]) > 2 else "warning",
                        "issues": result["issues"],
                    })

        elif checkpoint == "post_integration":
            # Final coherence audit
            # Check all outputs exist and are consistent
            expected_files = [
                "planning/requirements.yaml",
                "planning/stories.yaml",
                "planning/architecture.yaml",
            ]

            missing_files = [f for f in expected_files if not Path(f).exists()]

            if missing_files:
                issues.append({
                    "type": "missing_artifacts",
                    "severity": "critical",
                    "files": missing_files,
                })

        return issues

    def _generate_remediation_actions(self, critical_issues: List[Dict], state: Optional["PipelineState"]) -> List[Dict]:
        """Generate remediation actions for critical coherence issues.

        Returns list of actions to resolve issues.
        """
        actions = []

        for issue in critical_issues:
            issue_type = issue.get("type", "unknown")

            if issue_type == "ba_po_misalignment":
                # Refine requirements
                actions.append({
                    "tool": "RUN_ARCHITECT",
                    "arguments": {"architect_mode": "refine_requirements"},
                    "reason": "BA→PO misalignment detected, need requirement refinement",
                    "decision_method": "coherence_remediation",
                    "rule": "R_COHERENCE_REMEDIATE_BA_PO",
                    "confidence": 1.0,
                })

            elif issue_type == "arch_stories_misalignment":
                # Refine stories
                actions.append({
                    "tool": "RUN_ARCHITECT",
                    "arguments": {"architect_mode": "refine_stories"},
                    "reason": "Architecture→Stories misalignment detected, need story refinement",
                    "decision_method": "coherence_remediation",
                    "rule": "R_COHERENCE_REMEDIATE_ARCH_STORIES",
                    "confidence": 1.0,
                })

            elif issue_type == "missing_components":
                # Enrich architecture
                actions.append({
                    "tool": "RUN_ARCHITECT",
                    "arguments": {"architect_mode": "enrich_architecture"},
                    "reason": f"Missing components: {issue.get('components', [])}",
                    "decision_method": "coherence_remediation",
                    "rule": "R_COHERENCE_REMEDIATE_MISSING",
                    "confidence": 1.0,
                })

            elif issue_type == "missing_artifacts":
                # Re-run generation
                actions.append({
                    "tool": "RUN_ARCHITECT",
                    "arguments": {"architect_mode": "full_regenerate"},
                    "reason": f"Missing artifacts: {issue.get('files', [])}",
                    "decision_method": "coherence_remediation",
                    "rule": "R_COHERENCE_REMEDIATE_MISSING_ARTIFACTS",
                    "confidence": 1.0,
                })

            elif issue_type == "constraint_conflict":
                # Manual review needed
                actions.append({
                    "tool": "RUN_ARCHITECT",
                    "arguments": {"architect_mode": "resolve_conflicts"},
                    "reason": f"Constraint conflicts: {issue.get('conflicts', [])}",
                    "decision_method": "coherence_remediation",
                    "rule": "R_COHERENCE_REMEDIATE_CONFLICTS",
                    "confidence": 1.0,
                })

        logger.debug(f"[coherence_integration] Generated {len(actions)} remediation actions")

        return actions

    def _log_warnings_to_cot(self, warnings: List[Dict]) -> None:
        """Log coherence warnings to CoT tracker."""
        if not self.tracker or not warnings:
            return

        for warning in warnings:
            self.tracker.log_policy_evaluation(
                policy_name="coherence_warning",
                condition="warning_issued",
                matched=True,
                context={
                    "type": warning.get("type"),
                    "severity": warning.get("severity", "medium"),
                },
            )

    def _load_artifact(self, path: str) -> Optional[Dict]:
        """Load artifact from filesystem."""
        from pathlib import Path
        import yaml
        import json

        artifact_path = Path(path)

        if not artifact_path.exists():
            return None

        try:
            if path.endswith(".yaml") or path.endswith(".yml"):
                with open(artifact_path) as f:
                    return yaml.safe_load(f)
            elif path.endswith(".json"):
                with open(artifact_path) as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"[coherence_integration] Failed to load artifact {path}: {e}")

        return None
