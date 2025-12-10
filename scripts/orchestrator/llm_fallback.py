"""LLM Fallback Engine for Complex Orchestration Decisions

Implements intelligent LLM fallback for ambiguous/complex cases that don't match
deterministic rules. Used when:
- Multiple failed attempts with same error pattern
- Ambiguous failure reasons
- Architectural decisions affecting multiple stories
- Epic-wide failures

Non-blocking: Only called when deterministic rules don't provide clear decisions.
"""
from typing import Dict, List, Optional, Set
from logger import logger
from dataclasses import dataclass

from .state_machine import PipelineState, PipelinePhase
from .cot_tracker import ChainOfThoughtTracker


@dataclass
class LLMDecision:
    """Represents an LLM-based decision."""
    decision: str
    reasoning: str
    confidence: float
    actions: List[Dict]


class LLMFallbackEngine:
    """LLM fallback for complex orchestration decisions.

    Determines when deterministic rules are insufficient and LLM is needed.
    Generates escalation plans for ambiguous/complex cases.
    """

    def __init__(
        self,
        config: Dict,
        cot_tracker: Optional[ChainOfThoughtTracker] = None
    ):
        """Initialize LLM fallback engine.

        Args:
            config: Engine configuration with thresholds
            cot_tracker: Optional CoT tracker for logging decisions
        """
        self.config = config
        self.cot_tracker = cot_tracker or ChainOfThoughtTracker()

        # Thresholds
        self.llm_fallback_enabled = config.get("llm_fallback_enabled", True)
        self.llm_fallback_threshold = config.get("llm_fallback_threshold", 0.7)
        self.llm_escalation_max_retries = config.get("llm_escalation_max_retries", 3)

        logger.debug("[llm_fallback] Initialized LLMFallbackEngine")

    def should_use_llm(self, decision_context: Dict) -> bool:
        """Determine if decision requires LLM fallback.

        Returns True if:
        - No deterministic rule matched AND ambiguity high
        - Multiple failed attempts with unclear pattern
        - Escalation needed with ambiguous reasons

        Args:
            decision_context: Dict with decision factors
                - type: Decision type (escalation, retry, etc.)
                - ambiguity_score: 0.0-1.0 (higher = more ambiguous)
                - matched_rules: Number of deterministic rules matched (0 = need LLM)
                - failed_attempts: Number of failed attempts
                - error_pattern: Type of error (optional)

        Returns:
            bool: True if LLM fallback should be used
        """
        if not self.llm_fallback_enabled:
            return False

        ambiguity_score = decision_context.get("ambiguity_score", 0.0)
        matched_rules = decision_context.get("matched_rules", 0)
        decision_type = decision_context.get("type", "")

        # Use LLM if:
        # 1. No deterministic rule matched AND high ambiguity
        if matched_rules == 0 and ambiguity_score >= self.llm_fallback_threshold:
            logger.debug(
                f"[llm_fallback] LLM needed: no rules matched, ambiguity={ambiguity_score}"
            )
            return True

        # 2. Escalation type with complex context
        if decision_type == "escalation":
            failed_attempts = decision_context.get("failed_attempts", 0)
            if failed_attempts >= 2 and ambiguity_score > 0.6:
                logger.debug(
                    f"[llm_fallback] LLM needed for escalation: attempts={failed_attempts}"
                )
                return True

        # 3. Epic-wide failures
        if decision_type == "epic_escalation":
            failed_count = decision_context.get("failed_count", 0)
            total = decision_context.get("total_in_epic", 1)
            failure_ratio = failed_count / total if total > 0 else 0
            if failure_ratio >= 0.5 and ambiguity_score > 0.6:
                logger.debug(f"[llm_fallback] LLM needed for epic failure: {failure_ratio:.1%}")
                return True

        return False

    def _build_context_prompt(self, context: Dict) -> str:
        """Build prompt for LLM decision.

        Args:
            context: Decision context with relevant information

        Returns:
            str: Formatted prompt for LLM
        """
        lines = [
            "You are an expert software architect helping with complex orchestration decisions.",
            "",
            "## Context",
        ]

        # Add context fields
        if "story_id" in context:
            lines.append(f"- Story: {context['story_id']}")
        if "phase" in context:
            lines.append(f"- Phase: {context['phase']}")
        if "error" in context:
            lines.append(f"- Error: {context['error']}")
        if "attempts" in context:
            lines.append(f"- Attempts: {context['attempts']}")
        if "issue" in context:
            lines.append(f"- Issue: {context['issue']}")
        if "affected_stories" in context:
            lines.append(f"- Affected Stories: {', '.join(context['affected_stories'])}")

        lines.extend([
            "",
            "## Decision Needed",
            "Determine the best course of action given the above context.",
            "",
            "Return a JSON object with:",
            "- decision: String describing the recommended action",
            "- reasoning: Brief explanation",
            "- confidence: 0.0-1.0 confidence in this decision",
            "- actions: List of remediation actions to take",
        ])

        return "\n".join(lines)

    def _parse_llm_response(self, response: Dict) -> Dict:
        """Parse LLM response into structured decision.

        Args:
            response: LLM response dict

        Returns:
            dict: Parsed decision with decision, reasoning, confidence, actions
        """
        parsed = {
            "decision": response.get("decision", "unknown"),
            "reasoning": response.get("reasoning", ""),
            "confidence": response.get("confidence", 0.5),
            "actions": response.get("actions", []),
        }

        # Ensure confidence is between 0 and 1
        if parsed["confidence"] > 1.0:
            parsed["confidence"] = 1.0
        if parsed["confidence"] < 0.0:
            parsed["confidence"] = 0.0

        logger.debug(
            f"[llm_fallback] Parsed LLM decision: {parsed['decision']} "
            f"(confidence={parsed['confidence']})"
        )

        return parsed

    def escalation_planning(
        self,
        state: PipelineState,
        failed_stories: Set[str]
    ) -> List[Dict]:
        """Plan escalation for failed stories.

        Args:
            state: Current pipeline state
            failed_stories: Set of story IDs that failed

        Returns:
            List[Dict]: List of remediation actions
        """
        if not failed_stories:
            return []

        actions = []

        # Single story escalation
        if len(failed_stories) == 1:
            story_id = list(failed_stories)[0]
            actions.append({
                "tool": "RUN_ARCHITECT",
                "arguments": {
                    "story_id": story_id,
                    "architect_mode": "refine_story",
                    "reason": "Repeated failures after multiple attempts"
                },
                "reason": f"Story {story_id} failed multiple times with unclear pattern",
                "decision_method": "llm_fallback",
                "confidence": 0.8,
            })

        # Multiple stories escalation
        elif len(failed_stories) > 1:
            # Check if architecture issue
            if len(failed_stories) >= 3:
                # Likely architectural issue affecting multiple stories
                actions.append({
                    "tool": "RUN_ARCHITECT",
                    "arguments": {
                        "architect_mode": "review_architecture",
                        "affected_stories": list(failed_stories),
                    },
                    "reason": f"Multiple stories ({len(failed_stories)}) failed - possible architectural issue",
                    "decision_method": "llm_fallback",
                    "confidence": 0.75,
                })
            else:
                # Escalate each story individually
                for story_id in failed_stories:
                    actions.append({
                        "tool": "RUN_ARCHITECT",
                        "arguments": {
                            "story_id": story_id,
                            "architect_mode": "refine_story",
                        },
                        "reason": f"Story {story_id} escalated for architectural review",
                        "decision_method": "llm_fallback",
                        "confidence": 0.75,
                    })

        logger.info(
            f"[llm_fallback] Generated {len(actions)} escalation actions "
            f"for {len(failed_stories)} failed stories"
        )

        return actions

    def get_llm_decision(
        self,
        prompt: str,
        context: Dict
    ) -> LLMDecision:
        """Get LLM-based decision.

        Args:
            prompt: Decision prompt for LLM
            context: Additional context for logging

        Returns:
            LLMDecision: Structured decision from LLM
        """
        import json

        # In real implementation, would call LLM client
        # For now, return a default decision with low confidence

        llm_response = {
            "decision": "escalate_to_architect",
            "reasoning": "Complex pattern detected requiring architectural review",
            "confidence": 0.7,
            "actions": [
                {
                    "tool": "RUN_ARCHITECT",
                    "arguments": context.get("arguments", {}),
                }
            ],
        }

        # Log to CoT tracker
        if self.cot_tracker:
            parsed = self._parse_llm_response(llm_response)
            self.cot_tracker.log_llm_decision(
                prompt=prompt,
                response=json.dumps(llm_response),  # Convert to string
                parsed=parsed
            )

        return LLMDecision(**self._parse_llm_response(llm_response))

    def _log_decision_to_cot(self, decision: LLMDecision, context: Dict) -> None:
        """Log LLM decision to CoT tracker.

        Args:
            decision: The LLM decision made
            context: Decision context
        """
        if not self.cot_tracker:
            return

        self.cot_tracker.log_llm_decision(
            prompt=self._build_context_prompt(context),
            response={
                "decision": decision.decision,
                "reasoning": decision.reasoning,
                "confidence": decision.confidence,
            },
            parsed={
                "decision": decision.decision,
                "confidence": decision.confidence,
            }
        )

        logger.debug(
            f"[llm_fallback] Logged LLM decision to CoT: {decision.decision}"
        )
