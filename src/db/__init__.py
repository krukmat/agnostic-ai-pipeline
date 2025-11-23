"""Database layer for pipeline state management."""
from .storage import Database, get_db, get_db_config, is_db_enabled, reset_db
from .repository import (
    ProjectRepository,
    IterationRepository,
    StoryRepository,
    StoryAttemptRepository,
    RoleArtifactRepository,
    EventLogRepository,
)
from .dual_write import (
    DualWriteContext,
    get_current_context,
    set_current_context,
    db_enabled,
)

__all__ = [
    "Database",
    "get_db",
    "get_db_config",
    "is_db_enabled",
    "reset_db",
    "ProjectRepository",
    "IterationRepository",
    "StoryRepository",
    "StoryAttemptRepository",
    "RoleArtifactRepository",
    "EventLogRepository",
    "DualWriteContext",
    "get_current_context",
    "set_current_context",
    "db_enabled",
]
