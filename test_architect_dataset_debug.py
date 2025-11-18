"""Debug script to test generate_architect_dataset.py process() function."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scripts.llm import Client
from scripts.run_architect import run_architect_job
from scripts.po_format import grab_yaml_block
from scripts.run_product_owner import sanitize_yaml as sanitize_po_yaml
from common import PLANNING
from logger import logger

async def test_po_call():
    """Test calling Product Owner."""
    logger.info("[DEBUG] Testing Product Owner call...")

    concept = "A simple inventory tracking system"
    requirements = """
title: Inventory System
description: Track product stock levels
functional_requirements:
  - Add/remove products
  - Update quantities
"""

    po_client = Client(role="product_owner")
    prompt_path = ROOT / "prompts" / "product_owner.md"
    system_prompt = prompt_path.read_text(encoding="utf-8")

    user = (
        f"CONCEPT:\n{concept}\n\n"
        "EXISTING_VISION:\n(no existing vision)\n\n"
        f"REQUIREMENTS:\n{requirements}\n\n"
        "Follow the exact output format (VISION/REVIEW blocks)."
    )

    try:
        response = await po_client.chat(system=system_prompt, user=user)
        logger.info(f"[DEBUG] PO Response length: {len(response)} chars")
        vision_yaml = grab_yaml_block(response, "VISION")
        logger.info(f"[DEBUG] Vision YAML extracted: {len(vision_yaml)} chars")
        return vision_yaml
    except Exception as exc:
        logger.error(f"[DEBUG] PO call failed: {exc}", exc_info=True)
        return None

async def main():
    logger.info("[DEBUG] Starting diagnostic test...")
    vision = await test_po_call()
    if vision:
        logger.info("[DEBUG] ✅ Product Owner call successful!")
        print(f"Vision YAML preview:\n{vision[:200]}...")
    else:
        logger.error("[DEBUG] ❌ Product Owner call failed")

if __name__ == "__main__":
    asyncio.run(main())
