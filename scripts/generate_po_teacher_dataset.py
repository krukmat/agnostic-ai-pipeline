"""
Generate Product Owner teacher dataset using a higher-quality LLM (e.g., Gemini).

Reads concept + requirements payloads, calls the teacher model to produce
`product_vision` and `product_owner_review`, validates them with
`product_owner_metric`, and stores the results in JSONL.
"""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from typing import Dict, List, Optional

import typer
from dspy_baseline.metrics.product_owner_metrics import product_owner_metric
from logger import logger
from scripts.llm import Client
from scripts.po_format import grab_yaml_block, sanitize_yaml

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "product_owner.md"
DEFAULT_PROMPT = PROMPT_PATH.read_text(encoding="utf-8") + (
    "\n\n"
    "IMPORTANT:\n"
    "1. Always output two fenced YAML blocks exactly:\n"
    "   ```yaml VISION\n"
    "   ...\n"
    "   ```\n"
    "   ```yaml REVIEW\n"
    "   ...\n"
    "   ```\n"
    "2. If any section lacks information, use empty lists [] or short placeholders, but never omit the block.\n"
    "3. REVIEW must summarize alignment, list aligned/gaps/conflicts (even if empty) and include recommended_actions + narrative.\n"
)

app = typer.Typer(help="Generate Product Owner teacher dataset via premium LLM.")


class ExampleWrapper:
    def __init__(self, requirements: str) -> None:
        self.requirements = requirements


class PredictionWrapper:
    def __init__(self, vision_yaml: str, review_yaml: str) -> None:
        self.vision_yaml = vision_yaml
        self.review_yaml = review_yaml


def load_payloads(path: Path) -> List[Dict]:
    items: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def build_user_payload(concept: str, requirements: str, existing_vision: str = "") -> str:
    return (
        f"CONCEPT:\n{concept.strip()}\n\n"
        f"EXISTING_VISION:\n{existing_vision.strip() or '(no existing vision)'}\n\n"
        f"REQUIREMENTS:\n{requirements.strip()}\n\n"
        "Follow the exact output format."
    )


async def call_teacher(
    client: Client,
    concept: str,
    requirements_yaml: str,
    prompt: str,
    retries: int = 1,
) -> Optional[str]:
    user = build_user_payload(concept, requirements_yaml)
    response = await client.chat(system=prompt, user=user)
    if "```yaml REVIEW" not in response and retries > 0:
        logger.warning("[teacher] REVIEW block missing — retrying with explicit instruction.")
        retry_user = user + (
            "\n\nIMPORTANT: Output both fenced YAML blocks (VISION and REVIEW). "
            "If information is missing, use empty lists or short placeholders. "
            "Regenerate the full response now."
        )
        response = await client.chat(system=prompt, user=retry_user)
    if "```yaml REVIEW" not in response:
        logger.error("[teacher] REVIEW block missing after retry.")
        return None
    return response


def evaluate_sample(requirements: str, vision: str, review: str) -> float:
    example = ExampleWrapper(requirements)
    prediction = PredictionWrapper(vision, review)
    return product_owner_metric(example, prediction)


@app.command()
def generate(
    input_path: Path = typer.Option(
        Path("artifacts/synthetic/product_owner/concepts.jsonl"),
        help="Input JSONL with concept + requirements payloads.",
    ),
    output_path: Path = typer.Option(
        Path("artifacts/distillation/po_teacher_dataset.jsonl"),
        help="Destination JSONL for teacher outputs.",
    ),
    provider: str = typer.Option(
        "vertex_sdk",
        help="LLM provider for teacher (vertex_sdk, vertex_cli, openai, etc.).",
    ),
    model: str = typer.Option(
        "gemini-2.5-pro",
        help="Model name for the teacher provider.",
    ),
    temperature: float = typer.Option(0.2, help="Teacher temperature."),
    max_records: int = typer.Option(600, help="Maximum samples to generate."),
    min_score: float = typer.Option(0.85, help="Minimum metric score to keep sample."),
    seed: int = typer.Option(42, help="Random seed for shuffling inputs."),
    resume: bool = typer.Option(False, help="Append to existing output (resume)."),
) -> None:
    logger.info(f"[teacher] Loading payloads from {input_path}")
    payloads = load_payloads(input_path)
    if not payloads:
        raise typer.Exit(code=1)

    random.seed(seed)
    random.shuffle(payloads)

    client = Client(
        role="product_owner",
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=2048,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if resume else "w"
    written = 0
    attempts = 0

    async def process_entry(entry: Dict) -> Optional[Dict]:
        concept = entry.get("concept") or entry.get("input", {}).get("concept")
        requirements = entry.get("requirements_yaml") or entry.get("input", {}).get("requirements_yaml")
        if not concept or not requirements:
            logger.warning("[teacher] Missing concept or requirements, skipping.")
            return None

        response = await call_teacher(client, concept, requirements, DEFAULT_PROMPT)
        if response is None:
            return None

        vision_yaml = sanitize_yaml(grab_yaml_block(response, "VISION"))
        review_yaml = sanitize_yaml(grab_yaml_block(response, "REVIEW"))
        if not (vision_yaml and review_yaml):
            logger.warning("[teacher] Missing VISION/REVIEW content, skipping.")
            return None

        score = evaluate_sample(requirements, vision_yaml, review_yaml)
        if score < min_score:
            logger.info(f"[teacher] Sample discarded (score={score:.3f} < {min_score}).")
            return None

        return {
            "concept": concept,
            "requirements_yaml": requirements,
            "teacher_product_vision": vision_yaml,
            "teacher_product_owner_review": review_yaml,
            "score": score,
            "metadata": {
                "model": model,
                "provider": provider,
            },
        }

    with output_path.open(mode, encoding="utf-8") as fh:
        for payload in payloads:
            if written >= max_records:
                break
            attempts += 1
            result = asyncio.run(process_entry(payload))
            if not result:
                continue
            fh.write(json.dumps(result, ensure_ascii=False) + "\n")
            written += 1
            logger.info(f"[teacher] Stored sample #{written} (score={result['score']:.3f})")

    logger.info(f"[teacher] Completed: {written} samples written (attempts={attempts}) → {output_path}")


if __name__ == "__main__":
    app()
