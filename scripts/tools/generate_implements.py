"""Deterministic mapping of stories to functional requirements.

Reads requirements/stories YAML files plus an optional override map to ensure
that every story contains an `implements` array with FR IDs. The implementation
favors pure helper functions so tests can exercise the mapping logic without
filesystem side effects.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

import yaml

from logger import logger

DEFAULT_REQUIREMENTS = Path("planning/requirements.yaml")
DEFAULT_STORIES = Path("planning/stories.yaml")
DEFAULT_MAP = Path("planning/fr_story_map.yaml")


@dataclass
class FunctionalRequirement:
    fr_id: str
    title: str = ""
    description: str = ""
    keywords: Set[str] = field(default_factory=set)


def load_yaml(path: Path) -> Optional[object]:
    if not path.exists():
        logger.debug("[implements] %s not found", path)
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("[implements] Failed to parse %s: %s", path, exc)
        return None


def ensure_list_root(data: object) -> List[dict]:
    if isinstance(data, dict):
        # Accept structures like {"stories": [...]} or {"requirements": [...]}.
        for key in ("stories", "functional_requirements", "requirements"):
            value = data.get(key) if isinstance(data, dict) else None
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def extract_requirements(req_data: object, manual_keywords: Dict[str, Set[str]]) -> List[FunctionalRequirement]:
    entries = ensure_list_root(req_data)
    requirements: List[FunctionalRequirement] = []
    for entry in entries:
        fr_id = str(entry.get("id") or entry.get("fr_id") or entry.get("name") or "").strip()
        if not fr_id:
            continue
        title = str(entry.get("title") or entry.get("name") or "").strip()
        description = str(entry.get("description") or entry.get("summary") or "").strip()
        keywords = set(manual_keywords.get(fr_id, set()))
        keywords.update(_tokenize(title))
        keywords.update(_tokenize(description))
        requirements.append(FunctionalRequirement(fr_id=fr_id, title=title, description=description, keywords=keywords))
    return requirements


def load_manual_map(map_data: object) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]], Dict[str, Set[str]]]:
    """Return (fr->stories, fr->keywords, story->fr)"""
    if not isinstance(map_data, dict):
        return {}, {}, {}

    fr_to_stories: Dict[str, Set[str]] = {}
    fr_to_keywords: Dict[str, Set[str]] = {}
    story_to_fr: Dict[str, Set[str]] = {}

    for fr_id, raw in map_data.items():
        if not isinstance(fr_id, str):
            continue
        entry_stories: Set[str] = set()
        entry_keywords: Set[str] = set()

        if isinstance(raw, list):
            entry_stories.update(str(item).strip() for item in raw if str(item).strip())
        elif isinstance(raw, dict):
            stories = raw.get("stories")
            if isinstance(stories, list):
                entry_stories.update(str(item).strip() for item in stories if str(item).strip())
            keywords = raw.get("keywords")
            if isinstance(keywords, Sequence):
                for kw in keywords:
                    if isinstance(kw, str) and kw.strip():
                        entry_keywords.add(kw.strip().lower())
        else:
            entry_stories.add(str(raw).strip())

        if entry_stories:
            fr_to_stories.setdefault(fr_id, set()).update(entry_stories)
            for story_id in entry_stories:
                story_to_fr.setdefault(story_id, set()).add(fr_id)
        if entry_keywords:
            fr_to_keywords.setdefault(fr_id, set()).update(entry_keywords)

    return fr_to_stories, fr_to_keywords, story_to_fr


def _tokenize(text: str) -> Set[str]:
    if not text:
        return set()
    return set(re.findall(r"[a-z0-9]{4,}", text.lower()))


def _story_text(story: dict) -> Tuple[str, Set[str]]:
    parts: List[str] = []
    for key in ("title", "name", "summary", "description"):
        value = story.get(key)
        if isinstance(value, str):
            parts.append(value)
    acceptance = story.get("acceptance")
    if isinstance(acceptance, list):
        parts.extend(str(item) for item in acceptance)
    text = " ".join(parts)
    return text.lower(), _tokenize(text)


def generate_story_mappings(
    stories: List[dict],
    requirements: List[FunctionalRequirement],
    fr_to_stories: Dict[str, Set[str]],
    fr_to_keywords: Dict[str, Set[str]],
    story_to_fr: Dict[str, Set[str]],
) -> Dict[str, List[str]]:
    story_matches: Dict[str, Set[str]] = {sid: set(fr_ids) for sid, fr_ids in story_to_fr.items()}
    requirements_by_id = {req.fr_id: req for req in requirements}

    for story in stories:
        story_id = str(story.get("id") or story.get("story_id") or "").strip()
        if not story_id:
            continue
        matches = story_matches.setdefault(story_id, set())
        text_lower, tokens = _story_text(story)

        # Explicit FR->stories map
        for fr_id, story_ids in fr_to_stories.items():
            if story_id in story_ids:
                matches.add(fr_id)

        # Manual keyword map
        for fr_id, keywords in fr_to_keywords.items():
            for kw in keywords:
                if " " in kw:
                    if kw in text_lower:
                        matches.add(fr_id)
                elif kw in tokens:
                    matches.add(fr_id)

        # Heuristic match based on FR metadata
        for fr in requirements:
            if fr.fr_id in matches:
                continue
            if fr.keywords & tokens:
                matches.add(fr.fr_id)

        # Warn if story ended up unmatched
        if not matches:
            logger.debug("[implements] Story %s has no FR matches", story_id)

    return {story_id: sorted(list(fr_ids)) for story_id, fr_ids in story_matches.items() if fr_ids}


def apply_implements(
    stories_path: Path,
    requirements_path: Path,
    mapping_path: Path,
    dry_run: bool = False,
) -> bool:
    stories_data_raw = load_yaml(stories_path)
    stories = ensure_list_root(stories_data_raw)
    if not stories:
        logger.info("[implements] No stories to annotate (file missing or empty)")
        return False

    req_data = load_yaml(requirements_path)
    manual_map_data = load_yaml(mapping_path)
    fr_to_stories, fr_to_keywords, story_to_fr = load_manual_map(manual_map_data)
    manual_keywords = {fr_id: fr_to_keywords.get(fr_id, set()) for fr_id in fr_to_keywords}
    requirements = extract_requirements(req_data, manual_keywords)

    if not requirements:
        logger.warning("[implements] No functional requirements found; annotating via overrides only")

    match_map = generate_story_mappings(stories, requirements, fr_to_stories, fr_to_keywords, story_to_fr)

    changed = False
    for story in stories:
        story_id = str(story.get("id") or story.get("story_id") or "").strip()
        if not story_id:
            continue
        new_impl = match_map.get(story_id, [])
        if not new_impl:
            # Keep explicit empty list to surface gaps but avoid None
            if story.get("implements") != []:
                story["implements"] = []
                changed = True
            continue
        if story.get("implements") != new_impl:
            story["implements"] = new_impl
            changed = True

    if changed and not dry_run:
        logger.info("[implements] Updating %s with deterministic mappings", stories_path)
        stories_path.write_text(
            yaml.safe_dump(stories, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    elif not changed:
        logger.info("[implements] No changes required for %s", stories_path)

    return changed


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate story implements fields deterministically")
    parser.add_argument("--stories", type=Path, default=DEFAULT_STORIES, help="Path to stories.yaml")
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS, help="Path to requirements.yaml")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="Override FR/story map YAML")
    parser.add_argument("--dry-run", action="store_true", help="Inspect mappings without writing output")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = _parse_args(argv)
    apply_implements(
        stories_path=args.stories,
        requirements_path=args.requirements,
        mapping_path=args.map,
        dry_run=args.dry_run,
    )


def ensure_story_implements(
    stories_path: Path = DEFAULT_STORIES,
    requirements_path: Path = DEFAULT_REQUIREMENTS,
    mapping_path: Path = DEFAULT_MAP,
) -> bool:
    """Convenience wrapper for other modules (e.g., architect run)."""
    return apply_implements(
        stories_path=stories_path,
        requirements_path=requirements_path,
        mapping_path=mapping_path,
        dry_run=False,
    )


if __name__ == "__main__":
    main()
