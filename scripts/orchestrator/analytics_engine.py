"""
Execution Analytics Engine for detailed pattern analysis and reporting.

Analyzes execution history to identify:
- Story success/failure patterns
- Phase bottlenecks
- Role performance metrics
- Success probability predictions
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from collections import defaultdict
from logger import logger


class AnalyticsEngine:
    """Analyzes execution patterns and generates reports."""

    def __init__(self, history_dir: Optional[Path] = None):
        """Initialize analytics engine.

        Args:
            history_dir: Directory with execution history. Defaults to artifacts/iterations
        """
        self.history_dir = history_dir or Path("artifacts/iterations")
        self.executions: List[Dict] = []
        self._load_executions()
        logger.info(f"[analytics] Initialized, loaded {len(self.executions)} "
                    f"executions")

    def _load_executions(self) -> None:
        """Load all execution summaries."""
        if not self.history_dir.exists():
            logger.debug(f"[analytics] History dir not found: {self.history_dir}")
            return

        try:
            for iteration_dir in self.history_dir.iterdir():
                if iteration_dir.is_dir():
                    summary_file = iteration_dir / "latest_orchestrator_summary.json"
                    if summary_file.exists():
                        try:
                            data = json.loads(summary_file.read_text())
                            self.executions.append(data)
                        except Exception as e:
                            logger.debug(
                                f"[analytics] Failed to load {summary_file}: {e}"
                            )
        except Exception as e:
            logger.warning(f"[analytics] Failed to load executions: {e}")

    def get_story_patterns(self) -> Dict:
        """Analyze success/failure patterns per story type.

        Returns:
            Dict: {story_type: {success_rate, avg_duration, common_errors, count}}
        """
        patterns = defaultdict(lambda: {
            "count": 0,
            "success_count": 0,
            "durations": [],
            "errors": defaultdict(int),
        })

        for execution in self.executions:
            story_executions = execution.get("executions", [])
            for story_exec in story_executions:
                story_id = story_exec.get("story_id", "unknown")
                # Infer story type from ID (S1, S2, etc. -> story)
                story_type = "story"

                patterns[story_type]["count"] += 1

                if story_exec.get("status") in ["ok", "success"]:
                    patterns[story_type]["success_count"] += 1

                duration = story_exec.get("duration")
                if duration:
                    patterns[story_type]["durations"].append(duration)

                error = story_exec.get("error")
                if error:
                    patterns[story_type]["errors"][error] += 1

        # Compute statistics
        result = {}
        for story_type, data in patterns.items():
            success_rate = (
                data["success_count"] / data["count"]
                if data["count"] > 0 else 0
            )
            avg_duration = (
                sum(data["durations"]) / len(data["durations"])
                if data["durations"] else 0
            )
            common_errors = sorted(
                data["errors"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            result[story_type] = {
                "success_rate": success_rate,
                "avg_duration": avg_duration,
                "common_errors": [e[0] for e in common_errors],
                "count": data["count"],
            }

        logger.debug(f"[analytics] Story patterns: {len(result)} types analyzed")
        return result

    def get_bottleneck_analysis(self) -> List[Dict]:
        """Identify slowest phases and most-failing story types.

        Returns:
            List of bottlenecks: [{phase, bottleneck_type, value, impact_percent}]
        """
        bottlenecks = []
        phase_durations = defaultdict(list)
        phase_failures = defaultdict(int)

        for execution in self.executions:
            # Phase durations
            for phase_data in execution.get("phases", []):
                phase = phase_data.get("phase", "unknown")
                duration = phase_data.get("duration", 0)
                if duration > 0:
                    phase_durations[phase].append(duration)

                # Count failures per phase
                if phase_data.get("status") in ["failed", "error"]:
                    phase_failures[phase] += 1

        # Find slowest phases
        if phase_durations:
            total_duration = sum(
                sum(durations)
                for durations in phase_durations.values()
            )

            for phase, durations in phase_durations.items():
                avg_duration = sum(durations) / len(durations)
                phase_total = sum(durations)
                impact = (phase_total / total_duration * 100) if total_duration > 0 else 0

                if impact > 15:  # Bottleneck if >15% of time
                    bottlenecks.append({
                        "phase": phase,
                        "bottleneck_type": "slow_phase",
                        "value": avg_duration,
                        "impact_percent": impact,
                    })

        # Find high-failure phases
        total_executions = sum(len(e.get("executions", [])) for e in self.executions)
        for phase, failure_count in phase_failures.items():
            if failure_count > 0 and total_executions > 0:
                failure_rate = (failure_count / total_executions) * 100
                if failure_rate > 10:  # >10% failure rate is bottleneck
                    bottlenecks.append({
                        "phase": phase,
                        "bottleneck_type": "high_failure_rate",
                        "value": failure_rate,
                        "impact_percent": failure_rate,
                    })

        # Sort by impact
        bottlenecks.sort(key=lambda x: x["impact_percent"], reverse=True)

        logger.debug(f"[analytics] Found {len(bottlenecks)} bottlenecks")
        return bottlenecks

    def get_role_performance(self, role: str) -> Dict:
        """Get performance metrics for a role.

        Args:
            role: Role name (dev, qa, architect, ba, po)

        Returns:
            Dict: {success_rate, avg_duration, error_distribution, count}
        """
        executions = []
        durations = []
        errors = defaultdict(int)

        for execution in self.executions:
            role_executions = [
                e for e in execution.get("executions", [])
                if e.get("tool", "").lower().startswith(f"run_{role}")
            ]

            for role_exec in role_executions:
                executions.append(role_exec)
                if role_exec.get("status") in ["ok", "success"]:
                    pass  # Counted as success

                duration = role_exec.get("duration")
                if duration:
                    durations.append(duration)

                error = role_exec.get("error")
                if error:
                    errors[error] += 1

        success_count = sum(
            1 for e in executions
            if e.get("status") in ["ok", "success"]
        )
        success_rate = (
            success_count / len(executions)
            if executions else 0
        )
        avg_duration = (
            sum(durations) / len(durations)
            if durations else 0
        )

        result = {
            "role": role,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "error_distribution": dict(errors),
            "count": len(executions),
        }

        logger.debug(
            f"[analytics] {role} performance: {success_rate:.0%} success, "
            f"{avg_duration:.1f}s avg"
        )

        return result

    def get_execution_timeline(self) -> List[Dict]:
        """Get chronological timeline of executions.

        Returns:
            List of: {timestamp, status, duration, success_rate, key_metrics}
        """
        timeline = []

        for execution in self.executions:
            timestamp = execution.get("timestamp", "unknown")
            status = execution.get("status", "unknown")
            duration = execution.get("duration", 0)

            # Calculate success rate
            executions = execution.get("executions", [])
            success_count = sum(
                1 for e in executions
                if e.get("status") in ["ok", "success"]
            )
            success_rate = (
                success_count / len(executions)
                if executions else 0
            )

            entry = {
                "timestamp": timestamp,
                "status": status,
                "duration": duration,
                "success_rate": success_rate,
                "execution_count": len(executions),
            }

            timeline.append(entry)

        logger.debug(f"[analytics] Timeline with {len(timeline)} entries")
        return timeline

    def predict_success_probability(self, story_metadata: Dict) -> float:
        """Predict success probability for story based on patterns.

        Args:
            story_metadata: {story_type, complexity, dependencies}

        Returns:
            Success probability (0.0-1.0)
        """
        story_type = story_metadata.get("story_type", "story")
        patterns = self.get_story_patterns()

        if story_type in patterns:
            base_probability = patterns[story_type]["success_rate"]
        else:
            # Use overall success rate as baseline
            all_rates = [p["success_rate"] for p in patterns.values()]
            base_probability = (
                sum(all_rates) / len(all_rates)
                if all_rates else 0.7
            )

        # Adjust based on complexity
        complexity = story_metadata.get("complexity", 0)  # 0-10
        complexity_factor = 1.0 - (complexity / 100.0)  # High complexity = lower prob

        # Adjust based on dependencies
        dependencies = len(story_metadata.get("dependencies", []))
        dep_factor = 1.0 - (min(dependencies, 5) / 25.0)  # More deps = lower prob

        probability = base_probability * complexity_factor * dep_factor
        probability = max(0.1, min(1.0, probability))  # Clamp 0.1-1.0

        logger.debug(
            f"[analytics] Predicted success probability: {probability:.0%} "
            f"(base={base_probability:.0%}, complexity={complexity_factor:.2f}, "
            f"deps={dep_factor:.2f})"
        )

        return probability

    def get_trend_analysis(self) -> Dict:
        """Analyze trends: improving, degrading, stable.

        Returns:
            Dict: {overall_trend, trend_direction, success_rate_change, duration_change}
        """
        if len(self.executions) < 2:
            return {
                "overall_trend": "insufficient_data",
                "trend_direction": "unknown",
                "success_rate_change": 0.0,
                "duration_change": 0.0,
            }

        # Compare first half vs second half
        mid = len(self.executions) // 2
        first_half = self.executions[:mid]
        second_half = self.executions[mid:]

        def calc_metrics(executions: List[Dict]) -> Tuple[float, float]:
            """Calculate success rate and avg duration."""
            all_execs = []
            all_durations = []

            for execution in executions:
                all_execs.extend(execution.get("executions", []))
                all_durations.append(execution.get("duration", 0))

            success_rate = sum(
                1 for e in all_execs
                if e.get("status") in ["ok", "success"]
            ) / len(all_execs) if all_execs else 0

            avg_duration = (
                sum(all_durations) / len(all_durations)
                if all_durations else 0
            )

            return success_rate, avg_duration

        first_sr, first_dur = calc_metrics(first_half)
        second_sr, second_dur = calc_metrics(second_half)

        sr_change = second_sr - first_sr
        dur_change = second_dur - first_dur

        # Determine trend
        if sr_change > 0.05:
            trend = "improving"
        elif sr_change < -0.05:
            trend = "degrading"
        else:
            trend = "stable"

        result = {
            "overall_trend": trend,
            "trend_direction": "up" if sr_change > 0 else "down" if sr_change < 0 else "flat",
            "success_rate_change": sr_change,
            "duration_change": dur_change,
        }

        logger.debug(f"[analytics] Trend: {trend} (SR change: {sr_change:.0%})")
        return result

    def export_summary(self) -> Dict:
        """Export comprehensive analytics summary.

        Returns:
            Dict with all analytics data
        """
        return {
            "execution_count": len(self.executions),
            "story_patterns": self.get_story_patterns(),
            "bottlenecks": self.get_bottleneck_analysis(),
            "role_performance": {
                role: self.get_role_performance(role)
                for role in ["dev", "qa", "architect", "ba", "po"]
            },
            "timeline": self.get_execution_timeline(),
            "trend_analysis": self.get_trend_analysis(),
        }
