"""DSPy modules for the Architect role.

The Architect pipeline is split into two bounded DSPy modules:
1. StoriesEpicsModule → emits compact JSON (max 6 stories / 3 epics).
2. ArchitectureModule → emits short YAML snippets for core components.

Constraining each stage keeps LM outputs small, reduces truncation,
and makes dataset generation / MiPRO supervision more reliable.
"""

from __future__ import annotations

import dspy
from logger import logger
from pathlib import Path
import json
import yaml
from scripts.dspy_lm_helper import build_lm_for_role, get_role_output_cap, pick_max_tokens_for


class StoriesEpicsSignature(dspy.Signature):
    """Generate a list of user stories grouped into epics."""

    concept: str = dspy.InputField(desc="Original product concept or request.")
    requirements_yaml: str = dspy.InputField(
        desc="requirements.yaml contents from BA output."
    )
    product_vision: str = dspy.InputField(
        desc="product_vision.yaml contents. Can be empty."
    )
    complexity_tier: str = dspy.InputField(
        desc="Architect complexity tier (simple, medium, corporate)."
    )

    stories_epics_json: str = dspy.OutputField(
        desc=(
            "Valid JSON object with AT MOST 6 user stories and AT MOST 3 epics. "
            "Each story MUST be a single sentence. Each epic groups 1–3 stories by ID. "
            "Output ONLY the JSON object, with no extra text, comments, or markdown."
        )
    )


class ArchitectureSignature(dspy.Signature):
    """Generate a high-level architecture informed by previous stories."""

    concept: str = dspy.InputField(desc="Original product concept o petición.")
    requirements_yaml: str = dspy.InputField(
        desc="requirements.yaml contents del BA."
    )
    product_vision: str = dspy.InputField(
        desc="product_vision.yaml contents."
    )
    complexity_tier: str = dspy.InputField(
        desc="simple, medium o corporate."
    )
    stories_epics_json: str = dspy.InputField(
        desc="Salida del módulo de historias/épicas."
    )

    architecture_yaml: str = dspy.OutputField(
        desc=(
            "YAML describing AT MOST 6 top-level components: backend, frontend, data, integrations, observability, security. "
            "For backend and frontend USE A MAP with at least: framework: <string>. You MAY add small maps/lists (e.g., services: [svcA], api: [REST, GraphQL]). "
            "For other components USE up to 3 short bullet points (phrases, not paragraphs). Output ONLY the YAML, no prose/markdown."
        )
    )



class StoriesEpicsModule(dspy.Module):
    """Predict module for generating stories/epics."""

    def __init__(self, lm: dspy.LM | None = None) -> None:
        super().__init__()
        # Try to load optimized instructions for Stories stage (if present)
        _maybe_apply_instructions("stories")
        cap = get_role_output_cap("architect", "stories")
        mtok = pick_max_tokens_for("architect", cap)
        self.lm = lm or build_lm_for_role("architect", max_tokens=mtok)
        if lm is None:
            logger.info(
                "[ArchitectDSPy] Stories LM configured: model=%s cap=%s (max_tokens=%s)",
                getattr(self.lm, "model", "unknown"),
                cap,
                getattr(self.lm, "max_tokens", None) or "?",
            )
        self.generate = dspy.Predict(StoriesEpicsSignature)

    def forward(
        self,
        concept: str,
        requirements_yaml: str,
        product_vision: str,
        complexity_tier: str,
    ):
        tier_value = (complexity_tier or "medium").strip().lower() or "medium"
        with dspy.context(lm=self.lm):
            return self.generate(
                concept=concept,
                requirements_yaml=requirements_yaml,
                product_vision=product_vision or "",
                complexity_tier=tier_value,
            )


class ArchitectureModule(dspy.Module):
    """Predict module for architecture generation."""

    def __init__(self, lm: dspy.LM | None = None) -> None:
        super().__init__()
        # Try to load optimized instructions for Architecture stage (if present)
        _maybe_apply_instructions("architecture")
        cap = get_role_output_cap("architect", "architecture")
        mtok = pick_max_tokens_for("architect", cap)
        self.lm = lm or build_lm_for_role("architect", max_tokens=mtok)
        if lm is None:
            logger.info(
                "[ArchitectDSPy] Architecture LM configured: model=%s cap=%s (max_tokens=%s)",
                getattr(self.lm, "model", "unknown"),
                cap,
                getattr(self.lm, "max_tokens", None) or "?",
            )
        self.generate = dspy.Predict(ArchitectureSignature)

    def forward(
        self,
        concept: str,
        requirements_yaml: str,
        product_vision: str,
        complexity_tier: str,
        stories_epics_json: str,
    ):
        tier_value = (complexity_tier or "medium").strip().lower() or "medium"
        with dspy.context(lm=self.lm):
            return self.generate(
                concept=concept,
                requirements_yaml=requirements_yaml,
                product_vision=product_vision or "",
                complexity_tier=tier_value,
                stories_epics_json=stories_epics_json,
            )


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _load_components_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _extract_instructions(components: dict, key_candidates: list[str]) -> str | None:
    modules = components.get("modules", {}) if isinstance(components.get("modules"), dict) else {}
    # Try key candidates first
    for key in key_candidates:
        block = modules.get(key)
        if isinstance(block, dict) and isinstance(block.get("instructions"), str) and block["instructions"].strip():
            return block["instructions"].strip()
    # Otherwise, pick first module with instructions
    for block in modules.values():
        if isinstance(block, dict) and isinstance(block.get("instructions"), str) and block["instructions"].strip():
            return block["instructions"].strip()
    return None


def _maybe_apply_instructions(stage: str) -> None:
    """Load optimized instructions from artifacts and apply to signatures.

    stage: 'stories' or 'architecture'
    """
    root = _project_root()
    cfg = _read_yaml(root / "config.yaml")
    features = cfg.get("features", {}) if isinstance(cfg.get("features", {}), dict) else {}
    arch_features = features.get("architect", {}) if isinstance(features, dict) else {}
    # If a global switch exists and is false, skip
    use_opt = arch_features.get("use_optimized_prompt")
    if use_opt is False:
        return

    # Determine source paths (prefer stage-specific; fallback to end-to-end)
    sources: list[Path] = []
    if stage == "stories":
        sources.append(root / "artifacts/dspy/optimizer/architect_stories/program_components.json")
    elif stage == "architecture":
        sources.append(root / "artifacts/dspy/optimizer/architect_arch/program_components.json")
    sources.append(root / "artifacts/dspy/optimizer/architect/program_components.json")

    # Key candidates by stage
    key_candidates = ["_stories"] if stage == "stories" else ["_arch"]

    for path in sources:
        if not path.exists():
            continue
        components = _load_components_json(path)
        instr = _extract_instructions(components, key_candidates)
        if instr:
            if stage == "stories":
                StoriesEpicsSignature.instructions = instr
                logger.info("[ArchitectDSPy] Applied optimized instructions for Stories from %s", path)
            else:
                ArchitectureSignature.instructions = instr
                logger.info("[ArchitectDSPy] Applied optimized instructions for Architecture from %s", path)
            return
    # Nothing applied; proceed silently
    return
