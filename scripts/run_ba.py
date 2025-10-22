from __future__ import annotations

import asyncio
import json
import os
import re
import pathlib
import sys
from typing import Optional

import typer
import yaml
from common import ensure_dirs, PLANNING, ROOT
from llm import Client

BA_PROMPT = (ROOT / "prompts" / "ba.md").read_text(encoding="utf-8")


async def generate_requirements(concept: str) -> dict:
    ensure_dirs()
    client = Client(role="ba")
    print(f"Using CONCEPT: {concept}")
    print(
        f"DEBUG: Calling LLM via {client.provider_type} with model {client.model}, "
        f"temp {client.temperature}, max_tokens {client.max_tokens}"
    )
    text = await client.chat(system=BA_PROMPT, user=f"CONCEPT:\n{concept}\n\nFollow the exact output format.")
    print(f"DEBUG: LLM returned {len(text)} characters")
    print(f"DEBUG: Response preview: {text[:300]}...")

    debug_file = ROOT / "debug_ba_response.txt"
    debug_file.write_text(text, encoding="utf-8")
    print(f"DEBUG: Full response saved to {debug_file}")

    def grab(tag: str, label: str) -> str:
        match = re.search(rf"```{tag}\\s+{label}\\s*([\\s\\S]*?)```", text)
        content = match.group(1).strip() if match else ""
        print(f"DEBUG: Grabbed '{tag}:{label}' with {len(content)} characters")
        return content

    requirements_text = grab("yaml", "REQUIREMENTS")
    if concept:
        try:
            meta_block = yaml.safe_dump({"meta": {"original_request": concept}}, sort_keys=False).strip()
            if meta_block:
                requirements_text = f"{meta_block}\n\n{requirements_text}".rstrip() + "\n"
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"WARNING: Failed to embed original concept: {exc}")
    output_path = PLANNING / "requirements.yaml"
    output_path.write_text(requirements_text, encoding="utf-8")
    print("✓ requirements.yaml written under planning/")
    return {"requirements_path": str(output_path), "raw_response_path": str(debug_file)}


async def _main_env() -> None:
    concept = os.environ.get("CONCEPT", "").strip()
    if not concept:
        raise SystemExit('Set CONCEPT="..."')
    await generate_requirements(concept)


app = typer.Typer(help="Business Analyst agent CLI")


@app.command()
def generate(concept: Optional[str] = typer.Option(None, help="Concept description for requirements generation")) -> None:
    concept_value = concept or os.environ.get("CONCEPT", "").strip()
    if not concept_value:
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
    if len(sys.argv) == 1 and os.environ.get("CONCEPT"):
        asyncio.run(_main_env())
    else:
        app()
