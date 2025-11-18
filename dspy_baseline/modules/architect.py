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
from scripts.dspy_lm_helper import build_lm_for_role, get_role_output_cap


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
            "YAML describing AT MOST 6 top-level components: backend, frontend, data, "
            "integrations, observability, security. Each component may list up to 4 short "
            "bullet points (phrases, not paragraphs). Output ONLY the YAML, no prose/markdown."
        )
    )



class StoriesEpicsModule(dspy.Module):
    """Predict module for generating stories/epics."""

    def __init__(self, lm: dspy.LM | None = None) -> None:
        super().__init__()
        cap = get_role_output_cap("architect", "stories")
        self.lm = lm or build_lm_for_role("architect", max_output_tokens=cap)
        if lm is None:
            logger.info(
                "[ArchitectDSPy] Stories LM configured: model=%s cap=%s",
                getattr(self.lm, "model", "unknown"),
                cap,
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
        cap = get_role_output_cap("architect", "architecture")
        self.lm = lm or build_lm_for_role("architect", max_output_tokens=cap)
        if lm is None:
            logger.info(
                "[ArchitectDSPy] Architecture LM configured: model=%s cap=%s",
                getattr(self.lm, "model", "unknown"),
                cap,
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
