"""
State Machine for pipeline phase management.

Manages deterministic state transitions based on artifact presence and story status.
All state is synced with filesystem artifacts (requirements.yaml, stories.yaml, etc.).
"""

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
        Return stories that are ready to execute.

        A story is ready if:
        - Is in stories_todo
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
        """Return stories blocked by failed dependencies (including transitive blocking)."""
        failed_set = set(self.stories_failed.keys())
        blocked_set = set()

        # Build inverse dependency map: which stories depend on each story
        dependents = {}
        for story_id, deps in self.story_dependencies.items():
            for dep in deps:
                if dep not in dependents:
                    dependents[dep] = []
                dependents[dep].append(story_id)

        # BFS to find all transitively blocked stories
        queue = list(failed_set)
        while queue:
            failed_story = queue.pop(0)
            for dependent in dependents.get(failed_story, []):
                if dependent not in blocked_set and dependent not in failed_set:
                    blocked_set.add(dependent)
                    queue.append(dependent)

        return list(blocked_set)


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
        logger.info(f"[state_machine] Initialized: concept='{concept}', phase={self.state.phase.value}")

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
            allowed = [p.value for p in self.TRANSITIONS.get(self.state.phase, [])]
            raise ValueError(
                f"Invalid transition: {self.state.phase.value} → {next_phase.value}. "
                f"Allowed: {allowed}"
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
            tool = result.get("tool", "").upper()
            status = result.get("status", "").lower()
            story_id = result.get("story_id")

            # Update artifact presence
            if tool == "RUN_BA" and status in {"ok", "success"}:
                self.state.has_requirements = True
                logger.debug("[state_machine] Artifact created: requirements.yaml")

            elif tool == "RUN_PO" and status in {"ok", "success"}:
                self.state.has_product_vision = True
                logger.debug("[state_machine] Artifact created: product_owner_review.yaml")

            elif tool == "RUN_ARCHITECT" and status in {"ok", "success"}:
                self.state.has_stories = True
                self.state.has_architecture = True
                logger.debug("[state_machine] Artifacts created: stories.yaml, architecture.yaml")

            # Update story status
            if story_id:
                if status in {"ok", "passed", "success"}:
                    if tool == "RUN_DEV_STORY":
                        # Dev success → mark as doing (needs QA)
                        if story_id in self.state.stories_todo:
                            self.state.stories_todo.remove(story_id)
                        self.state.stories_doing[story_id] = self.state.stories_doing.get(story_id, 0) + 1
                        logger.debug(f"[state_machine] Story {story_id}: todo → doing")

                    elif tool == "RUN_QA_STORY":
                        # QA success → mark as done
                        self.state.stories_done.add(story_id)
                        self.state.stories_doing.pop(story_id, None)
                        self.state.stories_failed.pop(story_id, None)
                        logger.debug(f"[state_machine] Story {story_id}: doing → done")

                elif status in {"failed", "error", "exception"}:
                    error_msg = result.get("error", "Unknown error")
                    if story_id not in self.state.stories_failed:
                        self.state.stories_failed[story_id] = []
                    self.state.stories_failed[story_id].append(error_msg)
                    self.state.stories_doing.pop(story_id, None)
                    logger.warning(f"[state_machine] Story {story_id}: failed ({error_msg})")

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

            if not stories:
                logger.warning("[state_machine] stories.yaml is empty")
                return

            self.state.total_stories = len(stories)
            self.state.stories_todo = []

            for story in stories:
                if not isinstance(story, dict):
                    continue

                story_id = story.get("id")
                if not story_id:
                    continue

                status = story.get("status", "todo").lower()
                depends_on = story.get("depends_on", []) or []

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

            logger.debug(
                f"[state_machine] Loaded stories: total={self.state.total_stories}, "
                f"todo={len(self.state.stories_todo)}, done={len(self.state.stories_done)}, "
                f"failed={len(self.state.stories_failed)}"
            )

        except Exception as exc:
            logger.error(f"[state_machine] Failed to load stories: {exc}")
