from __future__ import annotations

import asyncio
import pathlib
from typing import Any, Dict

from common import load_config
from logger import logger
from scripts.utils.orchestrator_facade import load_stories_from_planning

from a2a.executors import get_executor, RoleExecutor
from a2a.metrics import instrumented
from scripts.run_ba import generate_requirements
from scripts.run_product_owner import main as run_po
from scripts.run_architect import run_architect_job
from scripts.run_dev import implement_story
from scripts.run_qa import run_quality_checks
from drivers.registry import load_driver, VALID_CATEGORIES


ROLE_SKILLS = {
    "business_analyst": "extract_requirements",
    "product_owner": "evaluate_alignment",
    "architect": "generate_plan",
    "developer": "implement_story",
    "qa": "run_quality_checks",
}


async def _local_business_analyst_handler(**payload: Any) -> Dict[str, Any]:
    concept = (payload.get("concept") or "").strip()
    if not concept:
        return {"status": "error", "detail": "concept is required"}
    try:
        result = await generate_requirements(concept)
        return {"status": "ok", **result}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[Executor] Business analyst handler failed.")
        return {"status": "exception", "error": str(exc)}


async def _local_product_owner_handler(**payload: Any) -> Dict[str, Any]:
    try:
        await run_po()
        return {"status": "ok"}
    except SystemExit as exc:
        exit_code = int(exc.code or 1)
        logger.warning(f"[Executor] Product owner exited with code {exit_code}.")
        return {"status": "error", "exit_code": exit_code}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[Executor] Product owner handler failed.")
        return {"status": "exception", "error": str(exc)}


async def _local_architect_handler(**payload: Any) -> Dict[str, Any]:
    try:
        result = await run_architect_job(
            concept=payload.get("concept"),
            architect_mode=payload.get("architect_mode", "normal"),
            story_id=payload.get("story_id", ""),
            detail_level=payload.get("detail_level", "medium"),
            iteration_count=int(payload.get("iteration_count", 1) or 1),
            force_tier=payload.get("force_tier"),
        )
        return {"status": "ok", **result}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[Executor] Architect handler failed.")
        return {"status": "exception", "error": str(exc)}


async def _local_developer_handler(**payload: Any) -> Dict[str, Any]:
    story_id = payload.get("story_id")
    retries_raw = payload.get("retries", payload.get("DEV_RETRIES", 3))
    try:
        retries = int(retries_raw)
    except (TypeError, ValueError):
        retries = 3
    try:
        result = await implement_story(story_id=story_id, retries=retries)
        if result.get("status") == "error":
            return result
        return {"status": "ok", **result}
    except SystemExit as exc:
        exit_code = int(exc.code or 1)
        logger.warning(
            f"[Executor] Developer exited with code {exit_code} for story {story_id}."
        )
        return {"status": "error", "exit_code": exit_code, "story_id": story_id}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[Executor] Developer handler failed.")
        return {"status": "exception", "error": str(exc), "story_id": story_id}


async def _local_qa_handler(**payload: Any) -> Dict[str, Any]:
    allow_flag = payload.get("allow_no_tests", True)
    if isinstance(allow_flag, str):
        allow_no_tests = str(allow_flag).lower() not in {"0", "false", "no"}
    else:
        allow_no_tests = bool(allow_flag)
    story_id = payload.get("story_id", "") or ""

    result = await asyncio.to_thread(
        run_quality_checks,
        allow_no_tests=allow_no_tests,
        story=story_id,
    )
    status = result.get("status", "unknown")
    return {"status": status, **result}


LOCAL_ROLE_HANDLERS = {
    "business_analyst": _local_business_analyst_handler,
    "product_owner": _local_product_owner_handler,
    "architect": _local_architect_handler,
    "developer": _local_developer_handler,
    "qa": _local_qa_handler,
}

_ROLE_EXECUTORS: dict[str, RoleExecutor] = {}


def _get_executor_for_role(role: str) -> RoleExecutor:
    if role not in LOCAL_ROLE_HANDLERS:
        raise KeyError(f"Unknown role '{role}' requested.")
    executor = _ROLE_EXECUTORS.get(role)
    if executor is None:
        handler = LOCAL_ROLE_HANDLERS[role]
        executor = get_executor(role, handler, skill_id=ROLE_SKILLS[role])
        _ROLE_EXECUTORS[role] = executor
    return executor


async def execute_role(role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        cfg = load_config()
        drv_cfg = (cfg.get("drivers") or {}) if isinstance(cfg, dict) else {}
        enabled = bool(drv_cfg.get("enabled", False))
        if enabled:
            proj = cfg.get("project") or {}
            targets = (proj.get("targets") or {}) if isinstance(proj, dict) else {}
            resolved = {}
            for cat in sorted(VALID_CATEGORIES):
                sel = targets.get(cat)
                if sel and str(sel).lower() != "none":
                    try:
                        drv = load_driver(cat, sel)
                        resolved[cat] = {
                            "id": drv.id,
                            "category": drv.category,
                            "language": drv.language,
                            "framework": drv.framework,
                            "build": getattr(drv.build, "command", None),
                            "test": getattr(drv.test, "command", None),
                            "lint": getattr(drv.lint, "command", None),
                            "artifact_paths": drv.artifact_paths,
                            "board": getattr(drv, "board", None),
                            "flash_command": getattr(drv, "flash_command", None),
                            "monitor_command": getattr(drv, "monitor_command", None),
                            "gpu_arch": getattr(drv, "gpu_arch", None),
                        }
                    except Exception as e:  # non-fatal: keep legacy behavior
                        logger.warning(f"[drivers] Failed to load driver {cat}/{sel}: {e}")
            if resolved:
                payload = dict(payload)
                payload["drivers"] = resolved
    except Exception as e:
        logger.warning(f"[drivers] Non-fatal driver wiring error: {e}")
    executor = _get_executor_for_role(role)

    @instrumented(role)
    async def _run() -> Dict[str, Any]:
        return await executor.execute(payload)

    return await _run()


def load_stories() -> list[dict[str, Any]]:
    """Load stories from planning/stories.yaml (no DB integration)."""
    return load_stories_from_planning()
