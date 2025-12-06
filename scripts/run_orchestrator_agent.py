from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import time
from typing import Any, Dict, List

from common import ART, PLANNING, ensure_dirs, load_config
from logger import logger
from llm import Client
from scripts.orchestrator_runtime import execute_role, load_stories
from a2a.metrics import save_metrics

try:
    from src.db import DualWriteContext, db_enabled
except Exception:  # pragma: no cover - DB optional
    DualWriteContext = None  # type: ignore
    db_enabled = lambda: False  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "orchestrator.md"
ITERATIONS_DIR = ART / "iterations"


def _read_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


def _file_presence(path: pathlib.Path) -> dict:
    if not path.exists():
        return {"present": False}
    stat = path.stat()
    return {"present": True, "mtime": int(stat.st_mtime)}


def _summarize_stories() -> list[dict[str, Any]]:
    stories = load_stories() or []
    summary = []
    for item in stories:
        if not isinstance(item, dict):
            continue
        summary.append(
            {
                "id": item.get("id") or "",
                "title": item.get("title"),
                "status": item.get("status", "todo"),
                "last_error": item.get("error") or item.get("last_error"),
            }
        )
    return summary


def _read_last_qa_summary() -> dict[str, Any]:
    qa_dir = ART / "qa"
    summary_path = qa_dir / "last_report.json"
    if not summary_path.exists():
        return {}
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"[orchestrator] Failed to read QA summary: {exc}")
        return {}


def _read_dev_errors() -> dict[str, str]:
    # Collect last error per story from artifacts/dev/<story>/error.txt if exists
    dev_dir = ART / "dev"
    errors: dict[str, str] = {}
    if not dev_dir.exists():
        return errors
    for story_dir in dev_dir.iterdir():
        if not story_dir.is_dir():
            continue
        err_file = story_dir / "error.txt"
        if err_file.exists():
            try:
                errors[story_dir.name] = err_file.read_text(encoding="utf-8").strip()
            except Exception:
                continue
    return errors


def _build_context(
    concept: str,
    actions: list[dict[str, Any]],
    limits: dict[str, Any],
    stories_state: dict[str, dict[str, Any]],
) -> str:
    state = {
        "concept": concept,
        "artifacts": {
            "requirements": _file_presence(PLANNING / "requirements.yaml"),
            "stories": _file_presence(PLANNING / "stories.yaml"),
        },
        "stories": list(stories_state.values()) or _summarize_stories(),
        "qa_summary": _read_last_qa_summary(),
        "dev_errors": _read_dev_errors(),
        "recent_actions": actions[-5:],
        "limits": limits,
    }
    return json.dumps(state, ensure_ascii=True, indent=2)


def _parse_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"[orchestrator] Invalid JSON from LLM: {exc}")
        raise


async def _call_orchestrator(client: Client, concept: str, context: str) -> dict:
    prompt = _read_prompt()
    reply = await client.chat(system=prompt, user=context)
    try:
        return _parse_response(reply)
    except Exception:
        # Attempt a single repair prompt
        repair_user = json.dumps(
            {
                "context": context,
                "previous_response": reply,
                "instruction": "Repair the previous response into valid JSON with keys state_update, next_actions, termination.",
            },
            ensure_ascii=True,
        )
        logger.warning("[orchestrator] Repairing invalid JSON from LLM.")
        repaired = await client.chat(system=prompt, user=repair_user)
        return _parse_response(repaired)


def _update_story_state(
    stories_state: dict[str, dict[str, Any]], results: List[dict[str, Any]]
) -> None:
    ok_statuses = {"ok", "success", "passed", "tests_passed"}
    failed_statuses = {"failed", "error", "exception", "tests_failed"}
    for res in results:
        story_id = res.get("story_id") or res.get("arguments", {}).get("story_id")
        if not story_id:
            continue
        story_state = stories_state.get(story_id, {"id": story_id, "status": "todo"})
        status = str(res.get("status", "")).lower()
        tool = res.get("tool", "")
        if status in ok_statuses and tool in {"RUN_DEV_STORY", "RUN_QA_STORY"}:
            story_state["status"] = "done"
            story_state.pop("last_error", None)
        elif status in failed_statuses:
            story_state["status"] = "failed"
            if res.get("error"):
                story_state["last_error"] = res.get("error")
        stories_state[story_id] = story_state


async def _dispatch_actions(actions: List[dict[str, Any]]) -> List[dict[str, Any]]:
    results: List[dict[str, Any]] = []
    for action in actions:
        tool = action.get("tool")
        args = action.get("arguments") or {}
        start = time.time()
        if tool not in {
            "RUN_BA",
            "RUN_PO",
            "RUN_ARCHITECT",
            "RUN_DEV_STORY",
            "RUN_QA_STORY",
            "RUN_QA_FULL",
        }:
            logger.warning(f"[orchestrator] Unknown tool requested: {tool}")
            results.append(
                {"tool": tool, "status": "skipped", "error": "unknown_tool", "elapsed": 0}
            )
            continue

        role_map = {
            "RUN_BA": "business_analyst",
            "RUN_PO": "product_owner",
            "RUN_ARCHITECT": "architect",
            "RUN_DEV_STORY": "developer",
            "RUN_QA_STORY": "qa",
            "RUN_QA_FULL": "qa",
        }
        payload = dict(args)
        if tool == "RUN_QA_FULL":
            payload.setdefault("story_id", "")
        try:
            result = await execute_role(role_map[tool], payload)
            elapsed = time.time() - start
            status = result.get("status", "unknown")
            result_summary = {
                "tool": tool,
                "arguments": payload,
                "status": status,
                "elapsed": elapsed,
            }
            if "error" in result:
                result_summary["error"] = result.get("error")
            if "story_id" in payload and payload["story_id"]:
                result_summary["story_id"] = payload["story_id"]
            results.append(result_summary)
        except Exception as exc:  # pragma: no cover - defensive
            elapsed = time.time() - start
            logger.exception(f"[orchestrator] Action {tool} failed.")
            results.append(
                {"tool": tool, "status": "exception", "error": str(exc), "elapsed": elapsed}
            )
    return results


def _write_summary(concept: str, steps: List[dict[str, Any]], termination: dict[str, Any]):
    ITERATIONS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "concept": concept,
        "termination": termination,
        "steps": steps,
    }
    path = ITERATIONS_DIR / "latest_orchestrator_summary.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info(f"[orchestrator] Summary written to {path}")


async def run_agentic_orchestrator(concept: str, max_steps: int, max_actions_per_step: int):
    ensure_dirs()
    client = Client(role="orchestrator")
    steps: List[dict[str, Any]] = []
    recent_actions: List[dict[str, Any]] = []
    stories_state: dict[str, dict[str, Any]] = {
        s["id"]: s for s in _summarize_stories() if s.get("id")
    }

    limits = {"max_steps": max_steps, "max_actions_per_step": max_actions_per_step, "step": 0}

    async def loop():
        nonlocal limits, recent_actions, stories_state
        for idx in range(max_steps):
            limits["step"] = idx + 1
            context = _build_context(concept, recent_actions, limits, stories_state)
            try:
                decision = await _call_orchestrator(client, concept, context)
            except Exception:
                logger.error("[orchestrator] Aborting due to repeated JSON errors.")
                break

            next_actions = decision.get("next_actions") or []
            next_actions = next_actions[:max_actions_per_step]
            results = await _dispatch_actions(next_actions)
            _update_story_state(stories_state, results)

            step_entry = {
                "step": idx + 1,
                "decision": decision,
                "results": results,
            }
            steps.append(step_entry)
            recent_actions.extend(results)

            termination = (decision.get("termination") or {}).get("should_stop", False)
            if termination:
                _write_summary(concept, steps, decision.get("termination") or {})
                return

        # limits reached
        _write_summary(
            concept,
            steps,
            {"should_stop": True, "reason": "max_steps_reached"},
        )

    if db_enabled() and DualWriteContext:
        project_name = concept[:50].replace(" ", "_") or "agentic"
        with DualWriteContext(project_name, concept) as ctx:
            logger.info(f"[orchestrator] DualWriteContext enabled: {ctx.enabled}")
            await loop()
    else:
        await loop()

    save_metrics()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agentic orchestrator runtime.")
    parser.add_argument("--concept", default="", help="Concept or brief for the iteration.")
    parser.add_argument("--max-steps", type=int, default=5, help="Max orchestration steps.")
    parser.add_argument(
        "--max-actions-per-step",
        type=int,
        default=2,
        help="Max actions to dispatch per step.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    concept = args.concept or ""
    if not concept:
        logger.error("Concept is required (use --concept or set CONCEPT).")
        return 1
    asyncio.run(run_agentic_orchestrator(concept, args.max_steps, args.max_actions_per_step))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
