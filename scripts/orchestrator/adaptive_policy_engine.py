"""
Adaptive Policy Engine that learns and adjusts policies from execution patterns.

Dynamically adjusts:
- Escalation thresholds based on success rates
- Retry limits per role and story type
- Parallelism factors for system conditions
- Backoff strategies based on effectiveness
"""

from typing import Dict, Optional, List
from collections import defaultdict
from logger import logger


class AdaptivePolicyEngine:
    """Manages adaptive policies that learn from execution patterns."""

    def __init__(self, base_config: Optional[Dict] = None):
        """Initialize adaptive policy engine.

        Args:
            base_config: Base configuration with initial policies
        """
        self.base_config = base_config or {}
        self.role_success_rates: Dict[str, float] = defaultdict(lambda: 0.8)
        self.story_type_failure_patterns: Dict[str, List[str]] = defaultdict(list)
        self.escalation_thresholds: Dict[str, int] = {
            "dev": 2,
            "qa": 1,
            "architect": 1,
        }
        self.retry_limits: Dict[str, int] = {
            "dev": 3,
            "qa": 2,
            "architect": 1,
        }
        self.parallelism_factors: Dict[str, float] = {
            "normal": 1.0,
            "stress": 0.5,
            "optimal": 1.5,
        }
        self.backoff_strategies: Dict[str, Dict] = {
            "dev": {"type": "exponential", "base": 60},
            "qa": {"type": "linear", "base": 120},
            "architect": {"type": "exponential", "base": 30},
        }
        logger.info("[adaptive_policy] Initialized")

    def evaluate_dynamic_escalation(
        self,
        story_id: str,
        context: Dict,
    ) -> Optional[str]:
        """Evaluate if story should escalate to architect.

        Escalation threshold adapts based on role success rate.

        Args:
            story_id: Story identifier
            context: {role, attempts, errors, phase}

        Returns:
            Escalation reason or None if no escalation needed
        """
        role = context.get("role", "dev")
        attempts = context.get("attempts", 0)
        errors = context.get("errors", [])

        # Get dynamic threshold based on role success rate
        success_rate = self.role_success_rates.get(role, 0.8)

        # Adjust threshold: lower success rate = lower threshold for escalation
        base_threshold = self.escalation_thresholds.get(role, 2)
        dynamic_threshold = max(1, int(base_threshold * success_rate))

        logger.debug(
            f"[adaptive_policy] Escalation check: {story_id}, "
            f"attempts={attempts}, threshold={dynamic_threshold}, "
            f"success_rate={success_rate:.0%}"
        )

        if attempts > dynamic_threshold:
            reason = (
                f"Escalation: {attempts} attempts > threshold {dynamic_threshold} "
                f"(success_rate={success_rate:.0%})"
            )
            logger.warning(f"[adaptive_policy] {reason}")
            return reason

        return None

    def learn_optimal_retry_limit(
        self,
        role: str,
        story_type: str,
    ) -> int:
        """Learn optimal retry count for role and story type.

        Args:
            role: Role name (dev, qa, architect)
            story_type: Story type identifier

        Returns:
            Optimal retry limit
        """
        # Check if this story type has high failure rate
        failures = self.story_type_failure_patterns.get(story_type, [])
        if len(failures) > 5:
            # High failure pattern: reduce retries
            optimal_retries = 1
        elif len(failures) > 2:
            # Medium failure: normal retries
            optimal_retries = self.retry_limits.get(role, 2)
        else:
            # Low failure: can afford more retries
            optimal_retries = self.retry_limits.get(role, 2) + 1

        # Clamp based on role
        min_retries = {"architect": 1, "qa": 1, "dev": 2}.get(role, 1)
        max_retries = {"architect": 1, "qa": 2, "dev": 4}.get(role, 3)

        optimal_retries = max(min_retries, min(max_retries, optimal_retries))

        logger.info(
            f"[adaptive_policy] Learned retry limit for {role}/{story_type}: "
            f"{optimal_retries} (base={self.retry_limits.get(role, 2)}, "
            f"failures={len(failures)})"
        )

        return optimal_retries

    def adjust_parallelism_factor(self, system_stress: float) -> float:
        """Adjust parallelism multiplier based on system stress.

        Args:
            system_stress: System stress level (0.0-1.0)

        Returns:
            Parallelism multiplier (0.5-2.0)
        """
        if system_stress > 0.8:
            factor = 0.5  # Critical stress: 50% parallelism
        elif system_stress > 0.6:
            factor = 0.75  # High stress: 75% parallelism
        elif system_stress < 0.3:
            factor = 1.5  # Low stress: 150% parallelism
        elif system_stress < 0.5:
            factor = 1.25  # Normal-low: 125% parallelism
        else:
            factor = 1.0  # Normal stress: 100% parallelism

        self.parallelism_factors["current"] = factor

        logger.debug(
            f"[adaptive_policy] Adjusted parallelism factor: {factor:.2f} "
            f"(stress={system_stress:.2f})"
        )

        return factor

    def should_escalate_immediately(
        self,
        story_id: str,
        attempt: int,
    ) -> bool:
        """Check if story should escalate immediately based on patterns.

        Args:
            story_id: Story identifier
            attempt: Current attempt number

        Returns:
            True if should escalate immediately
        """
        # Check if this story type has consistent failures
        story_type = story_id.split("_")[0] if "_" in story_id else "unknown"
        failures = self.story_type_failure_patterns.get(story_type, [])

        # Immediate escalation if:
        # 1. Story type has failed consistently (>80% failure rate)
        # 2. Already on 2nd attempt
        if len(failures) > 10:
            failure_rate = len(failures) / (len(failures) + 2)  # Estimate
            if failure_rate > 0.8 and attempt > 1:
                logger.warning(
                    f"[adaptive_policy] Immediate escalation for {story_id} "
                    f"(story type failure rate={failure_rate:.0%})"
                )
                return True

        return False

    def get_optimal_backoff_strategy(self, role: str) -> Dict:
        """Get optimal backoff strategy for role.

        Args:
            role: Role name

        Returns:
            Dict: {type: "exponential"|"linear", base: seconds}
        """
        strategy = self.backoff_strategies.get(role, {})

        # Adapt based on success rate
        success_rate = self.role_success_rates.get(role, 0.8)

        if success_rate > 0.9:
            # Very high success: use aggressive exponential
            return {"type": "exponential", "base": 30}
        elif success_rate > 0.7:
            # Good success: use moderate exponential
            return {"type": "exponential", "base": strategy.get("base", 60)}
        else:
            # Low success: use longer linear backoff
            return {"type": "linear", "base": strategy.get("base", 120) * 1.5}

    def record_execution_result(
        self,
        role: str,
        story_type: str,
        success: bool,
        error_type: Optional[str] = None,
    ) -> None:
        """Record execution result for learning.

        Args:
            role: Role that executed
            story_type: Type of story
            success: Execution success
            error_type: Type of error if failed
        """
        # Update role success rate
        current_rate = self.role_success_rates.get(role, 0.8)
        # Exponential moving average (alpha=0.1)
        alpha = 0.1
        new_rate = (alpha if success else 0) + (1 - alpha) * current_rate
        self.role_success_rates[role] = new_rate

        # Track failures per story type
        if not success and error_type:
            self.story_type_failure_patterns[story_type].append(error_type)
            # Keep only last 20 failures
            if len(self.story_type_failure_patterns[story_type]) > 20:
                self.story_type_failure_patterns[story_type] = \
                    self.story_type_failure_patterns[story_type][-20:]

        logger.debug(
            f"[adaptive_policy] Recorded {role}/{story_type}: "
            f"success={success}, new_rate={new_rate:.0%}"
        )

    def get_policy_recommendations(self) -> Dict:
        """Get current policy recommendations based on learning.

        Returns:
            Dict with all adaptive policy settings
        """
        recommendations = {
            "role_success_rates": dict(self.role_success_rates),
            "escalation_thresholds": self.escalation_thresholds,
            "retry_limits": self.retry_limits,
            "parallelism_factors": self.parallelism_factors,
            "backoff_strategies": self.backoff_strategies,
            "timestamp": str(__import__("datetime").datetime.now()),
        }

        logger.debug("[adaptive_policy] Generated policy recommendations")
        return recommendations

    def reset_to_base_policies(self) -> None:
        """Reset all adaptive policies to base configuration."""
        self.escalation_thresholds = {
            "dev": 2,
            "qa": 1,
            "architect": 1,
        }
        self.retry_limits = {
            "dev": 3,
            "qa": 2,
            "architect": 1,
        }
        self.parallelism_factors = {
            "normal": 1.0,
            "stress": 0.5,
            "optimal": 1.5,
        }
        self.backoff_strategies = {
            "dev": {"type": "exponential", "base": 60},
            "qa": {"type": "linear", "base": 120},
            "architect": {"type": "exponential", "base": 30},
        }
        logger.info("[adaptive_policy] Reset to base policies")

    def export_policy_snapshot(self) -> Dict:
        """Export complete policy snapshot for analysis.

        Returns:
            Complete policy state
        """
        return {
            "role_success_rates": dict(self.role_success_rates),
            "story_type_failures": dict(self.story_type_failure_patterns),
            "escalation_thresholds": self.escalation_thresholds,
            "retry_limits": self.retry_limits,
            "parallelism_factors": self.parallelism_factors,
            "backoff_strategies": self.backoff_strategies,
        }
