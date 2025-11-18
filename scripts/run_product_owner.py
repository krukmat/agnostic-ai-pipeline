from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
import yaml

from common import ensure_dirs, PLANNING, ROOT, ART, save_text
from llm import Client
from logger import logger # Import the logger

CONFIG_PATH = ROOT / "config.yaml"

DSPY_CACHE_DIR = Path(os.environ.get("DSPY_CACHEDIR", "/tmp/dspy_cache"))
DSPY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSPY_CACHEDIR", str(DSPY_CACHE_DIR))

import dspy
from dspy_baseline.modules.product_owner import ProductOwnerModule
from scripts.dspy_lm_helper import build_lm_for_role

PO_PROMPT = (ROOT / "prompts" / "product_owner.md").read_text(encoding="utf-8")
VISION_PATH = PLANNING / "product_vision.yaml"
REVIEW_PATH = PLANNING / "product_owner_review.yaml"
DEBUG_PATH = ART / "debug" / "debug_product_owner_response.txt"

_THIN_SPACE_CHARS = ("\u202f", "\u00a0", "\u2007")


def _normalize_po_yaml(content: str) -> str:
    """Pre-process Gemini output so yaml.safe_load can handle human text lists."""
    lines = content.splitlines()
    normalized: list[str] = []
    for raw_line in lines:
        line = raw_line
        for ch in _THIN_SPACE_CHARS:
            if ch in line:
                line = line.replace(ch, " ")

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("-"):
            payload = stripped[1:].lstrip()
            if payload:
                # Quote bullets that start with special characters that YAML treats as directives/tokens
                if payload[0] in ("%", "&", "*", "#", "!", "?", "@", "[", "]", "{", "}", ","):
                    payload_q = payload.replace('"', '\\"')
                    line = " " * indent + f"- \"{payload_q}\""
                elif payload[0] in (">", "<"):
                    payload = payload.replace('"', '\\"')
                    line = " " * indent + f"- \"{payload}\""
                else:
                    colon_idx = payload.find(":")
                    if colon_idx != -1:
                        key_part = payload[:colon_idx]
                        remainder = payload[colon_idx + 1 :].strip()
                        key_has_spaces = " " in key_part.strip()
                        key_has_unicode = any(ord(ch) > 127 for ch in key_part)
                        key_is_simple = re.fullmatch(r"[\w-]+", key_part.strip() or "") is not None
                        if remainder and (key_has_spaces or key_has_unicode) and not key_is_simple:
                            quoted = payload.replace('"', '\\"')
                            line = " " * indent + f"- \"{quoted}\""
        else:
            if stripped and stripped[0] in (">", "<"):
                payload = stripped.replace('"', '\\"')
                line = " " * indent + f"\"{payload}\""

        normalized.append(line)

    return "\n".join(normalized)


def extract_original_concept(requirements_text: str) -> str:
    if not requirements_text.strip():
        return ""
    try:
        data = yaml.safe_load(requirements_text)
    except Exception as exc:
        logger.warning(f"[PO] Failed to parse requirements metadata: {exc}")
        return ""
    if isinstance(data, dict):
        meta = data.get("meta")
        if isinstance(meta, dict):
            original = meta.get("original_request")
            if isinstance(original, str):
                return original.strip()
    return ""


def grab_block(text: str, tag: str, label: str) -> str:
    # Updated regex to be more robust for YAML block extraction
    pattern = re.compile(rf"```{tag}\s*{label}\s*\n([\s\S]+?)```", re.MULTILINE)
    match = pattern.search(text)
    content = match.group(1).strip() if match else ""
    logger.debug(f"[PO] Grabbed '{tag}:{label}' with {len(content)} characters")
    return content


def sanitize_yaml(content: str) -> str:
    """Remove markdown backticks from YAML content to prevent parsing errors.

    Task: fix-stories - YAML sanitization for PO output
    """
    if not content.strip():
        return content

    prepared = _normalize_po_yaml(content)

    try:
        # Try to parse and re-serialize to ensure valid YAML
        data = yaml.safe_load(prepared)
        # Re-serialize with safe_dump to ensure proper formatting
        sanitized = yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False
        )
        logger.debug(f"[PO] YAML sanitized via parse/dump cycle")
        return sanitized
    except yaml.YAMLError as exc:
        # If parsing fails, try regex-based backtick removal
        logger.warning(f"[PO] YAML parsing failed: {exc}. Attempting regex cleanup...")

        # Remove backticks from YAML values
        # Pattern: match backticks that are likely markdown formatting
        cleaned = re.sub(r'`([^`]+?)`', r'\1', prepared)

        # Try parsing again after cleanup
        try:
            data = yaml.safe_load(cleaned)
            sanitized = yaml.safe_dump(
                data,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False
            )
            logger.info(f"[PO] YAML sanitized via regex cleanup")
            return sanitized
        except yaml.YAMLError as exc2:
            logger.error(f"[PO] YAML sanitization failed even after cleanup: {exc2}")
            # Return cleaned version anyway, it's better than corrupted
            return cleaned


def build_user_payload(concept: str, existing_vision: str, requirements: str) -> str:
    concept_section = concept or "(concept not provided)"
    vision_section = existing_vision.strip() if existing_vision else "(no existing vision)"
    return (
        f"CONCEPT:\n{concept_section}\n\n"
        f"EXISTING_VISION:\n{vision_section}\n\n"
        f"REQUIREMENTS:\n{requirements.strip()}\n\n"
        "Follow the exact output format."
    )


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


def _use_dspy_po() -> bool:
    config = _load_config()
    features_candidate = config.get("features", {})
    features = features_candidate if isinstance(features_candidate, dict) else {}
    flag_value = features.get("use_dspy_product_owner")
    if flag_value is None:
        flag_value = features.get("use_dspy_po")
    config_flag = _normalize_bool(flag_value, default=False)

    env_override = os.environ.get("USE_DSPY_PO")
    if env_override is not None and env_override.strip() != "":
        return _normalize_bool(env_override, config_flag)
    return config_flag


async def main() -> None:
    ensure_dirs()

    requirements_path = PLANNING / "requirements.yaml"
    if not requirements_path.exists():
        logger.error("[PO] requirements.yaml not found. Run BA stage first.")
        raise SystemExit(1)

    requirements_content = requirements_path.read_text(encoding="utf-8")
    concept_meta = extract_original_concept(requirements_content)
    concept_env = os.environ.get("CONCEPT", "").strip()
    concept = concept_meta or concept_env
    if concept_env and not concept_meta:
        logger.info("[PO] Using CONCEPT from environment because requirements metadata was empty.")
    elif concept_env and concept_meta and concept_env != concept_meta:
        logger.warning(
            "[PO] CONCEPT env value differs from requirements meta; using requirements version to avoid drift."
        )

    existing_vision = ""
    if VISION_PATH.exists():
        existing_vision = VISION_PATH.read_text(encoding="utf-8")

    use_dspy = _use_dspy_po()
    if use_dspy:
        logger.info("[PO] DSPy flag enabled — running optimized snapshot")
        try:
            await run_dspy_program(requirements_content, concept, existing_vision)
            return
        except Exception as exc:
            logger.error(f"[PO][DSPY] Optimized path failed: {exc}. Falling back to default client.", exc_info=True)

    client = Client(role="product_owner")
    logger.info(f"[PO] Using CONCEPT: {concept or 'No concept provided'}")
    logger.info("[PO] Maintaining product vision and evaluating BA alignment...")
    logger.debug(f"[PO] Calling LLM via {client.provider_type} with model {client.model}, temp {client.temperature}, max_tokens {client.max_tokens}")


    user = build_user_payload(concept, existing_vision, requirements_content)
    response = await client.chat(system=PO_PROMPT, user=user)
    save_text(DEBUG_PATH, response)
    logger.debug(f"[PO] Full response saved to {DEBUG_PATH}")

    vision_yaml = grab_block(response, "yaml", "VISION")
    review_yaml = grab_block(response, "yaml", "REVIEW")

    if not review_yaml:
        logger.warning("[PO] REVIEW block missing — retrying with explicit instruction.")
        retry_user = (
            user
            + "\n\nIMPORTANT: You must output BOTH fenced blocks (VISION and REVIEW) exactly as specified."
            + " If you lack details for a section, return an empty list [] or a short placeholder,"
            + " but the REVIEW block is mandatory. Regenerate the entire response now."
        )
        response = await client.chat(system=PO_PROMPT, user=retry_user)
        save_text(DEBUG_PATH, response)
        vision_yaml = grab_block(response, "yaml", "VISION")
        review_yaml = grab_block(response, "yaml", "REVIEW")

    if not review_yaml:
        logger.error("[PO] REVIEW block missing after retry; aborting to prevent stale review.")
        raise SystemExit(1)

    # Task: fix-stories - Sanitize YAML before writing
    if vision_yaml:
        sanitized_vision = sanitize_yaml(vision_yaml)
        VISION_PATH.write_text(sanitized_vision.strip() + "\n", encoding="utf-8")
        logger.info("✓ product_vision.yaml updated")
    else:
        logger.warning("[PO] VISION block missing in LLM response")

    if review_yaml:
        sanitized_review = sanitize_yaml(review_yaml)
        REVIEW_PATH.write_text(sanitized_review.strip() + "\n", encoding="utf-8")
        logger.info("✓ product_owner_review.yaml updated")
    else:
        logger.warning("[PO] REVIEW block missing in LLM response")


async def run_dspy_program(requirements_content: str, concept: str, existing_vision: str) -> None:
    program_dir = ROOT / "artifacts" / "dspy" / "po_optimized_full_snapshot_20251117T105427" / "product_owner"
    if not program_dir.exists():
        logger.error(f"[PO][DSPY] Snapshot missing at {program_dir} — aborting")
        raise SystemExit(1)

    components_path = program_dir / "program_components.json"
    if not components_path.exists():
        logger.error(f"[PO][DSPY] program_components.json missing in {program_dir}")
        raise SystemExit(1)

    with components_path.open("r", encoding="utf-8") as f:
        components = json.load(f)

    lm = build_lm_for_role("product_owner")
    dspy.configure(lm=lm)

    module = ProductOwnerModule()

    generate_cfg = components.get("modules", {}).get("generate", {})
    instructions = generate_cfg.get("instructions")
    if instructions:
        module.generate.signature.instructions = instructions

    demos = []
    for demo in generate_cfg.get("demos", []):
        example = dspy.Example(
            concept=demo.get("concept", ""),
            requirements_yaml=demo.get("requirements_yaml", ""),
            existing_vision=demo.get("existing_vision", ""),
            product_vision=demo.get("product_vision", ""),
            product_owner_review=demo.get("product_owner_review", ""),
        ).with_inputs("concept", "requirements_yaml", "existing_vision")
        demos.append(example)
    if demos:
        module.generate.demos = demos

    prediction = module(
        concept=concept,
        requirements_yaml=requirements_content,
        existing_vision=existing_vision,
    )

    vision_yaml = prediction.product_vision
    review_yaml = prediction.product_owner_review

    if vision_yaml:
        sanitized_vision = sanitize_yaml(vision_yaml)
        VISION_PATH.write_text(sanitized_vision.strip() + "\n", encoding="utf-8")
        logger.info("[PO][DSPY] ✓ product_vision.yaml updated from DSPy snapshot")
    else:
        logger.warning("[PO][DSPY] Missing product_vision output from snapshot")

    if review_yaml:
        sanitized_review = sanitize_yaml(review_yaml)
        REVIEW_PATH.write_text(sanitized_review.strip() + "\n", encoding="utf-8")
        logger.info("[PO][DSPY] ✓ product_owner_review.yaml updated from DSPy snapshot")
    else:
        logger.warning("[PO][DSPY] Missing product_owner_review output from snapshot")


if __name__ == "__main__":
    asyncio.run(main())
