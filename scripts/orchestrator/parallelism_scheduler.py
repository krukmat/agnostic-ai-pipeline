"""
Intelligent Parallelism Scheduler for adaptive parallel execution.

Dynamically adjusts parallelism based on:
- Real-time system resource availability (CPU, memory, I/O)
- Execution error rates
- Story resource requirements
"""

from typing import Dict, Optional, List
import psutil
from logger import logger


class ParallelismScheduler:
    """Manages adaptive parallelism based on system resources."""

    def __init__(
        self,
        min_parallelism: int = 1,
        max_parallelism: int = 10,
        stress_threshold: float = 0.8,
    ):
        """Initialize parallelism scheduler.

        Args:
            min_parallelism: Minimum stories to run in parallel
            max_parallelism: Maximum stories to run in parallel
            stress_threshold: System stress threshold (0.0-1.0)
        """
        self.min_parallelism = min_parallelism
        self.max_parallelism = max_parallelism
        self.stress_threshold = stress_threshold
        self.current_parallelism = min(max_parallelism, 3)  # Default: 3
        self.error_rate = 0.0
        self.recent_errors = 0
        self.recent_successes = 0
        logger.info(
            f"[scheduler] Initialized: min={min_parallelism}, "
            f"max={max_parallelism}, stress={stress_threshold}"
        )

    def get_system_metrics(self) -> Dict:
        """Get current system resource metrics.

        Returns:
            Dict: {cpu_percent, memory_percent, io_percent, disk_percent}
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk I/O (estimated from disk usage)
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            # CPU context switches as proxy for I/O
            try:
                cpu_count = psutil.cpu_count() or 1
            except Exception:
                cpu_count = 1
            io_percent = min(100, cpu_count * 10)  # Simplified

            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "io_percent": io_percent,
                "disk_percent": disk_percent,
            }

            logger.debug(
                f"[scheduler] System: CPU={cpu_percent:.0f}%, "
                f"MEM={memory_percent:.0f}%, DISK={disk_percent:.0f}%"
            )

            return metrics
        except Exception as e:
            logger.warning(f"[scheduler] Failed to get metrics: {e}")
            return {
                "cpu_percent": 50.0,
                "memory_percent": 50.0,
                "io_percent": 50.0,
                "disk_percent": 50.0,
            }

    def get_stress_level(self) -> float:
        """Calculate overall system stress level (0.0-1.0).

        Returns:
            Stress level: 0.0 (no stress) to 1.0 (critical stress)
        """
        metrics = self.get_system_metrics()

        # Weighted average of metrics
        stress = (
            metrics["cpu_percent"] * 0.4 +
            metrics["memory_percent"] * 0.4 +
            metrics["disk_percent"] * 0.2
        ) / 100.0

        logger.debug(f"[scheduler] Stress level: {stress:.2f}")
        return stress

    def should_throttle(self) -> bool:
        """Check if system is under stress and should throttle.

        Returns:
            True if system stress > threshold
        """
        stress = self.get_stress_level()
        should_throttle = stress > self.stress_threshold

        if should_throttle:
            logger.warning(
                f"[scheduler] Throttling enabled (stress={stress:.2f} > "
                f"{self.stress_threshold})"
            )

        return should_throttle

    def get_safe_parallelism(self) -> int:
        """Get safe parallelism level based on current resources.

        Returns:
            Safe number of parallel stories
        """
        metrics = self.get_system_metrics()
        stress = self.get_stress_level()

        # Base parallelism from available memory
        available_memory_percent = 100 - metrics["memory_percent"]
        memory_based = max(1, int(available_memory_percent / 15))  # 15% per story

        # CPU-based parallelism
        cpu_percent = metrics["cpu_percent"]
        cpu_based = max(1, int((100 - cpu_percent) / 20))  # 20% per story

        # Base recommendation
        base_parallelism = min(memory_based, cpu_based, self.max_parallelism)

        # Adjust for stress
        if stress > self.stress_threshold:
            # Under stress: reduce parallelism
            safe_parallelism = max(self.min_parallelism, base_parallelism // 2)
        elif stress < 0.5:
            # Low stress: increase parallelism
            safe_parallelism = min(self.max_parallelism, base_parallelism * 2)
        else:
            # Normal: use base
            safe_parallelism = base_parallelism

        safe_parallelism = max(
            self.min_parallelism,
            min(self.max_parallelism, safe_parallelism)
        )

        logger.info(
            f"[scheduler] Safe parallelism: {safe_parallelism} "
            f"(base={base_parallelism}, stress={stress:.2f})"
        )

        return safe_parallelism

    def estimate_parallelism_for_batch(self, story_ids: List[str]) -> int:
        """Estimate safe parallelism for specific batch.

        Considers story resource requirements.

        Args:
            story_ids: List of story IDs to execute

        Returns:
            Safe parallelism for this batch
        """
        base_safe = self.get_safe_parallelism()

        # Reduce if batch contains resource-intensive stories
        # Stories with "db_" prefix are typically heavier
        heavy_stories = sum(1 for sid in story_ids if "db_" in sid.lower())

        if heavy_stories > 0:
            # Heavy stories: reduce parallelism
            reduction_factor = 0.5 + (heavy_stories / len(story_ids)) * 0.5
            parallelism = max(1, int(base_safe * reduction_factor))
        else:
            parallelism = base_safe

        logger.debug(
            f"[scheduler] Batch parallelism: {parallelism} "
            f"({len(story_ids)} stories, {heavy_stories} heavy)"
        )

        return parallelism

    def adaptive_parallelism_step(self) -> int:
        """Gradually adjust parallelism based on error rates.

        Returns:
            Recommended parallelism (may differ from current)
        """
        # Calculate error rate
        total = self.recent_errors + self.recent_successes
        if total > 0:
            self.error_rate = self.recent_errors / total
        else:
            self.error_rate = 0.0

        logger.debug(
            f"[scheduler] Error rate: {self.error_rate:.0%} "
            f"(errors={self.recent_errors}, successes={self.recent_successes})"
        )

        # Adjust based on error rate
        if self.error_rate > 0.3:
            # High error rate: reduce parallelism
            new_parallelism = max(
                self.min_parallelism,
                self.current_parallelism - 1
            )
            logger.warning(
                f"[scheduler] Error rate high ({self.error_rate:.0%}): "
                f"reducing parallelism {self.current_parallelism} → {new_parallelism}"
            )
        elif self.error_rate < 0.05:
            # Low error rate: increase parallelism
            new_parallelism = min(
                self.max_parallelism,
                self.current_parallelism + 1
            )
            logger.info(
                f"[scheduler] Error rate low ({self.error_rate:.0%}): "
                f"increasing parallelism {self.current_parallelism} → {new_parallelism}"
            )
        else:
            # Normal: keep current
            new_parallelism = self.current_parallelism

        # Clamp to safe range
        safe = self.get_safe_parallelism()
        new_parallelism = min(new_parallelism, safe)

        self.current_parallelism = new_parallelism

        # Reset counters
        self.recent_errors = 0
        self.recent_successes = 0

        return new_parallelism

    def record_execution(self, success: bool) -> None:
        """Record execution result for learning.

        Args:
            success: True if execution succeeded
        """
        if success:
            self.recent_successes += 1
        else:
            self.recent_errors += 1

        logger.debug(
            f"[scheduler] Recorded execution: "
            f"successes={self.recent_successes}, errors={self.recent_errors}"
        )

    def get_resource_quota_per_story(self) -> Dict:
        """Get resource quota for each parallel story.

        Returns:
            Dict: {memory_mb, cpu_percent, io_limit}
        """
        metrics = self.get_system_metrics()

        # Available resources
        available_memory = 100 - metrics["memory_percent"]
        available_cpu = 100 - metrics["cpu_percent"]

        # Per-story quota
        safe = self.get_safe_parallelism()
        memory_per_story = int((available_memory / 100) * 1000 / safe)  # in MB
        cpu_per_story = int(available_cpu / safe)

        quota = {
            "memory_mb": max(128, memory_per_story),
            "cpu_percent": max(10, cpu_per_story),
            "io_limit": "high",
        }

        logger.debug(
            f"[scheduler] Per-story quota: {quota['memory_mb']}MB, "
            f"{quota['cpu_percent']}% CPU"
        )

        return quota

    def get_scheduler_status(self) -> Dict:
        """Get current scheduler status.

        Returns:
            Dict with status information
        """
        return {
            "current_parallelism": self.current_parallelism,
            "safe_parallelism": self.get_safe_parallelism(),
            "stress_level": self.get_stress_level(),
            "error_rate": self.error_rate,
            "system_metrics": self.get_system_metrics(),
        }
