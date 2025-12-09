"""V2 Runtime - Main orchestration loop."""

import asyncio
from pathlib import Path
from typing import Dict
from logger import logger
from common import PLANNING, load_config

from .state_machine import StateMachine, PipelinePhase
from .story_dag import StoryDAG
from .policy_engine import PolicyEngine
from .planner import OrchestratorPlanner
from .executor import ActionExecutor


async def run_orchestrator_v2(
    concept: str,
    max_steps: int = 10,
    role_handlers: Dict = None,
) -> Dict:
    """Run V2 orchestrator with deterministic planning."""

    config = load_config()
    sm = StateMachine(concept, PLANNING)
    dag = StoryDAG()
    policy_engine = PolicyEngine(config)
    planner = OrchestratorPlanner(sm, dag, policy_engine, config)
    executor = ActionExecutor(role_handlers or {})

    logger.info(f"[v2_orchestrator] Starting: concept='{concept}'")

    steps = []
    for step_num in range(max_steps):
        state = sm.get_state()
        logger.info(f"[v2_orchestrator] Step {step_num + 1}: phase={state.phase.value}")

        # Plan next actions
        actions = planner.plan_next_actions(state)
        if not actions:
            logger.info("[v2_orchestrator] No actions planned, pipeline may be waiting or complete")
            if state.phase == PipelinePhase.DONE:
                break
            await asyncio.sleep(1)
            continue

        # Execute actions
        results = await executor.execute_actions(actions)

        # Update state
        sm.update_from_results(results)

        steps.append({
            "step": step_num + 1,
            "actions": actions,
            "results": results,
        })

        # Check termination
        if state.phase == PipelinePhase.DONE:
            logger.info("[v2_orchestrator] Pipeline complete")
            break

    logger.info(f"[v2_orchestrator] Completed {len(steps)} steps")
    return {
        "concept": concept,
        "steps": steps,
        "final_state": state.phase.value if 'state' in locals() else "unknown",
    }
