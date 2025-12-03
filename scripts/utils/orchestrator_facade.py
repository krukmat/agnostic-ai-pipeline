from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import List, Dict, Any

import yaml

from common import PLANNING
from logger import logger


def load_stories_from_planning(planning_path: Path | None = None) -> List[Dict[str, Any]]:
    """Load stories from planning/stories.yaml, handling list or dict formats."""
    base = planning_path or PLANNING
    path = base / "stories.yaml"
    if not path.exists():
        logger.debug("[orchestrator] planning/stories.yaml not found.")
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        if isinstance(data, dict) and "stories" in data:
            data = data["stories"]
        return data if isinstance(data, list) else []
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"[orchestrator] Unable to parse stories.yaml: {exc}")
        return []


def derive_max_loops(
    default_loops: int,
    *,
    loops_arg_provided: bool,
    loops_env_provided: bool,
    planning_path: Path | None = None,
) -> int:
    """Derive MAX_LOOPS from stories.yaml only if caller did not set loops explicitly."""
    derived = max(1, default_loops)
    if loops_arg_provided or loops_env_provided:
        return derived

    stories = load_stories_from_planning(planning_path)
    todos = [s for s in stories if isinstance(s, dict) and str(s.get("status", "")).lower() == "todo"]
    if todos:
        derived = max(derived, len(todos))
        logger.info(f"[orchestrator] Derived MAX_LOOPS from stories.yaml: {derived}")
    return derived


def build_loop_env(concept: str, allow_no_tests: bool, max_loops: int) -> dict:
    """Compose environment for make loop respecting concept/test flags."""
    env = {
        "MAX_LOOPS": str(max(1, max_loops)),
        "ALLOW_NO_TESTS": "1" if allow_no_tests else "0",
    }
    if concept:
        env["CONCEPT"] = concept
    return env


def default_iteration_name(now: dt.datetime | None = None) -> str:
    """Generate default iteration name."""
    now = now or dt.datetime.utcnow()
    return now.strftime("iteration-%Y%m%d-%H%M%S")


def log_cycle_start(db_ctx, role: str, story_id: str, message: str) -> None:
    """Standardized start logging (no-op if logger missing)."""
    if getattr(db_ctx, "enabled", False) and hasattr(db_ctx, "log_event"):
        try:
            db_ctx.log_event(f"{role}_start", role=role, story_id=story_id, message=message)
        except Exception:
            logger.debug(f"[orchestrator] log_cycle_start failed for role={role}", exc_info=True)


def log_cycle_end(db_ctx, role: str, story_id: str, status: str, message: str) -> None:
    """Standardized end logging (no-op if logger missing)."""
    if getattr(db_ctx, "enabled", False) and hasattr(db_ctx, "log_event"):
        try:
            db_ctx.log_event(f"{role}_end", role=role, story_id=story_id, message=message, severity=status)
        except Exception:
            logger.debug(f"[orchestrator] log_cycle_end failed for role={role}", exc_info=True)
