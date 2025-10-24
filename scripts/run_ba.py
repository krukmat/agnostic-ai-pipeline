from __future__ import annotations
import os, re, asyncio, pathlib
import yaml
from common import ensure_dirs, PLANNING, ROOT
from llm import Client
from logger import logger # Import the logger

BA_PROMPT = (ROOT/"prompts"/"ba.md").read_text(encoding="utf-8")

async def main():
    ensure_dirs()
    concept = os.environ.get("CONCEPT","").strip()
    if not concept:
        logger.error('Set CONCEPT="..." environment variable.')
        raise SystemExit(1)

    logger.info(f"[BA] Using CONCEPT: {concept}")
    client = Client(role="ba")
    logger.debug(f"[BA] Calling LLM via {client.provider_type} with model {client.model}, temp {client.temperature}, max_tokens {client.max_tokens}")
    text = await client.chat(system=BA_PROMPT, user=f"CONCEPT:\n{concept}\n\nFollow the exact output format.")
    logger.debug(f"[BA] LLM returned {len(text)} characters")
    logger.debug(f"[BA] Response preview: {text[:300]}...")

    # Save full response for debugging
    debug_file = ROOT / "debug_ba_response.txt"
    debug_file.write_text(text, encoding="utf-8")
    logger.debug(f"[BA] Full response saved to {debug_file}")

    def grab(tag, label):
        m = re.search(rf"```{tag}\s+{label}\s*([\s\S]*?)```", text)
        content = m.group(1).strip() if m else ""
        logger.debug(f"[BA] Grabbed '{tag}:{label}' with {len(content)} characters")
        return content

    requirements_text = grab("yaml","REQUIREMENTS")
    if concept:
        try:
            meta_block = yaml.safe_dump(
                {"meta": {"original_request": concept}},
                sort_keys=False,
            ).strip()
            if meta_block:
                requirements_text = f"{meta_block}\n\n{requirements_text}".rstrip() + "\n"
        except Exception as exc:
            logger.warning(f"[BA] Failed to embed original concept: {exc}")
    (PLANNING/"requirements.yaml").write_text(requirements_text, encoding="utf-8")
    logger.info("✓ requirements.yaml written under planning/")

if __name__ == "__main__":
    asyncio.run(main())
