from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
import yaml

from common import ensure_dirs, PLANNING, ROOT, ART, save_text
from scripts.utils.config_loader import load_config_base, normalize_bool
from scripts.utils.yaml_sanitizer import sanitize_po_yaml, sanitize_yaml_block, normalize_po_yaml
from scripts.utils.prompt_builders import build_po_user_payload
from scripts.utils.db_context import get_db_context_or_default
from scripts.utils.db_logger import DbLogger
from llm import Client
from logger import logger # Import the logger
from scripts.utils.llm_runner import LLMRunner

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


def build_user_payload(concept: str, existing_vision: str, requirements: str) -> str:
    concept_section = concept or "(concept not provided)"
    vision_section = existing_vision.strip() if existing_vision else "(no existing vision)"
    return (
        f"CONCEPT:\n{concept_section}\n\n"
        f"EXISTING_VISION:\n{vision_section}\n\n"
        f"REQUIREMENTS:\n{requirements.strip()}\n\n"
        "Follow the exact output format."
    )


def _use_dspy_po() -> bool:
    config = load_config_base()
    features_candidate = config.get("features", {})
    features = features_candidate if isinstance(features_candidate, dict) else {}
    flag_value = features.get("use_dspy_product_owner")
    if flag_value is None:
        flag_value = features.get("use_dspy_po")
    config_flag = normalize_bool(flag_value, default=False)

    env_override = os.environ.get("USE_DSPY_PO")
    if env_override is not None and env_override.strip() != "":
        return normalize_bool(env_override, config_flag)
    return config_flag


async def main() -> None:
    ensure_dirs()
    db = DbLogger(get_db_context_or_default())

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


    user = build_po_user_payload(concept, existing_vision, requirements_content)
    runner = LLMRunner([client])
    response, _ = await runner.chat(system=PO_PROMPT, user=user, retries=1)
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
        response, _ = await runner.chat(system=PO_PROMPT, user=retry_user, retries=1)
        save_text(DEBUG_PATH, response)
        vision_yaml = grab_block(response, "yaml", "VISION")
        review_yaml = grab_block(response, "yaml", "REVIEW")

    if not review_yaml:
        logger.error("[PO] REVIEW block missing after retry; aborting to prevent stale review.")
        raise SystemExit(1)

    # Task: fix-stories - Sanitize YAML before writing
    if vision_yaml:
        sanitized_vision = sanitize_po_yaml(vision_yaml)
        VISION_PATH.write_text(sanitized_vision.strip() + "\n", encoding="utf-8")
        logger.info("✓ product_vision.yaml updated")
    else:
        logger.warning("[PO] VISION block missing in LLM response")

    if review_yaml:
        sanitized_review = sanitize_po_yaml(review_yaml)
        REVIEW_PATH.write_text(sanitized_review.strip() + "\n", encoding="utf-8")
        logger.info("✓ product_owner_review.yaml updated")
    else:
        logger.warning("[PO] REVIEW block missing in LLM response")

    # Task: DB integration - Phase 2 - Save artifacts to DB with event logging
    if db.enabled:
        db.log_event("po_start", role="po", message="Validating product vision")
        if vision_yaml:
            db.save_artifact("po", "product_vision", sanitized_vision)
        if review_yaml:
            db.save_artifact("po", "product_owner_review", sanitized_review)
        db.log_event("po_end", role="po", message="PO artifacts generated successfully")
        logger.debug("[PO] Artifacts saved to database")


async def run_dspy_program(requirements_content: str, concept: str, existing_vision: str) -> None:
    # pragma: no cover - requires snapshot files and HF models; exercised manually
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
        sanitized_vision = sanitize_po_yaml(vision_yaml)
        VISION_PATH.write_text(sanitized_vision.strip() + "\n", encoding="utf-8")
        logger.info("[PO][DSPY] ✓ product_vision.yaml updated from DSPy snapshot")
    else:
        logger.warning("[PO][DSPY] Missing product_vision output from snapshot")

    if review_yaml:
        sanitized_review = sanitize_po_yaml(review_yaml)
        REVIEW_PATH.write_text(sanitized_review.strip() + "\n", encoding="utf-8")
        logger.info("[PO][DSPY] ✓ product_owner_review.yaml updated from DSPy snapshot")
    else:
        logger.warning("[PO][DSPY] Missing product_owner_review output from snapshot")

    # Task: DB integration - Phase 2 - Save artifacts to DB (DSPy path) with event logging
    db_ctx = get_db_context_or_default()
    if db_ctx and getattr(db_ctx, "enabled", False):
        try:
            db_ctx.log_event("po_start", role="po", message="Validating product vision (DSPy)")
            if vision_yaml:
                db_ctx.save_artifact("po", "product_vision", sanitized_vision)
            if review_yaml:
                db_ctx.save_artifact("po", "product_owner_review", sanitized_review)
            db_ctx.log_event("po_end", role="po", message="PO artifacts generated (DSPy)")
            logger.debug("[PO][DSPY] Artifacts saved to database")
        except Exception as e:
            logger.debug(f"[PO][db] Skipping DB persistence: {e}")


if __name__ == "__main__":
    asyncio.run(main())
