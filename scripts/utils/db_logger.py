from __future__ import annotations

from typing import Any

from logger import logger
from scripts.utils.db_context import get_db_context_or_default


class DbLogger:
    """Safe wrapper around DB context operations used by run_* scripts."""

    def __init__(self, ctx: Any | None = None):
        self.ctx = ctx if ctx is not None else get_db_context_or_default()
        self.enabled = bool(getattr(self.ctx, "enabled", False))

    def log_event(self, *args, **kwargs) -> bool:
        if not self.enabled or not hasattr(self.ctx, "log_event"):
            return False
        try:
            self.ctx.log_event(*args, **kwargs)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"[DB] log_event skipped: {exc}")
            return False

    def save_artifact(self, *args, **kwargs) -> bool:
        if not self.enabled or not hasattr(self.ctx, "save_artifact"):
            return False
        try:
            self.ctx.save_artifact(*args, **kwargs)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"[DB] save_artifact skipped: {exc}")
            return False

    def log_attempt(
        self,
        *,
        story_id: str | None = None,
        role: str = "",
        provider: str = "",
        model: str = "",
        status: str = "",
        duration_ms: int | None = None,
        error_message: str | None = None,
        artifacts_path: str | None = None,
        **extra: Any,
    ) -> bool:
        if not self.enabled or not hasattr(self.ctx, "log_attempt"):
            return False
        try:
            self.ctx.log_attempt(
                story_id=story_id,
                role=role,
                provider=provider,
                model=model,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message,
                artifacts_path=artifacts_path,
                **extra,
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"[DB] log_attempt skipped: {exc}")
            return False
