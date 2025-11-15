"""
Helpers for extracting, cleaning, and validating Product Owner YAML blocks.
"""

from __future__ import annotations

import re
from typing import Any, Tuple

import yaml


VISION_LABEL = "VISION"
REVIEW_LABEL = "REVIEW"


def grab_yaml_block(text: str, label: str) -> str:
    pattern = re.compile(rf"```yaml\s*{label}\s*\n([\s\S]+?)```", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def sanitize_yaml(content: str) -> str:
    if not content.strip():
        return content
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        cleaned = re.sub(r'`([^`]+?)`', r"\1", content)
        try:
            data = yaml.safe_load(cleaned)
        except yaml.YAMLError:
            return content.strip()
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()


def extract_vision_review(text: str) -> tuple[str, str]:
    vision = sanitize_yaml(grab_yaml_block(text, VISION_LABEL))
    review = sanitize_yaml(grab_yaml_block(text, REVIEW_LABEL))
    return vision, review


def _contains_requirement_id(value: Any) -> bool:
    return bool(re.search(r"\b(FR|NFR|REQ|C|CON)\d{2,}\b", str(value), flags=re.IGNORECASE))


def validate_po_output(vision_yaml: str, review_yaml: str) -> Tuple[bool, str]:
    if not vision_yaml or not review_yaml:
        return False, "missing_yaml_blocks"

    try:
        vision = yaml.safe_load(vision_yaml) or {}
    except yaml.YAMLError:
        return False, "invalid_vision_yaml"

    try:
        review = yaml.safe_load(review_yaml) or {}
    except yaml.YAMLError:
        return False, "invalid_review_yaml"

    for key in ("product_name", "product_summary"):
        if not vision.get(key):
            return False, f"vision_missing_{key}"

    required_review_keys = ("status", "summary", "requirements_alignment", "recommended_actions", "narrative")
    for key in required_review_keys:
        if key not in review:
            return False, f"review_missing_{key}"

    alignment = review.get("requirements_alignment", {})
    if not isinstance(alignment, dict):
        return False, "alignment_not_dict"

    id_found = False
    for bucket in ("aligned", "gaps", "conflicts"):
        items = alignment.get(bucket)
        if items is None:
            return False, f"alignment_missing_{bucket}"
        if not isinstance(items, list):
            return False, f"alignment_{bucket}_not_list"
        for item in items:
            if _contains_requirement_id(item):
                id_found = True
    if not id_found:
        return False, "no_requirement_ids"

    recommended_actions = review.get("recommended_actions") or []
    if not isinstance(recommended_actions, list) or len(recommended_actions) < 2:
        return False, "insufficient_recommended_actions"

    narrative = review.get("narrative", "")
    if not isinstance(narrative, str) or len(narrative.split()) > 120:
        return False, "narrative_length_exceeded"

    return True, ""
