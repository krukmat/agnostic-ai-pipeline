"""
Domain-Specific Rules Engine for customizable validation.

Allows registering domain-specific coherence checks and validation rules.
Supports multiple domains (backend, frontend, data, etc.) with context-aware
rule selection and execution.
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from logger import logger


@dataclass
class Rule:
    """Represents a validation rule."""
    name: str
    description: str
    severity: str  # ok, medium, high, critical
    check_function: Callable
    applies_to: List[str]  # Tools: RUN_BA, RUN_PO, RUN_ARCHITECT, RUN_DEV, RUN_QA
    context: Optional[Dict[str, Any]] = None


class DomainRulesEngine:
    """Manages domain-specific validation rules."""

    def __init__(self, domain_name: str = "default", rules_config: Optional[Dict] = None):
        """Initialize domain rules engine.

        Args:
            domain_name: Domain identifier (backend, frontend, data, etc.)
            rules_config: Optional rules configuration dict
        """
        self.domain_name = domain_name
        self.rules: Dict[str, Rule] = {}
        self.rule_results: Dict[str, Dict] = {}  # Cache results
        self._register_default_rules()
        if rules_config:
            self._load_from_config(rules_config)
        logger.info(f"[domain_rules] Initialized domain '{domain_name}' with "
                    f"{len(self.rules)} rules")

    def _register_default_rules(self) -> None:
        """Register default rules for common domains."""
        # Backend rules
        if self.domain_name in ["backend", "all"]:
            self.register_check(
                name="api_endpoint_naming",
                description="API endpoints follow /api/v[1-9]/resource pattern",
                severity="high",
                check_function=self._check_api_endpoints,
                applies_to=["RUN_ARCHITECT", "RUN_DEV"],
            )

            self.register_check(
                name="database_migrations",
                description="Database migrations include up/down steps",
                severity="high",
                check_function=self._check_migrations,
                applies_to=["RUN_DEV"],
            )

        # Common rules
        if self.domain_name in ["all", "default"]:
            self.register_check(
                name="test_coverage_minimum",
                description="Test coverage >= 70%",
                severity="high",
                check_function=self._check_test_coverage,
                applies_to=["RUN_QA"],
            )

            self.register_check(
                name="documentation_present",
                description="Code includes docstrings and comments",
                severity="medium",
                check_function=self._check_documentation,
                applies_to=["RUN_DEV"],
            )

    def register_check(
        self,
        name: str,
        description: str,
        severity: str,
        check_function: Callable,
        applies_to: List[str],
    ) -> None:
        """Register custom validation check.

        Args:
            name: Rule name (identifier)
            description: Human-readable description
            severity: ok, medium, high, critical
            check_function: Callable that performs check
            applies_to: List of tools where rule applies
        """
        rule = Rule(
            name=name,
            description=description,
            severity=severity,
            check_function=check_function,
            applies_to=applies_to,
        )
        self.rules[name] = rule
        logger.info(f"[domain_rules] Registered rule '{name}' ({severity})")

    def validate_output(self, tool_name: str, output: Dict) -> Dict:
        """Run domain-specific validation on tool output.

        Args:
            tool_name: Tool name (RUN_ARCHITECT, RUN_DEV, etc.)
            output: Tool output dict

        Returns:
            Validation result {issues: [], severity: str, passed: bool}
        """
        issues = []
        max_severity = "ok"

        # Get applicable rules
        applicable_rules = self.get_applicable_rules({
            "domain": self.domain_name,
            "tool": tool_name,
        })

        # Run each rule
        for rule in applicable_rules:
            try:
                result = rule.check_function(output)
                if not result.get("passed", True):
                    issues.append({
                        "rule": rule.name,
                        "description": rule.description,
                        "severity": rule.severity,
                        "message": result.get("message", "Failed"),
                    })

                    # Update max severity
                    severity_order = {"ok": 0, "medium": 1, "high": 2, "critical": 3}
                    if severity_order.get(rule.severity, 0) > severity_order.get(
                        max_severity, 0
                    ):
                        max_severity = rule.severity

            except Exception as e:
                logger.warning(f"[domain_rules] Error running rule '{rule.name}': {e}")

        result = {
            "issues": issues,
            "severity": max_severity,
            "passed": len(issues) == 0,
            "rule_count": len(applicable_rules),
        }

        logger.debug(
            f"[domain_rules] Validated {tool_name}: "
            f"passed={result['passed']}, severity={max_severity}"
        )

        return result

    def get_applicable_rules(self, context: Dict[str, str]) -> List[Rule]:
        """Get rules applicable to context.

        Args:
            context: {domain, tool, phase, story_type}

        Returns:
            List of applicable rules
        """
        tool = context.get("tool", "")
        applicable = [r for r in self.rules.values() if tool in r.applies_to]

        logger.debug(
            f"[domain_rules] Found {len(applicable)} applicable rules for {tool}"
        )

        return applicable

    def _load_from_config(self, config: Dict) -> None:
        """Load rules from config dict.

        Args:
            config: Configuration dict with rules
        """
        rules = config.get("rules", [])
        for rule_cfg in rules:
            try:
                # Dynamic function loading would go here
                # For now, skip custom rules from config
                logger.debug(f"[domain_rules] Config rules loading not implemented")
            except Exception as e:
                logger.warning(f"[domain_rules] Failed to load rule from config: {e}")

    # Default check functions

    def _check_api_endpoints(self, output: Dict) -> Dict:
        """Check API endpoint naming conventions.

        Args:
            output: Architect output

        Returns:
            {passed: bool, message: str}
        """
        endpoints = output.get("endpoints", [])
        if not endpoints:
            return {"passed": True, "message": "No endpoints"}

        invalid = [e for e in endpoints if not self._is_valid_endpoint(e)]
        if invalid:
            return {
                "passed": False,
                "message": f"Invalid endpoint names: {invalid}",
            }

        return {"passed": True, "message": f"{len(endpoints)} endpoints valid"}

    def _is_valid_endpoint(self, endpoint: str) -> bool:
        """Validate endpoint format."""
        # Accept /api/v1/... or /api/v2/... patterns
        import re
        pattern = r"^/api/v\d+/[a-z_/]+$"
        return bool(re.match(pattern, endpoint.lower()))

    def _check_migrations(self, output: Dict) -> Dict:
        """Check database migrations have up/down.

        Args:
            output: Dev output

        Returns:
            {passed: bool, message: str}
        """
        migrations = output.get("migrations", [])
        if not migrations:
            return {"passed": True, "message": "No migrations"}

        invalid = []
        for migration in migrations:
            if not migration.get("up") or not migration.get("down"):
                invalid.append(migration.get("name", "unknown"))

        if invalid:
            return {
                "passed": False,
                "message": f"Migrations without up/down: {invalid}",
            }

        return {"passed": True, "message": f"{len(migrations)} migrations valid"}

    def _check_test_coverage(self, output: Dict) -> Dict:
        """Check test coverage >= 70%.

        Args:
            output: QA output

        Returns:
            {passed: bool, message: str}
        """
        coverage = output.get("coverage", 0)
        if coverage >= 0.70:
            return {"passed": True, "message": f"Coverage {coverage*100:.0f}%"}

        return {
            "passed": False,
            "message": f"Coverage {coverage*100:.0f}% < 70%",
        }

    def _check_documentation(self, output: Dict) -> Dict:
        """Check code has documentation.

        Args:
            output: Dev output

        Returns:
            {passed: bool, message: str}
        """
        functions = output.get("functions", [])
        if not functions:
            return {"passed": True, "message": "No functions"}

        undocumented = sum(
            1 for f in functions if not f.get("docstring")
        )

        if undocumented > len(functions) * 0.2:  # >20% undocumented
            return {
                "passed": False,
                "message": f"{undocumented}/{len(functions)} functions undocumented",
            }

        return {
            "passed": True,
            "message": f"{len(functions)} functions documented",
        }

    def get_rules_summary(self) -> Dict:
        """Get summary of all rules.

        Returns:
            Dict with rule statistics
        """
        severity_counts = {"ok": 0, "medium": 0, "high": 0, "critical": 0}
        for rule in self.rules.values():
            severity_counts[rule.severity] += 1

        return {
            "domain": self.domain_name,
            "total_rules": len(self.rules),
            "severity_breakdown": severity_counts,
        }
