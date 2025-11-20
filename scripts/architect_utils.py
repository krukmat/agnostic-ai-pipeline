from __future__ import annotations

import json
import re
from typing import Tuple

import yaml


def sanitize_yaml_block(value) -> str:
    """Return a clean YAML string from a value or existing YAML text.

    - Strips markdown fences if present.
    - Serializes dict/list values via yaml.safe_dump.
    - Falls back to str(value) when dumping fails.
    """
    if not value:
        return ""
    if isinstance(value, str):
        cleaned = re.sub(r"```(?:yaml)?", "", value, flags=re.IGNORECASE)
        cleaned = cleaned.replace("```", "")
        return cleaned.strip()
    try:
        return yaml.safe_dump(
            value,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).strip()
    except yaml.YAMLError:
        return str(value).strip()


def convert_stories_epics_to_yaml(raw_text: str) -> Tuple[str, str]:
    """Convert a stories/epics JSON-or-YAML blob into two YAML blocks.

    Input can be JSON (preferred) or YAML. If structure is missing, returns empty blocks.
    """
    if not (raw_text or "").strip():
        return "", ""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError:
            data = None

    if isinstance(data, dict):
        stories = data.get("stories", [])
        epics = data.get("epics", [])
    else:
        stories = []
        epics = []

    stories_yaml = sanitize_yaml_block(stories)
    epics_yaml = sanitize_yaml_block(epics)
    return stories_yaml, epics_yaml

