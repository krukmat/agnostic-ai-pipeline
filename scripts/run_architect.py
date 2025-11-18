from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import hashlib
import time
from typing import List, Tuple, Optional

import yaml
import typer

from common import ensure_dirs, PLANNING, ROOT, ART, save_text
from llm import Client
from logger import logger # Import the logger
from dspy_baseline.modules.architect import (
    StoriesEpicsModule,
    ArchitectureModule,
)


ARCHITECT_PROMPTS = {
    "simple": (ROOT / "prompts" / "architect_simple.md").read_text(encoding="utf-8"),
    "medium": (ROOT / "prompts" / "architect.md").read_text(encoding="utf-8"),
    "corporate": (ROOT / "prompts" / "architect_corporate.md").read_text(encoding="utf-8"),
}

REVIEW_ADJUSTMENT_PROMPT = (ROOT / "prompts" / "architect_review_adjustment.md").read_text(
    encoding="utf-8"
)
COMPLEXITY_CLASSIFIER_PROMPT = (
    ROOT / "prompts" / "architect_complexity_classifier.md"
).read_text(encoding="utf-8")

_COMPLEXITY_CACHE: dict[str, tuple[str, float]] = {}
COMPLEXITY_CACHE_TTL_SECONDS = 300
DEBUG_DIR = ART / "debug"
CONFIG_PATH = ROOT / "config.yaml"


def _load_config() -> dict:
    try:
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}


def _normalize_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if not cleaned:
            return default
        if cleaned in {"1", "true", "yes", "on"}:
            return True
        if cleaned in {"0", "false", "no", "off"}:
            return False
    return default


def _use_dspy_architect() -> bool:
    config = _load_config()
    features_candidate = config.get("features", {})
    features = features_candidate if isinstance(features_candidate, dict) else {}
    flag_value = features.get("use_dspy_architect")
    config_flag = _normalize_bool(flag_value, default=False)
    env_override = os.environ.get("USE_DSPY_ARCHITECT")
    if env_override is not None and env_override.strip() != "":
        return _normalize_bool(env_override, config_flag)
    return config_flag

def _complexity_cache_key(requirements_text: str) -> str:
    return hashlib.sha256(requirements_text.encode("utf-8")).hexdigest()


def _run_dspy_pipeline(
    concept: str,
    requirements_yaml: str,
    product_vision: str,
    complexity_tier: str,
) -> dict:
    """Execute the modular DSPy pipeline (stories → architecture → PRD)."""
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

    stories_yaml, epics_yaml = _convert_stories_epics_to_yaml(stories_epics_json)
    architecture_yaml = _sanitize_yaml_block(architecture_yaml)
    return {
        "stories_yaml": stories_yaml,
        "epics_yaml": epics_yaml,
        "architecture_yaml": architecture_yaml,
    }


def _convert_stories_epics_to_yaml(raw_text: str) -> tuple[str, str]:
    if not raw_text.strip():
        return "", ""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError:
            data = None

    if isinstance(data, dict):
        stories = data.get("stories", [])
        epics = data.get("epics", [])
    else:
        stories = []
        epics = []

    stories_yaml = _sanitize_yaml_block(stories)
    epics_yaml = _sanitize_yaml_block(epics)
    return stories_yaml, epics_yaml


def _sanitize_yaml_block(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        cleaned = re.sub(r"```(?:yaml)?", "", value, flags=re.IGNORECASE)
        cleaned = cleaned.replace("```", "")
        return cleaned.strip()
    try:
        return yaml.safe_dump(
            value,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).strip()
    except yaml.YAMLError:
        return str(value).strip()

def get_architect_prompt(mode: str, tier: str) -> str:
    if mode == "review_adjustment":
        return REVIEW_ADJUSTMENT_PROMPT
    return ARCHITECT_PROMPTS.get(tier, ARCHITECT_PROMPTS["medium"])


async def classify_complexity_with_llm(requirements_text: str) -> str:
    """Ask the architect model to classify requirements as simple/medium/corporate."""
    cleaned = (requirements_text or "").strip()
    if not cleaned:
        return "simple"

    cache_key = _complexity_cache_key(cleaned)
    cached = _COMPLEXITY_CACHE.get(cache_key)
    now = time.time()
    if cached:
        cached_value, cached_at = cached
        if now - cached_at <= COMPLEXITY_CACHE_TTL_SECONDS:
            logger.debug(f"[ARCHITECT] Using cached complexity tier '{cached_value}' (age {now - cached_at:.1f}s).")
            return cached_value
        logger.debug("[ARCHITECT] Complexity cache entry expired; recomputing.")

    try:
        client = Client(role="architect")
        user = (
            "REQUIREMENTS:\n"
            f"{cleaned}\n\n"
            "Respond with exactly one word: simple, medium, or corporate."
        )
        response = await client.chat(system=COMPLEXITY_CLASSIFIER_PROMPT, user=user)
        tier = parse_complexity_response(response)
        if tier:
            _COMPLEXITY_CACHE[cache_key] = (tier, time.time())
            return tier
        print(f"[ARCHITECT] Unexpected classifier response: {response[:120]!r}")
    except Exception as exc:
        print(f"[ARCHITECT] Complexity classifier failed via LLM: {exc}")

    fallback = fallback_complexity(cleaned)
    _COMPLEXITY_CACHE[cache_key] = (fallback, time.time())
    return fallback


def parse_complexity_response(text: str) -> str | None:
    if not text:
        return None
    lowered = text.strip().split()
    if not lowered:
        return None
    candidate = lowered[0].lower().strip(",.:;")
    if candidate in {"simple", "medium", "corporate"}:
        return candidate
    return None


def fallback_complexity(requirements_text: str) -> str:
    """Fallback heuristic when the classifier cannot determine a tier."""
    words = len(requirements_text.split())
    if words <= 350:
        return "simple"
    if words >= 900:
        return "corporate"
    return "medium"


def extract_original_concept(requirements_text: str) -> str:
    """Pull the stored concept from requirements metadata if available."""
    if not requirements_text.strip():
        return ""
    try:
        data = yaml.safe_load(requirements_text)
    except Exception as exc:
        print(f"[ARCHITECT] Failed to parse requirements metadata: {exc}")
        return ""

    if isinstance(data, dict):
        meta = data.get("meta")
        if isinstance(meta, dict):
            original = meta.get("original_request")
            if isinstance(original, str):
                return original.strip()
    return ""


def load_stories() -> Tuple[str, List[dict]]:
    stories_file = PLANNING / "stories.yaml"
    if not stories_file.exists():
        return ("", [])

    content = stories_file.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(content) or []
    except Exception:
        data = []

    if isinstance(data, dict) and "stories" in data:
        data = data["stories"]

    if not isinstance(data, list):
        return (content, [])
    return (content, data)


def save_stories(stories):
    stories_file = PLANNING / "stories.yaml"
    stories_file.write_text(
        yaml.safe_dump(stories, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


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
    stories_content, stories = load_stories()
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
    _, stories = load_stories()
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
    logger.debug("[ARCHITECT] Directories ensured")
    requirements_path = PLANNING / "requirements.yaml"
    requirements_content = requirements_path.read_text(encoding="utf-8") if requirements_path.exists() else ""
    logger.debug(f"[ARCHITECT] Requirements loaded: {len(requirements_content)} chars")
    vision_path = PLANNING / "product_vision.yaml"
    product_vision_content = vision_path.read_text(encoding="utf-8") if vision_path.exists() else ""
    concept_meta = extract_original_concept(requirements_content)
    concept_value = (concept or "").strip() or concept_meta
    logger.debug(f"[ARCHITECT] Concept value: {concept_value}")

    stories_content, _stories_snapshot = load_stories()
    logger.debug("[ARCHITECT] Stories loaded")

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
        print("✓ Architect DSPy pipeline completed.")
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

    forced = (force_tier or "").strip().lower()
    logger.debug(f"[ARCHITECT] Force tier: {forced}")
    if forced in {"simple", "medium", "corporate"}:
        complexity_tier = forced
        print(f"[ARCHITECT] Forced complexity tier via env: {complexity_tier}")
    elif architect_mode == "review_adjustment":
        complexity_tier = "medium"
        logger.debug("[ARCHITECT] Review adjustment mode, tier=medium")
    else:
        logger.debug("[ARCHITECT] Starting complexity classification")
        # Caching logic for complexity tier
        arch_cache_dir = ROOT / "artifacts" / "architect"
        arch_cache_dir.mkdir(parents=True, exist_ok=True)
        tier_cache_path = arch_cache_dir / "tier_cache.json"

        req_hash = hashlib.sha256(requirements_content.encode('utf-8')).hexdigest()
        logger.debug(f"[ARCHITECT] Requirements hash: {req_hash[:12]}...")

        cache = {}
        if tier_cache_path.exists():
            try:
                cache = json.loads(tier_cache_path.read_text(encoding="utf-8"))
                logger.debug(f"[ARCHITECT] Cache loaded with {len(cache)} entries")
            except json.JSONDecodeError:
                cache = {}
                logger.debug("[ARCHITECT] Cache file corrupted, starting fresh")

        if req_hash in cache:
            complexity_tier = cache[req_hash]
            print(f"[ARCHITECT] Using cached complexity tier: {complexity_tier}")
        else:
            logger.debug("[ARCHITECT] Cache miss, calling LLM to classify complexity...")
            complexity_tier = await classify_complexity_with_llm(requirements_content)
            logger.debug(f"[ARCHITECT] LLM returned tier: {complexity_tier}")
            cache[req_hash] = complexity_tier
            tier_cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            print(f"[ARCHITECT] Classified and cached complexity tier: {complexity_tier}")

    arch_prompt = get_architect_prompt(architect_mode, complexity_tier)

    if architect_mode == "review_adjustment":
        user_input = (
            f"CURRENT_STORIES:\n{stories_content}\n\n"
            f"DETAIL_LEVEL: {detail_level}\nITERATION_COUNT: {iteration_count}\n"
            "INSTRUCTION: Ajusta únicamente las historias en estado in_review o bloqueadas, "
            "añadiendo criterios de aceptación técnicos y accionables."
        )
        if story_id:
            user_input += f"\nTARGET_STORY: {story_id}"
    else:
        if not concept_value:
            raise ValueError("Concept is required to run architect in normal mode.")
        user_input = (
            f"CONCEPT:\n{concept_value}\n\nREQUIREMENTS:\n{requirements_content}\n\n"
            f"COMPLEXITY_TIER: {complexity_tier.upper()}\n\n"
            "Follow the exact output format."
        )

    client = Client(role="architect")
    if concept_meta and not (concept or "").strip():
        print("[ARCHITECT] Using concept from requirements metadata.")
    elif (concept or "").strip() and not concept_meta:
        print("[ARCHITECT] Concept provided via environment (no metadata found).")
    elif (concept or "").strip() and concept_meta and (concept or "").strip() != concept_meta:
        print("[ARCHITECT] Concept differs between env and metadata; using metadata.")
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

    text = await client.chat(system=arch_prompt, user=user_input)

    raw_response_path = DEBUG_DIR / "debug_architect_response.txt"
    save_text(raw_response_path, text)

    def grab(tag: str, label: str) -> str:
        # Updated regex to be more robust for YAML/CSV block extraction
        pattern = re.compile(rf"```{tag}\s*{label}\s*\n([\s\S]+?)\n```", re.MULTILINE)
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    inline_json_pattern = re.compile(r"^(\s*)([^:#\n]+):(.*)$")
    emphasis_pattern = re.compile(r"(\*\*?)([^\*\n]+)(\*\*?)")

    def _strip_markdown_emphasis(content: str) -> str:
        def replace(match: re.Match) -> str:
            prefix, text, suffix = match.groups()
            if prefix == suffix and prefix in ("**", "*"):
                text = text.replace('"', '\\"')
                return f"\"{text}\""
            return match.group(0)

        return emphasis_pattern.sub(replace, content)

    def _normalize_inline_json(content: str) -> str:
        """Expand inline JSON objects/arrays into multiline YAML for safe loading."""
        if not content.strip():
            return content

        normalized_lines: list[str] = []
        for line in content.splitlines():
            match = inline_json_pattern.match(line)
            if not match:
                normalized_lines.append(line)
                continue

            leading_ws, key, remainder = match.groups()
            value = remainder.strip()
            if not value or (value[0] not in "{[" or not value.endswith(("}", "]"))):
                normalized_lines.append(line)
                continue

            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                normalized_lines.append(line)
                continue

            key_line = f"{leading_ws}{key.strip()}:"
            normalized_lines.append(key_line)
            dumped = yaml.safe_dump(
                parsed,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ).rstrip()
            child_indent = leading_ws + "  "
            for sub_line in dumped.splitlines():
                normalized_lines.append(f"{child_indent}{sub_line}")

        return "\n".join(normalized_lines)

    def sanitize_yaml(content: str) -> str:
        """Remove markdown backticks from YAML content to prevent parsing errors.

        Task: fix-stories - YAML sanitization for architect output
        """
        if not content.strip():
            return content

        prepped = _strip_markdown_emphasis(content)
        normalized = _normalize_inline_json(prepped)

        try:
            # Try to parse and re-serialize to ensure valid YAML
            data = yaml.safe_load(normalized)
            # Re-serialize with safe_dump to ensure proper formatting
            sanitized = yaml.safe_dump(
                data,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False
            )
            logger.debug(f"[ARCHITECT] YAML sanitized via parse/dump cycle")
            return sanitized
        except yaml.YAMLError as exc:
            # If parsing fails, try regex-based backtick removal
            logger.warning(f"[ARCHITECT] YAML parsing failed: {exc}. Attempting regex cleanup...")

            # Remove backticks from YAML values
            # Pattern: match backticks that are likely markdown formatting
            cleaned = re.sub(r'`([^`]+?)`', r'\1', normalized)

            # Try parsing again after cleanup
            try:
                data = yaml.safe_load(cleaned)
                sanitized = yaml.safe_dump(
                    data,
                    sort_keys=False,
                    allow_unicode=True,
                    default_flow_style=False
                )
                logger.info(f"[ARCHITECT] YAML sanitized via regex cleanup")
                return sanitized
            except yaml.YAMLError as exc2:
                logger.error(f"[ARCHITECT] YAML sanitization failed even after cleanup: {exc2}")
                # Return cleaned version anyway, it's better than corrupted
                return cleaned

    # Extract and save all planning artifacts
    prd_content = grab("yaml", "PRD")
    if not prd_content and not allow_partial_blocks:
        print("[ARCHITECT] WARNING: PRD block missing in LLM response. Retrying...")
        text = await client.chat(system=arch_prompt, user=user_input)
        retry_path = DEBUG_DIR / "debug_architect_response_retry_prd.txt"
        save_text(retry_path, text)
        logger.warning(f"[ARCHITECT] Saved retry response for missing PRD block at {retry_path}")
        prd_content = grab("yaml", "PRD")
        if not prd_content:
            print("[ARCHITECT] ERROR: PRD block still missing after retry.")

    if not prd_content and allow_partial_blocks:
        logger.warning("[ARCHITECT] Proceeding without PRD block (allow_partial_blocks=True).")

    arch_content = grab("yaml", "ARCHITECTURE")
    if not arch_content and not allow_partial_blocks:
        print("[ARCHITECT] WARNING: ARCHITECTURE block missing in LLM response. Retrying...")
        for i in range(1, 3):
            text = await client.chat(system=arch_prompt, user=user_input)
            retry_path = DEBUG_DIR / f"debug_architect_response_retry_arch_{i}.txt"
            save_text(retry_path, text)
            logger.warning(f"[ARCHITECT] Saved retry response for missing ARCHITECTURE block at {retry_path}")
            arch_content = grab("yaml", "ARCHITECTURE")
            if arch_content:
                print(f"[ARCHITECT] ARCHITECTURE block recovered after {i} retries.")
                break
        if not arch_content:
            print("[ARCHITECT] ERROR: ARCHITECTURE block still missing after retry.")

    if not arch_content and allow_partial_blocks:
        logger.warning("[ARCHITECT] Proceeding without ARCHITECTURE block (allow_partial_blocks=True).")

    tasks_content = grab("csv", "TASKS")
    if not tasks_content and not allow_partial_blocks:
        print("[ARCHITECT] WARNING: TASKS block missing in LLM response. Retrying...")
        for i in range(1, 3):
            text = await client.chat(system=arch_prompt, user=user_input)
            retry_path = DEBUG_DIR / f"debug_architect_response_retry_tasks_{i}.txt"
            save_text(retry_path, text)
            logger.warning(f"[ARCHITECT] Saved retry response for missing TASKS block at {retry_path}")
            tasks_content = grab("csv", "TASKS")
            if tasks_content:
                print(f"[ARCHITECT] TASKS block recovered after {i} retries.")
                break
        if not tasks_content:
            print("[ARCHITECT] ERROR: TASKS block still missing after retry.")

    if not tasks_content and allow_partial_blocks:
        logger.warning("[ARCHITECT] Proceeding without TASKS block (allow_partial_blocks=True).")

    # Task: fix-stories - Apply YAML sanitization to all outputs
    # Only write files that have actual content (not empty)
    if prd_content:
        (PLANNING / "prd.yaml").write_text(sanitize_yaml(prd_content), encoding="utf-8")
    else:
        (PLANNING / "prd.yaml").write_text("", encoding="utf-8")  # Empty file for simple tier

    if arch_content:
        (PLANNING / "architecture.yaml").write_text(sanitize_yaml(arch_content), encoding="utf-8")
    else:
        (PLANNING / "architecture.yaml").write_text("", encoding="utf-8")  # Empty file for simple tier

    (PLANNING / "epics.yaml").write_text(sanitize_yaml(grab("yaml", "EPICS")), encoding="utf-8")
    (PLANNING / "stories.yaml").write_text(sanitize_yaml(grab("yaml", "STORIES")), encoding="utf-8")

    if tasks_content:
        (PLANNING / "tasks.csv").write_text(tasks_content, encoding="utf-8")
    else:
        (PLANNING / "tasks.csv").write_text("", encoding="utf-8")  # Empty file for simple tier

    print("✓ planning written under planning/")

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


async def main() -> None:
    logger.debug("[ARCHITECT] Entered main()")
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
        app()
