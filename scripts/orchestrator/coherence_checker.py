"""
Coherence Checker for validating consistency between agent outputs.

Detects and flags inconsistencies between:
- BA requirements and PO review
- Architecture and generated stories
- Implementation and test coverage
- QA artifacts and expected fields
"""

from typing import Dict, List, Set
from logger import logger


class CoherenceChecker:
    """Validates consistency between different agent outputs."""

    def __init__(self, config: Dict = None):
        """Initialize coherence checker with optional config."""
        self.config = config or {}
        self.logger = logger

    def check_ba_po_alignment(
        self, requirements: Dict, po_review: Dict
    ) -> Dict:
        """Check if PO review aligns with BA requirements.

        Returns:
            Dict with keys: aligned (bool), issues (List[str]), severity (str)
        """
        issues = []

        # Check required fields
        if "requirements" not in requirements:
            issues.append("BA missing requirements list")
        if "approved" not in po_review:
            issues.append("PO missing approval status")

        # Check scope consistency
        ba_req_count = len(requirements.get("requirements", []))
        po_req_count = len(po_review.get("reviewed_requirements", []))
        if ba_req_count > 0 and po_req_count > 0 and po_req_count != ba_req_count:
            issues.append(
                f"Requirement count mismatch: BA={ba_req_count}, PO={po_req_count}"
            )

        # Check for constraint conflicts
        ba_constraints = set(requirements.get("constraints", []))
        po_constraints = set(po_review.get("constraints", []))
        if ba_constraints and po_constraints:
            conflicts = ba_constraints ^ po_constraints
            if conflicts:
                issues.append(f"Constraint conflicts: {conflicts}")

        severity = "high" if len(issues) > 1 else "medium" if issues else "ok"

        self.logger.debug(
            f"[coherence] BA→PO alignment: aligned={len(issues)==0}, issues={issues}"
        )

        return {
            "aligned": len(issues) == 0,
            "issues": issues,
            "severity": severity,
        }

    def check_arch_stories_alignment(
        self, architecture: Dict, stories: List[Dict]
    ) -> Dict:
        """Check if stories implement architecture components.

        Returns:
            Dict with keys: aligned (bool), issues (List[str]), severity (str)
        """
        issues = []

        # Check architecture components in stories
        arch_components = set(architecture.get("components", []))
        story_components = set()
        for story in stories:
            story_components.update(story.get("components", []))

        missing = arch_components - story_components
        if missing:
            issues.append(f"Architecture components not in stories: {missing}")

        # Check dependencies are consistent
        story_ids = {s.get("id") for s in stories}
        for story in stories:
            deps = story.get("depends_on", [])
            for dep in deps:
                if dep and dep not in story_ids:
                    issues.append(
                        f"Story {story.get('id')}: dependency {dep} not found"
                    )

        # Check layers/tiers respected
        arch_layers = architecture.get("layers", [])
        if arch_layers:
            for story in stories:
                story_layer = story.get("layer")
                if story_layer and story_layer not in arch_layers:
                    issues.append(
                        f"Story {story.get('id')}: layer {story_layer} not in "
                        f"architecture layers {arch_layers}"
                    )

        severity = (
            "high"
            if len(issues) > 2
            else "medium" if issues else "ok"
        )

        self.logger.debug(
            f"[coherence] Arch→Stories alignment: aligned={len(issues)==0}, "
            f"issues={issues}"
        )

        return {
            "aligned": len(issues) == 0,
            "issues": issues,
            "severity": severity,
        }

    def check_dev_tests_alignment(
        self, implementation: Dict, tests: Dict
    ) -> Dict:
        """Check if tests cover implementation adequately.

        Returns:
            Dict with keys: aligned (bool), issues (List[str]), severity (str)
        """
        issues = []

        # Check test coverage threshold
        coverage = tests.get("coverage", 0.0)
        if coverage < 0.7:
            issues.append(f"Low test coverage: {coverage*100:.1f}% (target: 70%)")

        # Check test types
        test_types = set(tests.get("test_types", []))
        required_types = {"unit", "integration"}
        missing_types = required_types - test_types
        if missing_types:
            issues.append(f"Missing test types: {missing_types}")

        # Check untested functions
        impl_functions = set(implementation.get("functions", []))
        tested_functions = set(tests.get("tested_functions", []))
        if impl_functions:
            untested = impl_functions - tested_functions
            untested_ratio = len(untested) / len(impl_functions)
            if untested_ratio > 0.2:
                issues.append(
                    f"Many untested functions: {len(untested)}/{len(impl_functions)} "
                    f"({untested_ratio*100:.0f}%)"
                )

        severity = (
            "high"
            if coverage < 0.5
            else "medium" if issues else "ok"
        )

        self.logger.debug(
            f"[coherence] Dev→Tests alignment: aligned={len(issues)==0}, "
            f"issues={issues}"
        )

        return {
            "aligned": len(issues) == 0,
            "issues": issues,
            "severity": severity,
        }

    def check_qa_artifacts(self, qa_report: Dict) -> Dict:
        """Validate QA report completeness and health.

        Returns:
            Dict with keys: valid (bool), issues (List[str]), severity (str)
        """
        issues = []

        required_fields = [
            "test_results",
            "coverage",
            "failures",
            "duration",
        ]

        for field in required_fields:
            if field not in qa_report:
                issues.append(f"QA report missing field: {field}")

        # Check for critical failures
        failures = qa_report.get("failures", {})
        if isinstance(failures, dict):
            if failures.get("critical"):
                issues.append("Critical test failures detected")

        severity = (
            "critical"
            if "Critical" in str(issues)
            else "high" if issues else "ok"
        )

        self.logger.debug(
            f"[coherence] QA artifacts: valid={len(issues)==0}, issues={issues}"
        )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "severity": severity,
        }
