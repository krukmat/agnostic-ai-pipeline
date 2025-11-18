"""Synthetic dataset generator for Architect DSPy optimization."""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer

from common import PLANNING
from dspy_baseline.metrics.architect_metrics import architect_metric
from logger import logger
from scripts.llm import Client
from scripts.po_format import grab_yaml_block
from scripts.run_architect import run_architect_job
from scripts.run_product_owner import sanitize_yaml as sanitize_po_yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BA_DATA = ROOT / "dspy_baseline" / "data" / "production" / "ba_train.jsonl"
DEFAULT_OUTPUT_TRAIN = ROOT / "dspy_baseline" / "data" / "production" / "architect_train.jsonl"
DEFAULT_OUTPUT_VAL = ROOT / "dspy_baseline" / "data" / "production" / "architect_val.jsonl"

app = typer.Typer(help="Generate Architect synthetic dataset (requires BA/PO/Architect providers).")


@dataclass
class ArchitectSample:
    concept: str
    requirements_yaml: str
    product_vision: str
    complexity_tier: str
    stories_yaml: str
    epics_yaml: str
    architecture_yaml: str
    score: float
    provider: str
    model: str

    def to_json(self) -> Dict:
        return {
            "input": {
                "concept": self.concept,
                "requirements_yaml": self.requirements_yaml,
                "product_vision": self.product_vision,
                "complexity_tier": self.complexity_tier,
            },
            "output": {
                "stories_yaml": self.stories_yaml,
                "epics_yaml": self.epics_yaml,
                "architecture_yaml": self.architecture_yaml,
            },
            "metadata": {
                "score": self.score,
                "provider": self.provider,
                "model": self.model,
            },
        }


def load_ba_examples(path: Path) -> List[Dict]:
    payloads: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            payloads.append(json.loads(line))
    return payloads


def estimate_tier(requirements_yaml: str) -> str:
    words = len(requirements_yaml.split())
    if words <= 350:
        return "simple"
    if words >= 900:
        return "corporate"
    return "medium"


def metric_score(stories: str, epics: str, architecture: str) -> float:
    class Prediction:
        def __init__(self, s: str, e: str, a: str) -> None:
            self.stories_yaml = s
            self.epics_yaml = e
            self.architecture_yaml = a

    return architect_metric(None, Prediction(stories, epics, architecture))


def split_train_val(samples: List[Dict], val_ratio: float = 0.2) -> tuple[List[Dict], List[Dict]]:
    size = len(samples)
    val_size = max(1, int(size * val_ratio))
    return samples[:-val_size], samples[-val_size:]


def write_planning_artifacts(requirements: str, vision: str) -> None:
    (PLANNING / "requirements.yaml").write_text(requirements, encoding="utf-8")
    (PLANNING / "product_vision.yaml").write_text(vision, encoding="utf-8")


def read_architect_outputs() -> Optional[Dict[str, str]]:
    stories_path = PLANNING / "stories.yaml"
    epics_path = PLANNING / "epics.yaml"
    architecture_path = PLANNING / "architecture.yaml"
    if not (stories_path.exists() and epics_path.exists() and architecture_path.exists()):
        return None
    return {
        "stories": stories_path.read_text(encoding="utf-8"),
        "epics": epics_path.read_text(encoding="utf-8"),
        "architecture": architecture_path.read_text(encoding="utf-8"),
    }


async def call_product_owner(requirements: str, concept: str, client: Client) -> Optional[str]:
    prompt_path = ROOT / "prompts" / "product_owner.md"
    if not prompt_path.exists():
        return None
    user = (
        f"CONCEPT:\n{concept}\n\n"
        "EXISTING_VISION:\n(no existing vision)\n\n"
        f"REQUIREMENTS:\n{requirements}\n\n"
        "Follow the exact output format (VISION/REVIEW blocks)."
    )
    try:
        return await client.chat(system=prompt_path.read_text(encoding="utf-8"), user=user)
    except Exception as exc:
        logger.error(f"[architect-dataset] Product Owner call failed: {exc}")
        return None


@app.command()
def generate(
    ba_path: Path = typer.Option(DEFAULT_BA_DATA, help="BA outputs JSONL"),
    out_train: Path = typer.Option(DEFAULT_OUTPUT_TRAIN, help="Train JSONL output"),
    out_val: Path = typer.Option(DEFAULT_OUTPUT_VAL, help="Validation JSONL output"),
    min_score: float = typer.Option(0.6, help="Minimum architect_metric score"),
    max_records: int = typer.Option(200, help="Desired sample count"),
    seed: int = typer.Option(42, help="Shuffle seed"),
    resume: bool = typer.Option(False, help="Append to existing JSONL files instead of overwriting"),
) -> None:
    payloads = load_ba_examples(ba_path)
    if not payloads:
        logger.error("[architect-dataset] No BA payloads found.")
        raise typer.Exit(code=1)

    random.seed(seed)
    random.shuffle(payloads)

    po_client = Client(role="product_owner")
    architect_client = Client(role="architect")

    existing_train = _load_existing_jsonl(out_train) if resume else []
    existing_val = _load_existing_jsonl(out_val) if resume else []
    seen_keys = _build_seen_keys(existing_train + existing_val)

    collected: List[Dict] = []

    async def process(entry: Dict) -> Optional[Dict]:
        concept = entry.get("concept") or entry.get("input", {}).get("concept")
        requirements = entry.get("requirements_yaml") or entry.get("input", {}).get("requirements_yaml")

        # Task 9.0.11.3 - Handle BA dataset format where requirements is a dict, not YAML string
        if not requirements and "requirements" in entry:
            import yaml
            requirements = yaml.dump(entry["requirements"], default_flow_style=False, allow_unicode=True)

        if not concept or not requirements:
            logger.warning(f"[architect-dataset] Skipping entry: concept={bool(concept)}, requirements={bool(requirements)}")
            return None

        po_response = await call_product_owner(requirements, concept, po_client)
        if not po_response:
            return None
        vision_yaml = sanitize_po_yaml(grab_yaml_block(po_response, "VISION"))
        if not vision_yaml:
            logger.warning("[architect-dataset] Missing VISION block; skipping sample.")
            return None

        write_planning_artifacts(requirements, vision_yaml)
        result = await run_architect_job(concept=concept, allow_partial_blocks=True)
        outputs = read_architect_outputs()
        if not outputs:
            logger.warning("[architect-dataset] Architect outputs missing; skipping sample.")
            return None

        score = metric_score(outputs["stories"], outputs["epics"], outputs["architecture"])
        if score < min_score:
            logger.info(f"[architect-dataset] Sample filtered (score={score:.3f} < {min_score}).")
            return None

        tier = result.get("complexity_tier", "medium") if isinstance(result, dict) else estimate_tier(requirements)

        sample = ArchitectSample(
            concept=concept,
            requirements_yaml=requirements,
            product_vision=vision_yaml,
            complexity_tier=str(tier),
            stories_yaml=outputs["stories"],
            epics_yaml=outputs["epics"],
            architecture_yaml=outputs["architecture"],
            score=score,
            provider=architect_client.provider_type,
            model=architect_client.model,
        )

        sample_json = sample.to_json()
        sample_key = _sample_key(sample_json)
        if sample_key in seen_keys:
            logger.info(f"[architect-dataset] Duplicate sample skipped for concept '{concept}'.")
            return None

        seen_keys.add(sample_key)
        return sample_json

    async def run_loop() -> None:
        for entry in payloads:
            if len(collected) >= max_records:
                break
            result = await process(entry)
            if result:
                collected.append(result)

    # Task 9.0.11.3 - Fix asyncio.run() en contexto sync
    # Use new event loop + proper async cleanup
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_loop())
        finally:
            # Close all pending tasks before closing loop
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
    except Exception as exc:
        logger.error(f"[architect-dataset] Generation failed: {exc}", exc_info=True)
        raise typer.Exit(code=2)

    if not collected:
        logger.error("[architect-dataset] No samples collected (provider offline?).")
        raise typer.Exit(code=3)

    train, val = split_train_val(collected)
    out_train.parent.mkdir(parents=True, exist_ok=True)
    out_val.parent.mkdir(parents=True, exist_ok=True)
    combined_train = existing_train + train if resume else train
    combined_val = existing_val + val if resume else val

    _write_jsonl(out_train, combined_train)
    _write_jsonl(out_val, combined_val)

    logger.info(
        f"[architect-dataset] Wrote {len(train)} train / {len(val)} val samples (min_score={min_score})"
        + (" (resume mode)" if resume else "")
    )


def _load_existing_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    data: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"[architect-dataset] Skipping malformed JSONL line in {path}.")
    return data


def _write_jsonl(path: Path, rows: List[Dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for item in rows:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def _sample_key(sample: Dict) -> Tuple[str, str]:
    inp = sample.get("input", {})
    concept = inp.get("concept", "")
    requirements = inp.get("requirements_yaml", "")
    return (concept, requirements)


def _build_seen_keys(rows: List[Dict]) -> set[Tuple[str, str]]:
    keys: set[Tuple[str, str]] = set()
    for row in rows:
        keys.add(_sample_key(row))
    return keys


if __name__ == "__main__":
    app()
