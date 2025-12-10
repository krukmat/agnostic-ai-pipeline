"""
Feedback Loop Integration for continuous improvement.

Collects feedback from:
- Agents (helpfulness, suggestions, errors)
- Users (ratings, comments)
- Executions (success/failure patterns)

Analyzes patterns and applies learned improvements.
"""

from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import json
from logger import logger


class FeedbackCollector:
    """Collects and analyzes feedback from agents and users."""

    def __init__(self, feedback_dir: Optional[Path] = None):
        """Initialize feedback collector.

        Args:
            feedback_dir: Directory for feedback storage. Defaults to artifacts/feedback
        """
        self.feedback_dir = feedback_dir or Path("artifacts/feedback")
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        self.feedback_entries: List[Dict] = []
        self.agent_feedback: Dict[str, List[Dict]] = defaultdict(list)
        self.user_feedback: List[Dict] = []
        self._load_feedback()
        logger.info(f"[feedback] Initialized: {len(self.feedback_entries)} entries")

    def _load_feedback(self) -> None:
        """Load existing feedback from disk."""
        try:
            feedback_file = self.feedback_dir / "all_feedback.json"
            if feedback_file.exists():
                data = json.loads(feedback_file.read_text())
                self.feedback_entries = data.get("entries", [])
                logger.debug(f"[feedback] Loaded {len(self.feedback_entries)} entries")
        except Exception as e:
            logger.warning(f"[feedback] Failed to load feedback: {e}")

    def record_agent_feedback(
        self,
        role: str,
        story_id: str,
        feedback: Dict,
    ) -> None:
        """Record feedback from an agent.

        Args:
            role: Agent role (ba, po, architect, dev, qa)
            story_id: Story identifier
            feedback: {helpful: bool, suggestions: [str], errors: [str]}
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "agent",
            "role": role,
            "story_id": story_id,
            "helpful": feedback.get("helpful", False),
            "suggestions": feedback.get("suggestions", []),
            "errors": feedback.get("errors", []),
        }

        self.feedback_entries.append(entry)
        self.agent_feedback[role].append(entry)
        self._save_feedback()

        logger.info(
            f"[feedback] Recorded {role} feedback for {story_id}: "
            f"helpful={entry['helpful']}"
        )

    def record_user_feedback(
        self,
        story_id: str,
        rating: int,
        comment: str = "",
    ) -> None:
        """Record user feedback on story implementation.

        Args:
            story_id: Story identifier
            rating: Rating 1-5 stars
            comment: Optional comment
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "user",
            "story_id": story_id,
            "rating": max(1, min(5, rating)),
            "comment": comment,
        }

        self.feedback_entries.append(entry)
        self.user_feedback.append(entry)
        self._save_feedback()

        logger.info(
            f"[feedback] Recorded user feedback for {story_id}: "
            f"rating={entry['rating']}/5"
        )

    def record_execution_feedback(
        self,
        story_id: str,
        success: bool,
        error_type: Optional[str] = None,
        duration: float = 0.0,
    ) -> None:
        """Record execution feedback.

        Args:
            story_id: Story identifier
            success: Execution success
            error_type: Type of error if failed
            duration: Execution duration in seconds
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "execution",
            "story_id": story_id,
            "success": success,
            "error_type": error_type,
            "duration": duration,
        }

        self.feedback_entries.append(entry)
        self._save_feedback()

        logger.debug(
            f"[feedback] Recorded execution feedback for {story_id}: "
            f"success={success}"
        )

    def analyze_feedback_patterns(self) -> Dict:
        """Analyze patterns in collected feedback.

        Returns:
            Dict: {common_errors: {error: count}, suggestions: [str], issues: [{...}]}
        """
        patterns = {
            "common_errors": defaultdict(int),
            "common_suggestions": defaultdict(int),
            "low_rating_stories": [],
            "high_error_stories": [],
            "high_failure_rates": {},
        }

        # Analyze agent feedback
        for entries in self.agent_feedback.values():
            for entry in entries:
                for error in entry.get("errors", []):
                    patterns["common_errors"][error] += 1

                for suggestion in entry.get("suggestions", []):
                    patterns["common_suggestions"][suggestion] += 1

        # Analyze user feedback
        low_ratings = [
            e for e in self.user_feedback
            if e.get("rating", 5) < 3
        ]
        patterns["low_rating_stories"] = [e["story_id"] for e in low_ratings]

        # Analyze execution feedback
        story_failures = defaultdict(int)
        story_totals = defaultdict(int)

        for entry in self.feedback_entries:
            if entry.get("type") == "execution":
                story_id = entry.get("story_id")
                story_totals[story_id] += 1
                if not entry.get("success"):
                    story_failures[story_id] += 1

        # High failure rate stories
        for story_id, total in story_totals.items():
            failure_rate = story_failures[story_id] / total
            if failure_rate > 0.3:
                patterns["high_failure_rates"][story_id] = failure_rate

        # Convert defaultdicts to regular dicts
        patterns["common_errors"] = dict(patterns["common_errors"])
        patterns["common_suggestions"] = dict(patterns["common_suggestions"])

        logger.debug(
            f"[feedback] Analyzed patterns: "
            f"{len(patterns['common_errors'])} error types, "
            f"{len(patterns['low_rating_stories'])} low-rated stories"
        )

        return patterns

    def suggest_improvements(self, context: Optional[Dict] = None) -> List[str]:
        """Generate improvement suggestions based on feedback.

        Args:
            context: Optional context (role, phase, etc.)

        Returns:
            List of actionable improvement suggestions
        """
        patterns = self.analyze_feedback_patterns()
        suggestions = []

        # Top errors
        if patterns["common_errors"]:
            top_error = max(patterns["common_errors"].items(), key=lambda x: x[1])
            suggestions.append(
                f"Address recurring error: '{top_error[0]}' ({top_error[1]} occurrences)"
            )

        # Low-rated stories
        if patterns["low_rating_stories"]:
            suggestions.append(
                f"Review implementation of low-rated stories: "
                f"{patterns['low_rating_stories'][:3]}"
            )

        # High failure stories
        if patterns["high_failure_rates"]:
            for story_id, rate in sorted(
                patterns["high_failure_rates"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]:
                suggestions.append(
                    f"Story {story_id} has {rate*100:.0f}% failure rate - "
                    f"investigate root cause"
                )

        # Common suggestions from agents
        if patterns["common_suggestions"]:
            top_suggestion = max(
                patterns["common_suggestions"].items(),
                key=lambda x: x[1]
            )
            suggestions.append(f"Agent feedback: {top_suggestion[0]}")

        logger.info(f"[feedback] Generated {len(suggestions)} improvement suggestions")
        return suggestions

    def apply_learned_rules(self) -> Dict:
        """Apply learned improvements to policies.

        Returns:
            Dict: {updated_policies: {policy: new_value}, changes: [str]}
        """
        patterns = self.analyze_feedback_patterns()
        changes = []
        updated_policies = {}

        # Policy: Increase retry limit for low-failure stories
        high_success_stories = []
        for story_id, failures in patterns["high_failure_rates"].items():
            if failures < 0.1:  # <10% failure
                high_success_stories.append(story_id)

        if high_success_stories:
            updated_policies["retry_limit_increase"] = True
            changes.append(
                f"Increase retry limit for stable stories: {high_success_stories[:3]}"
            )

        # Policy: Reduce parallelism if high error rate
        total_failures = len([
            e for e in self.feedback_entries
            if e.get("type") == "execution" and not e.get("success")
        ])
        total_executions = len([
            e for e in self.feedback_entries
            if e.get("type") == "execution"
        ])

        if total_executions > 0:
            overall_failure_rate = total_failures / total_executions
            if overall_failure_rate > 0.2:  # >20% failure
                updated_policies["parallelism_reduction"] = True
                changes.append(
                    f"Reduce parallelism (failure rate {overall_failure_rate*100:.0f}%)"
                )

        # Policy: Escalate problematic stories
        if patterns["high_failure_rates"]:
            updated_policies["auto_escalate"] = list(
                patterns["high_failure_rates"].keys()
            )[:5]
            changes.append(
                f"Auto-escalate high-failure stories to architect"
            )

        result = {
            "updated_policies": updated_policies,
            "changes": changes,
            "applied_at": datetime.now().isoformat(),
        }

        logger.info(f"[feedback] Applied {len(changes)} policy changes")
        return result

    def get_feedback_summary(self) -> Dict:
        """Get summary of all feedback collected.

        Returns:
            Dict with feedback statistics
        """
        agent_count = sum(len(v) for v in self.agent_feedback.values())
        user_count = len(self.user_feedback)
        execution_count = len([
            e for e in self.feedback_entries
            if e.get("type") == "execution"
        ])

        avg_user_rating = 0
        if self.user_feedback:
            avg_user_rating = sum(
                e.get("rating", 3) for e in self.user_feedback
            ) / len(self.user_feedback)

        return {
            "total_feedback_entries": len(self.feedback_entries),
            "agent_feedback_count": agent_count,
            "user_feedback_count": user_count,
            "execution_feedback_count": execution_count,
            "average_user_rating": avg_user_rating,
            "feedback_by_role": {
                role: len(entries)
                for role, entries in self.agent_feedback.items()
            },
        }

    def _save_feedback(self) -> None:
        """Save feedback to disk."""
        try:
            feedback_file = self.feedback_dir / "all_feedback.json"
            data = {
                "entries": self.feedback_entries,
                "last_saved": datetime.now().isoformat(),
            }
            feedback_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"[feedback] Saved {len(self.feedback_entries)} entries")
        except Exception as e:
            logger.warning(f"[feedback] Failed to save feedback: {e}")

    def export_feedback_report(self) -> Dict:
        """Export comprehensive feedback report.

        Returns:
            Dict with full feedback analysis
        """
        return {
            "summary": self.get_feedback_summary(),
            "patterns": self.analyze_feedback_patterns(),
            "improvements": self.suggest_improvements(),
            "applied_policies": self.apply_learned_rules(),
        }
