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
from scripts.utils.config_loader import load_config_base, normalize_bool
from logger import logger
import importlib.util

# Task: database-layer - Import dual-write support
# Task: DB integration - Phase 2 - Use ad-hoc context for standalone runs
from scripts.utils.db_context import get_db_context_or_default

from dspy_baseline.modules.ba_requirements import (
    generate_requirements as dsp_generate,
)
from scripts.dspy_lm_helper import build_lm_for_role
import dspy
from scripts.utils.db_context import get_db_context_or_default


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
    config = load_config_base()
    features = config.get("features", {}) if isinstance(config, dict) else {}
    return normalize_bool(features.get("use_dspy_ba"), default=True)


def _run_dspy(concept: str) -> dict[str, str]:
    ensure_dirs()
    lm = build_lm_for_role("ba")
    with dspy.context(lm=lm):
        payload = dsp_generate(concept=concept, lm=None)

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

    # Task: DB integration - Phase 2 - Save artifact to DB with ad-hoc context
    db_ctx = get_db_context_or_default()
    if db_ctx and db_ctx.enabled:
        db_ctx.log_event("ba_start", role="ba", message=f"Generating requirements for: {concept}")
        db_ctx.save_artifact("ba", "requirements", data)
        db_ctx.log_event("ba_end", role="ba", message="BA requirements generated successfully")
        logger.debug("[BA] Artifact saved to database")

    return {"requirements_path": str(output_path)}


async def generate_requirements(concept: str) -> dict[str, str]:
    if _use_dspy():
        return _run_dspy(concept)
    logger.info("[BA] DSPy disabled; using legacy implementation.")
    db_ctx = get_db_context_or_default()
    legacy_module = _load_legacy_module()
    result = await legacy_module.generate_requirements(concept)

    # DB persistence (ad-hoc context)
    if db_ctx and getattr(db_ctx, "enabled", False):
        try:
            req_path = PLANNING / "requirements.yaml"
            if req_path.exists():
                payload = req_path.read_text(encoding="utf-8")
                db_ctx.log_event("ba_start", role="ba", message=f"Generating requirements for: {concept}")
                db_ctx.save_artifact("ba", "requirements", payload)
                db_ctx.log_event("ba_end", role="ba", message="Requirements generated")
        except Exception as e:
            logger.debug(f"[BA][db] Skipping DB persistence: {e}")

    return result


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
