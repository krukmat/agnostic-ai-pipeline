"""
Orchestrator V2 components.

Provides deterministic state machine, DAG scheduling, and policy-driven planning.
Minimal LLM usage - orchestration decisions are rule-based.

Phase 1 (Core):
- State Machine, Story DAG, Policy Engine, Planner, Executor

Phase 2 (Intelligence):
- Coherence Checker: Validates consistency between agent outputs
- Chain-of-Thought Logger: Structured reasoning capture
- Execution Optimizer: Learning from execution history

Phase 3 (Advanced):
- Performance Predictor: Duration and resource prediction
- Domain Rules Engine: Customizable validation rules
- Analytics Engine: Execution pattern analysis
- Parallelism Scheduler: Adaptive parallel execution
- Cache Manager: Intelligent result caching
- Feedback Loop: Agent and user feedback integration
- Advanced CoT: Hierarchical decision reasoning
- Adaptive Policy Engine: Learning-based policy adjustment

Phase 4 (Complete):
- Layer 6 CoT Tracker: Unified thought tracking across all layers
"""

from .state_machine import PipelineState, PipelinePhase, StateMachine
from .story_dag import StoryDAG
from .policy_engine import PolicyEngine
from .planner import OrchestratorPlanner
from .executor import ActionExecutor
from .v2_runtime import run_orchestrator_v2

# Phase 2: Intelligence layer
from .coherence_checker import CoherenceChecker
from .cot_logger import ChainOfThoughtLogger
from .optimizer import ExecutionOptimizer

# Phase 3: Advanced features
from .performance_predictor import PerformancePredictor
from .domain_rules import DomainRulesEngine
from .analytics_engine import AnalyticsEngine
from .parallelism_scheduler import ParallelismScheduler
from .cache_manager import CacheManager
from .feedback_loop import FeedbackCollector
from .advanced_cot import AdvancedChainOfThought
from .adaptive_policy_engine import AdaptivePolicyEngine

# Phase 4: Complete closure
from .cot_tracker import ThoughtEntry, ChainOfThoughtTracker
from .coherence_orchestration_integration import CoherenceOrchestrationIntegration
from .llm_fallback import LLMFallbackEngine, LLMDecision  # Task 9: LLM fallback
from .main_orchestration_loop import run_agentic_orchestrator_v2  # Task 5: Main loop

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
    # Phase 2 (Intelligence)
    "CoherenceChecker",
    "ChainOfThoughtLogger",
    "ExecutionOptimizer",
    # Phase 3 (Advanced)
    "PerformancePredictor",
    "DomainRulesEngine",
    "AnalyticsEngine",
    "ParallelismScheduler",
    "CacheManager",
    "FeedbackCollector",
    "AdvancedChainOfThought",
    "AdaptivePolicyEngine",
    # Phase 4 (Complete)
    "ThoughtEntry",
    "ChainOfThoughtTracker",
    "CoherenceOrchestrationIntegration",
    "LLMFallbackEngine",
    "LLMDecision",
    "run_agentic_orchestrator_v2",
]
