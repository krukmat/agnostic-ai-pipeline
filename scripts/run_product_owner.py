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

DSPY_CACHE_DIR = Path(os.environ.get("DSPY_CACHEDIR", "/tmp/dspy_cache"))
DSPY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSPY_CACHEDIR", str(DSPY_CACHE_DIR))

import dspy
from dspy_baseline.modules.product_owner import ProductOwnerModule

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


def sanitize_yaml(content: str) -> str:
    """Remove markdown backticks from YAML content to prevent parsing errors.

    Task: fix-stories - YAML sanitization for PO output
    """
    if not content.strip():
        return content

    try:
        # Try to parse and re-serialize to ensure valid YAML
        data = yaml.safe_load(content)
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
        cleaned = re.sub(r'`([^`]+?)`', r'\1', content)

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


async def main() -> None:
    ensure_dirs()

    requirements_path = PLANNING / "requirements.yaml"
    if not requirements_path.exists():
        logger.error("[PO] requirements.yaml not found. Run BA stage first.")
        raise SystemExit(1)

    requirements_content = requirements_path.read_text(encoding="utf-8")
    concept_env = os.environ.get("CONCEPT", "").strip()
    concept_meta = extract_original_concept(requirements_content)
    concept = concept_env or concept_meta

    existing_vision = ""
    if VISION_PATH.exists():
        existing_vision = VISION_PATH.read_text(encoding="utf-8")

    use_dspy = os.environ.get("USE_DSPY_PO") == "1"
    if use_dspy:
        logger.info("[PO] USE_DSPY_PO=1 detected — running optimized DSPy snapshot")
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

    lm_spec = os.environ.get("DSPY_PO_LM", "ollama/granite4")
    lm_kwargs = {
        "max_tokens": int(os.environ.get("DSPY_PO_MAX_TOKENS", "4096")),
        "temperature": float(os.environ.get("DSPY_PO_TEMPERATURE", "0.3")),
    }
    if lm_spec.startswith("ollama/"):
        lm_kwargs["base_url"] = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    dspy.configure(lm=dspy.LM(lm_spec, **lm_kwargs))

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
