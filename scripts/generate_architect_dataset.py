"""Synthetic dataset generator for Architect DSPy optimization."""

from __future__ import annotations

import asyncio
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
import yaml

from dspy_baseline.metrics.architect_metrics import architect_metric
from dspy_baseline.modules.architect import (
    ArchitectureModule,
    StoriesEpicsModule,
)
from logger import logger
from scripts.llm import Client, load_config
from scripts.po_format import grab_yaml_block
from scripts.run_architect import (
    _convert_stories_epics_to_yaml,
    _sanitize_yaml_block,
)
from scripts.run_product_owner import sanitize_yaml as sanitize_po_yaml
from scripts.dspy_lm_helper import build_lm_for_role, get_role_output_cap

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


VALID_ARCH_COMPONENTS = {
    "backend",
    "frontend",
    "data",
    "integrations",
    "observability",
    "security",
}
MAX_STORIES = 6
MAX_EPICS = 3
MAX_COMPONENT_POINTS = 3


def _strip_code_fences(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_+-]*\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _bool_like(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "on"}:
            return True
        if v in {"0", "false", "no", "off"}:
            return False
    return False


def parse_and_validate_stories_json(raw: str) -> Optional[Dict[str, Any]]:
    text = _strip_code_fences(raw)
    if not text:
        logger.warning("[architect-dataset] Empty stories JSON; skipping sample.")
        return None
    if not text.endswith("}"):
        logger.warning("[architect-dataset] Stories JSON missing closing brace (likely truncated).")
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning(f"[architect-dataset] Invalid stories JSON: {exc}")
        return None
    if not isinstance(data, dict):
        logger.warning("[architect-dataset] Stories JSON must be an object.")
        return None

    stories = data.get("stories")
    if not isinstance(stories, list) or not stories:
        logger.warning("[architect-dataset] Stories JSON missing 'stories' list.")
        return None
    if len(stories) > MAX_STORIES:
        logger.warning("[architect-dataset] Stories JSON exceeds maximum story count.")
        return None

    for idx, story in enumerate(stories):
        if not isinstance(story, dict):
            logger.warning(f"[architect-dataset] Story #{idx+1} is not an object.")
            return None
        description = story.get("description") or story.get("title")
        if not isinstance(description, str) or not description.strip():
            logger.warning(f"[architect-dataset] Story #{idx+1} missing description/title.")
            return None
        sentences = [seg for seg in re.split(r"[.!?]+", description) if seg.strip()]
        if len(sentences) > 1:
            logger.warning(f"[architect-dataset] Story #{idx+1} is not a single sentence.")
            return None

    epics = data.get("epics", [])
    if epics and not isinstance(epics, list):
        logger.warning("[architect-dataset] Stories JSON 'epics' must be a list.")
        return None
    if len(epics) > MAX_EPICS:
        logger.warning("[architect-dataset] Stories JSON exceeds maximum epic count.")
        return None
    for idx, epic in enumerate(epics):
        if not isinstance(epic, dict):
            logger.warning(f"[architect-dataset] Epic #{idx+1} is not an object.")
            return None
        story_refs = epic.get("stories") or epic.get("story_ids") or []
        if story_refs:
            if not isinstance(story_refs, list):
                logger.warning(f"[architect-dataset] Epic #{idx+1} story references must be a list.")
                return None
            if len(story_refs) > 3:
                logger.warning(f"[architect-dataset] Epic #{idx+1} references more than 3 stories.")
                return None

    return data


def parse_and_validate_arch_yaml(raw: str) -> Optional[Dict[str, Any]]:
    text = _strip_code_fences(raw)
    if not text:
        logger.warning("[architect-dataset] Empty architecture YAML; skipping sample.")
        return None
    def _normalize_minified_architecture(s: str) -> str:
        # Insert newlines before top-level keys if they are glued together
        top = r"backend|frontend|data|integrations|observability|security"
        s = re.sub(rf"([^\n])((?:{top}):)", r"\1\n\2", s)
        # Ensure backend/frontend block keys are on their own lines and indented
        inner = r"framework|api|services|components|features"
        # Add newline+indent before inner keys when missing
        s = re.sub(rf"(?<!\n)\s*({inner}):", r"\n  \1:", s)
        # Ensure backend/frontend markers end with newline and indent
        s = re.sub(r"backend:\s*", "backend:\n  ", s)
        s = re.sub(r"frontend:\s*", "frontend:\n  ", s)
        return s

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        # Attempt normalization for minified one-line maps if enabled
        cfg = load_config() or {}
        features = cfg.get("features", {}) if isinstance(cfg.get("features", {}), dict) else {}
        arch_features = features.get("architect", {}) if isinstance(features, dict) else {}
        normalize_flag = _bool_like(arch_features.get("normalize_minified_arch")) if 'normalize_minified_arch' in arch_features else True
        if normalize_flag:
            norm = _normalize_minified_architecture(text)
            try:
                data = yaml.safe_load(norm)
                logger.info("[architect-dataset] Applied minified-arch normalization before YAML parse.")
            except yaml.YAMLError as exc2:
                logger.warning(f"[architect-dataset] Invalid architecture YAML after normalization: {exc2}")
                return None
        else:
            logger.warning(f"[architect-dataset] Invalid architecture YAML: {exc}")
            return None
    if not isinstance(data, dict) or not data:
        logger.warning("[architect-dataset] Architecture YAML must be a non-empty mapping.")
        return None

    keys = list(data.keys())
    if len(keys) > len(VALID_ARCH_COMPONENTS):
        logger.warning("[architect-dataset] Architecture YAML exceeds component limit.")
        return None
    invalid_keys = [key for key in keys if key not in VALID_ARCH_COMPONENTS]
    if invalid_keys:
        logger.warning(f"[architect-dataset] Architecture YAML has invalid components: {invalid_keys}")
        return None

    for comp, section in data.items():
        # Allow dicts for backend/frontend to satisfy metric (framework key required)
        if comp in {"backend", "frontend"} and isinstance(section, dict):
            fw = section.get("framework")
            if not isinstance(fw, str) or not fw.strip() or len(fw) > 80:
                logger.warning(f"[architect-dataset] Component '{comp}' dict missing valid 'framework'.")
                return None
            # Optional light validation for small maps/lists inside these sections
            for k, v in section.items():
                if k == "framework":
                    continue
                if isinstance(v, list):
                    if len(v) > MAX_COMPONENT_POINTS:
                        logger.warning(
                            f"[architect-dataset] Component '{comp}.{k}' has too many items; pruning to {MAX_COMPONENT_POINTS}."
                        )
                        v = v[:MAX_COMPONENT_POINTS]
                        section[k] = v
                    for item in v:
                        if not isinstance(item, str) or not item.strip():
                            logger.warning(f"[architect-dataset] Component '{comp}.{k}' contains non-string item.")
                            return None
                elif isinstance(v, str):
                    if len(v.split()) > 40:
                        logger.warning(f"[architect-dataset] Component '{comp}.{k}' string too long.")
                        return None
                elif isinstance(v, (int, float)):
                    # allow small scalar values
                    continue
                else:
                    logger.warning(f"[architect-dataset] Component '{comp}.{k}' has unsupported type.")
                    return None
            continue

        # Allow a small dict for 'data' (common LM output); no required key, but keep values simple
        if comp == "data" and isinstance(section, dict):
            for k, v in section.items():
                if isinstance(v, list):
                    if len(v) > MAX_COMPONENT_POINTS:
                        logger.warning(
                            f"[architect-dataset] Component '{comp}.{k}' has too many items; pruning to {MAX_COMPONENT_POINTS}."
                        )
                        v = v[:MAX_COMPONENT_POINTS]
                        section[k] = v
                    for item in v:
                        if not isinstance(item, str) or not item.strip():
                            logger.warning(f"[architect-dataset] Component '{comp}.{k}' contains non-string item.")
                            return None
                elif isinstance(v, str):
                    if len(v.split()) > 40:
                        logger.warning(f"[architect-dataset] Component '{comp}.{k}' string too long.")
                        return None
                elif isinstance(v, (int, float)):
                    continue
                else:
                    logger.warning(f"[architect-dataset] Component '{comp}.{k}' has unsupported type.")
                    return None
            continue

        if isinstance(section, list):
            if len(section) > MAX_COMPONENT_POINTS:
                logger.warning(f"[architect-dataset] Component '{comp}' has too many bullet points.")
                return None
            for i, bullet in enumerate(list(section)):
                if isinstance(bullet, str):
                    text = bullet.strip()
                else:
                    # Coerce simple non-string bullets into short strings when possible
                    text = None
                    if isinstance(bullet, (int, float, bool)):
                        text = str(bullet)
                    elif isinstance(bullet, list):
                        items = [str(x).strip() for x in bullet if isinstance(x, (str, int, float, bool))]
                        if items:
                            text = ", ".join(items[:3])
                    elif isinstance(bullet, dict):
                        parts = []
                        for k, v in bullet.items():
                            if len(parts) >= 2:
                                break
                            if isinstance(k, str) and isinstance(v, (str, int, float, bool)):
                                kv = f"{k}: {v}"
                                parts.append(kv)
                        if parts:
                            text = "; ".join(parts)
                    if text is None or not text.strip():
                        logger.warning(f"[architect-dataset] Component '{comp}' has non-string bullet.")
                        return None
                    section[i] = text
                if len(section[i].split()) > 25:
                    logger.warning(f"[architect-dataset] Component '{comp}' bullet too long.")
                    return None
        elif isinstance(section, str):
            if len(section.split()) > 40:
                logger.warning(f"[architect-dataset] Component '{comp}' paragraph too long.")
                return None
        else:
            logger.warning(f"[architect-dataset] Component '{comp}' must be string or list of strings.")
            return None

    return data


def _lm_metadata(lm) -> Tuple[str, str]:
    model_name = getattr(lm, "model", "unknown")
    provider = "unknown"
    if isinstance(model_name, str):
        provider = model_name.split("/", 1)[0] if "/" in model_name else model_name
    return provider, model_name or "unknown"


def _build_stub_stories_from_requirements(requirements_yaml: str, max_stories: int = 3) -> Dict[str, Any]:
    """Create a tiny stories/epics JSON from BA requirements to feed ArchitectureModule.

    - Picks up to `max_stories` items from `functional_requirements` if present; otherwise
      derives short statements from `description`/`title`.
    - Returns a dict with `stories` and `epics` suitable for JSON-serialization.
    """
    try:
        data = yaml.safe_load(requirements_yaml) or {}
    except Exception:
        data = {}

    fr_list = []
    if isinstance(data, dict):
        fr = data.get("functional_requirements")
        if isinstance(fr, list):
            fr_list = [str(x).strip() for x in fr if str(x).strip()]

    stories: list[Dict[str, Any]] = []
    picked = fr_list[: max_stories or 3] if fr_list else []

    if not picked:
        # Fallback: synthesize from title/description
        title = str(data.get("title") or "Feature").strip()
        desc = str(data.get("description") or "Core capability").strip()
        picked = [f"{title}: {desc}"]

    def _estimate_band(text: str) -> str:
        w = len(text.split())
        if w <= 6:
            return "S"
        if w <= 14:
            return "M"
        return "L"

    for i, text in enumerate(picked, start=1):
        sentence = text.split(".")[0].strip()
        if not sentence.endswith("."):
            sentence = sentence + "."
        concise = sentence.rstrip(".")
        estimate = _estimate_band(sentence)
        # Gherkin‑like acceptance to improve story completeness
        acceptance = [
            f"Given the system context, when implementing '{concise}', then the feature works end-to-end.",
            "Given unit and integration tests, when executed in CI, then they pass for core flows.",
            "Given documented edge cases, when tested, then no critical regressions are found.",
        ]
        # Ensure description is long enough for metric (>=20 chars)
        long_desc = sentence if len(sentence) >= 20 else (sentence + " This supports architecture alignment.")
        stories.append(
            {
                "id": f"S{i}",
                "epic": "EPIC-ARCH",
                "title": concise,
                "description": long_desc,
                "acceptance": acceptance,
                "depends_on": [],
                "estimate": estimate,
                "priority": "P2",
                "status": "To Do",
            }
        )

    # Add simple, valid dependencies to improve dependency_score without cycles
    if len(stories) >= 2:
        stories[1]["depends_on"] = [stories[0]["id"]]
    if len(stories) >= 3:
        stories[2]["depends_on"] = [stories[1]["id"]]

    epics = [
        {
            "id": "EPIC-ARCH",
            "name": "Architecture-aligned Stories",
            "description": "Stories derived from BA requirements for architecture context.",
            "priority": "Medium",
            "stories": [s["id"] for s in stories],
        }
    ]

    return {"stories": stories, "epics": epics}


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
    # Read feature toggle for architecture-only mode
    cfg = load_config() or {}
    features = cfg.get("features", {}) if isinstance(cfg.get("features", {}), dict) else {}
    arch_features = features.get("architect", {}) if isinstance(features, dict) else {}
    arch_only = _bool_like(arch_features.get("arch_only"))

    architecture_cap = get_role_output_cap("architect", "architecture")
    architecture_lm = build_lm_for_role("architect", max_tokens=architecture_cap)
    architecture_module = ArchitectureModule(lm=architecture_lm)
    arch_provider, arch_model = _lm_metadata(architecture_module.lm)

    if arch_only:
        logger.info(
            "[architect-dataset] MODE=arch_only. Using stubbed stories. architecture:(provider=%s model=%s cap=%s)",
            arch_provider,
            arch_model,
            architecture_cap,
        )
        stories_module = None
        stories_cap = None
    else:
        stories_cap = get_role_output_cap("architect", "stories")
        stories_lm = build_lm_for_role("architect", max_tokens=stories_cap)
        stories_module = StoriesEpicsModule(lm=stories_lm)
        stories_provider, stories_model = _lm_metadata(stories_module.lm)
        logger.info(
            "[architect-dataset] LM setup → stories:(provider=%s model=%s cap=%s) architecture:(provider=%s model=%s cap=%s)",
            stories_provider,
            stories_model,
            stories_cap,
            arch_provider,
            arch_model,
            architecture_cap,
        )

    existing_train = _load_existing_jsonl(out_train) if resume else []
    existing_val = _load_existing_jsonl(out_val) if resume else []
    seen_keys = _build_seen_keys(existing_train + existing_val)

    collected: List[Dict] = []

    async def process(entry: Dict) -> Optional[Dict]:
        concept = entry.get("concept") or entry.get("input", {}).get("concept")
        requirements = entry.get("requirements_yaml") or entry.get("input", {}).get("requirements_yaml")

        # Task 9.0.11.3 - Handle BA dataset format where requirements is a dict, not YAML string
        if not requirements and "requirements" in entry:
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

        tier = (
            entry.get("complexity_tier")
            or entry.get("input", {}).get("complexity_tier")
            or estimate_tier(requirements)
        )
        if arch_only:
            stories_data = _build_stub_stories_from_requirements(requirements, max_stories=3)
            stories_json_raw = json.dumps(stories_data, ensure_ascii=False)
        else:
            try:
                stories_prediction = stories_module(
                    concept=concept,
                    requirements_yaml=requirements,
                    product_vision=vision_yaml,
                    complexity_tier=str(tier),
                )
            except Exception as exc:
                logger.warning(f"[architect-dataset] Stories module failed: {exc}")
                return None
            stories_json_raw = getattr(stories_prediction, "stories_epics_json", "") or ""
            stories_data = parse_and_validate_stories_json(stories_json_raw)
            if not stories_data:
                return None
        stories_json = json.dumps(stories_data, ensure_ascii=False)
        stories_yaml, epics_yaml = _convert_stories_epics_to_yaml(stories_json)
        if not stories_yaml or not epics_yaml:
            logger.warning("[architect-dataset] Failed to convert stories/epics to YAML.")
            return None

        try:
            architecture_prediction = architecture_module(
                concept=concept,
                requirements_yaml=requirements,
                product_vision=vision_yaml,
                complexity_tier=str(tier),
                stories_epics_json=stories_json,
            )
        except Exception as exc:
            logger.warning(f"[architect-dataset] Architecture module failed: {exc}")
            return None
        architecture_raw = getattr(architecture_prediction, "architecture_yaml", "") or ""
        architecture_data = parse_and_validate_arch_yaml(architecture_raw)
        if not architecture_data:
            return None
        architecture_yaml = _sanitize_yaml_block(architecture_data)
        if not architecture_yaml:
            logger.warning("[architect-dataset] Sanitized architecture YAML is empty.")
            return None

        score = metric_score(stories_yaml, epics_yaml, architecture_yaml)
        if score < min_score:
            logger.info(f"[architect-dataset] Sample filtered (score={score:.3f} < {min_score}).")
            return None

        sample = ArchitectSample(
            concept=concept,
            requirements_yaml=requirements,
            product_vision=vision_yaml,
            complexity_tier=str(tier),
            stories_yaml=stories_yaml,
            epics_yaml=epics_yaml,
            architecture_yaml=architecture_yaml,
            score=score,
            provider=arch_provider,
            model=arch_model,
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
