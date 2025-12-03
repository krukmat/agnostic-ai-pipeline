from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from typing import List, Tuple, Optional

import pathlib

ROOT_PATH = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

import typer
import yaml

from common import ensure_dirs, PLANNING, ROOT, ART, save_text
from scripts.utils.db_context import get_db_context_or_default
from scripts.utils.db_logger import DbLogger
from scripts.utils.config_loader import load_config_base, normalize_bool
from scripts.utils.story_manager import load_stories as _load_stories_shared, save_stories as _save_stories_shared, STORIES_PATH
from llm import Client
from logger import logger # Import the logger

# Task: database-layer - Import dual-write support
from pathlib import Path
from scripts.architect_utils import (
    convert_stories_epics_to_yaml,
)
# Task: DB integration - Phase 2 - Import story normalization
from scripts.fix_stories import normalize_status
from scripts.architect.complexity_classifier import (
    classify_complexity_with_llm,
)
from scripts.utils.yaml_sanitizer import sanitize_yaml_block, sanitize_requirements_yaml
from scripts.utils.prompt_builders import build_architect_prompt
from scripts.utils.llm_runner import LLMRunner
try:
    from dspy_baseline.modules.architect import (
        StoriesEpicsModule,
        ArchitectureModule,
    )
    _DSPY_MODULES_AVAILABLE = True
except Exception:
    StoriesEpicsModule = None  # type: ignore
    ArchitectureModule = None  # type: ignore
    _DSPY_MODULES_AVAILABLE = False
from scripts.checks.pipeline_guard import run_guard


def _load_config() -> dict:
    """Thin wrapper to load base config safely."""
    try:
        return load_config_base()
    except Exception:
        return {}


ARCHITECT_PROMPTS = {
    "simple": (ROOT / "prompts" / "architect_simple.md").read_text(encoding="utf-8"),
    "medium": (ROOT / "prompts" / "architect.md").read_text(encoding="utf-8"),
    "corporate": (ROOT / "prompts" / "architect_corporate.md").read_text(encoding="utf-8"),
}

REVIEW_ADJUSTMENT_PROMPT = (ROOT / "prompts" / "architect_review_adjustment.md").read_text(
    encoding="utf-8"
)
DEBUG_DIR = ART / "debug"


def _use_dspy_architect() -> bool:
    if not _DSPY_MODULES_AVAILABLE:
        return False
    config = load_config_base()
    features_candidate = config.get("features", {})
    features = features_candidate if isinstance(features_candidate, dict) else {}
    flag_value = features.get("use_dspy_architect")
    config_flag = normalize_bool(flag_value, default=False)
    env_override = os.environ.get("USE_DSPY_ARCHITECT")
    if env_override is not None and env_override.strip() != "":
        return normalize_bool(env_override, config_flag)
    return config_flag

def _run_dspy_pipeline(
    concept: str,
    requirements_yaml: str,
    product_vision: str,
    complexity_tier: str,
) -> dict:
    """Execute the modular DSPy pipeline (stories → architecture → PRD)."""
    if StoriesEpicsModule is None or ArchitectureModule is None:
        raise RuntimeError("DSPy modules not available; install dspy_baseline and dependencies.")
    tier_value = (complexity_tier or "medium").strip().lower() or "medium"
    stories_module = StoriesEpicsModule()
    architecture_module = ArchitectureModule()
    stories_prediction = stories_module(
        concept=concept,
        requirements_yaml=requirements_yaml,
        product_vision=product_vision or "",
        complexity_tier=tier_value,
    )
    stories_epics_json = getattr(stories_prediction, "stories_epics_json", "") or ""

    architecture_prediction = architecture_module(
        concept=concept,
        requirements_yaml=requirements_yaml,
        product_vision=product_vision or "",
        complexity_tier=tier_value,
        stories_epics_json=stories_epics_json,
    )
    architecture_yaml = getattr(architecture_prediction, "architecture_yaml", "") or ""

    stories_yaml, epics_yaml = convert_stories_epics_to_yaml(stories_epics_json)
    architecture_yaml = sanitize_yaml_block(architecture_yaml)
    return {
        "stories_yaml": stories_yaml,
        "epics_yaml": epics_yaml,
        "architecture_yaml": architecture_yaml,
    }

def _convert_stories_epics_to_yaml(raw_text: str) -> tuple[str, str]:
    # Backward-compatible wrapper retained for legacy callers inside this module
    return convert_stories_epics_to_yaml(raw_text)


def _sanitize_yaml_block(value) -> str:
    # Backward-compatible wrapper retained for legacy callers inside this module
    return sanitize_yaml_block(value)

def get_architect_prompt(mode: str, tier: str) -> str:
    if mode == "review_adjustment":
        return REVIEW_ADJUSTMENT_PROMPT
    # Allow optimized prompt override via config
    cfg = _load_config()
    features = cfg.get("features", {}) if isinstance(cfg.get("features", {}), dict) else {}
    arch_features = features.get("architect", {}) if isinstance(features, dict) else {}
    if arch_features and bool(arch_features.get("use_optimized_prompt")):
        override_path = str(arch_features.get("prompt_override_file") or "").strip()
        if override_path:
            try:
                p = (ROOT / override_path) if not override_path.startswith("/") else Path(override_path)
                if p.exists():
                    return p.read_text(encoding="utf-8")
            except Exception as exc:
                logger.warning(f"[ARCH] Prompt override failed for {override_path}: {exc}")
    return ARCHITECT_PROMPTS.get(tier, ARCHITECT_PROMPTS["medium"])


def extract_original_concept(requirements_text: str) -> str:
    """Pull the stored concept from requirements metadata if available."""
    if not requirements_text.strip():
        return ""
    try:
        data = yaml.safe_load(requirements_text)
    except Exception:
        return ""
    if isinstance(data, dict):
        meta = data.get("meta")
        if isinstance(meta, dict):
            original = meta.get("original_request")
            if isinstance(original, str):
                return original.strip()
    return ""


def _load_stories_with_content() -> Tuple[str, List[dict]]:
    """Load stories using shared utility, returning raw content + list."""
    if not STORIES_PATH.exists():
        return ("", [])
    content = STORIES_PATH.read_text(encoding="utf-8")
    data = _load_stories_shared(recover_comments=True)
    return (content, data if isinstance(data, list) else [])


def save_stories(stories):
    _save_stories_shared(stories)


def require_po_approval() -> None:
    """Abort early if the PO review has not been approved."""
    if os.environ.get("PIPELINE_GUARD_BYPASS", "").strip().lower() in {"1", "true", "yes"}:
        return
    review_path = PLANNING / "product_owner_review.yaml"
    if not review_path.exists():
        raise SystemExit("Falta product_owner_review.yaml: ejecuta make po antes de Architect.")
    try:
        review = yaml.safe_load(review_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"No se pudo leer product_owner_review.yaml ({exc}); reejecuta make po.")
    status = str(review.get("status", "")).strip().lower()
    if status != "approved":
        raise SystemExit(
            "PO en needs_adjustment: ejecuta make ba-revise && make po antes de correr Architect."
        )


def _run_pipeline_guard_for_architect() -> None:
    """
    Run guardrail checks before Architect.

    We skip architecture presence to allow the first Architect run, but still
    enforce PO approval and story integrity when stories.yaml already exists.
    """
    stories_path = PLANNING / "stories.yaml"
    if not stories_path.exists():
        return
    guard_result = run_guard(check_architecture=False, allow_empty_stories=True)
    if not guard_result.passed:
        issues = "\n".join(f"- {item}" for item in guard_result.issues)
        raise SystemExit(f"pipeline_guard detectó problemas antes de Architect:\n{issues}")


def _build_architect_context(
    concept: Optional[str],
    architect_mode: str,
    story_id: str,
    detail_level: str,
    iteration_count: int,
) -> dict:
    requirements_path = PLANNING / "requirements.yaml"
    requirements_content_raw = requirements_path.read_text(encoding="utf-8") if requirements_path.exists() else ""
    requirements_content = sanitize_requirements_yaml(requirements_content_raw)
    vision_path = PLANNING / "product_vision.yaml"
    product_vision_content = vision_path.read_text(encoding="utf-8") if vision_path.exists() else ""
    concept_meta = extract_original_concept(requirements_content)
    concept_value = (concept or "").strip() or concept_meta
    stories_content, stories_snapshot = _load_stories_with_content()

    return {
        "requirements_content": requirements_content,
        "requirements_content_raw": requirements_content_raw,
        "vision_content": product_vision_content,
        "concept_value": concept_value,
        "stories_content": stories_content,
        "stories_snapshot": stories_snapshot,
        "detail_level": detail_level,
        "iteration_count": iteration_count,
        "architect_mode": architect_mode,
        "story_id": story_id,
    }


async def _select_prompt_tier(requirements_content: str, force_tier: Optional[str], architect_mode: str) -> tuple[str, str]:
    forced = (force_tier or "").strip().lower()
    if forced in {"simple", "medium", "corporate"}:
        return forced, get_architect_prompt(architect_mode, forced)
    if architect_mode == "review_adjustment":
        tier = "medium"
        return tier, get_architect_prompt(architect_mode, tier)
    tier = await classify_complexity_with_llm(requirements_content)
    return tier, get_architect_prompt(architect_mode, tier)


async def _parse_architect_response(
    text: str,
    client,
    arch_prompt: str,
    user_input: str,
    allow_partial_blocks: bool,
    complexity_tier: str,
    concept_value: str,
    architect_mode: str,
    detail_level: str,
    iteration_count: int,
) -> dict:
    raw_response_path = DEBUG_DIR / "debug_architect_response.txt"
    save_text(raw_response_path, text)

    def grab(tag: str, label: str) -> str:
        pattern = re.compile(rf"```{tag}\s*{label}\s*\n([\s\S]+?)\n```", re.MULTILINE)
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    prd_content = grab("yaml", "PRD")
    arch_content = grab("yaml", "ARCHITECTURE")
    tasks_content = grab("csv", "TASKS")

    if not prd_content and not allow_partial_blocks:
        text = await client.chat(system=arch_prompt, user=user_input)
        save_text(DEBUG_DIR / "debug_architect_response_retry_prd.txt", text)
        prd_content = grab("yaml", "PRD")

    if not arch_content and not allow_partial_blocks:
        for i in range(1, 3):
            retry = await client.chat(system=arch_prompt, user=user_input)
            save_text(DEBUG_DIR / f"debug_architect_response_retry_arch_{i}.txt", retry)
            text = retry
            arch_content = grab("yaml", "ARCHITECTURE")
            if arch_content:
                break

    if not tasks_content and not allow_partial_blocks:
        for i in range(1, 3):
            retry = await client.chat(system=arch_prompt, user=user_input)
            save_text(DEBUG_DIR / f"debug_architect_response_retry_tasks_{i}.txt", retry)
            text = retry
            tasks_content = grab("csv", "TASKS")
            if tasks_content:
                break

    (PLANNING / "prd.yaml").write_text(sanitize_yaml_block(prd_content), encoding="utf-8")
    (PLANNING / "architecture.yaml").write_text(sanitize_yaml_block(arch_content), encoding="utf-8")
    (PLANNING / "epics.yaml").write_text(sanitize_yaml_block(grab("yaml", "EPICS")), encoding="utf-8")
    (PLANNING / "stories.yaml").write_text(sanitize_yaml_block(grab("yaml", "STORIES")), encoding="utf-8")
    (PLANNING / "tasks.csv").write_text(tasks_content or "", encoding="utf-8")

    return {
        "mode": architect_mode,
        "concept": concept_value,
        "complexity_tier": complexity_tier,
        "outputs": {
            "prd": str(PLANNING / "prd.yaml"),
            "architecture": str(PLANNING / "architecture.yaml"),
            "epics": str(PLANNING / "epics.yaml"),
            "stories": str(PLANNING / "stories.yaml"),
            "tasks": str(PLANNING / "tasks.csv"),
            "raw_response": str(raw_response_path),
        },
    }


def extract_qa_failure_context(story_id: str) -> str:
    """Extract detailed QA failure context for the requested story."""
    try:
        qa_report_path = ROOT / "artifacts" / "qa" / "last_report.json"
        if not qa_report_path.exists():
            return "No QA report available"

        qa_data = json.loads(qa_report_path.read_text(encoding="utf-8"))
        failure_details = qa_data.get("failure_details", {})
        story_context = qa_data.get("story_context", "")

        if story_context and story_context != story_id:
            return f"QA failures correspond to {story_context}, not {story_id}"

        failure_info: List[str] = []
        for module, details in failure_details.items():
            errors = details.get("errors", []) if isinstance(details, dict) else []
            warnings = details.get("warnings", []) if isinstance(details, dict) else []
            if errors:
                failure_info.append(f"Module {module.upper()}:")
                for error in errors:
                    failure_info.append(f"  - Test {error.get('test','?')}: {error.get('error','')[:200]}...")
            if warnings:
                failure_info.append(f"Warnings {module.upper()}:")
                for warning in warnings:
                    failure_info.append(f"  - {warning}")

        return "\n".join(failure_info) if failure_info else "No detailed QA errors extracted"
    except Exception as exc:
        return f"Error extracting QA context: {exc}"


def try_programmatic_adjustment(story_id: str, detail_level: str) -> bool:
    """Attempt to adjust a story without invoking the LLM."""
    stories_content, stories = _load_stories_with_content()
    if not stories:
        print(f"[ARCHITECT] No stories available to adjust for {story_id}")
        return False

    target = None
    for story in stories:
        if isinstance(story, dict) and str(story.get("id")) == story_id:
            target = story
            break

    if not target:
        print(f"[ARCHITECT] Story {story_id} not found for programmatic adjustment")
        return False

    acceptance = target.get("acceptance", [])
    if not isinstance(acceptance, list):
        acceptance = [acceptance] if acceptance else []

    additions: List[str] = []
    level = detail_level.lower()
    if level == "high":
        additions = [
            "Documentar validaciones exhaustivas con formatos y límites claros.",
            "Definir códigos HTTP o mensajes de error específicos para cada fallo esperado.",
            "Cubrir escenarios edge incluyendo datos nulos, duplicados o inconsistentes.",
        ]
        print(f"[ARCHITECT] Adding HIGH detail acceptance criteria to {story_id}")
    elif level == "maximum":
        qa_context = extract_qa_failure_context(story_id)
        if "pytest_execution" in qa_context:
            additions = [
                "Configurar correctamente backend/.venv/bin/pytest y asegurar su disponibilidad.",
                "Verificar instalación de dependencias de testing y rutas relativas.",
            ]
            print(f"[ARCHITECT] Adding pytest-focused fixes to {story_id}")
        else:
            additions = [
                "Aplicar validaciones con expresiones regulares para cada entrada crítica.",
                "Agregar logging detallado a nivel debug para rastrear incidentes.",
                "Manejar timeouts y reconexiones en llamados externos involucrados.",
            ]
            print(f"[ARCHITECT] Adding MAXIMUM technical requirements to {story_id}")

    for item in additions:
        if item not in acceptance:
            acceptance.append(item)

    if not additions:
        print(f"[ARCHITECT] No programmatic additions computed for {story_id} (detail level {detail_level})")
        return False

    target["acceptance"] = acceptance
    target["status"] = "todo"
    save_stories(stories)
    print(f"[ARCHITECT] Programmatic adjustment complete for {story_id}")
    return True


def mark_story_todo(story_id: str) -> bool:
    """Fallback: mark story as todo when adjustments cannot be automated."""
    _, stories = _load_stories_with_content()
    if not stories:
        return False

    updated = False
    for story in stories:
        if isinstance(story, dict) and str(story.get("id")) == story_id:
            story["status"] = "todo"
            updated = True
            break

    if not updated:
        return False

    save_stories(stories)
    return True


async def run_architect_job(
    *,
    concept: str | None = None,
    architect_mode: str = "normal",
    story_id: str = "",
    detail_level: str = "medium",
    iteration_count: int = 1,
    force_tier: str | None = None,
    allow_partial_blocks: bool = False,
) -> dict:
    logger.debug("[ARCHITECT] Starting run_architect_job")
    ensure_dirs()
    if architect_mode == "normal":
        require_po_approval()
        _run_pipeline_guard_for_architect()
    ctx = _build_architect_context(concept, architect_mode, story_id, detail_level, iteration_count)
    requirements_content = ctx["requirements_content"]
    product_vision_content = ctx["vision_content"]
    concept_value = ctx["concept_value"]
    stories_content = ctx["stories_content"]

    if _use_dspy_architect():
        tier_value = (force_tier or await classify_complexity_with_llm(requirements_content)).strip().lower() or "medium"
        logger.info(f"[ARCHITECT][DSPy] Running modular DSPy pipeline with tier '{tier_value}'.")
        outputs = _run_dspy_pipeline(
            concept=concept_value,
            requirements_yaml=requirements_content,
            product_vision=product_vision_content,
            complexity_tier=tier_value,
        )
        (PLANNING / "stories.yaml").write_text(outputs["stories_yaml"], encoding="utf-8")
        (PLANNING / "epics.yaml").write_text(outputs["epics_yaml"], encoding="utf-8")
        (PLANNING / "architecture.yaml").write_text(outputs["architecture_yaml"], encoding="utf-8")
        if outputs.get("prd_yaml"):
            (PLANNING / "prd_generated.yaml").write_text(outputs["prd_yaml"], encoding="utf-8")

        # Task: DB integration - Phase 2 - Use ad-hoc context for standalone runs
        db = DbLogger(get_db_context_or_default())
        if db.enabled:
            db.log_event("architect_start", role="architect", message=f"Generating stories (DSPy, tier={tier_value})")

            db.save_artifact("architect", "stories", outputs["stories_yaml"])
            db.save_artifact("architect", "epics", outputs["epics_yaml"])
            db.save_artifact("architect", "architecture", outputs["architecture_yaml"])
            if outputs.get("prd_yaml"):
                db.save_artifact("architect", "prd", outputs["prd_yaml"])

            # Task: DB integration - Phase 2 - Normalize stories before DB sync
            try:
                stories_data = yaml.safe_load(outputs["stories_yaml"])
                stories_list = None
                if isinstance(stories_data, list):
                    stories_list = stories_data
                elif isinstance(stories_data, dict) and "stories" in stories_data:
                    stories_list = stories_data["stories"]

                if stories_list:
                    # Normalize status and complexity before syncing to DB
                    stories_list = normalize_status(stories_list)
                    # Update the file with normalized data
                    if isinstance(stories_data, list):
                        normalized_yaml = yaml.safe_dump(stories_list, sort_keys=False, allow_unicode=True)
                    else:
                        stories_data["stories"] = stories_list
                        normalized_yaml = yaml.safe_dump(stories_data, sort_keys=False, allow_unicode=True)
                    (PLANNING / "stories.yaml").write_text(normalized_yaml, encoding="utf-8")
                    outputs["stories_yaml"] = normalized_yaml

                    # Now sync to DB with normalized data
                    db.ctx.create_stories_from_list(stories_list) if hasattr(db, "ctx") else None
                    logger.info(f"[ARCHITECT] Synced {len(stories_list)} normalized stories to DB")
            except Exception as e:
                logger.warning(f"[ARCHITECT] Could not sync stories to DB: {e}")

            db.log_event("architect_end", role="architect", message="Architect artifacts generated (DSPy)")

        return {
            "mode": "dspy",
            "concept": concept_value,
            "complexity_tier": tier_value,
            "outputs": {
                "stories": str(PLANNING / "stories.yaml"),
                "epics": str(PLANNING / "epics.yaml"),
                "architecture": str(PLANNING / "architecture.yaml"),
            },
        }

    if architect_mode == "review_adjustment" and story_id:
        print(f"[ARCHITECT] Programmatic review adjustment for {story_id} (level={detail_level}, iteration={iteration_count})")
        if try_programmatic_adjustment(story_id, detail_level):
            print(f"✓ Arquitecto ajustó criterios de {story_id} (programático)")
            return {
                "mode": "review_adjustment",
                "story_id": story_id,
                "action": "programmatic_adjustment",
            }
        if mark_story_todo(story_id):
            print(f"✓ Arquitecto marcó {story_id} como todo (fallback)")
            return {
                "mode": "review_adjustment",
                "story_id": story_id,
                "action": "marked_todo",
            }
        print(f"[ARCHITECT] Programmatic adjustment failed; falling back to LLM for {story_id}")

    complexity_tier, arch_prompt = await _select_prompt_tier(requirements_content, force_tier, architect_mode)

    if architect_mode != "review_adjustment" and not concept_value:
        raise ValueError("Concept is required to run architect in normal mode.")
    user_input = build_architect_prompt(
        concept_value=concept_value,
        requirements_content=requirements_content,
        complexity_tier=complexity_tier,
        stories_content=stories_content,
        detail_level=detail_level,
        iteration_count=iteration_count,
        architect_mode=architect_mode,
        story_id=story_id,
    )

    client = Client(role="architect")

    print(f"Using CONCEPT: {concept_value or 'No concept defined'}")
    print(f"Architect mode: {architect_mode}")
    if architect_mode != "review_adjustment":
        print(f"Complexity tier selected: {complexity_tier}")
    print(
        f"Provider: {client.provider_type} | Model: {client.model} | "
        f"Temp: {client.temperature} | Max tokens: {client.max_tokens}"
    )
    print(f"System prompt length: {len(arch_prompt)}")
    print(f"User input preview: {user_input[:300]}...")

    runner = LLMRunner([client])
    text, _ = await runner.chat(system=arch_prompt, user=user_input, retries=1)

    return await _parse_architect_response(
        text=text,
        client=client,
        arch_prompt=arch_prompt,
        user_input=user_input,
        allow_partial_blocks=allow_partial_blocks,
        complexity_tier=complexity_tier,
        concept_value=concept_value,
        architect_mode=architect_mode,
        detail_level=detail_level,
        iteration_count=iteration_count,
    )


async def main() -> None:
    logger.debug("[ARCHITECT] Entered main()")
    db_ctx = get_db_context_or_default()
    architect_mode = os.environ.get("ARCHITECT_MODE", "normal")
    concept_env = os.environ.get("CONCEPT", "").strip()
    story_id = os.environ.get("STORY", "").strip()
    detail_level = os.environ.get("DETAIL_LEVEL", "medium")
    try:
        iteration_count = int(os.environ.get("ITERATION_COUNT", "1"))
    except ValueError:
        iteration_count = 1
    force_tier = os.environ.get("FORCE_ARCHITECT_TIER", "").strip().lower()
    logger.debug(f"[ARCHITECT] Calling run_architect_job with mode={architect_mode}")

    result = await run_architect_job(
        concept=concept_env,
        architect_mode=architect_mode,
        story_id=story_id,
        detail_level=detail_level,
        iteration_count=iteration_count,
        force_tier=force_tier or None,
    )
    print(json.dumps(result, indent=2))

    # Normalize and persist artifacts via DB (ad-hoc if enabled)
    try:
        defaults = load_config_base().get("defaults", {}) if isinstance(load_config_base(), dict) else {}
    except Exception:
        defaults = {}
    default_complexity = defaults.get("complexity", "medium") if isinstance(defaults, dict) else "medium"

    def _normalize_stories(path):
        if not path.exists():
            return None, None
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) if raw.strip() else []
        if isinstance(data, dict) and "stories" in data:
            data = data["stories"]
        if isinstance(data, list):
            for s in data:
                if isinstance(s, dict):
                    s.setdefault("status", "todo")
                    s.setdefault("complexity", default_complexity)
            normalized = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
            path.write_text(normalized, encoding="utf-8")
            return data, normalized
        return None, raw

    try:
        db = DbLogger(db_ctx)
        if db.enabled:
            db.log_event("architect_start", role="architect", message="Architect run completed")

            stories_p = PLANNING / "stories.yaml"
            stories_data, stories_yaml = _normalize_stories(stories_p)
            if stories_yaml:
                db.save_artifact("architect", "stories", stories_yaml)
                if stories_data and hasattr(db_ctx, "create_stories_from_list"):
                    try:
                        db_ctx.create_stories_from_list(stories_data)
                    except Exception as exc:
                        logger.warning(f"[ARCH][db] Failed creating stories in DB: {exc}")

            epics_p = PLANNING / "epics.yaml"
            if epics_p.exists():
                db.save_artifact("architect", "epics", epics_p.read_text(encoding="utf-8"))
            arch_p = PLANNING / "architecture.yaml"
            if arch_p.exists():
                db.save_artifact("architect", "architecture", arch_p.read_text(encoding="utf-8"))
            prd_p = PLANNING / "prd.yaml"
            if prd_p.exists():
                db.save_artifact("architect", "prd", prd_p.read_text(encoding="utf-8"))
            db.log_event("architect_end", role="architect", message="Architect artifacts persisted")
    except Exception as e:
        logger.debug(f"[ARCHITECT][db] Skipping DB persistence: {e}")


app = typer.Typer(help="Architect agent CLI")


@app.command()
def run(
    concept: Optional[str] = typer.Option(None, help="Concept to evaluate"),
    mode: str = typer.Option("normal", help="Architect mode"),
    story_id: Optional[str] = typer.Option(None, help="Story identifier for review mode"),
    detail_level: str = typer.Option("medium", help="Detail level for review adjustments"),
    iteration_count: int = typer.Option(1, help="Iteration count for review adjustments"),
    force_tier: Optional[str] = typer.Option(None, help="Force complexity tier"),
) -> None:
    result = asyncio.run(
        run_architect_job(
            concept=concept,
            architect_mode=mode,
            story_id=story_id or "",
            detail_level=detail_level,
            iteration_count=iteration_count,
            force_tier=force_tier,
        )
    )
    typer.echo(json.dumps(result, indent=2))


@app.command()
def serve(reload: bool = typer.Option(False, help="Auto-reload server on code changes")) -> None:
    from a2a.cards import architect_card
    from a2a.runtime import run_agent

    card, handlers = architect_card()
    run_agent("architect", card, handlers, reload=reload)


if __name__ == "__main__":
    logger.debug(f"[ARCHITECT] __main__ started, sys.argv: {sys.argv}")
    if len(sys.argv) == 1:
        logger.debug("[ARCHITECT] Running main() via asyncio")
        asyncio.run(main())
    else:
        logger.debug("[ARCHITECT] Running typer app")
        try:
            app()
        except RuntimeError:
            logger.debug("[ARCHITECT] Typer failed to resolve command; fallback to main()")
            asyncio.run(main())
