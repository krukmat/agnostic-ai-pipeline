"""Dual-write helper for gradual migration from YAML to SQLite.

This module provides functions that write to both YAML (existing) and SQLite (new).
Enable via config.yaml: database.enabled = true
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .storage import get_db, is_db_enabled, get_db_config
from .schema import create_schema
from .repository import (
    ProjectRepository,
    IterationRepository,
    StoryRepository,
    StoryAttemptRepository,
    RoleArtifactRepository,
    EventLogRepository,
)


class DualWriteContext:
    """Context manager for dual-write operations.

    Usage:
        with DualWriteContext(project_name, concept) as ctx:
            ctx.log_event("role_start", role="ba")
            ctx.save_artifact("ba", "requirements", content)
            ctx.create_stories(stories_list)
            ctx.log_attempt(story_db_id, ...)
    """

    def __init__(self, project_name: str, concept: str, iteration_id: Optional[int] = None):
        self.project_name = project_name
        self.concept = concept
        self._enabled = is_db_enabled()
        self._db = None
        self._project_id: Optional[int] = None
        self._iteration_id: Optional[int] = iteration_id

        # Repositories
        self._projects: Optional[ProjectRepository] = None
        self._iterations: Optional[IterationRepository] = None
        self._stories: Optional[StoryRepository] = None
        self._attempts: Optional[StoryAttemptRepository] = None
        self._artifacts: Optional[RoleArtifactRepository] = None
        self._events: Optional[EventLogRepository] = None

    def __enter__(self) -> "DualWriteContext":
        if not self._enabled:
            return self

        self._db = get_db()
        create_schema(self._db)  # Ensure schema exists

        # Initialize repositories
        self._projects = ProjectRepository(self._db)
        self._iterations = IterationRepository(self._db)
        self._stories = StoryRepository(self._db)
        self._attempts = StoryAttemptRepository(self._db)
        self._artifacts = RoleArtifactRepository(self._db)
        self._events = EventLogRepository(self._db)

        # Get or create project
        project = self._projects.get_by_name(self.project_name)
        if project:
            self._project_id = project["id"]
        else:
            self._project_id = self._projects.create(self.project_name, self.concept)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't close DB - it's a singleton
        return False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def project_id(self) -> Optional[int]:
        return self._project_id

    @property
    def iteration_id(self) -> Optional[int]:
        return self._iteration_id

    def start_iteration(self, loops_requested: int = 1, config_snapshot: Dict = None) -> Optional[int]:
        """Start a new iteration and return its ID."""
        if not self._enabled or not self._iterations:
            return None

        self._iteration_id = self._iterations.create(
            self._project_id,
            loops_requested=loops_requested,
            config_snapshot=config_snapshot,
        )
        self.log_event("iteration_start", f"Started iteration {self._iteration_id}")
        return self._iteration_id

    def end_iteration(self, status: str = "completed") -> None:
        """Mark current iteration as finished."""
        if not self._enabled or not self._iterations or not self._iteration_id:
            return

        self._iterations.update_status(self._iteration_id, status)
        self.log_event("iteration_end", f"Iteration {self._iteration_id} ended with status {status}")

    def increment_loop(self) -> None:
        """Increment loop counter for current iteration."""
        if not self._enabled or not self._iterations or not self._iteration_id:
            return
        self._iterations.increment_loops(self._iteration_id)

    def log_event(
        self,
        event_type: str,
        message: str = None,
        role: str = None,
        story_id: int = None,
        severity: str = "info",
        payload: Dict = None,
    ) -> Optional[int]:
        """Log an event to the event_log table."""
        if not self._enabled or not self._events:
            return None

        return self._events.log(
            event_type=event_type,
            message=message,
            project_id=self._project_id,
            iteration_id=self._iteration_id,
            story_id=story_id,
            role=role,
            severity=severity,
            payload=payload,
        )

    def save_artifact(
        self,
        role: str,
        artifact_type: str,
        content: Any,
    ) -> Optional[int]:
        """Save a role artifact (requirements, product_vision, etc.)."""
        if not self._enabled or not self._artifacts:
            return None

        return self._artifacts.create(
            project_id=self._project_id,
            role=role,
            artifact_type=artifact_type,
            content=content,
            iteration_id=self._iteration_id,
        )

    def _normalize_priority(self, priority: str) -> Optional[str]:
        """Normalize priority to P0-P3 format."""
        if not priority:
            return None
        p = str(priority).strip().upper()
        # Accept P0, P1, P2, P3 directly
        if p in ("P0", "P1", "P2", "P3"):
            return p
        # Map numeric priorities
        if p in ("0", "1", "2", "3"):
            return f"P{p}"
        # Map high/medium/low
        priority_map = {
            "HIGH": "P1", "ALTA": "P1",
            "MEDIUM": "P2", "MED": "P2", "MEDIA": "P2",
            "LOW": "P3", "BAJA": "P3",
            "CRITICAL": "P0", "CRITICA": "P0",
        }
        return priority_map.get(p, None)  # Return None for unknown

    def create_story(
        self,
        story_id: str,
        title: str,
        description: str = None,
        priority: str = None,
        estimate: str = None,
        acceptance_criteria: List = None,
        depends_on: List = None,
    ) -> Optional[int]:
        """Create a story in the database."""
        if not self._enabled or not self._stories or not self._iteration_id:
            return None

        # Task: database-layer - Normalize priority to match CHECK constraint
        normalized_priority = self._normalize_priority(priority)

        return self._stories.create(
            iteration_id=self._iteration_id,
            story_id=story_id,
            title=title,
            description=description,
            priority=normalized_priority,
            estimate=estimate,
            acceptance_criteria=acceptance_criteria,
            depends_on=depends_on,
        )

    def create_stories_from_list(self, stories: List[Dict]) -> Dict[str, int]:
        """Create multiple stories from a list of dicts. Returns mapping of story_id -> db_id."""
        if not self._enabled or not self._stories or not self._iteration_id:
            return {}

        mapping = {}
        for s in stories:
            db_id = self.create_story(
                story_id=s.get("id", ""),
                title=s.get("title", s.get("name", "")),
                description=s.get("description", ""),
                priority=s.get("priority"),
                estimate=s.get("estimate"),
                acceptance_criteria=s.get("acceptance", s.get("acceptance_criteria")),
                depends_on=s.get("depends_on"),
            )
            if db_id:
                mapping[s.get("id", "")] = db_id
        return mapping

    def update_story_status(self, story_id: str, status: str) -> None:
        """Update a story's status by its story_id (e.g., 'S1')."""
        if not self._enabled or not self._stories or not self._iteration_id:
            return

        story = self._stories.get_by_story_id(self._iteration_id, story_id)
        if story:
            self._stories.update_status(story["id"], status)

    def update_story_metadata(self, story_id: str, metadata: Dict) -> None:
        """Update a story's metadata by its story_id."""
        if not self._enabled or not self._stories or not self._iteration_id:
            return

        story = self._stories.get_by_story_id(self._iteration_id, story_id)
        if story:
            self._stories.update_metadata(story["id"], metadata)

    def get_story_db_id(self, story_id: str) -> Optional[int]:
        """Get the database ID for a story by its story_id."""
        if not self._enabled or not self._stories or not self._iteration_id:
            return None

        story = self._stories.get_by_story_id(self._iteration_id, story_id)
        return story["id"] if story else None

    def log_attempt(
        self,
        story_id: str,
        role: str,
        provider: str,
        model: str,
        status: str,
        duration_ms: int = None,
        tokens_in: int = None,
        tokens_out: int = None,
        cost_usd: float = None,
        error_message: str = None,
        error_category: str = None,
        artifacts_path: str = None,
        raw_response_path: str = None,
    ) -> Optional[int]:
        """Log a story attempt (dev, qa, architect_review)."""
        if not self._enabled or not self._attempts:
            return None

        db_story_id = self.get_story_db_id(story_id)
        if not db_story_id:
            return None

        # Get attempt number
        attempt_number = self._attempts.count_attempts(db_story_id, role) + 1

        return self._attempts.create(
            story_id=db_story_id,
            attempt_number=attempt_number,
            role=role,
            provider=provider,
            model=model,
            status=status,
            duration_ms=duration_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            error_message=error_message,
            error_category=error_category,
            artifacts_path=artifacts_path,
            raw_response_path=raw_response_path,
        )

    def get_story_counts(self) -> Dict[str, int]:
        """Get story counts by status for current iteration."""
        if not self._enabled or not self._stories or not self._iteration_id:
            return {}
        return self._stories.count_by_status(self._iteration_id)


# Singleton context for orchestrator use
_current_context: Optional[DualWriteContext] = None


def get_current_context() -> Optional[DualWriteContext]:
    """Get the current dual-write context (if any)."""
    return _current_context


def set_current_context(ctx: Optional[DualWriteContext]) -> None:
    """Set the current dual-write context."""
    global _current_context
    _current_context = ctx


def db_enabled() -> bool:
    """Check if database dual-write is enabled."""
    return is_db_enabled()


def load_stories_from_db(iteration_id: int) -> List[Dict]:
    """Load stories from database for a given iteration.

    Task: database-layer - Fase 4 cut-over

    Returns list of story dicts compatible with YAML format.
    """
    if not is_db_enabled():
        return []

    db = get_db()
    stories_repo = StoryRepository(db)
    db_stories = stories_repo.list_by_iteration(iteration_id)

    result = []
    for s in db_stories:
        story = {
            "id": s["story_id"],
            "title": s["title"],
            "status": s["status"] or "todo",
        }
        if s.get("description"):
            story["description"] = s["description"]
        if s.get("priority"):
            story["priority"] = s["priority"]
        if s.get("estimate"):
            story["estimate"] = s["estimate"]
        if s.get("acceptance_criteria"):
            try:
                story["acceptance"] = json.loads(s["acceptance_criteria"])
            except:
                story["acceptance"] = s["acceptance_criteria"]
        if s.get("depends_on"):
            try:
                story["depends_on"] = json.loads(s["depends_on"])
            except:
                story["depends_on"] = s["depends_on"]
        result.append(story)

    return result


def export_stories_to_yaml(iteration_id: int, output_path: Path) -> bool:
    """Export stories from DB to YAML file.

    Task: database-layer - Fase 4 cut-over

    Returns True if export succeeded.
    """
    import yaml

    stories = load_stories_from_db(iteration_id)
    if not stories:
        return False

    output_path.write_text(
        yaml.safe_dump(stories, sort_keys=False, allow_unicode=True),
        encoding="utf-8"
    )
    return True


def backup_db_to_artifacts(artifacts_dir: Path) -> Optional[Path]:
    """Backup database to artifacts directory.

    Task: database-layer - Fase 4 cut-over

    Returns path to backup file if successful.
    """
    import shutil

    if not is_db_enabled():
        return None

    config = get_db_config()
    db_path = config["path"]

    if not db_path.exists():
        return None

    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = artifacts_dir / "db_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = backup_dir / f"pipeline_{timestamp}.db"
    shutil.copy2(db_path, backup_path)

    return backup_path
