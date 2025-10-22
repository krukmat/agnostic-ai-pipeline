from __future__ import annotations

import datetime
import json
import sys
from typing import Optional

import typer
import yaml
from common import ensure_dirs, PLANNING

VISION_PATH = PLANNING / "product_vision.yaml"
REVIEW_PATH = PLANNING / "product_owner_review.yaml"


def _load_requirements() -> dict:
    req_path = PLANNING / "requirements.yaml"
    if not req_path.exists():
        raise FileNotFoundError("planning/requirements.yaml not found. Run BA stage first.")
    return yaml.safe_load(req_path.read_text(encoding="utf-8")) or {}


def _concept_from_requirements(data: dict) -> str:
    meta = data.get("meta") if isinstance(data, dict) else {}
    concept = meta.get("original_request") if isinstance(meta, dict) else ""
    return str(concept or "Unknown concept")


def _write_vision(concept: str) -> dict:
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    vision = {
        "product_name": concept[:60],
        "product_summary": concept,
        "target_users": [],
        "value_proposition": [],
        "key_capabilities": [],
        "non_goals": [],
        "success_metrics": [],
        "last_updated": timestamp,
    }
    VISION_PATH.write_text(yaml.safe_dump(vision, sort_keys=False), encoding="utf-8")
    return vision


def _write_review(alignment: str, notes: str) -> dict:
    review = {
        "status": alignment,
        "summary": [notes],
        "requirements_alignment": {
            "aligned": [],
            "gaps": [],
            "conflicts": [],
        },
        "recommended_actions": [],
        "narrative": notes,
    }
    REVIEW_PATH.write_text(yaml.safe_dump(review, sort_keys=False), encoding="utf-8")
    return review


def evaluate_alignment() -> dict:
    ensure_dirs()
    data = _load_requirements()
    concept = _concept_from_requirements(data)
    vision = _write_vision(concept)
    review = _write_review("aligned", "Baseline alignment generated automatically.")
    return {
        "concept": concept,
        "vision_path": str(VISION_PATH),
        "review_path": str(REVIEW_PATH),
        "vision": vision,
        "review": review,
    }


app = typer.Typer(help="Product Owner agent CLI")


@app.command()
def evaluate() -> None:
    result = evaluate_alignment()
    typer.echo(json.dumps(result, indent=2))


@app.command()
def serve(reload: bool = typer.Option(False, help="Auto-reload server on code changes")) -> None:
    from a2a.cards import product_owner_card
    from a2a.runtime import run_agent

    card, handlers = product_owner_card()
    run_agent("product_owner", card, handlers, reload=reload)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        typer.echo(json.dumps(evaluate_alignment(), indent=2))
    else:
        app()
