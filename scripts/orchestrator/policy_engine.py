"""
Policy Engine for orchestration.

Evaluates policies for retries, escalation, and resource constraints.
All policies defined in config.yaml (declarative, not hardcoded).
"""

from typing import Dict, Optional, List
from logger import logger


class PolicyEngine:
    """Evaluates policies for retries, escalation, and resource constraints."""

    def __init__(self, config: Dict):
        """Initialize policy engine from config."""
        pipeline_config = config.get("pipeline", {})

        self.retry_policies = pipeline_config.get("retry_policies", {})
        self.escalation_policies = pipeline_config.get("escalation_policies", [])
        self.resource_policies = pipeline_config.get("resource_policies", {})
        self.priority_policies = pipeline_config.get("priority_policies", [])

        logger.info(f"[policy] Loaded {len(self.escalation_policies)} escalation policies")
        logger.info(f"[policy] Resource limits: {self.resource_policies}")

    def should_retry(self, role: str, attempts: int) -> bool:
        """Check if retry is allowed by policy."""
        policy = self.retry_policies.get(role, {})
        max_attempts = policy.get("max_attempts", 3)
        return attempts < max_attempts

    def get_backoff_delay(self, role: str, attempt: int) -> float:
        """Calculate backoff delay in seconds."""
        policy = self.retry_policies.get(role, {})
        backoff_type = policy.get("backoff", "none")

        if backoff_type == "exponential":
            return 60 * (2 ** (attempt - 1))
        elif backoff_type == "linear":
            return 60 * attempt
        else:
            return 0

    def get_max_parallel_stories(self) -> int:
        """Get maximum number of stories that can run in parallel."""
        return self.resource_policies.get("max_parallel_stories", 3)

    def get_timeout(self, role: str) -> int:
        """Get timeout in seconds for a role."""
        key = f"{role}_timeout"
        return self.resource_policies.get(key, 600)

    def evaluate_escalation(self, story_id: str, attempts: int, error_history: List[str], context: Dict) -> Optional[str]:
        """Evaluate if escalation is needed. Returns action name or None."""
        for policy in self.escalation_policies:
            condition = policy.get("condition", "")
            action = policy.get("action", "")

            if self._evaluate_condition(condition, attempts, error_history, context):
                logger.warning(f"[policy] Escalation triggered: {policy.get('reason', 'N/A')}")
                return action

        return None

    def _evaluate_condition(self, condition: str, attempts: int, error_history: List[str], context: Dict) -> bool:
        """Evaluate escalation condition expression."""
        same_error_pattern = len(set(error_history)) == 1 and len(error_history) >= 2

        # Convert English operators to Python operators
        normalized = condition.replace(" AND ", " and ").replace(" OR ", " or ").replace(" NOT ", " not ")

        eval_ctx = {
            "dev_attempts": attempts,
            "same_error_pattern": same_error_pattern,
            "qa_coverage": context.get("qa_coverage", 1.0),
            "tests_failed": context.get("tests_failed", 0),
        }

        try:
            return eval(normalized, {"__builtins__": {}}, eval_ctx)
        except Exception as exc:
            logger.error(f"[policy] Failed to evaluate condition '{condition}': {exc}")
            return False
