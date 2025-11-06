
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Optional

import typer
import yaml

from common import ensure_dirs, PLANNING, ART, ROOT, save_text
from llm import Client
from logger import logger

BA_PROMPT = (ROOT / "prompts" / "ba.md").read_text(encoding="utf-8")
DEBUG_DIR = ART / "debug"

async def generate_requirements(concept: str) -> dict:
    ensure_dirs()
    logger.info(f"[BA-LEGACY] Using CONCEPT: {concept}")
    client = Client(role="ba")
    payload = f"CONCEPT:\n{concept}\n\nFollow the exact output format."
    response = await client.chat(system=BA_PROMPT, user=payload)
    save_text(DEBUG_DIR / "debug_ba_response.txt", response)

    def grab(tag: str, label: str) -> str:
        pattern = rf"```{tag}\s*{label}\s*\n([\s\S]+?)\n```"
        match = re.search(pattern, response)
        return match.group(1).strip() if match else ""

    content = grab("yaml", "REQUIREMENTS")
    requirements_text = content if content else response

    if concept:
        meta = yaml.safe_dump({"meta": {"original_request": concept}}, sort_keys=False).strip()
        requirements_text = f"{meta}\n\n{requirements_text}".strip()

    output_path = PLANNING / "requirements.yaml"
    output_path.write_text(requirements_text + "\n", encoding="utf-8")
    logger.info("✓ requirements.yaml written under planning/ (legacy)")
    return {"requirements_path": str(output_path)}

app = typer.Typer()

@app.command()
def generate(concept: Optional[str] = typer.Option(None)) -> None:
    concept_value = concept or os.environ.get("CONCEPT", "").strip()
    if not concept_value:
        typer.echo('Concept not provided. Use --concept flag or set CONCEPT="...".')
        raise typer.Exit(code=1)
    result = asyncio.run(generate_requirements(concept_value))
    typer.echo(json.dumps(result, indent=2))

if __name__ == "__main__":
    if len(os.sys.argv) == 1 and os.environ.get("CONCEPT"):
        asyncio.run(generate_requirements(os.environ["CONCEPT"].strip()))
    else:
        app()
