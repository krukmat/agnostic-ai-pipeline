"""
Rule-Based Planner for deterministic orchestration.

Makes decisions based on state machine, DAG, and policies (no LLM).
"""

from typing import List, Dict, Optional
from logger import logger
from pathlib import Path
import yaml
import json

from .state_machine import PipelinePhase, PipelineState, StateMachine
from .story_dag import StoryDAG
from .policy_engine import PolicyEngine
from .coherence_checker import CoherenceChecker


class OrchestratorPlanner:
    """
    Deterministic planner that decides next actions based on:
    - Current pipeline phase (state machine)
    - Story dependencies and priorities (DAG)
    - Retry/escalation policies (policy engine)
    """

    def __init__(self, state_machine: StateMachine, dag: StoryDAG, policy_engine: PolicyEngine, config: Dict):
        """Initialize planner."""
        self.state_machine = state_machine
        self.dag = dag
        self.policy_engine = policy_engine
        self.config = config
        self.coherence_checker = CoherenceChecker(config)
        logger.info("[planner] Initialized rule-based planner (no LLM)")

    def plan_next_actions(self, state: PipelineState) -> List[Dict]:
        """Decide what to execute next based on state. Returns list of actions."""
        logger.debug(f"[planner] Planning for phase: {state.phase.value}")

        # Phase-based planning
        if state.phase == PipelinePhase.INIT:
            return self._plan_init(state)
        elif state.phase == PipelinePhase.REQUIREMENTS:
            return self._plan_requirements(state)
        elif state.phase == PipelinePhase.PLANNING:
            return self._plan_planning(state)
        elif state.phase == PipelinePhase.DEVELOPMENT:
            return self._plan_development(state)
        elif state.phase == PipelinePhase.INTEGRATION:
            return self._plan_integration(state)
        elif state.phase == PipelinePhase.DONE:
            logger.info("[planner] Pipeline complete, no more actions")
            return []
        else:
            logger.error(f"[planner] Unknown phase: {state.phase.value}")
            return []

    def _plan_init(self, state: PipelineState) -> List[Dict]:
        """INIT phase: Check artifacts and start BA if needed."""
        # If requirements exist, transition to next phase (handled by state machine)
        if state.has_requirements:
            logger.info("[planner] Requirements exist, transitioning to REQUIREMENTS phase")
            return []

        # Start BA
        logger.info("[planner] No requirements found, starting BA")
        return [
            {
                "tool": "RUN_BA",
                "arguments": {"concept": state.concept},
                "reason": "Initial requirements generation",
                "decision_method": "rule_based",
                "rule": "R1_MISSING_REQUIREMENTS",
                "confidence": 1.0,
            }
        ]

    def _plan_requirements(self, state: PipelineState) -> List[Dict]:
        """REQUIREMENTS phase: BA → PO → Architect transition."""
        if not state.has_requirements:
            logger.debug("[planner] Waiting for BA requirements...")
            return []

        if not state.has_product_vision:
            return [
                {
                    "tool": "RUN_PO",
                    "arguments": {},
                    "reason": "Validate requirements before architecture",
                    "decision_method": "rule_based",
                    "rule": "R2_VALIDATE_REQUIREMENTS",
                    "confidence": 1.0,
                }
            ]

        if not state.has_stories:
            return [
                {
                    "tool": "RUN_ARCHITECT",
                    "arguments": {"concept": state.concept, "architect_mode": "initial_design"},
                    "reason": "Generate stories and architecture from requirements",
                    "decision_method": "rule_based",
                    "rule": "R3_GENERATE_STORIES",
                    "confidence": 1.0,
                }
            ]

        # Ready to transition to PLANNING
        self.state_machine.transition_to(PipelinePhase.PLANNING, "Requirements complete, ready for development planning")
        return self._plan_planning(state)

    def _plan_planning(self, state: PipelineState) -> List[Dict]:
        """PLANNING phase: Stories are available."""
        if not state.has_stories:
            logger.debug("[planner] Waiting for stories...")
            return []

        # Rebuild DAG from current state
        self._rebuild_dag_from_state(state)

        # Ready to transition to DEVELOPMENT
        self.state_machine.transition_to(PipelinePhase.DEVELOPMENT, "Architecture complete, ready for development")
        return self._plan_development(state)

    def _plan_development(self, state: PipelineState) -> List[Dict]:
        """DEVELOPMENT phase: Execute stories with DAG and policies."""
        actions = []

        # Get ready stories from DAG
        ready_stories = self.dag.get_ready_stories(
            done_stories=state.stories_done,
            failed_stories=set(state.stories_failed.keys()),
            doing_stories=set(state.stories_doing.keys()),
        )

        if not ready_stories:
            # No ready stories - check if we're done or blocked
            if len(state.stories_done) == state.total_stories:
                logger.info("[planner] All stories completed, transitioning to INTEGRATION")
                self.state_machine.transition_to(PipelinePhase.INTEGRATION, "All stories done, running full QA")
                return self._plan_integration(state)

            # Some stories blocked by failures
            blocked = self.dag.get_blocked_stories(set(state.stories_failed.keys()))
            if blocked:
                logger.warning(f"[planner] {len(blocked)} stories blocked by failures: {blocked}")
                # Return to PLANNING for architect refinement
                self.state_machine.transition_to(PipelinePhase.PLANNING, "Stories blocked by failures, need refinement")
                return []

            # Waiting for async completion
            logger.debug("[planner] Waiting for in-progress stories to complete...")
            return []

        # Get parallel batch
        max_parallel = self.policy_engine.get_max_parallel_stories()
        batch = self.dag.get_parallel_batch(ready_stories, max_parallelism=max_parallel)

        # Plan each story in batch
        for story_id in batch:
            # Check for escalation policies
            attempts = state.stories_doing.get(story_id, 0)
            error_history = state.stories_failed.get(story_id, [])
            escalation_action = self.policy_engine.evaluate_escalation(
                story_id=story_id,
                attempts=attempts,
                error_history=error_history,
                context={},
            )

            if escalation_action:
                logger.warning(f"[planner] Escalation for {story_id}: {escalation_action}")
                actions.append(
                    {
                        "tool": "RUN_ARCHITECT",
                        "arguments": {"story_id": story_id, "architect_mode": "refine_story"},
                        "reason": f"Story failed {attempts} times, needs refinement",
                        "decision_method": "rule_based",
                        "rule": "R6_ESCALATE_TO_ARCHITECT",
                        "confidence": 1.0,
                    }
                )
                continue

            # Check if retry is allowed
            if attempts > 0 and not self.policy_engine.should_retry("dev", attempts):
                logger.warning(f"[planner] Max retries exceeded for {story_id}")
                # Mark as failed (will be blocked)
                state.stories_failed[story_id].append("Max retries exceeded")
                continue

            # Normal dev execution
            actions.append(
                {
                    "tool": "RUN_DEV_STORY",
                    "arguments": {"story_id": story_id, "retries": attempts},
                    "reason": f"Implement story (attempt {attempts + 1})",
                    "decision_method": "rule_based",
                    "rule": "R4_IMPLEMENT_STORY",
                    "confidence": 1.0,
                }
            )

        return actions

    def _plan_integration(self, state: PipelineState) -> List[Dict]:
        """INTEGRATION phase: Run full QA."""
        if len(state.stories_done) == state.total_stories and not state.stories_failed:
            return [
                {
                    "tool": "RUN_QA_FULL",
                    "arguments": {},
                    "reason": "All stories completed, run full QA",
                    "decision_method": "rule_based",
                    "rule": "R7_FULL_QA",
                    "confidence": 1.0,
                }
            ]

        return []

    def _rebuild_dag_from_state(self, state: PipelineState) -> None:
        """Rebuild DAG from current state."""
        self.dag = StoryDAG()

        for story_id in range(1, state.total_stories + 1):
            sid = f"S{story_id}"
            metadata = {"priority": "P1"}  # Default, will be overridden by actual story data

            depends_on = state.story_dependencies.get(sid, [])
            self.dag.add_story(sid, metadata, depends_on)

        logger.debug(f"[planner] Rebuilt DAG with {state.total_stories} stories")

    def _check_and_log_coherence(self, state: PipelineState) -> None:
        """Check coherence after phase transitions and log issues non-blocking."""
        # Phase 2 Task 4: Coherence integration at key points
        coherence_issues = []

        # Check BA→PO alignment
        if state.phase == PipelinePhase.REQUIREMENTS:
            ba_output = self._load_artifact("planning/requirements.yaml")
            po_output = self._load_artifact("planning/product_owner_review.yaml")
            if ba_output and po_output:
                alignment = self.coherence_checker.check_ba_po_alignment(
                    ba_output, po_output
                )
                if not alignment["aligned"]:
                    logger.warning(
                        f"[coherence] BA→PO misalignment: {alignment['issues']}"
                    )
                    coherence_issues.append(
                        {"phase": "REQUIREMENTS", "check": "BA→PO", **alignment}
                    )

        # Check Arch→Stories alignment
        elif state.phase == PipelinePhase.PLANNING:
            arch_output = self._load_artifact("planning/architecture.yaml")
            stories_output = self._load_artifact("planning/stories.yaml")
            if arch_output and stories_output:
                alignment = self.coherence_checker.check_arch_stories_alignment(
                    arch_output, stories_output
                )
                if not alignment["aligned"]:
                    logger.warning(
                        f"[coherence] Arch→Stories misalignment: {alignment['issues']}"
                    )
                    coherence_issues.append(
                        {"phase": "PLANNING", "check": "Arch→Stories", **alignment}
                    )

        # Store coherence issues in state (can be retrieved later)
        if coherence_issues and not hasattr(state, "coherence_issues"):
            state.coherence_issues = []
        if hasattr(state, "coherence_issues"):
            state.coherence_issues.extend(coherence_issues)

    def _load_artifact(self, path: str) -> Optional[Dict]:
        """Load artifact from filesystem.

        Supports both .yaml and .json files.
        """
        artifact_path = Path(path)
        if artifact_path.exists():
            try:
                if path.endswith(".yaml") or path.endswith(".yml"):
                    with open(artifact_path) as f:
                        return yaml.safe_load(f)
                elif path.endswith(".json"):
                    with open(artifact_path) as f:
                        return json.load(f)
            except Exception as e:
                logger.debug(f"[planner] Failed to load artifact {path}: {e}")
        return None
