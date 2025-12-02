from __future__ import annotations

"""Lightweight DB context helper for standalone role scripts.

This provides a minimal get_current_context()-like object when the orchestrator
is not running, so Dev/QA/BA/PO/Architect can persist artifacts/attempts/events
without a full iteration context.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AdHocContext:
    project_id: int = 0
    iteration_id: int = 0

    def log_event(self, *_args, **_kwargs) -> None:
        # No-op placeholder; real logging is handled by src.db when available.
        return None

    def save_artifact(self, *_args, **_kwargs) -> None:
        # No-op placeholder; real persistence is handled by src.db when available.
        return None

    def create_stories_from_list(self, *_args, **_kwargs) -> None:
        return None

    @property
    def enabled(self) -> bool:
        return False


def get_db_context_or_default():
    """Return the real DB context if available; otherwise an ad-hoc stub."""
    try:
        from src.db import get_current_context, dual_write  # type: ignore

        ctx = get_current_context()
        if ctx:
            return ctx
    except Exception as exc:
        logger.warning("[db_context] Falling back to ad-hoc context (get_current_context failed: %s)", exc)

    try:
        # Attempt to create an ad-hoc context via dual_write helper
        return dual_write.get_or_create_adhoc_context()  # type: ignore[attr-defined]
    except Exception as exc:
        logger.warning("[db_context] Ad-hoc context creation failed (%s); returning stub", exc)
        return AdHocContext()
