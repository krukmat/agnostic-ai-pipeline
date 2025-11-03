"""
DSPy module for Business Analyst requirements generation.
Baseline implementation using dspy.Predict without optimization.
"""

from typing import Any, Dict, List, Optional

import dspy
import yaml


class BARequirementsSignature(dspy.Signature):
    """Generate structured requirements from a business concept.

    Output format example for functional_requirements:
    - id: FR001
      description: User can create blog posts
      priority: High
    - id: FR002
      description: User can comment on posts
      priority: Medium
    """

    concept: str = dspy.InputField(
        desc="Business concept or idea description from stakeholder"
    )

    title: str = dspy.OutputField(
        desc="Concise project title (max 100 chars)"
    )
    description: str = dspy.OutputField(
        desc="Detailed project description (2-3 paragraphs)"
    )
    functional_requirements: str = dspy.OutputField(
        desc="List of functional requirements in YAML format"
    )
    non_functional_requirements: str = dspy.OutputField(
        desc="List of non-functional requirements in YAML format"
    )
    constraints: str = dspy.OutputField(
        desc="Project constraints and assumptions in YAML format"
    )


class BARequirementsModule(dspy.Module):
    """Business Analyst module using DSPy Predict baseline."""

    def __init__(self) -> None:
        super().__init__()
        self.generate = dspy.Predict(BARequirementsSignature)

    def forward(self, concept: str) -> Dict[str, Any]:
        """Generate requirements from concept and return structured dict."""
        prediction = self.generate(concept=concept)

        return {
            "title": prediction.title,
            "description": prediction.description,
            "functional_requirements": self._parse_yaml_field(
                prediction.functional_requirements
            ),
            "non_functional_requirements": self._parse_yaml_field(
                prediction.non_functional_requirements
            ),
            "constraints": self._parse_yaml_field(prediction.constraints),
        }

    def _parse_yaml_field(self, field_text: str) -> List[Any]:
        """Best-effort YAML parsing with fallbacks to simple lists."""
        if not field_text or field_text.strip() == "":
            return []

        try:
            parsed = yaml.safe_load(field_text)
        except Exception:
            parsed = None

        if isinstance(parsed, list):
            return parsed

        if isinstance(parsed, dict):
            return [parsed]

        lines = [
            line.strip("- ").strip()
            for line in field_text.splitlines()
            if line.strip()
        ]
        return lines


def generate_requirements(
    concept: str,
    lm: Optional[dspy.LM] = None,
) -> Dict[str, Any]:
    """Main entry point for BA requirements generation."""
    if lm is not None:
        dspy.configure(lm=lm)

    module = BARequirementsModule()
    return module.forward(concept=concept)
