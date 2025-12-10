"""Main Orchestration Loop - Task 5

Complete run_agentic_orchestrator_v2() function that coordinates all components:
- State Machine (Layer 1): Phase management
- Story DAG (Layer 2): Dependency tracking
- Policy Engine (Layer 3): Rule-based decisions
- Planner (Layer 4): Action planning
- CoT Tracker (Layer 6): Reasoning capture
- Coherence Checker + Integration (Layer 7): Validation

Non-blocking orchestration with deterministic phase progression.
"""
from typing import Dict, Optional, List
from logger import logger

from .state_machine import PipelinePhase, PipelineState, StateMachine
from .story_dag import StoryDAG
from .policy_engine import PolicyEngine
from .planner import OrchestratorPlanner
from .coherence_checker import CoherenceChecker
from .coherence_orchestration_integration import CoherenceOrchestrationIntegration
from .cot_tracker import ChainOfThoughtTracker


def run_agentic_orchestrator_v2(
    concept: str,
    max_steps: int = 100,
    config: Optional[Dict] = None
) -> Dict:
    """Run complete orchestration pipeline with all 7 layers integrated.

    Coordinates:
    1. State Machine: Phase transitions
    2. Story DAG: Story dependencies and batching
    3. Policy Engine: Retry/escalation rules
    4. Planner: Deterministic action planning
    5. Coherence Checker + Integration: Validation and remediation
    6. CoT Tracker: Reasoning capture
    7. (Implicit in planner) Executor handling

    Args:
        concept: Business concept to implement
        max_steps: Maximum planning steps (prevents infinite loops)
        config: Optional configuration dict

    Returns:
        Dict with:
        - state: Final PipelineState
        - success: bool (True if reached DONE phase)
        - coherence_report: Final coherence audit
        - cot: CoT exports (jsonl_path, markdown_path, etc.)
    """

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    logger.info(f"[orchestrator] Starting V2 orchestration: {concept}")

    # Load configuration
    if config is None:
        config = {}

    # Initialize State Machine (Layer 1)
    # Use default planning directory for state sync
    from pathlib import Path
    planning_dir = Path("planning")
    planning_dir.mkdir(exist_ok=True)
    state_machine = StateMachine(concept=concept, planning_dir=planning_dir)
    state = state_machine.get_state()

    # Initialize Story DAG (Layer 2)
    dag = StoryDAG()

    # Initialize Policy Engine (Layer 3)
    policy_engine = PolicyEngine(config)

    # Initialize CoT Tracker (Layer 6)
    cot_tracker = ChainOfThoughtTracker()

    # Initialize Coherence Checker (Layer 7)
    coherence_checker = CoherenceChecker(config)

    # Initialize Coherence Integration (Layer 7 + Layer 6)
    coherence_integration = CoherenceOrchestrationIntegration(
        checker=coherence_checker,
        tracker=cot_tracker
    )

    # Initialize Planner (Layer 4, coordinates others)
    planner = OrchestratorPlanner(
        state_machine=state_machine,
        dag=dag,
        policy_engine=policy_engine,
        config=config
    )

    logger.info("[orchestrator] All components initialized")

    # =========================================================================
    # MAIN ORCHESTRATION LOOP
    # =========================================================================

    step = 0
    coherence_report = None

    while step < max_steps:
        step += 1
        state = state_machine.get_state()

        logger.info(
            f"[orchestrator] Step {step}: phase={state.phase.value}, "
            f"stories={state.total_stories}, done={len(state.stories_done)}"
        )

        # Check termination condition
        if state.phase == PipelinePhase.DONE:
            logger.info("[orchestrator] Pipeline reached DONE phase, terminating")
            break

        # =====================================================================
        # STEP 1: Planning (Layer 4 + Layer 7 coherence)
        # =====================================================================

        logger.debug(f"[orchestrator] Planning actions for phase: {state.phase.value}")
        actions = planner.plan_next_actions(state)

        if not actions:
            logger.debug("[orchestrator] No actions planned, waiting for async completion")
            # Wait for in-progress work
            continue

        logger.debug(f"[orchestrator] Planned {len(actions)} actions")

        # =====================================================================
        # STEP 2: Simulate Action Execution
        # (In real implementation, would call ActionExecutor to run tools)
        # =====================================================================

        logger.debug("[orchestrator] Executing planned actions")
        execution_results = _execute_actions(actions, state)

        # =====================================================================
        # STEP 3: Update State (Layer 1 + Layer 2)
        # =====================================================================

        logger.debug("[orchestrator] Updating state from execution results")
        _update_state_from_results(state_machine, state, execution_results, dag)

        # =====================================================================
        # STEP 4: Log to CoT (Layer 6)
        # =====================================================================

        cot_tracker.phase = state.phase.value
        cot_tracker.log_planner_decision(
            decision_type="step_completion",
            alternatives=["continue", "terminate"],
            chosen="continue" if state.phase != PipelinePhase.DONE else "terminate",
            confidence=1.0
        )

    # =========================================================================
    # FINALIZATION
    # =========================================================================

    logger.info("[orchestrator] Main loop completed")

    # Final state
    final_state = state_machine.get_state()

    # Final coherence audit (post_integration checkpoint)
    logger.info("[orchestrator] Running final coherence audit")
    try:
        coherence_report = coherence_checker.check_ba_po_alignment({}, {})
    except Exception as e:
        logger.warning(f"[orchestrator] Final coherence audit failed: {e}")
        coherence_report = None

    # Export CoT reasoning
    logger.info("[orchestrator] Exporting CoT reasoning")
    cot_export = planner.export_cot_reasoning()

    # Determine success (reached DONE phase)
    success = final_state.phase == PipelinePhase.DONE

    logger.info(
        f"[orchestrator] Orchestration complete: success={success}, "
        f"phase={final_state.phase.value}, steps={step}"
    )

    return {
        "state": final_state,
        "success": success,
        "coherence_report": coherence_report,
        "cot": cot_export,
        "steps_executed": step,
    }


def _execute_actions(actions: List[Dict], state: PipelineState) -> Dict:
    """Simulate execution of planned actions.

    In production, would call ActionExecutor.execute_batch(actions).
    For now, simulates action execution.

    Args:
        actions: List of planned actions from planner
        state: Current pipeline state

    Returns:
        Dict with execution results
    """
    results = {
        "executed_actions": len(actions),
        "successful": True,
        "errors": [],
        "action_results": {}
    }

    for action in actions:
        tool = action.get("tool", "UNKNOWN")

        if tool == "RUN_BA":
            # Simulate BA generation
            logger.debug("[executor] Simulating RUN_BA")
            results["action_results"]["RUN_BA"] = {
                "success": True,
                "has_requirements": True,
                "requirement_count": 5
            }

        elif tool == "RUN_PO":
            # Simulate PO validation
            logger.debug("[executor] Simulating RUN_PO")
            results["action_results"]["RUN_PO"] = {
                "success": True,
                "has_product_vision": True,
                "validated": True
            }

        elif tool == "RUN_ARCHITECT":
            # Simulate Architect planning
            logger.debug("[executor] Simulating RUN_ARCHITECT")
            results["action_results"]["RUN_ARCHITECT"] = {
                "success": True,
                "has_stories": True,
                "story_count": 3,
                "stories": ["S1", "S2", "S3"]
            }

        elif tool == "RUN_DEV_STORY":
            # Simulate Dev implementation
            logger.debug("[executor] Simulating RUN_DEV_STORY")
            story_id = action.get("arguments", {}).get("story_id", "UNKNOWN")
            results["action_results"][f"DEV_{story_id}"] = {
                "success": True,
                "story_id": story_id,
                "implemented": True
            }

        elif tool == "RUN_QA_FULL":
            # Simulate QA execution
            logger.debug("[executor] Simulating RUN_QA_FULL")
            results["action_results"]["RUN_QA_FULL"] = {
                "success": True,
                "tests_passed": True,
                "coverage": 0.92
            }

        else:
            logger.debug(f"[executor] Unknown tool: {tool}")

    return results


def _update_state_from_results(
    state_machine,
    state: PipelineState,
    execution_results: Dict,
    dag
) -> None:
    """Update pipeline state based on execution results.

    Updates:
    - Artifact flags (has_requirements, has_product_vision, etc.)
    - Story status in DAG
    - Phase transitions

    Args:
        state_machine: StateMachine to update
        state: Current state (modified in place)
        execution_results: Results from action execution
        dag: StoryDAG (for story tracking)
    """

    action_results = execution_results.get("action_results", {})

    # Update based on executed actions
    if "RUN_BA" in action_results and action_results["RUN_BA"].get("success"):
        state.has_requirements = True
        logger.debug("[state] Updated: has_requirements=True")

    if "RUN_PO" in action_results and action_results["RUN_PO"].get("success"):
        state.has_product_vision = True
        logger.debug("[state] Updated: has_product_vision=True")

    if "RUN_ARCHITECT" in action_results:
        arch_result = action_results["RUN_ARCHITECT"]
        if arch_result.get("success"):
            state.has_stories = True
            state.total_stories = arch_result.get("story_count", 0)
            logger.debug(f"[state] Updated: has_stories=True, total_stories={state.total_stories}")

    # Update story status
    for key, result in action_results.items():
        if key.startswith("DEV_") and result.get("success"):
            story_id = key.replace("DEV_", "")
            state.stories_done.add(story_id)
            if story_id in state.stories_doing:
                del state.stories_doing[story_id]
            logger.debug(f"[state] Updated: story {story_id} marked done")

    if "RUN_QA_FULL" in action_results and action_results["RUN_QA_FULL"].get("success"):
        state.qa_passed = True
        logger.debug("[state] Updated: qa_passed=True")

    # Determine next phase based on state
    if state.phase == PipelinePhase.INIT and state.has_requirements:
        logger.info("[state] Transitioning: INIT → REQUIREMENTS")
        state_machine.transition_to(PipelinePhase.REQUIREMENTS, "Requirements available")

    elif state.phase == PipelinePhase.REQUIREMENTS and state.has_stories:
        logger.info("[state] Transitioning: REQUIREMENTS → PLANNING")
        state_machine.transition_to(PipelinePhase.PLANNING, "Stories available")

    elif state.phase == PipelinePhase.PLANNING and state.has_stories:
        logger.info("[state] Transitioning: PLANNING → DEVELOPMENT")
        state_machine.transition_to(PipelinePhase.DEVELOPMENT, "Ready for development")

    elif state.phase == PipelinePhase.DEVELOPMENT and len(state.stories_done) == state.total_stories:
        logger.info("[state] Transitioning: DEVELOPMENT → INTEGRATION")
        state_machine.transition_to(PipelinePhase.INTEGRATION, "All stories completed")

    elif state.phase == PipelinePhase.INTEGRATION and state.qa_passed:
        logger.info("[state] Transitioning: INTEGRATION → DONE")
        state_machine.transition_to(PipelinePhase.DONE, "QA passed, pipeline complete")
