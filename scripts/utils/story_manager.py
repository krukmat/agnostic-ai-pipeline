from __future__ import annotations

"""Story management helpers shared across roles.

Provides consistent load/save and status update helpers with optional recovery
for commented YAML (used by Dev). All functions are defensive and return empty
structures on failure.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from common import PLANNING


STORIES_PATH = PLANNING / "stories.yaml"


def _recover_commented_yaml(text: str) -> Optional[Any]:
    """Attempt to recover YAML where all lines are commented out."""
    clean: List[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            clean.append(re.sub(r"^\s*#\s?", "", line))
        else:
            clean.append(line)
    candidate = "\n".join(clean).strip()
    if not candidate:
        return None
    try:
        loaded = yaml.safe_load(candidate)
        # If top-level is dict with stories key, return that
        if isinstance(loaded, dict) and "stories" in loaded:
            return loaded["stories"]
        return loaded
    except Exception:
        return None


def load_stories(recover_comments: bool = False) -> List[Dict[str, Any]]:
    """Load stories from planning/stories.yaml.

    Args:
        recover_comments: attempt to recover commented YAML (used by Dev).
    """
    path = STORIES_PATH
    if not path.exists():
        return []

    raw = path.read_text(encoding="utf-8")
    data = None
    try:
        data = yaml.safe_load(raw)
    except Exception:
        data = None

    if isinstance(data, dict) and "stories" in data:
        data = data["stories"]

    if not isinstance(data, list) and recover_comments:
        recovered = _recover_commented_yaml(raw)
        if isinstance(recovered, dict) and "stories" in recovered:
            recovered = recovered["stories"]
        if isinstance(recovered, list):
            data = recovered

    return data if isinstance(data, list) else []


def save_stories(stories: List[Dict[str, Any]]) -> None:
    """Persist stories to planning/stories.yaml."""
    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORIES_PATH.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            stories,
            fh,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )


def mark_story_status(story_id: str, status: str) -> bool:
    """Set a story status and persist. Returns True if updated."""
    stories = load_stories()
    updated = False
    for s in stories:
        if str(s.get("id", "")).lower() == str(story_id).lower():
            s["status"] = status
            updated = True
            break
    if updated:
        save_stories(stories)
    return updated


def mark_story_todo(story_id: str) -> bool:
    """Shortcut to mark story as todo."""
    return mark_story_status(story_id, "todo")
