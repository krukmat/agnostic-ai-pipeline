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


# --- Optional shared helpers (story/artifacts/report/db) ---

def resolve_story(story_env: str | None, planning_path: Path | None = None) -> Dict[str, Any] | None:
    """Resolve story by env ID (case-insensitive) else first TODO."""
    stories = load_stories_from_planning(planning_path)
    if not stories:
        return None
    if story_env:
        target = story_env.strip().lower()
        for s in stories:
            sid = str(s.get("id", "")).strip().lower()
            if sid == target:
                return s
    for s in stories:
        if str(s.get("status", "")).lower() == "todo":
            return s
    return None


def ensure_artifact_dir(root: Path, story_id: str) -> Path:
    """Ensure artifact directory for a story exists and return it."""
    path = root / story_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_run_name(now: dt.datetime | None = None, prefix: str = "run") -> str:
    """Default run name (prefix + timestamp)."""
    now = now or dt.datetime.utcnow()
    return f"{prefix}-{now:%Y%m%d-%H%M%S}"


def write_report_files(report: Dict[str, Any], story_art_dir: Path, last_report_dir: Path | None = None) -> Path:
    """Write report.json under story artifacts and optional last_report.json."""
    story_art_dir.mkdir(parents=True, exist_ok=True)
    report_path = story_art_dir / "report.json"
    report_path.write_text(yaml.safe_dump(report, sort_keys=False), encoding="utf-8")
    if last_report_dir:
        last_report_dir.mkdir(parents=True, exist_ok=True)
        (last_report_dir / "last_report.json").write_text(
            yaml.safe_dump(report, sort_keys=False),
            encoding="utf-8",
        )
    return report_path


def log_attempt_safe(
    db_ctx,
    *,
    story_id: str,
    role: str,
    status: str,
    provider: str = "unknown",
    model: str = "unknown",
    artifacts_path: str | None = None,
    error_message: str | None = None,
) -> None:
    """Wrapper around db.log_attempt that no-ops if disabled/missing."""
    if getattr(db_ctx, "enabled", False) and hasattr(db_ctx, "log_attempt"):
        try:
            db_ctx.log_attempt(
                story_id=story_id,
                role=role,
                status=status,
                provider=provider,
                model=model,
                artifacts_path=artifacts_path,
                error_message=error_message,
            )
        except Exception:
            logger.debug(f"[orchestrator] log_attempt_safe failed for role={role}", exc_info=True)
