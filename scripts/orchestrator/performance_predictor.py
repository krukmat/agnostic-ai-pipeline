"""
Performance Predictor for execution time and resource usage estimation.

Predicts story duration and resource requirements based on:
- Story characteristics (complexity, dependencies, test count)
- Historical execution patterns
- Online learning from actual executions
"""

from typing import Dict, Optional, List
from pathlib import Path
import json
from logger import logger


class PerformancePredictor:
    """Predicts execution duration and resource usage for stories."""

    def __init__(self, history_dir: Optional[Path] = None):
        """Initialize predictor with optional history directory.

        Args:
            history_dir: Directory with execution history. Defaults to artifacts/iterations
        """
        self.history_dir = history_dir or Path("artifacts/iterations")
        self.execution_history: List[Dict] = []
        self.story_profiles: Dict[str, Dict] = {}  # story_id -> {duration, resources}
        self._load_history()
        logger.info(f"[predictor] Initialized, loaded {len(self.execution_history)} "
                    f"executions")

    def _load_history(self) -> None:
        """Load execution history from artifacts."""
        if not self.history_dir.exists():
            logger.debug(f"[predictor] History dir not found: {self.history_dir}")
            return

        try:
            for iteration_dir in self.history_dir.iterdir():
                if iteration_dir.is_dir():
                    summary_file = iteration_dir / "latest_orchestrator_summary.json"
                    if summary_file.exists():
                        try:
                            data = json.loads(summary_file.read_text())
                            self.execution_history.append(data)

                            # Build story profiles
                            executions = data.get("executions", [])
                            for execution in executions:
                                story_id = execution.get("story_id")
                                if story_id:
                                    if story_id not in self.story_profiles:
                                        self.story_profiles[story_id] = {
                                            "durations": [],
                                            "resources": []
                                        }
                                    duration = execution.get("duration", 0)
                                    if duration > 0:
                                        self.story_profiles[story_id]["durations"].append(
                                            duration
                                        )
                        except Exception as e:
                            logger.debug(
                                f"[predictor] Failed to load summary from "
                                f"{summary_file}: {e}"
                            )
        except Exception as e:
            logger.warning(f"[predictor] Failed to load history: {e}")

    def predict_duration(self, story_id: str, story_metadata: Optional[Dict] = None) -> float:
        """Predict story execution duration.

        Args:
            story_id: Story identifier
            story_metadata: Optional metadata {lines_of_code, dependencies, test_count}

        Returns:
            Predicted duration in seconds
        """
        # Check historical data
        if story_id in self.story_profiles:
            durations = self.story_profiles[story_id]["durations"]
            if durations:
                avg_duration = sum(durations) / len(durations)
                logger.debug(
                    f"[predictor] {story_id}: using historical avg "
                    f"({avg_duration:.1f}s from {len(durations)} samples)"
                )
                return avg_duration

        # Estimate based on complexity if metadata available
        if story_metadata:
            loc = story_metadata.get("lines_of_code", 100)
            deps = len(story_metadata.get("dependencies", []))
            tests = story_metadata.get("test_count", 5)

            # Simple estimation: base + complexity factors
            base_duration = 30.0
            loc_factor = (loc / 100.0) * 10.0  # 10s per 100 LOC
            dep_factor = deps * 5.0  # 5s per dependency
            test_factor = tests * 2.0  # 2s per test

            estimated = base_duration + loc_factor + dep_factor + test_factor
            logger.debug(
                f"[predictor] {story_id}: estimated {estimated:.1f}s based on "
                f"complexity (LOC={loc}, deps={deps}, tests={tests})"
            )
            return estimated

        # Default fallback
        logger.debug(f"[predictor] {story_id}: using default duration (60s)")
        return 60.0

    def predict_resource_usage(self, story_id: str) -> Dict:
        """Predict resource requirements for story.

        Returns:
            Dict with keys: memory_mb (int), cpu_percent (int), parallel_safe (bool)
        """
        # Check if story type allows parallelism
        is_parallel_safe = not any(
            marker in story_id.lower()
            for marker in ["db_migrate", "data_sync", "config"]
        )

        # Estimate memory usage
        if story_id in self.story_profiles:
            # Use 128-512 MB based on history
            memory_mb = 256
        else:
            memory_mb = 128  # Default

        # Estimate CPU usage
        duration = self.predict_duration(story_id)
        cpu_percent = max(25, min(75, int(500 / duration)))  # Inverse to duration

        result = {
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "parallel_safe": is_parallel_safe,
        }

        logger.debug(
            f"[predictor] {story_id}: resources {memory_mb}MB, "
            f"{cpu_percent}% CPU, parallel={is_parallel_safe}"
        )

        return result

    def train_on_execution(
        self, story_id: str, actual_duration: float, actual_resources: Optional[Dict] = None
    ) -> None:
        """Update model with actual execution data.

        Args:
            story_id: Story identifier
            actual_duration: Actual execution duration in seconds
            actual_resources: Optional actual resource usage {memory_mb, cpu_percent}
        """
        if story_id not in self.story_profiles:
            self.story_profiles[story_id] = {"durations": [], "resources": []}

        self.story_profiles[story_id]["durations"].append(actual_duration)
        if actual_resources:
            self.story_profiles[story_id]["resources"].append(actual_resources)

        logger.info(
            f"[predictor] Trained {story_id}: actual={actual_duration:.1f}s, "
            f"samples={len(self.story_profiles[story_id]['durations'])}"
        )

    def get_confidence_score(self, story_id: str) -> float:
        """Get confidence score for prediction.

        Based on number of training samples:
        - <5 samples: 0.3 (low)
        - 5-20 samples: 0.6 (medium)
        - 20+ samples: 0.9 (high)

        Args:
            story_id: Story identifier

        Returns:
            Confidence score (0.0-1.0)
        """
        if story_id not in self.story_profiles:
            return 0.1  # Very low confidence

        samples = len(self.story_profiles[story_id]["durations"])

        if samples < 5:
            confidence = 0.1 + (samples * 0.04)  # 0.1-0.3
        elif samples < 20:
            confidence = 0.3 + ((samples - 5) / 15.0) * 0.3  # 0.3-0.6
        else:
            confidence = 0.6 + (min(samples - 20, 30) / 30.0) * 0.3  # 0.6-0.9

        logger.debug(
            f"[predictor] {story_id}: confidence={confidence:.2f} "
            f"({samples} samples)"
        )

        return confidence

    def predict_batch_duration(self, story_ids: List[str]) -> float:
        """Predict total duration for batch of stories.

        Assumes sequential execution (sum of durations).

        Args:
            story_ids: List of story identifiers

        Returns:
            Predicted total duration in seconds
        """
        total = sum(self.predict_duration(sid) for sid in story_ids)
        logger.debug(
            f"[predictor] Batch ({len(story_ids)} stories): "
            f"total duration {total:.1f}s"
        )
        return total

    def get_optimal_batch_size(self, parallelism: int, available_memory_mb: int) -> int:
        """Recommend safe batch size given parallelism and memory.

        Args:
            parallelism: Number of parallel stories
            available_memory_mb: Available system memory

        Returns:
            Safe batch size
        """
        # Estimate memory per parallel execution
        per_story_memory = 128  # Base
        safe_batch = min(
            parallelism,
            max(1, available_memory_mb // (per_story_memory * 2))
        )

        logger.debug(
            f"[predictor] Safe batch size: {safe_batch} "
            f"(parallelism={parallelism}, mem={available_memory_mb}MB)"
        )

        return safe_batch
