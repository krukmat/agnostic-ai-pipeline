"""DSPy modules for the Architect role."""

from __future__ import annotations

import dspy


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
            "JSON o YAML con dos claves: `stories` y `epics`. "
            "`stories` es una lista de historias con campos id, epic, "
            "title, description, acceptance, priority, status. "
            "`epics` es una lista con id, name, description, priority y "
            "los ids de historias relacionadas."
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
            "YAML con backend/frontend/integration/data stores, "
            "alineado a las historias generadas."
        )
    )



class StoriesEpicsModule(dspy.Module):
    """Predict module for generating stories/epics."""

    def __init__(self) -> None:
        super().__init__()
        self.generate = dspy.Predict(StoriesEpicsSignature)

    def forward(
        self,
        concept: str,
        requirements_yaml: str,
        product_vision: str,
        complexity_tier: str,
    ):
        tier_value = (complexity_tier or "medium").strip().lower() or "medium"
        return self.generate(
            concept=concept,
            requirements_yaml=requirements_yaml,
            product_vision=product_vision or "",
            complexity_tier=tier_value,
        )


class ArchitectureModule(dspy.Module):
    """Predict module for architecture generation."""

    def __init__(self) -> None:
        super().__init__()
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
        return self.generate(
            concept=concept,
            requirements_yaml=requirements_yaml,
            product_vision=product_vision or "",
            complexity_tier=tier_value,
            stories_epics_json=stories_epics_json,
        )

