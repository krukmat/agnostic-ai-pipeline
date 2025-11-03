"""Legacy BA entry point now delegating to DSPy baseline."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml

from common import ensure_dirs, PLANNING
from logger import logger

from dspy_baseline.modules.ba_requirements import (
    generate_requirements as dsp_generate,
)
from dspy_baseline.scripts.run_ba import load_llm_config


def _run_dspy(concept: str) -> dict[str, str]:
    """Generate requirements via DSPy and persist them under planning/."""
    ensure_dirs()

    lm = load_llm_config()
    payload = dsp_generate(concept=concept, lm=lm)

    data: dict = {"meta": {"original_request": concept}}
    if isinstance(payload, dict):
        data.update(payload)

    output_path = PLANNING / "requirements.yaml"
    output_path.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    logger.info("✓ requirements.yaml written via DSPy baseline")
    return {"requirements_path": str(output_path)}


async def generate_requirements(concept: str) -> dict[str, str]:
    """Async wrapper retained for orchestrators awaiting this function."""
    return await asyncio.to_thread(_run_dspy, concept)


app = typer.Typer(help="Business Analyst agent CLI (delegates to DSPy)")


@app.command()
def generate(
    concept: Optional[str] = typer.Option(None, help="Concept description"),
) -> None:
    concept_value = concept or os.environ.get("CONCEPT", "").strip()
    if not concept_value:
        typer.echo('Concept not provided. Use --concept or set CONCEPT="...".')
        raise typer.Exit(code=1)

    result = asyncio.run(generate_requirements(concept_value))
    typer.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 1 and os.environ.get("CONCEPT"):
        asyncio.run(generate_requirements(os.environ["CONCEPT"].strip()))
    else:
        app()
