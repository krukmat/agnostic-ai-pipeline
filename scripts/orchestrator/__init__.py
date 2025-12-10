"""
Orchestrator V2 components.

Provides deterministic state machine, DAG scheduling, and policy-driven planning.
Minimal LLM usage - orchestration decisions are rule-based.

Phase 2 features:
- Coherence Checker: Validates consistency between agent outputs
- Chain-of-Thought Logger: Structured reasoning capture
- Execution Optimizer: Learning from execution history
"""

from .state_machine import PipelineState, PipelinePhase, StateMachine
from .story_dag import StoryDAG
from .policy_engine import PolicyEngine
from .planner import OrchestratorPlanner
from .executor import ActionExecutor
from .v2_runtime import run_orchestrator_v2

# Phase 2: Advanced features
from .coherence_checker import CoherenceChecker
from .cot_logger import ChainOfThoughtLogger
from .optimizer import ExecutionOptimizer

__all__ = [
    # Phase 1 (Core)
    "PipelineState",
    "PipelinePhase",
    "StateMachine",
    "StoryDAG",
    "PolicyEngine",
    "OrchestratorPlanner",
    "ActionExecutor",
    "run_orchestrator_v2",
    # Phase 2 (Advanced)
    "CoherenceChecker",
    "ChainOfThoughtLogger",
    "ExecutionOptimizer",
]
