"""Evaluation metrics for BA requirements generation."""

from __future__ import annotations

from typing import Any

import yaml


def ba_requirements_metric(example: Any, prediction: Any, trace=None) -> float:
    """Evaluate BA requirements generation quality.

    Scores from 0.0 to 1.0 based on:
    - Field completeness (title, description, requirements present)
    - YAML validity for requirement lists
    - Minimum quantity of requirements (quality proxy)
    - ID format correctness (FR001, NFR001, C001 patterns)

    Parameters
    ----------
    example : dspy.Example
        Ground truth example (not used for scoring, only for signature)
    prediction : Any
        Model prediction with BA output fields
    trace : optional
        Execution trace (not used)

    Returns
    -------
    float
        Score in [0.0, 1.0] range
    """
    score = 0.0
    max_score = 7.0  # Total points available

    # 1. Check required fields exist (1 point)
    required_fields = ["title", "description", "functional_requirements",
                      "non_functional_requirements", "constraints"]

    fields_present = sum(1 for field in required_fields
                        if hasattr(prediction, field) and getattr(prediction, field))
    if fields_present == len(required_fields):
        score += 1.0
    else:
        score += fields_present / len(required_fields)

    # 2. Validate title and description (1 point)
    if hasattr(prediction, "title") and prediction.title:
        title = str(prediction.title).strip()
        if 10 <= len(title) <= 100:
            score += 0.5

    if hasattr(prediction, "description") and prediction.description:
        desc = str(prediction.description).strip()
        if len(desc) >= 100:  # At least 100 chars for detailed description
            score += 0.5

    # 3-5. Validate each requirement category (1.5 points each)
    requirement_fields = [
        ("functional_requirements", "FR"),
        ("non_functional_requirements", "NFR"),
        ("constraints", "C"),
    ]

    for field_name, id_prefix in requirement_fields:
        if not hasattr(prediction, field_name):
            continue

        field_value = getattr(prediction, field_name)
        if not field_value:
            continue

        # Try to parse as YAML
        try:
            if isinstance(field_value, str):
                parsed = yaml.safe_load(field_value)
            elif isinstance(field_value, list):
                parsed = field_value
            else:
                continue

            if not isinstance(parsed, list):
                continue

            # YAML is valid (0.5 points)
            score += 0.5

            # Check minimum quantity: at least 2 requirements (0.5 points)
            if len(parsed) >= 2:
                score += 0.5

            # Check ID format and required fields (0.5 points)
            valid_items = 0
            for item in parsed:
                if not isinstance(item, dict):
                    continue

                # Must have id, description, priority
                has_required = all(k in item for k in ["id", "description", "priority"])
                if not has_required:
                    continue

                # ID should match pattern (FR001, NFR001, C001, etc.)
                item_id = str(item.get("id", ""))
                if item_id.startswith(id_prefix) and item_id[len(id_prefix):].isdigit():
                    valid_items += 1

            if valid_items >= 2:
                score += 0.5

        except (yaml.YAMLError, ValueError, AttributeError):
            # YAML parsing failed, no points for this category
            pass

    # Normalize to [0, 1]
    return min(score / max_score, 1.0)
