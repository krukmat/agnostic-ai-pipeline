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

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from common import ensure_dirs, PLANNING
from logger import logger
import importlib.util

from dspy_baseline.modules.ba_requirements import (
    generate_requirements as dsp_generate,
)
from dspy_baseline.scripts.run_ba import load_llm_config


def _load_legacy_module():
    spec = importlib.util.spec_from_file_location(
        "ba_legacy", Path(__file__).with_name("ba_legacy.py")
    )
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    raise ImportError("Unable to load ba_legacy module.")


def _use_dspy() -> bool:
    from pathlib import Path
    import yaml

    config = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    return config.get("features", {}).get("use_dspy_ba", True)


def _run_dspy(concept: str) -> dict[str, str]:
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
    if _use_dspy():
        return await asyncio.to_thread(_run_dspy, concept)
    logger.info("[BA] DSPy disabled; using legacy implementation.")
    legacy_module = _load_legacy_module()
    return await legacy_module.generate_requirements(concept)


app = typer.Typer(help="Business Analyst agent CLI (DSPy or legacy)")


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
