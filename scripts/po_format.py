"""
Helpers for extracting and cleaning Product Owner YAML blocks.
"""

from __future__ import annotations

import re
from typing import Optional

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
