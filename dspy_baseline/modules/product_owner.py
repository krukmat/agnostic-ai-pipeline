"""
DSPy module for the Product Owner role.
"""

from __future__ import annotations

import dspy


class ProductOwnerSignature(dspy.Signature):
    """Generate product vision + review from concept and requirements."""

    concept: str = dspy.InputField(
        desc="Concept or original request provided by BA/Stakeholder"
    )
    requirements_yaml: str = dspy.InputField(
        desc="YAML string with functional/non-functional requirements"
    )
    existing_vision: str = dspy.InputField(
        desc="Existing product vision (can be empty string for first iteration)"
    )

    product_vision: str = dspy.OutputField(
        desc="Updated product_vision.yaml content (string YAML)"
    )
    product_owner_review: str = dspy.OutputField(
        desc="product_owner_review.yaml content (string YAML)"
    )


class ProductOwnerModule(dspy.Module):
    """DSPy Predict wrapper for Product Owner generation."""

    def __init__(self) -> None:
        super().__init__()
        self.generate = dspy.Predict(ProductOwnerSignature)

    def forward(
        self,
        concept: str,
        requirements_yaml: str,
        existing_vision: str = "",
    ):
        return self.generate(
            concept=concept,
            requirements_yaml=requirements_yaml,
            existing_vision=existing_vision or "",
        )
