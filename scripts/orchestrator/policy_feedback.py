"""Policy feedback loop that adapts story priorities and escalations using learning artifacts."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

from .learning_store import LearningStore
from .state_machine import PipelineState

logger = logging.getLogger("policy_feedback")


class PolicyFeedback:
    """Simple feedback loop leveraging learning history."""

    def __init__(self, learning_store: LearningStore, config: Dict[str, Any]) -> None:
        self.learning_store = learning_store
        features = config.get("features") or {}
        policy_cfg = features.get("policy_feedback") or {}
        self.enabled = bool(policy_cfg.get("enabled", True))
        self.failure_threshold = int(policy_cfg.get("failure_threshold", 2))
        self.priority_boosts = {
            sid: int(value or 0)
            for sid, value in (policy_cfg.get("priority_boosts") or {}).items()
            if isinstance(value, int)
        }

    def plan_remediation(self, state: PipelineState) -> List[Dict]:
        """Return remediation actions if a failed story exceeds the threshold."""
        if not self.enabled:
            return []

        for story_id in state.stories_failed.keys():
            history = self.learning_store.get_recent_attempts(story_id, limit=self.failure_threshold + 1)
            failure_count = sum(
                1 for entry in history if entry.get("status") != "ok"
            )
            if failure_count >= self.failure_threshold:
                logger.info("[policy_feedback] Escalating story %s (failures=%s)", story_id, failure_count)
                return [
                    {
                        "tool": "RUN_ARCHITECT",
                        "arguments": {"story_id": story_id, "architect_mode": "refine_story"},
                        "reason": f"Story {story_id} failed {failure_count} times, escalate to architect",
                        "decision_method": "policy_feedback",
                        "rule": "PF1_ESCALATE_FAILURES",
                        "confidence": 1.0,
                    }
                ]
        return []

    def prioritize_ready_stories(self, ready_stories: Sequence[str]) -> List[str]:
        """Sort ready stories by their feedback score (higher failure = higher priority)."""
        if not self.enabled:
            return list(ready_stories)

        scored = []
        for story_id in ready_stories:
            errors = self.learning_store.get_error_summary(story_id)
            score = sum(errors.values())
            score += self.priority_boosts.get(story_id, 0)
            scored.append((score, story_id))

        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [story_id for _, story_id in scored]
