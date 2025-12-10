"""
Execution Optimizer for learning from past executions.

Analyzes execution history to recommend optimal:
- Parallelism levels for stories
- Retry backoff strategies per role
- Resource allocation strategies
"""

from typing import Dict, List, Optional
from pathlib import Path
import json
from logger import logger


class ExecutionOptimizer:
    """Learns from execution history to optimize future decisions."""

    def __init__(self, history_dir: Optional[Path] = None):
        """Initialize optimizer with history directory.

        Args:
            history_dir: Directory containing execution summaries.
                         Defaults to artifacts/iterations
        """
        self.history_dir = history_dir or Path("artifacts/iterations")
        self.execution_history: List[Dict] = []
        self.metrics_cache: Dict = {}
        self._load_history()
        logger.info(f"[optimizer] Initialized, loaded {len(self.execution_history)} "
                    f"execution records")

    def _load_history(self) -> None:
        """Load all past execution summaries from disk."""
        if not self.history_dir.exists():
            logger.debug(f"[optimizer] History directory not found: {self.history_dir}")
            return

        try:
            for iteration_dir in self.history_dir.iterdir():
                if iteration_dir.is_dir():
                    # Try to load summary from iteration
                    summary_file = iteration_dir / "latest_orchestrator_summary.json"
                    if summary_file.exists():
                        try:
                            data = json.loads(summary_file.read_text())
                            self.execution_history.append(data)
                        except Exception as e:
                            logger.debug(
                                f"[optimizer] Failed to load summary from "
                                f"{summary_file}: {e}"
                            )

                    # Try alternate path
                    summary_file = iteration_dir / "summary.json"
                    if summary_file.exists():
                        try:
                            data = json.loads(summary_file.read_text())
                            if data not in self.execution_history:
                                self.execution_history.append(data)
                        except Exception as e:
                            logger.debug(
                                f"[optimizer] Failed to load summary from "
                                f"{summary_file}: {e}"
                            )
        except Exception as e:
            logger.warning(f"[optimizer] Failed to load history: {e}")

    def get_optimal_parallelism(self) -> int:
        """Learn optimal number of parallel stories from history.

        Analyzes successful executions and returns the parallelism
        level with best efficiency (time/parallelism ratio).

        Returns:
            Optimal parallelism (1-10), defaults to 3 if no history
        """
        if not self.execution_history:
            logger.debug("[optimizer] No history, returning default parallelism=3")
            return 3

        successful_runs = [
            e for e in self.execution_history
            if e.get("status") == "success"
        ]

        if not successful_runs:
            logger.debug("[optimizer] No successful runs, returning default parallelism=3")
            return 3

        parallelism_stats = []
        for execution in successful_runs:
            parallelism = execution.get("max_parallel", 3)
            duration = execution.get("duration", 0)

            if duration > 0:
                efficiency = duration / max(parallelism, 1)
                parallelism_stats.append({
                    "parallelism": parallelism,
                    "duration": duration,
                    "efficiency": efficiency,
                })

        if not parallelism_stats:
            return 3

        # Return parallelism with best (lowest) efficiency
        best = min(parallelism_stats, key=lambda x: x["efficiency"])
        optimal = best["parallelism"]

        logger.info(
            f"[optimizer] Learned optimal parallelism={optimal} "
            f"(efficiency={best['efficiency']:.2f})"
        )

        return optimal

    def get_optimal_backoff(self, role: str) -> Dict:
        """Learn optimal retry backoff strategy for a role.

        Analyzes failure patterns and success rates per retry count
        to recommend exponential vs linear backoff.

        Args:
            role: Role name (dev, qa, architect, etc.)

        Returns:
            Dict with keys: type (exponential/linear), base (seconds)
        """
        if not self.execution_history:
            logger.debug(
                f"[optimizer] No history for {role}, using default backoff"
            )
            return {"type": "exponential", "base": 60}

        # Analyze failures for this role
        role_failures = []
        for execution in self.execution_history:
            failures_key = f"{role}_failures"
            if failures_key in execution:
                role_failures.extend(execution[failures_key])

        if not role_failures:
            logger.debug(
                f"[optimizer] No failures recorded for {role}, "
                f"using default backoff"
            )
            return {"type": "exponential", "base": 60}

        # Calculate success rate by retry count
        retry_effectiveness: Dict[int, Dict] = {}
        for failure in role_failures:
            retries = failure.get("retries", 0)
            succeeded = failure.get("succeeded", False)

            if retries not in retry_effectiveness:
                retry_effectiveness[retries] = {"success": 0, "total": 0}

            retry_effectiveness[retries]["total"] += 1
            if succeeded:
                retry_effectiveness[retries]["success"] += 1

        # Compute success rates
        success_rates = {}
        for retries, data in retry_effectiveness.items():
            if data["total"] > 0:
                success_rates[retries] = data["success"] / data["total"]

        # Decide strategy based on max success rate
        if not success_rates:
            return {"type": "exponential", "base": 60}

        max_success_rate = max(success_rates.values())

        strategy = (
            {"type": "exponential", "base": 60}
            if max_success_rate > 0.7
            else {"type": "linear", "base": 120}
        )

        logger.info(
            f"[optimizer] Learned {role} backoff strategy: {strategy} "
            f"(max_success_rate={max_success_rate:.2f})"
        )

        return strategy

    def get_execution_metrics(self) -> Dict:
        """Get aggregated metrics from execution history.

        Returns:
            Dict with metrics like avg_duration, success_rate, etc.
        """
        if self.metrics_cache:
            return self.metrics_cache

        if not self.execution_history:
            return {}

        total = len(self.execution_history)
        successful = len([e for e in self.execution_history
                         if e.get("status") == "success"])

        durations = [
            e.get("duration", 0)
            for e in self.execution_history
            if e.get("duration", 0) > 0
        ]

        metrics = {
            "total_executions": total,
            "successful_executions": successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
        }

        self.metrics_cache = metrics
        logger.debug(f"[optimizer] Computed metrics: {metrics}")

        return metrics

    def record_execution(self, execution: Dict) -> None:
        """Record a new execution result for learning.

        Args:
            execution: Execution result dict with status, duration, etc.
        """
        self.execution_history.append(execution)
        self.metrics_cache = {}  # Invalidate cache
        logger.debug(f"[optimizer] Recorded execution, total history size="
                     f"{len(self.execution_history)}")
