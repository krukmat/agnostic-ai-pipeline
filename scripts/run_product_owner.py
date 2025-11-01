from __future__ import annotations

import asyncio
import os
import re
import yaml

from common import ensure_dirs, PLANNING, ROOT, ART, save_text
from llm import Client
from logger import logger # Import the logger

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
    pattern = re.compile(rf"```{tag}\s*{label}\s*\n([\s\S]+?)\n```", re.MULTILINE)
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

    if vision_yaml:
        VISION_PATH.write_text(vision_yaml.strip() + "\n", encoding="utf-8")
        logger.info("✓ product_vision.yaml updated")
    else:
        logger.warning("[PO] VISION block missing in LLM response")

    if review_yaml:
        REVIEW_PATH.write_text(review_yaml.strip() + "\n", encoding="utf-8")
        logger.info("✓ product_owner_review.yaml updated")
    else:
        logger.warning("[PO] REVIEW block missing in LLM response")


if __name__ == "__main__":
    asyncio.run(main())
