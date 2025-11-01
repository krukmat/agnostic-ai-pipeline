from __future__ import annotations

import asyncio
import json
import os
import re
import pathlib
import sys
import textwrap
from typing import Any, Dict, List, Optional

import typer
import yaml
from common import ensure_dirs, PLANNING, ROOT, ART, save_text
from llm import Client
from logger import logger # Import the logger

BA_PROMPT = (ROOT / "prompts" / "ba.md").read_text(encoding="utf-8")
DEBUG_DIR = ART / "debug"


async def generate_requirements(concept: str) -> dict:
    ensure_dirs()
    # Use logger instead of print for debug/info messages
    logger.info(f"[BA] Using CONCEPT: {concept}")
    client = Client(role="ba")
    logger.debug(f"[BA] Calling LLM via {client.provider_type} with model {client.model}, temp {client.temperature}, max_tokens {client.max_tokens}")
    
    text = await client.chat(system=BA_PROMPT, user=f"CONCEPT:\n{concept}\n\nFollow the exact output format.")
    logger.debug(f"[BA] LLM returned {len(text)} characters")
    logger.debug(f"[BA] Response preview: {text[:300]}...")

    debug_file = DEBUG_DIR / "debug_ba_response.txt"
    save_text(debug_file, text)
    logger.debug(f"[BA] Full response saved to {debug_file}")

    def grab(tag: str, label: str) -> str:
        # Updated regex to be more robust for YAML block extraction
        match = re.search(rf"```{tag}\s*{label}\s*\n([\s\S]+?)\n```", text)
        content = match.group(1).strip() if match else ""
        logger.debug(f"[BA] Grabbed '{tag}:{label}' with {len(content)} characters")
        return content

    def sanitize_yaml(content: str) -> str:
        """Remove markdown backticks from YAML content to prevent parsing errors.

        Task: fix-stories - YAML sanitization for BA output
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
            logger.debug(f"[BA] YAML sanitized via parse/dump cycle")
            return sanitized
        except yaml.YAMLError as exc:
            # If parsing fails, try regex-based backtick removal
            logger.warning(f"[BA] YAML parsing failed: {exc}. Attempting regex cleanup...")

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
                logger.info(f"[BA] YAML sanitized via regex cleanup")
                return sanitized
            except yaml.YAMLError as exc2:
                logger.error(f"[BA] YAML sanitization failed even after cleanup: {exc2}")
                # Return cleaned version anyway, it's better than corrupted
                return cleaned

    requirements_text = grab("yaml", "REQUIREMENTS")

    # Task: fix-stories - Sanitize YAML before adding metadata
    requirements_text = sanitize_yaml(requirements_text)

    if concept:
        try:
            meta_block = yaml.safe_dump({"meta": {"original_request": concept}}, sort_keys=False).strip()
            if meta_block:
                requirements_text = f"{meta_block}\n\n{requirements_text}".rstrip() + "\n"
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(f"[BA] Failed to embed original concept: {exc}")
    output_path = PLANNING / "requirements.yaml"
    output_path.write_text(requirements_text, encoding="utf-8")
    logger.info("✓ requirements.yaml written under planning/")
    return {"requirements_path": str(output_path), "raw_response_path": str(debug_file)}


async def _main_env() -> None:
    concept = os.environ.get("CONCEPT", "").strip()
    if not concept:
        logger.error('Set CONCEPT="..." environment variable.')
        raise SystemExit(1)
    await generate_requirements(concept)


app = typer.Typer(help="Business Analyst agent CLI")


@app.command()
def generate(concept: Optional[str] = typer.Option(None, help="Concept description for requirements generation")) -> None:
    concept_value = concept or os.environ.get("CONCEPT", "").strip()
    if not concept_value:
        logger.error('Concept not provided. Use --concept flag or set CONCEPT="..." environment variable.')
        raise typer.Exit(code=1)
    result = asyncio.run(generate_requirements(concept_value))
    typer.echo(json.dumps(result, indent=2))


@app.command()
def serve(reload: bool = typer.Option(False, help="Auto-reload server on code changes")) -> None:
    from a2a.cards import business_analyst_card
    from a2a.runtime import run_agent

    card, handlers = business_analyst_card()
    run_agent("business_analyst", card, handlers, reload=reload)


if __name__ == "__main__":
    # Check if running via make or directly
    if len(sys.argv) == 1 and os.environ.get("CONCEPT"):
        asyncio.run(_main_env())
    else:
        app()
