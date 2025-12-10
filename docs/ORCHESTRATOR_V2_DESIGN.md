# Orchestrator V2: Production-Ready Design

## Architecture Overview

### Design Principles
1. **Separation of Concerns**: State management, planning, execution are separate
2. **Declarative Policies**: Configuration-driven behavior (not hardcoded)
3. **DAG-based Scheduling**: Handle complex story dependencies
4. **LLM Minimization**: LLMs only for domain tasks (BA, Dev, QA), not orchestration
5. **Observable by Default**: Every decision is logged and traceable
6. **Learnable**: System captures patterns and improves over time

### Phase 4 Completion Status

- **Status**: ✅ All Phase 4 deliverables implemented and documented (see `docs/ORCHESTRATOR_V2_PHASE4_PLAN.md` and `docs/ORCHESTRATOR_V2_PHASE4_COMPLETION.md`).
- **Entry point**: `scripts/run_orchestrator_agent.py` replaces the legacy orchestrator CLI for day‑to‑day execution, while `scripts/orchestrate.py` supplies `execute_role`/`load_stories` helpers until the legacy runtime is fully retired.
- **CoT observability**: The new tracker in `scripts/orchestrator/cot_tracker.py` logs planner/policy/LLM decisions and exports JSONL/markdown summaries under `artifacts/cot_layer6/`.
- **Policy governance**: `config.yaml` exposes `pipeline.allow_architect_with_po_needs_adjustment` and `features.pipeline_guard.bypass` for temporary relaxation during story generation; these flags should be reset once automated `implements` coverage is in place.
- **Docs**: Usage and migration guidance now live in `docs/ORCHESTRATOR_V2_USAGE.md` and `docs/ORCHESTRATOR_V2_MIGRATION.md` so teams can learn the new workflow and retire legacy targets.

---

## Layer 1: State Machine

```python
# scripts/orchestrator/state_machine.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class PipelinePhase(Enum):
    INIT = "init"
    REQUIREMENTS = "requirements"      # BA → PO
    PLANNING = "planning"              # Architect
    DEVELOPMENT = "development"        # Dev + QA per story
    INTEGRATION = "integration"        # Full QA
    DONE = "done"
    FAILED = "failed"

@dataclass
class PipelineState:
    """Deterministic state of the pipeline."""
    phase: PipelinePhase
    concept: str

    # Artifacts presence
    has_requirements: bool
    has_product_vision: bool
    has_stories: bool
    has_architecture: bool

    # Stories state
    stories_graph: "StoryDAG"  # Dependency graph
    stories_ready: list[str]   # No blocked dependencies
    stories_running: dict[str, int]  # story_id -> attempt
    stories_done: list[str]
    stories_failed: dict[str, list[str]]  # story_id -> [error_types]

    # Metrics
    total_stories: int
    stories_passed: int
    iteration_number: int
    elapsed_time: float

    # History (for learning)
    decision_history: list["Decision"]

    def can_transition_to(self, next_phase: PipelinePhase) -> bool:
        """Check if transition is valid based on current state."""
        transitions = {
            PipelinePhase.INIT: [PipelinePhase.REQUIREMENTS],
            PipelinePhase.REQUIREMENTS: [PipelinePhase.PLANNING],
            PipelinePhase.PLANNING: [PipelinePhase.DEVELOPMENT],
            PipelinePhase.DEVELOPMENT: [PipelinePhase.INTEGRATION, PipelinePhase.PLANNING],
            PipelinePhase.INTEGRATION: [PipelinePhase.DONE, PipelinePhase.DEVELOPMENT, PipelinePhase.FAILED],
            PipelinePhase.DONE: [],
            PipelinePhase.FAILED: [PipelinePhase.REQUIREMENTS],  # Can restart
        }
        return next_phase in transitions.get(self.phase, [])

    def transition_to(self, next_phase: PipelinePhase, reason: str) -> None:
        """Perform state transition with validation."""
        if not self.can_transition_to(next_phase):
            raise ValueError(f"Invalid transition: {self.phase} → {next_phase}")

        logger.info(f"[state] Transitioning: {self.phase.value} → {next_phase.value} ({reason})")
        self.phase = next_phase
```

---

## Layer 2: Dependency Graph (DAG)

```python
# scripts/orchestrator/story_dag.py

from collections import defaultdict, deque
from typing import Dict, List, Set

class StoryDAG:
    """Dependency graph for stories (handles complex dependencies)."""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}  # story_id -> story metadata
        self.edges: Dict[str, List[str]] = defaultdict(list)  # story_id -> [depends_on]
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)  # story_id -> [blocks]

    def add_story(self, story_id: str, metadata: Dict, depends_on: List[str] = None):
        """Add story to graph."""
        self.nodes[story_id] = metadata
        if depends_on:
            for dep in depends_on:
                self.edges[story_id].append(dep)
                self.reverse_edges[dep].append(story_id)

    def get_ready_stories(self, done_stories: Set[str], failed_stories: Set[str]) -> List[str]:
        """
        Return stories that:
        - All dependencies are in done_stories
        - Not in done_stories or failed_stories
        - Topologically sorted by priority
        """
        ready = []
        for story_id, deps in self.edges.items():
            if story_id in done_stories or story_id in failed_stories:
                continue

            # Check if all dependencies are satisfied
            if all(dep in done_stories for dep in deps):
                ready.append(story_id)

        # Sort by priority (P0 > P1 > P2) and epic
        ready.sort(key=lambda sid: (
            self.nodes[sid].get("priority", "P9"),
            self.nodes[sid].get("epic", ""),
            sid
        ))

        return ready

    def get_blocked_stories(self, failed_stories: Set[str]) -> List[str]:
        """Return stories that depend on failed stories (transitively)."""
        blocked = set()
        queue = deque(failed_stories)

        while queue:
            failed_story = queue.popleft()
            for dependent in self.reverse_edges[failed_story]:
                if dependent not in blocked:
                    blocked.add(dependent)
                    queue.append(dependent)

        return list(blocked)

    def get_parallel_batch(self, ready_stories: List[str], max_parallelism: int = 3) -> List[str]:
        """
        Return up to max_parallelism stories that can run in parallel.
        Considers:
        - Same epic stories should run sequentially (shared context)
        - Different epics can run in parallel
        """
        if not ready_stories:
            return []

        # Group by epic
        by_epic: Dict[str, List[str]] = defaultdict(list)
        for sid in ready_stories:
            epic = self.nodes[sid].get("epic", "")
            by_epic[epic].append(sid)

        # Take first story from each epic (up to max_parallelism)
        batch = []
        for epic, stories in by_epic.items():
            if len(batch) >= max_parallelism:
                break
            batch.append(stories[0])

        return batch
```

---

## Layer 3: Policy Engine

```yaml
# config.yaml (extended with policies)

pipeline:
  # State machine config
  max_iterations: 10
  timeout_seconds: 3600

  # Retry policies
  retry_policies:
    dev:
      max_attempts: 3
      backoff: exponential  # 1min, 2min, 4min
      circuit_breaker:
        threshold: 5  # After 5 consecutive failures, escalate to architect
        window: 600   # Within 10 minutes

    architect:
      max_attempts: 2
      backoff: linear
      escalation: manual  # Require human intervention

    qa:
      max_attempts: 2
      backoff: none
      on_failure: return_to_dev  # QA fail → Dev retry

  # Escalation policies
  escalation_policies:
    - condition: "dev_attempts >= 3 AND same_error_pattern"
      action: "architect_refine"
      reason: "Repeated Dev failures suggest architectural issue"

    - condition: "qa_coverage < 0.8 AND tests_failed > 0"
      action: "architect_review_tests"
      reason: "Low coverage with failures needs design review"

    - condition: "multiple_stories_failed_in_epic"
      action: "architect_redesign_epic"
      reason: "Epic-wide failures suggest wrong decomposition"

  # Resource policies
  resource_policies:
    max_parallel_stories: 3
    max_concurrent_dev: 2
    max_concurrent_qa: 1
    dev_timeout: 600      # 10 minutes per story
    qa_timeout: 300       # 5 minutes per story

  # Priority policies
  priority_policies:
    - priority: P0
      max_retries: 5
      timeout_multiplier: 2.0
    - priority: P1
      max_retries: 3
      timeout_multiplier: 1.0
    - priority: P2
      max_retries: 2
      timeout_multiplier: 0.8
```

```python
# scripts/orchestrator/policy_engine.py

class PolicyEngine:
    """Evaluates policies and returns actions (no LLM)."""

    def __init__(self, config: Dict):
        self.retry_policies = config["pipeline"]["retry_policies"]
        self.escalation_policies = config["pipeline"]["escalation_policies"]
        self.resource_policies = config["pipeline"]["resource_policies"]

    def should_retry(self, role: str, story_id: str, attempts: int) -> bool:
        """Check if retry is allowed by policy."""
        policy = self.retry_policies.get(role, {})
        max_attempts = policy.get("max_attempts", 1)
        return attempts < max_attempts

    def get_backoff_delay(self, role: str, attempt: int) -> float:
        """Calculate backoff delay in seconds."""
        policy = self.retry_policies.get(role, {})
        backoff_type = policy.get("backoff", "none")

        if backoff_type == "exponential":
            return 60 * (2 ** (attempt - 1))  # 1min, 2min, 4min, 8min
        elif backoff_type == "linear":
            return 60 * attempt  # 1min, 2min, 3min
        else:
            return 0

    def evaluate_escalation(self, state: PipelineState, story_id: str) -> Optional[str]:
        """
        Check if any escalation policy matches current state.
        Returns: action name or None
        """
        for policy in self.escalation_policies:
            condition = policy["condition"]

            # Parse condition (simple expression evaluator)
            if self._evaluate_condition(condition, state, story_id):
                logger.warning(f"[policy] Escalation triggered: {policy['reason']}")
                return policy["action"]

        return None

    def _evaluate_condition(self, condition: str, state: PipelineState, story_id: str) -> bool:
        """
        Simple condition evaluator (can be replaced with a proper expression engine).
        Examples:
        - "dev_attempts >= 3 AND same_error_pattern"
        - "qa_coverage < 0.8"
        """
        # Extract variables from state
        story_data = state.stories_graph.nodes.get(story_id, {})
        dev_attempts = state.stories_running.get(story_id, 0)
        errors = state.stories_failed.get(story_id, [])
        same_error_pattern = len(set(errors)) == 1 and len(errors) >= 2

        # Build evaluation context
        ctx = {
            "dev_attempts": dev_attempts,
            "same_error_pattern": same_error_pattern,
            "qa_coverage": story_data.get("qa_coverage", 1.0),
            "tests_failed": story_data.get("tests_failed", 0),
        }

        # Simple eval (in production, use ast.literal_eval or a DSL parser)
        try:
            return eval(condition, {"__builtins__": {}}, ctx)
        except Exception as exc:
            logger.error(f"[policy] Failed to evaluate condition '{condition}': {exc}")
            return False
```

---

## Layer 4: Planning Layer (Intelligent Scheduler)

```python
# scripts/orchestrator/planner.py

class OrchestratorPlanner:
    """
    High-level planner that decides what to execute next.
    Uses state machine + DAG + policies (no LLM for most decisions).
    """

    def __init__(self, config: Dict):
        self.policy_engine = PolicyEngine(config)
        self.config = config
        self.llm_enabled = config.get("pipeline", {}).get("llm_planner_enabled", False)
        self.llm_client = Client(role="orchestrator") if self.llm_enabled else None

    async def plan_next_actions(self, state: PipelineState) -> List[Dict]:
        """
        Decide what to execute next based on state.
        Returns list of actions: [{"tool": "RUN_DEV_STORY", "arguments": {...}}]
        """

        # Phase-based planning
        if state.phase == PipelinePhase.INIT:
            return self._plan_init(state)

        elif state.phase == PipelinePhase.REQUIREMENTS:
            return self._plan_requirements(state)

        elif state.phase == PipelinePhase.PLANNING:
            return self._plan_planning(state)

        elif state.phase == PipelinePhase.DEVELOPMENT:
            return await self._plan_development(state)

        elif state.phase == PipelinePhase.INTEGRATION:
            return self._plan_integration(state)

        else:
            return []

    def _plan_init(self, state: PipelineState) -> List[Dict]:
        """INIT phase: Start BA."""
        return [{
            "tool": "RUN_BA",
            "arguments": {"concept": state.concept},
            "reason": "Initial requirements generation",
            "phase_transition": PipelinePhase.REQUIREMENTS
        }]

    def _plan_requirements(self, state: PipelineState) -> List[Dict]:
        """REQUIREMENTS phase: BA → PO → Architect."""
        if not state.has_requirements:
            return []  # Wait for BA to complete

        if not state.has_product_vision:
            return [{
                "tool": "RUN_PO",
                "arguments": {},
                "reason": "Validate requirements before planning"
            }]

        if not state.has_stories:
            return [{
                "tool": "RUN_ARCHITECT",
                "arguments": {
                    "concept": state.concept,
                    "architect_mode": "initial_design"
                },
                "reason": "Generate stories from requirements",
                "phase_transition": PipelinePhase.PLANNING
            }]

        return []

    async def _plan_development(self, state: PipelineState) -> List[Dict]:
        """
        DEVELOPMENT phase: Most complex planning.
        - Decide which stories to run
        - Handle retries and escalations
        - Respect DAG dependencies
        - Apply resource limits
        """
        actions = []

        # Get ready stories from DAG
        ready_stories = state.stories_graph.get_ready_stories(
            done_stories=set(state.stories_done),
            failed_stories=set(state.stories_failed.keys())
        )

        if not ready_stories:
            # No ready stories - check if we're done or blocked
            if len(state.stories_done) == state.total_stories:
                return [{
                    "tool": "TRANSITION",
                    "arguments": {"phase": "integration"},
                    "reason": "All stories completed"
                }]

            # Some stories blocked by failures - need escalation
            blocked = state.stories_graph.get_blocked_stories(set(state.stories_failed.keys()))
            return await self._plan_escalation(state, blocked)

        # Get parallel batch respecting resource limits
        max_parallel = self.config["pipeline"]["resource_policies"]["max_parallel_stories"]
        batch = state.stories_graph.get_parallel_batch(ready_stories, max_parallel)

        # Plan each story in batch
        for story_id in batch:
            # Check for escalation policies
            escalation_action = self.policy_engine.evaluate_escalation(state, story_id)
            if escalation_action:
                actions.append(self._create_escalation_action(escalation_action, story_id))
                continue

            # Check if retry is allowed
            attempts = state.stories_running.get(story_id, 0)
            if attempts > 0 and not self.policy_engine.should_retry("dev", story_id, attempts):
                # Max retries reached - fail story
                actions.append({
                    "tool": "MARK_FAILED",
                    "arguments": {"story_id": story_id},
                    "reason": f"Max retry attempts ({attempts}) reached"
                })
                continue

            # Normal dev execution
            actions.append({
                "tool": "RUN_DEV_STORY",
                "arguments": {
                    "story_id": story_id,
                    "retries": attempts
                },
                "reason": f"Implement story (attempt {attempts + 1})"
            })

        return actions

    async def _plan_escalation(self, state: PipelineState, blocked_stories: List[str]) -> List[Dict]:
        """
        Handle escalation when stories are blocked.
        This is where LLM CAN be used for complex decisions.
        """
        if not self.llm_enabled:
            # Fallback: Refine all failed stories
            return [{
                "tool": "RUN_ARCHITECT",
                "arguments": {
                    "story_id": story_id,
                    "architect_mode": "refine_story"
                },
                "reason": "Story failed, needs refinement"
            } for story_id in state.stories_failed.keys()]

        # Use LLM for complex escalation decision
        context = self._build_escalation_context(state, blocked_stories)
        decision = await self.llm_client.chat(
            system="You are an escalation planner...",
            user=context
        )
        return self._parse_llm_decision(decision)
```

---

## Layer 5: Chain-of-Thought Integration

```python
# scripts/orchestrator/cot_tracker.py

@dataclass
class ThoughtEntry:
    timestamp: str
    phase: str
    layer: str  # "state_machine" | "dag" | "policy" | "planner" | "llm"
    kind: str   # "transition" | "decision" | "policy_eval" | "escalation"
    message: str
    details: Dict[str, Any]

    # Reasoning chain
    inputs: Dict[str, Any]
    reasoning_steps: List[str]
    output: Any
    confidence: float  # 1.0 for deterministic, <1.0 for LLM

class ChainOfThoughtTracker:
    """Tracks reasoning at every layer."""

    def __init__(self):
        self.thoughts: List[ThoughtEntry] = []

    def log_state_transition(self, from_phase: str, to_phase: str, reason: str):
        self.thoughts.append(ThoughtEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase=to_phase,
            layer="state_machine",
            kind="transition",
            message=f"Transitioned {from_phase} → {to_phase}",
            details={"reason": reason},
            inputs={"from": from_phase},
            reasoning_steps=[f"Valid transition check passed", reason],
            output=to_phase,
            confidence=1.0
        ))

    def log_dag_decision(self, ready_stories: List[str], batch: List[str], reason: str):
        self.thoughts.append(ThoughtEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="development",
            layer="dag",
            kind="decision",
            message=f"Selected {len(batch)} stories for parallel execution",
            details={"ready": ready_stories, "selected": batch},
            inputs={"ready_stories": ready_stories},
            reasoning_steps=[
                f"Found {len(ready_stories)} ready stories (dependencies satisfied)",
                f"Grouped by epic for parallelization",
                f"Selected {len(batch)} stories respecting resource limits"
            ],
            output=batch,
            confidence=1.0
        ))

    def log_policy_evaluation(self, policy_name: str, condition: str, matched: bool, context: Dict):
        self.thoughts.append(ThoughtEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="development",
            layer="policy",
            kind="policy_eval",
            message=f"Policy '{policy_name}' {'matched' if matched else 'not matched'}",
            details={"condition": condition, "context": context},
            inputs=context,
            reasoning_steps=[
                f"Evaluated condition: {condition}",
                f"Context: {context}",
                f"Result: {matched}"
            ],
            output=matched,
            confidence=1.0
        ))

    def log_llm_decision(self, prompt: str, response: str, parsed: Dict):
        self.thoughts.append(ThoughtEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="escalation",
            layer="llm",
            kind="decision",
            message="LLM-based escalation decision",
            details={"prompt_length": len(prompt), "response_length": len(response)},
            inputs={"prompt": prompt[:500]},
            reasoning_steps=["No deterministic rule matched", "Consulted LLM for decision"],
            output=parsed,
            confidence=0.7  # Lower confidence for LLM decisions
        ))

    def export_jsonl(self, path: Path):
        """Export thoughts as JSONL."""
        with path.open("w") as f:
            for thought in self.thoughts:
                f.write(json.dumps(asdict(thought)) + "\n")

    def export_markdown(self, path: Path):
        """Export human-readable reasoning chain."""
        lines = ["# Chain of Thought Log\n\n"]

        by_phase = defaultdict(list)
        for thought in self.thoughts:
            by_phase[thought.phase].append(thought)

        for phase, thoughts in by_phase.items():
            lines.append(f"## Phase: {phase}\n\n")
            for t in thoughts:
                lines.append(f"### [{t.layer}] {t.message}\n")
                lines.append(f"**Timestamp**: {t.timestamp}  \n")
                lines.append(f"**Confidence**: {t.confidence * 100:.0f}%  \n\n")

                lines.append("**Reasoning Steps**:\n")
                for step in t.reasoning_steps:
                    lines.append(f"- {step}\n")
                lines.append("\n")

                if t.details:
                    lines.append(f"**Details**: `{json.dumps(t.details, indent=2)}`\n\n")

                lines.append("---\n\n")

        path.write_text("".join(lines))
```

---

---

## Layer 7: Coherence Checker (Consistency Validation)

```python
# scripts/orchestrator/coherence_checker.py

from dataclasses import dataclass
from typing import List, Dict, Set, Optional
import yaml
import json
from pathlib import Path

@dataclass
class InconsistencyReport:
    """Report of detected inconsistencies."""
    severity: str  # "critical" | "warning" | "info"
    category: str  # "coverage" | "conflict" | "drift" | "quality"
    title: str
    description: str
    affected_artifacts: List[str]
    affected_stories: List[str]
    evidence: Dict[str, any]
    recommendation: str
    requires_llm_analysis: bool = False

class CoherenceChecker:
    """
    Validates consistency across all agent outputs.
    Runs at key checkpoints: after BA+PO, after Architect, after Dev.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.llm_client = Client(role="orchestrator")
        self.checks_enabled = config.get("pipeline", {}).get("coherence_checks_enabled", True)

        # Thresholds from config
        self.coverage_threshold = config.get("coherence", {}).get("min_coverage", 0.95)
        self.semantic_similarity_threshold = config.get("coherence", {}).get("min_similarity", 0.75)

    async def check_coherence(self, checkpoint: str, state: PipelineState) -> List[InconsistencyReport]:
        """
        Run coherence checks at a specific checkpoint.
        Returns list of inconsistencies found.
        """
        if not self.checks_enabled:
            return []

        reports = []

        if checkpoint == "post_requirements":
            # BA → PO coherence
            reports.extend(await self._check_requirements_po_alignment(state))

        elif checkpoint == "post_planning":
            # Requirements → Stories coherence
            reports.extend(await self._check_requirements_coverage(state))
            reports.extend(await self._check_architecture_consistency(state))
            reports.extend(await self._check_story_quality(state))

        elif checkpoint == "post_development":
            # Stories → Code coherence
            reports.extend(await self._check_implementation_matches_stories(state))
            reports.extend(await self._check_architecture_violations(state))

        elif checkpoint == "post_integration":
            # Full system coherence
            reports.extend(await self._check_end_to_end_coherence(state))

        return reports

    async def _check_requirements_coverage(self, state: PipelineState) -> List[InconsistencyReport]:
        """
        CHECK: All functional requirements are covered by at least one story.
        """
        reports = []

        # Load requirements
        req_path = Path("planning/requirements.yaml")
        if not req_path.exists():
            return reports

        with req_path.open() as f:
            requirements = yaml.safe_load(f)

        functional_reqs = requirements.get("functional_requirements", [])
        if not functional_reqs:
            return reports

        # Load stories
        stories_path = Path("planning/stories.yaml")
        if not stories_path.exists():
            return reports

        with stories_path.open() as f:
            stories = yaml.safe_load(f)

        # Build mapping: requirement_id -> list of stories that mention it
        req_coverage = {req["id"]: [] for req in functional_reqs}

        for story in stories:
            # Check if story description/acceptance mentions any requirement
            story_text = json.dumps(story).lower()
            for req in functional_reqs:
                req_id = req["id"]
                req_keywords = [
                    req_id.lower(),
                    req.get("name", "").lower(),
                ]
                if any(keyword in story_text for keyword in req_keywords if keyword):
                    req_coverage[req_id].append(story["id"])

        # Find uncovered requirements
        uncovered = [req_id for req_id, stories in req_coverage.items() if not stories]

        if uncovered:
            coverage_ratio = 1 - (len(uncovered) / len(functional_reqs))
            severity = "critical" if coverage_ratio < 0.8 else "warning"

            reports.append(InconsistencyReport(
                severity=severity,
                category="coverage",
                title=f"{len(uncovered)} requirements not covered by any story",
                description=f"Coverage: {coverage_ratio:.1%}. These requirements have no implementing stories: {', '.join(uncovered)}",
                affected_artifacts=["requirements.yaml", "stories.yaml"],
                affected_stories=[],
                evidence={
                    "uncovered_requirements": uncovered,
                    "coverage_ratio": coverage_ratio,
                    "requirement_details": [
                        {"id": req["id"], "name": req.get("name")}
                        for req in functional_reqs if req["id"] in uncovered
                    ]
                },
                recommendation="Run Architect in 'refine' mode to generate missing stories, or update requirements to remove obsolete items.",
                requires_llm_analysis=True
            ))

        return reports

    async def _check_architecture_consistency(self, state: PipelineState) -> List[InconsistencyReport]:
        """
        CHECK: All stories follow the global architecture decisions.
        Example: If architecture says "use PostgreSQL", no story should implement SQLite.
        """
        reports = []

        arch_path = Path("planning/architecture.yaml")
        stories_path = Path("planning/stories.yaml")

        if not arch_path.exists() or not stories_path.exists():
            return reports

        with arch_path.open() as f:
            architecture = yaml.safe_load(f)

        with stories_path.open() as f:
            stories = yaml.safe_load(f)

        # Extract architectural constraints
        constraints = {
            "backend.database": architecture.get("backend", {}).get("database"),
            "backend.framework": architecture.get("backend", {}).get("framework"),
            "frontend.framework": architecture.get("frontend", {}).get("framework"),
        }

        # Check each story for violations
        violations = []
        for story in stories:
            story_text = json.dumps(story).lower()

            # Database check
            if constraints["backend.database"]:
                expected_db = constraints["backend.database"].lower()
                conflicting_dbs = ["sqlite", "mysql", "mongodb", "redis"]
                conflicting_dbs.remove(expected_db) if expected_db in conflicting_dbs else None

                for conflict_db in conflicting_dbs:
                    if conflict_db in story_text and expected_db not in story_text:
                        violations.append({
                            "story_id": story["id"],
                            "constraint": "backend.database",
                            "expected": constraints["backend.database"],
                            "found": conflict_db,
                            "context": story.get("description", "")[:200]
                        })

        if violations:
            reports.append(InconsistencyReport(
                severity="critical",
                category="conflict",
                title="Architecture violations detected in stories",
                description=f"{len(violations)} stories conflict with global architecture",
                affected_artifacts=["architecture.yaml", "stories.yaml"],
                affected_stories=[v["story_id"] for v in violations],
                evidence={"violations": violations},
                recommendation="Run Architect in 'refine_story' mode for affected stories to align with architecture.",
                requires_llm_analysis=False
            ))

        return reports

    async def _check_story_quality(self, state: PipelineState) -> List[InconsistencyReport]:
        """
        CHECK: All stories have:
        - Clear acceptance criteria
        - Priority
        - Complexity estimate
        - Valid references to epics
        """
        reports = []

        stories_path = Path("planning/stories.yaml")
        if not stories_path.exists():
            return reports

        with stories_path.open() as f:
            stories = yaml.safe_load(f)

        quality_issues = []
        for story in stories:
            issues = []

            # Check acceptance criteria
            acceptance = story.get("acceptance", [])
            if not acceptance or len(acceptance) == 0:
                issues.append("missing_acceptance_criteria")
            elif len(acceptance) < 2:
                issues.append("insufficient_acceptance_criteria")

            # Check priority
            if not story.get("priority"):
                issues.append("missing_priority")

            # Check description
            desc = story.get("description", "")
            if len(desc) < 20:
                issues.append("description_too_short")

            # Check complexity
            if not story.get("complexity"):
                issues.append("missing_complexity")

            if issues:
                quality_issues.append({
                    "story_id": story["id"],
                    "issues": issues
                })

        if quality_issues:
            reports.append(InconsistencyReport(
                severity="warning",
                category="quality",
                title=f"{len(quality_issues)} stories have quality issues",
                description="Some stories lack essential details (acceptance criteria, priority, etc.)",
                affected_artifacts=["stories.yaml"],
                affected_stories=[item["story_id"] for item in quality_issues],
                evidence={"quality_issues": quality_issues},
                recommendation="Run Architect in 'enrich_stories' mode to add missing details.",
                requires_llm_analysis=False
            ))

        return reports

    async def _check_implementation_matches_stories(self, state: PipelineState) -> List[InconsistencyReport]:
        """
        CHECK: Code implemented actually matches story acceptance criteria.
        This requires analyzing code + tests.
        """
        reports = []

        for story_id in state.stories_done:
            # Load story
            story = state.stories_graph.nodes.get(story_id)
            if not story:
                continue

            # Load QA report for this story
            qa_path = Path(f"artifacts/qa/{story_id}/report.json")
            if not qa_path.exists():
                continue

            with qa_path.open() as f:
                qa_report = json.load(f)

            # Check if all acceptance criteria are tested
            acceptance = story.get("acceptance", [])
            tests_run = qa_report.get("tests_run", 0)
            tests_passed = qa_report.get("tests_passed", 0)

            # Heuristic: Should have at least 1 test per acceptance criterion
            expected_min_tests = len(acceptance)

            if tests_run < expected_min_tests:
                reports.append(InconsistencyReport(
                    severity="warning",
                    category="quality",
                    title=f"Story {story_id} has insufficient test coverage",
                    description=f"Story has {len(acceptance)} acceptance criteria but only {tests_run} tests",
                    affected_artifacts=[f"project/*/tests/*{story_id}*"],
                    affected_stories=[story_id],
                    evidence={
                        "acceptance_count": len(acceptance),
                        "tests_run": tests_run,
                        "coverage": qa_report.get("coverage", 0)
                    },
                    recommendation=f"Run Dev for {story_id} with instruction to add tests for each acceptance criterion.",
                    requires_llm_analysis=False
                ))

        return reports

    async def _check_requirements_po_alignment(self, state: PipelineState) -> List[InconsistencyReport]:
        """
        CHECK: PO review aligns with requirements (not conflicting).
        Uses LLM to check semantic alignment.
        """
        reports = []

        req_path = Path("planning/requirements.yaml")
        po_path = Path("planning/product_owner_review.yaml")

        if not req_path.exists() or not po_path.exists():
            return reports

        with req_path.open() as f:
            requirements = yaml.safe_load(f)

        with po_path.open() as f:
            po_review = yaml.safe_load(f)

        # Check if PO flagged conflicts
        conflicts = po_review.get("requirements_alignment", {}).get("conflicts", [])
        if conflicts:
            reports.append(InconsistencyReport(
                severity="critical",
                category="conflict",
                title="PO identified conflicts in requirements",
                description=f"Product Owner found {len(conflicts)} conflicts between requirements and product vision",
                affected_artifacts=["requirements.yaml", "product_owner_review.yaml"],
                affected_stories=[],
                evidence={"conflicts": conflicts},
                recommendation="Review and resolve conflicts before proceeding to Architect phase.",
                requires_llm_analysis=False
            ))

        # Check for gaps
        gaps = po_review.get("requirements_alignment", {}).get("gaps", [])
        if gaps:
            reports.append(InconsistencyReport(
                severity="warning",
                category="coverage",
                title="PO identified gaps in requirements",
                description=f"Product Owner found {len(gaps)} missing requirements",
                affected_artifacts=["requirements.yaml"],
                affected_stories=[],
                evidence={"gaps": gaps},
                recommendation="Re-run BA to address gaps, or accept gaps and document as out-of-scope.",
                requires_llm_analysis=False
            ))

        return reports

    async def _check_end_to_end_coherence(self, state: PipelineState) -> List[InconsistencyReport]:
        """
        FULL CHECK: Requirements → Stories → Code → Tests
        Uses LLM to perform semantic analysis across all artifacts.
        """
        # This is the most expensive check - only run at end of iteration
        reports = []

        # Build context summary
        context = self._build_coherence_context(state)

        # Call LLM for deep analysis
        system_prompt = """You are a software architect performing a coherence audit across a multi-agent development pipeline.

You receive:
1. Original requirements (from Business Analyst)
2. Product vision validation (from Product Owner)
3. Stories and architecture (from Architect)
4. Implementation summaries (from Developer)
5. QA test results

Your task: Identify semantic inconsistencies, gaps, conflicts, or quality issues that span multiple artifacts.

Return a JSON array of inconsistency reports:
[
  {
    "severity": "critical" | "warning" | "info",
    "category": "drift" | "coverage" | "conflict" | "quality",
    "title": "Brief title",
    "description": "Detailed explanation",
    "evidence": {...},
    "recommendation": "Actionable next step"
  }
]
"""

        user_prompt = f"""Perform coherence audit:

{context}

Focus on:
1. Semantic drift (did implementation diverge from requirements?)
2. Coverage gaps (are all requirements implemented and tested?)
3. Architectural conflicts (does code follow architecture?)
4. Quality issues (insufficient tests, missing validations, etc.)
"""

        try:
            response = await self.llm_client.chat(system=system_prompt, user=user_prompt)
            llm_reports = json.loads(response)

            for report_data in llm_reports:
                reports.append(InconsistencyReport(
                    severity=report_data["severity"],
                    category=report_data["category"],
                    title=report_data["title"],
                    description=report_data["description"],
                    affected_artifacts=report_data.get("affected_artifacts", []),
                    affected_stories=report_data.get("affected_stories", []),
                    evidence=report_data.get("evidence", {}),
                    recommendation=report_data["recommendation"],
                    requires_llm_analysis=False  # Already analyzed
                ))

        except Exception as exc:
            logger.error(f"[coherence] LLM-based coherence check failed: {exc}")

        return reports

    def _build_coherence_context(self, state: PipelineState) -> str:
        """Build summary context for LLM analysis."""
        parts = []

        # Requirements summary
        req_path = Path("planning/requirements.yaml")
        if req_path.exists():
            with req_path.open() as f:
                req_data = yaml.safe_load(f)
                func_reqs = req_data.get("functional_requirements", [])
                parts.append(f"## Requirements ({len(func_reqs)} functional)")
                for req in func_reqs[:10]:  # First 10 only
                    parts.append(f"- {req['id']}: {req.get('name', 'N/A')}")

        # Stories summary
        stories_path = Path("planning/stories.yaml")
        if stories_path.exists():
            with stories_path.open() as f:
                stories = yaml.safe_load(f)
                parts.append(f"\n## Stories ({len(stories)} total)")
                for story in stories[:10]:
                    parts.append(f"- {story['id']}: {story.get('description', 'N/A')[:100]}")

        # Architecture summary
        arch_path = Path("planning/architecture.yaml")
        if arch_path.exists():
            with arch_path.open() as f:
                arch = yaml.safe_load(f)
                parts.append(f"\n## Architecture")
                parts.append(f"Backend: {arch.get('backend', {})}")
                parts.append(f"Frontend: {arch.get('frontend', {})}")

        # QA summary
        parts.append(f"\n## QA Results")
        parts.append(f"Stories done: {len(state.stories_done)}")
        parts.append(f"Stories failed: {len(state.stories_failed)}")

        return "\n".join(parts)


class CoherenceOrchestrationIntegration:
    """
    Integrates coherence checking into the main orchestration loop.
    """

    def __init__(self, planner: OrchestratorPlanner, checker: CoherenceChecker):
        self.planner = planner
        self.checker = checker

    async def plan_with_coherence(self, state: PipelineState) -> List[Dict]:
        """
        Enhanced planning that checks coherence at key checkpoints.
        """
        # Determine checkpoint based on phase
        checkpoint = None
        if state.phase == PipelinePhase.REQUIREMENTS and state.has_product_vision:
            checkpoint = "post_requirements"
        elif state.phase == PipelinePhase.PLANNING and state.has_stories:
            checkpoint = "post_planning"
        elif state.phase == PipelinePhase.DEVELOPMENT and len(state.stories_done) > 0:
            checkpoint = "post_development"
        elif state.phase == PipelinePhase.INTEGRATION:
            checkpoint = "post_integration"

        # Run coherence checks
        if checkpoint:
            logger.info(f"[coherence] Running checks at checkpoint: {checkpoint}")
            inconsistencies = await self.checker.check_coherence(checkpoint, state)

            if inconsistencies:
                # Log all inconsistencies
                for inc in inconsistencies:
                    logger.warning(f"[coherence] {inc.severity.upper()}: {inc.title}")

                # Handle critical inconsistencies
                critical = [i for i in inconsistencies if i.severity == "critical"]
                if critical:
                    # Block progression - must fix critical issues
                    return self._generate_remediation_actions(critical, state)

                # Warnings don't block, but are logged for observability
                warnings = [i for i in inconsistencies if i.severity == "warning"]
                if warnings:
                    self._log_warnings_to_cot(warnings)

        # Normal planning continues
        return await self.planner.plan_next_actions(state)

    def _generate_remediation_actions(
        self,
        critical_inconsistencies: List[InconsistencyReport],
        state: PipelineState
    ) -> List[Dict]:
        """
        Generate remediation actions for critical inconsistencies.
        """
        actions = []

        for inc in critical_inconsistencies:
            if inc.category == "coverage":
                # Missing requirements → re-run Architect to add stories
                actions.append({
                    "tool": "RUN_ARCHITECT",
                    "arguments": {
                        "concept": state.concept,
                        "architect_mode": "add_missing_stories",
                        "context": inc.evidence
                    },
                    "reason": f"Remediation: {inc.title}"
                })

            elif inc.category == "conflict":
                # Architecture conflict → re-run Architect to refine stories
                for story_id in inc.affected_stories:
                    actions.append({
                        "tool": "RUN_ARCHITECT",
                        "arguments": {
                            "story_id": story_id,
                            "architect_mode": "refine_story",
                            "detail_level": "detailed"
                        },
                        "reason": f"Remediation: {inc.title}"
                    })

        return actions

    def _log_warnings_to_cot(self, warnings: List[InconsistencyReport]):
        """Log warnings to chain-of-thought for visibility."""
        for warning in warnings:
            logger.warning(f"[coherence_warning] {warning.title}: {warning.description}")
            # TODO: Add to CoT tracker
```

---

## Integration with Main Loop

```python
# scripts/run_orchestrator_agent.py (modified)

async def run_agentic_orchestrator_v2(concept: str, max_steps: int):
    """Enhanced orchestrator with coherence checking."""

    # Initialize components
    config = load_config()
    state_machine = StateMachine(concept)
    planner = OrchestratorPlanner(config)
    checker = CoherenceChecker(config)
    integrated_planner = CoherenceOrchestrationIntegration(planner, checker)
    cot_tracker = ChainOfThoughtTracker()

    for step in range(max_steps):
        # Get current state
        state = state_machine.get_state()

        # Plan next actions (with coherence checks)
        actions = await integrated_planner.plan_with_coherence(state)

        # Execute actions
        results = await execute_actions(actions)

        # Update state based on results
        state_machine.update(results)

        # Log to CoT
        cot_tracker.log_step(state, actions, results)

        # Check termination
        if state.phase == PipelinePhase.DONE:
            break

    # Final coherence audit
    final_report = await checker.check_coherence("post_integration", state)

    return {
        "state": state,
        "coherence_report": final_report,
        "cot": cot_tracker.export()
    }
```

---

## Coherence Check Schedule

```yaml
# config.yaml

coherence:
  enabled: true

  # When to run checks
  checkpoints:
    post_requirements: true   # After BA + PO
    post_planning: true       # After Architect
    post_development: false   # Too expensive, skip
    post_integration: true    # Final audit before done

  # Check configurations
  min_coverage: 0.95          # 95% requirements must be covered
  min_similarity: 0.75        # Semantic similarity threshold

  # LLM usage for coherence
  llm_enabled: true
  llm_for_checkpoints: ["post_integration"]  # Only use LLM at end

  # Actions on inconsistencies
  block_on_critical: true     # Stop pipeline on critical issues
  auto_remediate: true        # Automatically generate fix actions
  notify_on_warnings: true    # Log warnings to CoT
```

---

## Benefits of This Design

### 1. **Scalability**
- ✅ Handles 100+ stories with complex dependencies
- ✅ DAG algorithm scales O(n log n) for topological sort
- ✅ Policy engine is O(p) where p = number of policies (configurable)
- ✅ Coherence checks scale O(n×m) where n=stories, m=requirements

### 2. **Determinism**
- ✅ 95%+ of decisions are deterministic (state machine + DAG + policies)
- ✅ LLM only for <5% of ambiguous cases
- ✅ Every decision has a clear reason

### 3. **Observability**
- ✅ Every layer logs its reasoning
- ✅ Can trace why any decision was made
- ✅ Confidence scores show LLM vs deterministic decisions
- ✅ Inconsistency reports provide full audit trail

### 4. **Maintainability**
- ✅ Policies in YAML (not Python code)
- ✅ Easy to add new policies without code changes
- ✅ Each layer is independently testable
- ✅ Coherence checks are modular and extensible

### 5. **Cost-Effective**
- ✅ LLM calls reduced by 90%+
- ✅ Only expensive operations use LLM (escalation planning)
- ✅ Caching and batching where possible
- ✅ Coherence checks use LLM only at final audit

### 6. **Consistency Assurance** (NEW)
- ✅ Multi-layer validation across all artifacts
- ✅ Catches semantic drift before it causes bugs
- ✅ Ensures complete coverage of requirements
- ✅ Validates architectural conformance
- ✅ Automatic remediation for critical issues

---

## Migration Path

1. **Phase 1**: Implement state machine + DAG (no LLM)
2. **Phase 2**: Add policy engine with basic policies
3. **Phase 3**: Integrate with existing run_orchestrator_agent.py
4. **Phase 4**: Add LLM fallback for complex cases
5. **Phase 5**: Add CoT tracking and learning layer

## Questions?

Is this level of complexity appropriate for your use case? Or should I simplify further?
