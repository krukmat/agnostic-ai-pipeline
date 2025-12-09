# Orchestrator V2 - Phase 1 Implementation Plan

**Goal**: Implement core deterministic orchestration with state machine, DAG scheduling, and policy engine.

**Duration**: 2-3 days
**Prerequisites**: Current `scripts/run_orchestrator_agent.py` working
**Deliverable**: Production-ready orchestrator with 90%+ autonomy (minimal LLM usage)

---

## Phase 1 Scope

### ✅ In Scope
1. **State Machine**: Deterministic phase transitions (INIT → REQUIREMENTS → PLANNING → DEVELOPMENT → INTEGRATION → DONE)
2. **Story DAG**: Dependency graph with topological sorting and parallel execution
3. **Policy Engine**: YAML-driven retry, escalation, and resource policies
4. **Rule-Based Planner**: Deterministic decision-making without LLM
5. **Integration**: Work with existing role scripts (BA, PO, Architect, Dev, QA)
6. **Testing**: Unit tests for each component
7. **Backward Compatibility**: Current orchestrator continues to work

### ❌ Out of Scope (Future Phases)
- Coherence checking (Phase 2)
- Chain-of-thought tracking (Phase 3)
- LLM-based fallback for complex decisions (Phase 3)
- Learning from past executions (Phase 4)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ scripts/run_orchestrator_agent.py (ENTRY POINT)            │
│ - CLI argument parsing                                      │
│ - Initializes V2 components                                 │
│ - Main execution loop                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ scripts/orchestrator/v2_runtime.py (COORDINATOR)           │
│ - Orchestrates state machine + DAG + planner               │
│ - Handles phase transitions                                │
│ - Dispatches actions to role executors                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                     ↓
┌─────────────────────┐           ┌─────────────────────┐
│ State Machine       │           │ Story DAG           │
│ (state_machine.py)  │           │ (story_dag.py)      │
│ - Phase management  │           │ - Dependencies      │
│ - Transitions       │           │ - Ready stories     │
│ - Validation        │           │ - Parallelization   │
└─────────────────────┘           └─────────────────────┘
        ↓                                     ↓
        └─────────────────┬─────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Policy Engine (policy_engine.py)                           │
│ - Retry policies (exponential backoff)                     │
│ - Escalation policies (dev fail → architect)               │
│ - Resource policies (max parallel stories)                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Planner (planner.py)                                       │
│ - Decides next actions based on state + DAG + policies     │
│ - No LLM usage (pure rule-based)                           │
│ - Returns list of actions to execute                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Action Executor (executor.py)                              │
│ - Dispatches actions to role handlers                      │
│ - Handles parallel execution                               │
│ - Collects results                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Role Handlers (scripts/orchestrator_runtime.py)           │
│ - execute_role("business_analyst", payload)                │
│ - execute_role("architect", payload)                       │
│ - execute_role("developer", payload)                       │
│ - execute_role("qa", payload)                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Task Breakdown

### Task 1: Project Structure Setup (1 hour)

**Goal**: Create new module structure without breaking existing code.

**Files to Create**:
```
scripts/orchestrator/
├── __init__.py
├── state_machine.py      # State management
├── story_dag.py          # Dependency graph
├── policy_engine.py      # Policy evaluation
├── planner.py            # Decision engine
├── executor.py           # Action dispatcher
└── v2_runtime.py         # Main coordinator
```

**Implementation**:

```python
# scripts/orchestrator/__init__.py
"""
Orchestrator V2 components.
Provides deterministic state machine, DAG scheduling, and policy-driven planning.
"""

from .state_machine import PipelineState, PipelinePhase, StateMachine
from .story_dag import StoryDAG
from .policy_engine import PolicyEngine
from .planner import OrchestratorPlanner
from .executor import ActionExecutor
from .v2_runtime import run_orchestrator_v2

__all__ = [
    "PipelineState",
    "PipelinePhase",
    "StateMachine",
    "StoryDAG",
    "PolicyEngine",
    "OrchestratorPlanner",
    "ActionExecutor",
    "run_orchestrator_v2",
]
```

**Acceptance Criteria**:
- [ ] Directory `scripts/orchestrator/` created
- [ ] All stub files created with docstrings
- [ ] `__init__.py` imports work without errors
- [ ] Existing `scripts/run_orchestrator_agent.py` still works

**Tests**:
```python
# tests/test_orchestrator_v2_structure.py
def test_orchestrator_v2_module_imports():
    """Verify all V2 components can be imported."""
    from scripts.orchestrator import (
        PipelineState, StateMachine, StoryDAG,
        PolicyEngine, OrchestratorPlanner
    )
    assert PipelineState is not None
    assert StateMachine is not None
```

---

### Task 2: State Machine Implementation (3 hours)

**Goal**: Implement deterministic state machine with phase transitions.

**File**: `scripts/orchestrator/state_machine.py`

**Implementation**:

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
from pathlib import Path
import yaml
from logger import logger

class PipelinePhase(Enum):
    """Pipeline execution phases."""
    INIT = "init"
    REQUIREMENTS = "requirements"
    PLANNING = "planning"
    DEVELOPMENT = "development"
    INTEGRATION = "integration"
    DONE = "done"
    FAILED = "failed"

@dataclass
class PipelineState:
    """
    Complete state of the pipeline.
    All fields are deterministically updated based on artifacts and results.
    """
    # Core
    concept: str
    phase: PipelinePhase = PipelinePhase.INIT

    # Artifacts presence (filesystem-based)
    has_requirements: bool = False
    has_product_vision: bool = False
    has_stories: bool = False
    has_architecture: bool = False

    # Stories state
    total_stories: int = 0
    stories_todo: List[str] = field(default_factory=list)
    stories_doing: Dict[str, int] = field(default_factory=dict)  # story_id -> attempt
    stories_done: Set[str] = field(default_factory=set)
    stories_failed: Dict[str, List[str]] = field(default_factory=dict)  # story_id -> [errors]

    # Dependency tracking
    story_dependencies: Dict[str, List[str]] = field(default_factory=dict)  # story_id -> [depends_on]

    # Metrics
    iteration_number: int = 0
    step_number: int = 0

    def get_ready_stories(self) -> List[str]:
        """
        Return stories that:
        - Are in stories_todo
        - All dependencies are in stories_done
        - Not in stories_doing or stories_failed
        """
        ready = []
        for story_id in self.stories_todo:
            if story_id in self.stories_doing or story_id in self.stories_failed:
                continue

            deps = self.story_dependencies.get(story_id, [])
            if all(dep in self.stories_done for dep in deps):
                ready.append(story_id)

        return ready

    def get_blocked_stories(self) -> List[str]:
        """Return stories blocked by failed dependencies."""
        blocked = []
        failed_set = set(self.stories_failed.keys())

        for story_id in self.stories_todo:
            if story_id in failed_set:
                continue
            deps = self.story_dependencies.get(story_id, [])
            if any(dep in failed_set for dep in deps):
                blocked.append(story_id)

        return blocked


class StateMachine:
    """
    Manages pipeline state and phase transitions.
    All transitions are deterministic based on artifact presence and story status.
    """

    # Valid transitions
    TRANSITIONS = {
        PipelinePhase.INIT: [PipelinePhase.REQUIREMENTS],
        PipelinePhase.REQUIREMENTS: [PipelinePhase.PLANNING],
        PipelinePhase.PLANNING: [PipelinePhase.DEVELOPMENT, PipelinePhase.FAILED],
        PipelinePhase.DEVELOPMENT: [PipelinePhase.INTEGRATION, PipelinePhase.PLANNING, PipelinePhase.FAILED],
        PipelinePhase.INTEGRATION: [PipelinePhase.DONE, PipelinePhase.DEVELOPMENT, PipelinePhase.FAILED],
        PipelinePhase.DONE: [],
        PipelinePhase.FAILED: [PipelinePhase.REQUIREMENTS],  # Can restart
    }

    def __init__(self, concept: str, planning_dir: Path):
        """Initialize state machine."""
        self.concept = concept
        self.planning_dir = planning_dir
        self.state = PipelineState(concept=concept)
        self._sync_state_from_filesystem()

    def get_state(self) -> PipelineState:
        """Get current state (synced from filesystem)."""
        self._sync_state_from_filesystem()
        return self.state

    def can_transition_to(self, next_phase: PipelinePhase) -> bool:
        """Check if transition is valid."""
        allowed = self.TRANSITIONS.get(self.state.phase, [])
        return next_phase in allowed

    def transition_to(self, next_phase: PipelinePhase, reason: str) -> None:
        """
        Perform state transition with validation.

        Args:
            next_phase: Target phase
            reason: Human-readable reason for transition

        Raises:
            ValueError: If transition is invalid
        """
        if not self.can_transition_to(next_phase):
            raise ValueError(
                f"Invalid transition: {self.state.phase.value} → {next_phase.value}. "
                f"Allowed: {[p.value for p in self.TRANSITIONS.get(self.state.phase, [])]}"
            )

        logger.info(
            f"[state_machine] Transitioning: {self.state.phase.value} → {next_phase.value} ({reason})"
        )
        self.state.phase = next_phase

    def update_from_results(self, results: List[Dict]) -> None:
        """
        Update state based on action results.

        Args:
            results: List of action results with 'tool', 'status', 'story_id' fields
        """
        for result in results:
            tool = result.get("tool")
            status = result.get("status", "").lower()
            story_id = result.get("story_id")

            # Update artifact presence
            if tool == "RUN_BA" and status == "ok":
                self.state.has_requirements = True
            elif tool == "RUN_PO" and status == "ok":
                self.state.has_product_vision = True
            elif tool == "RUN_ARCHITECT" and status == "ok":
                self.state.has_stories = True
                self.state.has_architecture = True

            # Update story status
            if story_id:
                if status in {"ok", "passed"}:
                    if tool == "RUN_DEV_STORY":
                        # Dev success → mark as doing (needs QA)
                        if story_id in self.state.stories_todo:
                            self.state.stories_todo.remove(story_id)
                        self.state.stories_doing[story_id] = self.state.stories_doing.get(story_id, 0)

                    elif tool == "RUN_QA_STORY":
                        # QA success → mark as done
                        self.state.stories_done.add(story_id)
                        self.state.stories_doing.pop(story_id, None)
                        self.state.stories_failed.pop(story_id, None)

                elif status in {"failed", "error"}:
                    error_msg = result.get("error", "Unknown error")
                    if story_id not in self.state.stories_failed:
                        self.state.stories_failed[story_id] = []
                    self.state.stories_failed[story_id].append(error_msg)
                    self.state.stories_doing.pop(story_id, None)

        # Re-sync from filesystem to catch any file changes
        self._sync_state_from_filesystem()

    def _sync_state_from_filesystem(self) -> None:
        """Sync state with actual filesystem artifacts."""
        # Check artifact files
        self.state.has_requirements = (self.planning_dir / "requirements.yaml").exists()
        self.state.has_product_vision = (self.planning_dir / "product_owner_review.yaml").exists()
        self.state.has_stories = (self.planning_dir / "stories.yaml").exists()
        self.state.has_architecture = (self.planning_dir / "architecture.yaml").exists()

        # Load stories if available
        if self.state.has_stories:
            self._load_stories_from_yaml()

    def _load_stories_from_yaml(self) -> None:
        """Load story state from stories.yaml."""
        stories_path = self.planning_dir / "stories.yaml"
        if not stories_path.exists():
            return

        try:
            with stories_path.open() as f:
                stories = yaml.safe_load(f) or []

            self.state.total_stories = len(stories)
            self.state.stories_todo = []

            for story in stories:
                story_id = story.get("id")
                if not story_id:
                    continue

                status = story.get("status", "todo").lower()
                depends_on = story.get("depends_on", [])

                # Update dependency tracking
                if depends_on:
                    self.state.story_dependencies[story_id] = depends_on

                # Update status
                if status == "todo":
                    if story_id not in self.state.stories_done and story_id not in self.state.stories_doing:
                        self.state.stories_todo.append(story_id)
                elif status == "done":
                    self.state.stories_done.add(story_id)
                elif status == "failed":
                    if story_id not in self.state.stories_failed:
                        self.state.stories_failed[story_id] = ["Previous failure"]

        except Exception as exc:
            logger.error(f"[state_machine] Failed to load stories: {exc}")
```

**Acceptance Criteria**:
- [ ] `PipelinePhase` enum with 7 phases
- [ ] `PipelineState` dataclass with all fields
- [ ] `StateMachine` class with transition validation
- [ ] State syncs from filesystem (requirements.yaml, stories.yaml)
- [ ] `get_ready_stories()` respects dependencies
- [ ] Invalid transitions raise `ValueError`

**Tests**:
```python
# tests/test_state_machine.py

def test_state_machine_initialization():
    """Test state machine starts in INIT phase."""
    sm = StateMachine(concept="Test", planning_dir=Path("/tmp"))
    assert sm.state.phase == PipelinePhase.INIT
    assert sm.state.concept == "Test"

def test_valid_transition():
    """Test valid phase transition."""
    sm = StateMachine(concept="Test", planning_dir=Path("/tmp"))
    sm.transition_to(PipelinePhase.REQUIREMENTS, "Starting BA")
    assert sm.state.phase == PipelinePhase.REQUIREMENTS

def test_invalid_transition():
    """Test invalid transition raises error."""
    sm = StateMachine(concept="Test", planning_dir=Path("/tmp"))
    with pytest.raises(ValueError, match="Invalid transition"):
        sm.transition_to(PipelinePhase.DEVELOPMENT, "Skip ahead")

def test_state_sync_from_filesystem(tmp_path):
    """Test state syncs with filesystem artifacts."""
    planning_dir = tmp_path / "planning"
    planning_dir.mkdir()

    # Create requirements.yaml
    (planning_dir / "requirements.yaml").write_text("meta:\n  test: true\n")

    sm = StateMachine(concept="Test", planning_dir=planning_dir)
    state = sm.get_state()
    assert state.has_requirements is True
    assert state.has_stories is False

def test_get_ready_stories_with_dependencies(tmp_path):
    """Test ready stories calculation with dependencies."""
    planning_dir = tmp_path / "planning"
    planning_dir.mkdir()

    stories = [
        {"id": "S1", "status": "todo", "depends_on": []},
        {"id": "S2", "status": "todo", "depends_on": ["S1"]},
        {"id": "S3", "status": "todo", "depends_on": ["S1"]},
    ]
    (planning_dir / "stories.yaml").write_text(yaml.dump(stories))

    sm = StateMachine(concept="Test", planning_dir=planning_dir)
    state = sm.get_state()

    # Initially, only S1 is ready (no dependencies)
    ready = state.get_ready_stories()
    assert ready == ["S1"]

    # Mark S1 as done
    state.stories_done.add("S1")
    state.stories_todo.remove("S1")

    # Now S2 and S3 should be ready
    ready = state.get_ready_stories()
    assert set(ready) == {"S2", "S3"}
```

---

### Task 3: Story DAG Implementation (2 hours)

**Goal**: Implement dependency graph with topological sorting and parallel batch selection.

**File**: `scripts/orchestrator/story_dag.py`

**Implementation**:

```python
from collections import defaultdict, deque
from typing import Dict, List, Set
from logger import logger

class StoryDAG:
    """
    Directed Acyclic Graph for story dependencies.
    Supports dependency tracking, topological sorting, and parallel batch selection.
    """

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}  # story_id -> story metadata
        self.edges: Dict[str, List[str]] = defaultdict(list)  # story_id -> [depends_on]
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)  # story_id -> [blocks]

    def add_story(self, story_id: str, metadata: Dict, depends_on: List[str] = None) -> None:
        """
        Add story to graph.

        Args:
            story_id: Unique story identifier
            metadata: Story data (description, priority, etc.)
            depends_on: List of story IDs this story depends on
        """
        self.nodes[story_id] = metadata

        if depends_on:
            for dep in depends_on:
                self.edges[story_id].append(dep)
                self.reverse_edges[dep].append(story_id)

        logger.debug(f"[dag] Added story {story_id} with {len(depends_on or [])} dependencies")

    def get_ready_stories(
        self,
        done_stories: Set[str],
        failed_stories: Set[str],
        doing_stories: Set[str]
    ) -> List[str]:
        """
        Return stories that are ready to execute.

        A story is ready if:
        - All dependencies are in done_stories
        - Not in done_stories, failed_stories, or doing_stories

        Results are sorted by priority (P0 > P1 > P2) and then by story ID.

        Args:
            done_stories: Set of completed story IDs
            failed_stories: Set of failed story IDs
            doing_stories: Set of in-progress story IDs

        Returns:
            List of ready story IDs, sorted by priority
        """
        ready = []

        for story_id, deps in self.edges.items():
            # Skip if already processed
            if story_id in done_stories or story_id in failed_stories or story_id in doing_stories:
                continue

            # Check if all dependencies are satisfied
            if all(dep in done_stories for dep in deps):
                ready.append(story_id)

        # Also check stories with no dependencies
        for story_id in self.nodes.keys():
            if (story_id not in self.edges or not self.edges[story_id]) and \
               story_id not in done_stories and \
               story_id not in failed_stories and \
               story_id not in doing_stories:
                if story_id not in ready:
                    ready.append(story_id)

        # Sort by priority and ID
        ready.sort(key=lambda sid: (
            self.nodes[sid].get("priority", "P9"),
            sid
        ))

        logger.debug(f"[dag] Found {len(ready)} ready stories: {ready}")
        return ready

    def get_blocked_stories(self, failed_stories: Set[str]) -> Set[str]:
        """
        Return stories blocked by failed dependencies (transitively).

        Args:
            failed_stories: Set of failed story IDs

        Returns:
            Set of blocked story IDs
        """
        blocked = set()
        queue = deque(failed_stories)

        while queue:
            failed_story = queue.popleft()
            for dependent in self.reverse_edges.get(failed_story, []):
                if dependent not in blocked:
                    blocked.add(dependent)
                    queue.append(dependent)

        logger.debug(f"[dag] Found {len(blocked)} blocked stories: {blocked}")
        return blocked

    def get_parallel_batch(
        self,
        ready_stories: List[str],
        max_parallelism: int = 3
    ) -> List[str]:
        """
        Select up to max_parallelism stories for parallel execution.

        Strategy:
        - Stories from different epics can run in parallel
        - Stories from the same epic run sequentially (shared context)
        - Priority is respected

        Args:
            ready_stories: List of ready story IDs
            max_parallelism: Maximum number of stories to return

        Returns:
            List of story IDs for parallel execution
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

        logger.info(f"[dag] Selected batch of {len(batch)} stories for parallel execution: {batch}")
        return batch

    def topological_sort(self) -> List[str]:
        """
        Return stories in topological order (dependencies first).

        Returns:
            List of story IDs in execution order

        Raises:
            ValueError: If graph contains a cycle
        """
        in_degree = {node: 0 for node in self.nodes}

        for deps in self.edges.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        sorted_order = []

        while queue:
            node = queue.popleft()
            sorted_order.append(node)

            for neighbor in self.reverse_edges.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_order) != len(self.nodes):
            raise ValueError("Graph contains a cycle")

        return sorted_order
```

**Acceptance Criteria**:
- [ ] `StoryDAG` class with add_story method
- [ ] `get_ready_stories()` returns only stories with satisfied dependencies
- [ ] `get_blocked_stories()` transitively finds blocked stories
- [ ] `get_parallel_batch()` groups by epic and respects max_parallelism
- [ ] `topological_sort()` returns valid execution order
- [ ] Cycle detection raises `ValueError`

**Tests**:
```python
# tests/test_story_dag.py

def test_dag_simple_dependency():
    """Test DAG with simple linear dependency."""
    dag = StoryDAG()
    dag.add_story("S1", {"priority": "P1"}, depends_on=[])
    dag.add_story("S2", {"priority": "P1"}, depends_on=["S1"])

    # Initially, only S1 is ready
    ready = dag.get_ready_stories(done_stories=set(), failed_stories=set(), doing_stories=set())
    assert ready == ["S1"]

    # After S1 done, S2 is ready
    ready = dag.get_ready_stories(done_stories={"S1"}, failed_stories=set(), doing_stories=set())
    assert ready == ["S2"]

def test_dag_parallel_stories():
    """Test DAG with parallel independent stories."""
    dag = StoryDAG()
    dag.add_story("S1", {"priority": "P1", "epic": "E1"}, depends_on=[])
    dag.add_story("S2", {"priority": "P1", "epic": "E2"}, depends_on=[])
    dag.add_story("S3", {"priority": "P1", "epic": "E3"}, depends_on=[])

    ready = dag.get_ready_stories(done_stories=set(), failed_stories=set(), doing_stories=set())
    assert set(ready) == {"S1", "S2", "S3"}

    # Get parallel batch (max 2)
    batch = dag.get_parallel_batch(ready, max_parallelism=2)
    assert len(batch) == 2

def test_dag_blocked_by_failure():
    """Test that stories are blocked when dependencies fail."""
    dag = StoryDAG()
    dag.add_story("S1", {"priority": "P1"}, depends_on=[])
    dag.add_story("S2", {"priority": "P1"}, depends_on=["S1"])
    dag.add_story("S3", {"priority": "P1"}, depends_on=["S2"])

    # S1 fails
    blocked = dag.get_blocked_stories(failed_stories={"S1"})
    assert blocked == {"S2", "S3"}

def test_dag_topological_sort():
    """Test topological sorting of stories."""
    dag = StoryDAG()
    dag.add_story("S1", {}, depends_on=[])
    dag.add_story("S2", {}, depends_on=["S1"])
    dag.add_story("S3", {}, depends_on=["S1"])
    dag.add_story("S4", {}, depends_on=["S2", "S3"])

    order = dag.topological_sort()

    # S1 must come before S2, S3, S4
    assert order.index("S1") < order.index("S2")
    assert order.index("S1") < order.index("S3")
    assert order.index("S1") < order.index("S4")

    # S2 and S3 must come before S4
    assert order.index("S2") < order.index("S4")
    assert order.index("S3") < order.index("S4")
```

---

### Task 4: Policy Engine Implementation (2 hours)

**Goal**: Implement YAML-driven policy evaluation for retries, escalation, and resources.

**File**: `scripts/orchestrator/policy_engine.py`

**Implementation**:

```python
from typing import Dict, Optional, List
from logger import logger

class PolicyEngine:
    """
    Evaluates policies for retries, escalation, and resource constraints.
    All policies are defined in config.yaml (no hardcoded logic).
    """

    def __init__(self, config: Dict):
        """
        Initialize policy engine from config.

        Args:
            config: Configuration dict with 'pipeline' section
        """
        pipeline_config = config.get("pipeline", {})

        self.retry_policies = pipeline_config.get("retry_policies", {})
        self.escalation_policies = pipeline_config.get("escalation_policies", [])
        self.resource_policies = pipeline_config.get("resource_policies", {})
        self.priority_policies = pipeline_config.get("priority_policies", [])

        logger.info(f"[policy] Loaded {len(self.escalation_policies)} escalation policies")
        logger.info(f"[policy] Resource limits: {self.resource_policies}")

    def should_retry(self, role: str, attempts: int) -> bool:
        """
        Check if retry is allowed by policy.

        Args:
            role: Role name (e.g., "dev", "architect")
            attempts: Number of attempts so far

        Returns:
            True if retry is allowed
        """
        policy = self.retry_policies.get(role, {})
        max_attempts = policy.get("max_attempts", 3)

        should_retry = attempts < max_attempts
        logger.debug(f"[policy] Retry check for {role}: {attempts}/{max_attempts} -> {should_retry}")
        return should_retry

    def get_backoff_delay(self, role: str, attempt: int) -> float:
        """
        Calculate backoff delay in seconds.

        Args:
            role: Role name
            attempt: Attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        policy = self.retry_policies.get(role, {})
        backoff_type = policy.get("backoff", "none")

        if backoff_type == "exponential":
            delay = 60 * (2 ** (attempt - 1))  # 1min, 2min, 4min, 8min
        elif backoff_type == "linear":
            delay = 60 * attempt  # 1min, 2min, 3min
        else:
            delay = 0

        logger.debug(f"[policy] Backoff for {role} attempt {attempt}: {delay}s ({backoff_type})")
        return delay

    def get_max_parallel_stories(self) -> int:
        """Get maximum number of stories that can run in parallel."""
        return self.resource_policies.get("max_parallel_stories", 3)

    def get_timeout(self, role: str) -> int:
        """
        Get timeout in seconds for a role.

        Args:
            role: Role name (e.g., "dev", "qa")

        Returns:
            Timeout in seconds
        """
        key = f"{role}_timeout"
        return self.resource_policies.get(key, 600)

    def evaluate_escalation(
        self,
        story_id: str,
        attempts: int,
        error_history: List[str],
        context: Dict
    ) -> Optional[str]:
        """
        Evaluate if escalation is needed.

        Args:
            story_id: Story ID
            attempts: Number of attempts
            error_history: List of error messages
            context: Additional context (e.g., test results)

        Returns:
            Action name if escalation needed, None otherwise
        """
        for policy in self.escalation_policies:
            condition = policy.get("condition", "")
            action = policy.get("action", "")

            # Simple condition evaluation
            # In production, use a proper expression parser
            if self._evaluate_condition(condition, attempts, error_history, context):
                logger.warning(f"[policy] Escalation triggered: {policy.get('reason', 'N/A')}")
                return action

        return None

    def _evaluate_condition(
        self,
        condition: str,
        attempts: int,
        error_history: List[str],
        context: Dict
    ) -> bool:
        """
        Evaluate escalation condition.

        Supported conditions:
        - "dev_attempts >= 3"
        - "dev_attempts >= 3 AND same_error_pattern"
        - "qa_coverage < 0.8"

        Args:
            condition: Condition string
            attempts: Number of attempts
            error_history: List of errors
            context: Additional context

        Returns:
            True if condition matches
        """
        # Build evaluation context
        same_error_pattern = len(set(error_history)) == 1 and len(error_history) >= 2

        eval_ctx = {
            "dev_attempts": attempts,
            "same_error_pattern": same_error_pattern,
            "qa_coverage": context.get("qa_coverage", 1.0),
            "tests_failed": context.get("tests_failed", 0),
        }

        try:
            # Simple eval (in production, use ast.literal_eval or a DSL parser)
            return eval(condition, {"__builtins__": {}}, eval_ctx)
        except Exception as exc:
            logger.error(f"[policy] Failed to evaluate condition '{condition}': {exc}")
            return False
```

**Config Schema** (`config.yaml`):
```yaml
pipeline:
  # Retry policies
  retry_policies:
    dev:
      max_attempts: 3
      backoff: exponential  # exponential, linear, none

    architect:
      max_attempts: 2
      backoff: linear

    qa:
      max_attempts: 2
      backoff: none

  # Escalation policies
  escalation_policies:
    - condition: "dev_attempts >= 3 AND same_error_pattern"
      action: "architect_refine"
      reason: "Repeated Dev failures suggest architectural issue"

    - condition: "qa_coverage < 0.8 AND tests_failed > 0"
      action: "architect_review_tests"
      reason: "Low coverage with failures needs design review"

  # Resource policies
  resource_policies:
    max_parallel_stories: 3
    max_concurrent_dev: 2
    max_concurrent_qa: 1
    dev_timeout: 600      # 10 minutes
    qa_timeout: 300       # 5 minutes

  # Priority policies
  priority_policies:
    - priority: P0
      max_retries: 5
      timeout_multiplier: 2.0
    - priority: P1
      max_retries: 3
      timeout_multiplier: 1.0
```

**Acceptance Criteria**:
- [ ] `PolicyEngine` class loads config
- [ ] `should_retry()` respects max_attempts
- [ ] `get_backoff_delay()` calculates exponential/linear backoff
- [ ] `evaluate_escalation()` matches conditions
- [ ] `get_max_parallel_stories()` returns resource limit

**Tests**:
```python
# tests/test_policy_engine.py

def test_retry_policy():
    """Test retry policy evaluation."""
    config = {
        "pipeline": {
            "retry_policies": {
                "dev": {"max_attempts": 3, "backoff": "exponential"}
            }
        }
    }
    engine = PolicyEngine(config)

    assert engine.should_retry("dev", 0) is True
    assert engine.should_retry("dev", 2) is True
    assert engine.should_retry("dev", 3) is False

def test_backoff_exponential():
    """Test exponential backoff calculation."""
    config = {
        "pipeline": {
            "retry_policies": {
                "dev": {"backoff": "exponential"}
            }
        }
    }
    engine = PolicyEngine(config)

    assert engine.get_backoff_delay("dev", 1) == 60    # 1 min
    assert engine.get_backoff_delay("dev", 2) == 120   # 2 min
    assert engine.get_backoff_delay("dev", 3) == 240   # 4 min

def test_escalation_policy():
    """Test escalation policy matching."""
    config = {
        "pipeline": {
            "escalation_policies": [
                {
                    "condition": "dev_attempts >= 3 AND same_error_pattern",
                    "action": "architect_refine",
                    "reason": "Repeated failures"
                }
            ]
        }
    }
    engine = PolicyEngine(config)

    # Same error 3 times → escalate
    action = engine.evaluate_escalation(
        story_id="S1",
        attempts=3,
        error_history=["ImportError", "ImportError", "ImportError"],
        context={}
    )
    assert action == "architect_refine"

    # Different errors 3 times → no escalation
    action = engine.evaluate_escalation(
        story_id="S1",
        attempts=3,
        error_history=["ImportError", "SyntaxError", "NameError"],
        context={}
    )
    assert action is None
```

---

### Task 5: Rule-Based Planner (3 hours)

**Goal**: Implement deterministic planner that decides next actions without LLM.

**File**: `scripts/orchestrator/planner.py`

**Implementation** (see next comment due to length limit)

---

**Estimated Total Time for Task 1-5**: ~11 hours (1.5 days)

---

### Task 6: Integration with Existing Orchestrator (4 hours)

**Goal**: Integrate V2 components with `run_orchestrator_agent.py` without breaking existing functionality.

**Acceptance Criteria**:
- [ ] V2 can be enabled via `--use-v2` flag
- [ ] Existing orchestrator still works by default
- [ ] V2 uses same role executors (BA, PO, Architect, Dev, QA)
- [ ] V2 writes summary compatible with existing format

---

### Task 7: End-to-End Testing (4 hours)

**Goal**: Validate complete V2 pipeline with real execution.

**Tests**:
- [ ] Simple pipeline: BA → PO → Architect → Dev (3 stories) → QA
- [ ] DAG test: Stories with dependencies execute in correct order
- [ ] Retry test: Failed story retries with backoff
- [ ] Escalation test: Repeated failures trigger architect refinement
- [ ] Parallel test: 3 stories execute concurrently

---

## Deliverables

### Code Files
- [ ] `scripts/orchestrator/__init__.py`
- [ ] `scripts/orchestrator/state_machine.py`
- [ ] `scripts/orchestrator/story_dag.py`
- [ ] `scripts/orchestrator/policy_engine.py`
- [ ] `scripts/orchestrator/planner.py`
- [ ] `scripts/orchestrator/executor.py`
- [ ] `scripts/orchestrator/v2_runtime.py`

### Configuration
- [ ] Updated `config.yaml` with policy sections

### Tests
- [ ] `tests/test_state_machine.py` (>90% coverage)
- [ ] `tests/test_story_dag.py` (>90% coverage)
- [ ] `tests/test_policy_engine.py` (>90% coverage)
- [ ] `tests/test_planner.py` (>90% coverage)
- [ ] `tests/test_orchestrator_v2_integration.py` (E2E)

### Documentation
- [ ] Updated `CLAUDE.md` with V2 usage
- [ ] Docstrings in all modules
- [ ] Examples in `docs/ORCHESTRATOR_V2_EXAMPLES.md`

---

## Success Criteria

### Functional Requirements
- ✅ V2 orchestrator completes full pipeline (BA → PO → Architect → Dev → QA)
- ✅ Stories with dependencies execute in correct order
- ✅ Failed stories retry with exponential backoff
- ✅ Repeated failures trigger escalation to architect
- ✅ Parallel execution respects resource limits
- ✅ State machine enforces valid phase transitions

### Non-Functional Requirements
- ✅ 90%+ of decisions made by rules (not LLM)
- ✅ Test coverage >85%
- ✅ No regression: existing orchestrator still works
- ✅ Performance: ≤10% overhead vs current orchestrator

### Observability
- ✅ Every decision logged with rule name
- ✅ State transitions logged with reasons
- ✅ DAG scheduling decisions logged

---

## Risk Mitigation

### Risk 1: Breaking Existing Orchestrator
**Mitigation**:
- V2 is opt-in via `--use-v2` flag
- Keep existing code untouched
- Run smoke tests on both versions

### Risk 2: Complex DAG Logic
**Mitigation**:
- Start with simple linear dependencies
- Add complexity incrementally
- Extensive unit tests for edge cases

### Risk 3: Config Complexity
**Mitigation**:
- Provide sensible defaults
- Document all config options
- Validate config on startup

---

## Post-Phase 1 Roadmap

### Phase 2 (3 days): Coherence Checking
- Implement coherence checker
- Add automatic remediation
- LLM-based semantic validation

### Phase 3 (2 days): Chain-of-Thought
- Structured reasoning logs
- JSONL + Markdown export
- Confidence scores

### Phase 4 (2 days): Learning & Optimization
- Pattern detection from past executions
- Dynamic policy adjustment
- Performance optimization

---

## Notes

- **Backward Compatibility**: Critical - must not break existing workflows
- **Testing First**: Write tests before implementation (TDD)
- **Incremental**: Each task should be independently testable
- **Documentation**: Keep CLAUDE.md updated as we go

---

**Ready to start implementation?** Reply "start phase 1" to begin with Task 1.
