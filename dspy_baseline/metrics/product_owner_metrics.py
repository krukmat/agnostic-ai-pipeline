"""Metrics for evaluating Product Owner DSPy programs."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import yaml

STOPWORDS = {
    "the",
    "and",
    "with",
    "para",
    "con",
    "los",
    "las",
    "una",
    "unos",
    "unas",
    "user",
    "users",
    "system",
    "systems",
    "api",
    "apis",
    "rest",
    "crud",
}

TOKEN_PATTERN = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñ0-9]+")


def _get_attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _safe_yaml_load(raw: Any) -> Any:
    if not raw or not isinstance(raw, str):
        return None
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError:
        return None


def _has_text(value: Any, min_len: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= min_len


def _is_list(value: Any) -> bool:
    return isinstance(value, list)


def _list_min_items(value: Any, min_len: int = 1) -> bool:
    return isinstance(value, list) and len(value) >= min_len


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _tokenize(text: str) -> List[str]:
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(text or "")]
    return [t for t in tokens if t not in STOPWORDS]


def _extract_requirements(requirements_yaml: str) -> List[Tuple[str, str]]:
    data = _safe_yaml_load(requirements_yaml)
    if not isinstance(data, dict):
        return []

    entries: List[Tuple[str, str]] = []
    for section in (
        "functional_requirements",
        "non_functional_requirements",
        "constraints",
    ):
        section_items = data.get(section) or []
        if not isinstance(section_items, list):
            continue
        for item in section_items:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("id", "")).strip()
            desc = str(item.get("description", "")).strip()
            if rid or desc:
                entries.append((rid, desc))
    return entries


def _score_schema(vision: Dict[str, Any], review: Dict[str, Any]) -> float:
    checks = []

    # Vision checks (8)
    checks.extend(
        [
            _has_text(vision.get("product_name")),
            _has_text(vision.get("product_summary"), 40),
            _list_min_items(vision.get("target_users"), 1),
            _list_min_items(vision.get("value_proposition"), 1),
            _list_min_items(vision.get("key_capabilities"), 1),
            _is_list(vision.get("non_goals")),
            _list_min_items(vision.get("success_metrics"), 1),
            _valid_timestamp(vision.get("last_updated")),
        ]
    )

    # Review checks (7)
    req_align = review.get("requirements_alignment", {}) or {}
    checks.extend(
        [
            review.get("status") in {"aligned", "needs_adjustment", "misaligned"},
            _list_min_items(review.get("summary"), 1),
            isinstance(req_align, dict),
            _is_list(req_align.get("aligned")),
            _is_list(req_align.get("gaps")),
            _is_list(req_align.get("conflicts")),
            _list_min_items(review.get("recommended_actions"), 1),
            _has_text(review.get("narrative"), 40),
        ]
    )

    passed = sum(1 for flag in checks if flag)
    total = len(checks)
    return 30.0 * passed / total if total else 0.0


def _score_vision_completeness(vision: Dict[str, Any]) -> float:
    score = 0.0

    def richness(lst: Any, weight: float) -> float:
        if not isinstance(lst, list) or not lst:
            return 0.0
        return weight if len(lst) >= 2 else weight / 2

    score += richness(vision.get("target_users"), 6.0)
    score += richness(vision.get("value_proposition"), 6.0)
    score += richness(vision.get("key_capabilities"), 6.0)
    score += richness(vision.get("success_metrics"), 6.0)

    summary = vision.get("product_summary", "") if isinstance(vision.get("product_summary"), str) else ""
    summary_len = len(summary.strip())
    if summary_len >= 120:
        score += 6.0
    elif summary_len >= 60:
        score += 3.0

    return min(score, 30.0)


def _semantic_match(requirement_desc: str, corpus: Sequence[str]) -> bool:
    req_tokens = set(_tokenize(requirement_desc))
    if not req_tokens:
        return False
    for entry in corpus:
        entry_tokens = set(_tokenize(entry))
        if not entry_tokens:
            continue
        overlap = len(req_tokens & entry_tokens)
        if overlap and overlap / len(req_tokens) >= 0.3:
            return True
    return False


def _score_alignment(requirements_yaml: str, review: Dict[str, Any]) -> float:
    requirements = _extract_requirements(requirements_yaml)
    if not requirements:
        return 0.0

    req_align = review.get("requirements_alignment", {}) or {}
    review_segments: List[str] = []
    for key in ("summary", "recommended_actions"):
        value = review.get(key)
        if isinstance(value, list):
            review_segments.extend(str(item) for item in value)
        elif isinstance(value, str):
            review_segments.append(value)

    for key in ("aligned", "gaps", "conflicts"):
        value = req_align.get(key)
        if isinstance(value, list):
            review_segments.extend(str(item) for item in value)

    narrative = review.get("narrative")
    if isinstance(narrative, str):
        review_segments.append(narrative)

    review_text = " ".join(review_segments).lower()
    covered = 0
    for req_id, description in requirements:
        if req_id and req_id.lower() in review_text:
            covered += 1
            continue
        if description and _semantic_match(description, review_segments):
            covered += 1
    coverage = covered / len(requirements)

    if coverage >= 0.85:
        coverage_points = 22.0
    elif coverage >= 0.7:
        coverage_points = 16.0 + (coverage - 0.7) / 0.15 * 6.0
    elif coverage >= 0.5:
        coverage_points = 8.0 + (coverage - 0.5) / 0.2 * 8.0
    else:
        coverage_points = max(0.0, coverage * 8.0)

    aligned_list = req_align.get("aligned")
    aligned_ratio = 0.0
    if isinstance(aligned_list, list):
        aligned_ratio = min(len(aligned_list) / max(len(requirements), 1), 1.0)
    structure_points = min(8.0, aligned_ratio * 8.0)

    depth_points = 0.0
    if isinstance(req_align.get("gaps"), list) and req_align["gaps"]:
        depth_points += 3.0
    if isinstance(req_align.get("conflicts"), list) and req_align["conflicts"]:
        depth_points += 3.0

    return min(30.0, coverage_points + structure_points + depth_points)


def _score_review_specificity(review: Dict[str, Any]) -> float:
    score = 0.0

    summary = review.get("summary")
    if isinstance(summary, list):
        if len(summary) >= 2:
            score += 6.0
        elif summary:
            score += 3.0

    recommended = review.get("recommended_actions")
    if isinstance(recommended, list):
        if len(recommended) >= 2:
            score += 12.0
        elif recommended:
            score += 6.0

    req_align = review.get("requirements_alignment", {}) or {}
    has_gap = isinstance(req_align.get("gaps"), list) and bool(req_align["gaps"])
    has_conflict = isinstance(req_align.get("conflicts"), list) and bool(
        req_align["conflicts"]
    )
    if has_gap:
        score += 6.0
    elif isinstance(req_align.get("gaps"), list):
        score += 2.0

    if has_conflict:
        score += 6.0
    elif isinstance(req_align.get("conflicts"), list):
        score += 2.0

    narrative = review.get("narrative")
    if isinstance(narrative, str):
        length = len(narrative.strip())
        if length >= 160:
            score += 6.0
        elif length >= 80:
            score += 3.0

    return min(score, 30.0)


def product_owner_metric(example: Any, prediction: Any, trace=None) -> float:
    """Composite metric for Product Owner role.

    Returns a score in [0.0, 1.0], mapping the four components (Schema compliance,
    requirements alignment, vision completeness, review specificity) to 120 points.
    """

    vision_yaml = _get_attr(prediction, "vision_yaml")
    review_yaml = _get_attr(prediction, "review_yaml")
    requirements_yaml = _get_attr(example, "requirements")

    vision_data = _safe_yaml_load(vision_yaml) or {}
    review_data = _safe_yaml_load(review_yaml) or {}

    schema_points = _score_schema(vision_data, review_data)
    vision_points = _score_vision_completeness(vision_data)
    alignment_points = (
        _score_alignment(requirements_yaml, review_data) if requirements_yaml else 0.0
    )
    review_points = _score_review_specificity(review_data)

    total = schema_points + vision_points + alignment_points + review_points
    return max(0.0, min(total / 120.0, 1.0))


__all__ = ["product_owner_metric"]
