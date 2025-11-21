"""Metrics for evaluating Architect DSPy outputs."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml


RE_STORY_ID = re.compile(r"^S(\d+)$")
PRIORITIES = {"P1", "P2", "P3"}
PRIORITIES_HML = {"HIGH", "MEDIUM", "LOW"}
ESTIMATES = {"XS", "S", "M", "L", "XL"}


def _strip_markdown_fences(raw: str) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    cleaned = re.sub(r"^```ya?ml?\s*\n?", "", raw, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"^```\s*\n?", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned, flags=re.MULTILINE)
    return cleaned.lstrip("]\n ")


def _safe_yaml_load(raw: Any) -> Any:
    if not raw or not isinstance(raw, str):
        return None
    try:
        cleaned = _strip_markdown_fences(raw)
        return yaml.safe_load(cleaned)
    except yaml.YAMLError:
        return None


def _ensure_story_list(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        if isinstance(data.get("stories"), list):
            data = data["stories"]
    return [item for item in data] if isinstance(data, list) else []


def _ensure_epic_list(data: Any) -> List[Dict[str, Any]]:
    return [item for item in data] if isinstance(data, list) else []


def _extract_architecture(data: Any) -> Dict[str, Any]:
    return data if isinstance(data, dict) else {}


def _stories_completeness(stories: List[Dict[str, Any]], epic_ids: Sequence[str]) -> float:
    if not stories:
        return 0.0
    required_fields = ["id", "epic", "title", "description", "acceptance", "priority", "estimate", "status"]
    total_fields = len(stories) * len(required_fields)
    filled = 0
    for story in stories:
        for field in required_fields:
            value = story.get(field)
            if field == "acceptance":
                if isinstance(value, list) and value:
                    filled += 1
            elif isinstance(value, str) and value.strip():
                filled += 1
    field_ratio = filled / total_fields if total_fields else 0.0

    ids = []
    sequential = False
    unique = True
    for story in stories:
        match = RE_STORY_ID.match(str(story.get("id", "")).strip())
        if not match:
            unique = False
            break
        ids.append(int(match.group(1)))
    if ids and len(ids) == len(set(ids)):
        sorted_ids = sorted(ids)
        sequential = sorted_ids == list(range(1, len(stories) + 1))
    else:
        unique = False

    epic_ref_ok = all(str(story.get("epic")) in epic_ids for story in stories if story.get("epic")) if epic_ids else False

    checks = [field_ratio, 1.0 if (unique and sequential) else 0.0, 1.0 if epic_ref_ok else 0.0]
    return (sum(checks) / len(checks)) * 25.0


def _stories_quality(stories: List[Dict[str, Any]]) -> float:
    if not stories:
        return 0.0
    total_checks = len(stories) * 5
    passed = 0
    for story in stories:
        acceptance = story.get("acceptance")
        title = story.get("title")
        description = story.get("description")
        priority = story.get("priority")
        estimate = story.get("estimate")

        if isinstance(acceptance, list) and acceptance:
            passed += 1
        if isinstance(title, str) and 1 <= len(title.strip()) <= 100:
            passed += 1
        if isinstance(description, str) and len(description.strip()) >= 20:
            passed += 1
        if isinstance(priority, str) and priority.strip() in PRIORITIES:
            passed += 1
        if isinstance(estimate, str) and estimate.strip().upper() in ESTIMATES:
            passed += 1

    ratio = passed / total_checks if total_checks else 0.0
    return ratio * 25.0


def _epics_structure(epics: List[Dict[str, Any]], stories: List[Dict[str, Any]]) -> float:
    if not epics or not stories:
        return 0.0
    story_ids = {str(story.get("id")) for story in stories if story.get("id")}
    checks: List[float] = []
    for epic in epics:
        basics = all(isinstance(epic.get(field), str) and epic.get(field).strip() for field in ("id", "name", "description"))
        story_list = epic.get("stories") if isinstance(epic.get("stories"), list) else []
        has_story_list = bool(story_list)
        stories_exist = all(str(sid) in story_ids for sid in story_list) if story_list else False
        checks.extend([
            1.0 if basics else 0.0,
            1.0 if has_story_list else 0.0,
            1.0 if stories_exist else 0.0,
        ])

    epic_ids = {str(epic.get("id")) for epic in epics if epic.get("id")}
    orphan_ok = all(str(story.get("epic")) in epic_ids for story in stories if story.get("epic"))
    checks.append(1.0 if orphan_ok else 0.0)
    return (sum(checks) / len(checks)) * 20.0 if checks else 0.0


def _architecture_validity(architecture: Dict[str, Any]) -> float:
    if not architecture:
        return 0.0
    checks = []
    for section in ("backend", "frontend"):
        section_data = architecture.get(section)
        checks.append(1.0 if isinstance(section_data, dict) else 0.0)
        if isinstance(section_data, dict):
            checks.append(1.0 if isinstance(section_data.get("framework"), str) and section_data.get("framework").strip() else 0.0)
        else:
            checks.append(0.0)
    return (sum(checks) / len(checks)) * 20.0 if checks else 0.0


def _depends_valid(stories: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, List[str]]]:
    ids = {str(story.get("id")) for story in stories if story.get("id")}
    graph: Dict[str, List[str]] = {story_id: [] for story_id in ids}
    for story in stories:
        story_id = str(story.get("id")) if story.get("id") else None
        if not story_id:
            continue
        deps = story.get("depends_on")
        if deps is None:
            continue
        if isinstance(deps, str):
            deps_list = [dep.strip() for dep in deps.split(",") if dep.strip()]
        elif isinstance(deps, list):
            deps_list = [str(dep).strip() for dep in deps if dep]
        else:
            return False, graph
        for dep in deps_list:
            if dep and dep in ids and dep != story_id:
                graph.setdefault(story_id, []).append(dep)
            elif dep:
                return False, graph
    return True, graph


def _has_cycle(graph: Dict[str, List[str]]) -> bool:
    visiting: Dict[str, int] = {}

    def dfs(node: str) -> bool:
        state = visiting.get(node, 0)
        if state == 1:
            return True
        if state == 2:
            return False
        visiting[node] = 1
        for neighbor in graph.get(node, []):
            if dfs(neighbor):
                return True
        visiting[node] = 2
        return False

    return any(dfs(node) for node in graph)


def _dependency_score(stories: List[Dict[str, Any]]) -> float:
    valid_refs, graph = _depends_valid(stories)
    if not valid_refs:
        return 0.0
    return 10.0 if not _has_cycle(graph) else 0.0


def architect_metric(example: Any, prediction: Any, trace=None) -> float:
    stories_raw = getattr(prediction, "stories_yaml", "")
    epics_raw = getattr(prediction, "epics_yaml", "")
    architecture_raw = getattr(prediction, "architecture_yaml", "")

    stories = _ensure_story_list(_safe_yaml_load(stories_raw))
    epics = _ensure_epic_list(_safe_yaml_load(epics_raw))
    architecture = _extract_architecture(_safe_yaml_load(architecture_raw))

    epic_ids = [str(epic.get("id")) for epic in epics if epic.get("id")]

    stories_completeness = _stories_completeness(stories, epic_ids)
    stories_quality = _stories_quality(stories)
    epics_structure = _epics_structure(epics, stories)
    architecture_validity = _architecture_validity(architecture)
    dependency_score = _dependency_score(stories)

    total = stories_completeness + stories_quality + epics_structure + architecture_validity + dependency_score
    return max(0.0, min(total / 100.0, 1.0))


def _stories_completeness_v2(stories: List[Dict[str, Any]], epic_ids: Sequence[str]) -> float:
    if not stories:
        return 0.0
    required_fields = ["id", "epic", "title", "description", "acceptance", "priority", "estimate"]
    total_fields = len(stories) * len(required_fields)
    filled = 0
    for story in stories:
        for field in required_fields:
            value = story.get(field)
            if field == "acceptance":
                if isinstance(value, list) and value:
                    filled += 1
            elif isinstance(value, str) and value.strip():
                filled += 1
    field_ratio = filled / total_fields if total_fields else 0.0

    expected_ids = [f"S{i+1}" for i in range(len(stories))]
    sequential_matches = 0
    seen_ids: set[str] = set()
    for idx, story in enumerate(stories):
        current = str(story.get("id", "")).strip()
        if current:
            seen_ids.add(current)
        if idx < len(expected_ids) and current == expected_ids[idx]:
            sequential_matches += 1
    sequential_ratio = sequential_matches / len(stories) if stories else 0.0
    if len(seen_ids) != len(stories):
        sequential_ratio *= 0.7

    epic_ids_set = set(epic_ids)
    stories_with_epic = sum(1 for story in stories if str(story.get("epic", "")).strip())
    stories_with_valid_epic = sum(
        1 for story in stories if str(story.get("epic", "")).strip() in epic_ids_set
    )
    epic_ratio = (stories_with_valid_epic / stories_with_epic) if stories_with_epic else 1.0

    field_score = field_ratio * 15.0
    sequential_score = sequential_ratio * 5.0
    epic_score = epic_ratio * 5.0
    return field_score + sequential_score + epic_score


def _stories_quality_v2(stories: List[Dict[str, Any]]) -> float:
    if not stories:
        return 0.0
    total_checks = len(stories) * 5
    passed = 0.0
    for story in stories:
        acceptance = story.get("acceptance")
        title = story.get("title")
        description = story.get("description")
        priority = story.get("priority")
        estimate = story.get("estimate")

        if isinstance(acceptance, list) and acceptance:
            passed += min(len(acceptance) / 3.0, 1.0)
        if isinstance(title, str) and 1 <= len(title.strip()) <= 100:
            passed += 1
        if isinstance(description, str) and len(description.strip()) >= 20:
            passed += 1
        if isinstance(priority, str):
            p = priority.strip().upper()
            if p in PRIORITIES or p in PRIORITIES_HML:
                passed += 1
        if isinstance(estimate, str) and estimate.strip().upper() in ESTIMATES:
            passed += 1

    ratio = passed / total_checks if total_checks else 0.0
    return ratio * 25.0


def _epics_structure_v2(epics: List[Dict[str, Any]], stories: List[Dict[str, Any]]) -> float:
    if not epics or not stories:
        return 0.0
    story_ids = {str(story.get("id")) for story in stories if story.get("id")}
    id_scores: List[float] = []
    list_scores: List[float] = []
    valid_scores: List[float] = []
    for epic in epics:
        epic_id = str(epic.get("id", "")).strip()
        id_scores.append(1.0 if epic_id else 0.0)
        raw_list = epic.get("stories")
        story_list = raw_list if isinstance(raw_list, list) else []
        list_scores.append(1.0 if story_list else 0.0)
        if story_list:
            valid_refs = sum(1 for sid in story_list if str(sid).strip() in story_ids)
            valid_scores.append(valid_refs / len(story_list))
        else:
            valid_scores.append(0.0)

    def _avg(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    base = (_avg(id_scores) + _avg(list_scores) + _avg(valid_scores)) / 3.0
    return base * 20.0


def _depends_valid_v2(stories: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, List[str]], int, int]:
    ids = {str(story.get("id")) for story in stories if story.get("id")}
    graph: Dict[str, List[str]] = {story_id: [] for story_id in ids}
    total_edges = 0
    valid_edges = 0
    for story in stories:
        story_id = str(story.get("id")) if story.get("id") else None
        if not story_id:
            continue
        deps = story.get("depends_on")
        if deps is None:
            continue
        if isinstance(deps, str):
            deps_list = [dep.strip() for dep in deps.split(",") if dep.strip()]
        elif isinstance(deps, list):
            deps_list = [str(dep).strip() for dep in deps if dep]
        else:
            return False, graph, valid_edges, total_edges
        for dep in deps_list:
            if not dep:
                continue
            total_edges += 1
            if dep in ids and dep != story_id:
                graph.setdefault(story_id, []).append(dep)
                valid_edges += 1
            else:
                return False, graph, valid_edges, total_edges
    return True, graph, valid_edges, total_edges


def _dependency_score_v2(stories: List[Dict[str, Any]]) -> float:
    valid_refs, graph, valid_edges, total_edges = _depends_valid_v2(stories)
    base = (valid_edges / total_edges) if total_edges else 1.0
    if not valid_refs:
        base *= 0.5
    if _has_cycle(graph):
        base *= 0.5
    return base * 10.0


def architect_metric_v2(example: Any, prediction: Any, trace=None) -> float:
    stories_raw = getattr(prediction, "stories_yaml", "")
    epics_raw = getattr(prediction, "epics_yaml", "")
    architecture_raw = getattr(prediction, "architecture_yaml", "")

    stories = _ensure_story_list(_safe_yaml_load(stories_raw))
    epics = _ensure_epic_list(_safe_yaml_load(epics_raw))
    architecture = _extract_architecture(_safe_yaml_load(architecture_raw))

    epic_ids = [str(epic.get("id")) for epic in epics if epic.get("id")]

    stories_completeness = _stories_completeness_v2(stories, epic_ids)
    stories_quality = _stories_quality_v2(stories)
    epics_structure = _epics_structure_v2(epics, stories)
    architecture_validity = _architecture_validity(architecture)
    dependency_score = _dependency_score_v2(stories)

    total = stories_completeness + stories_quality + epics_structure + architecture_validity + dependency_score
    return max(0.0, min(total / 100.0, 1.0))


def stories_epics_metric(example: Any, prediction: Any, trace=None) -> float:
    """Metric for Stage 1 (stories/epics only). Scales to 1.0.

    Expects prediction to have attributes: stories_yaml, epics_yaml.
    """
    stories_raw = getattr(prediction, "stories_yaml", "")
    epics_raw = getattr(prediction, "epics_yaml", "")

    stories = _ensure_story_list(_safe_yaml_load(stories_raw))
    epics = _ensure_epic_list(_safe_yaml_load(epics_raw))
    epic_ids = [str(epic.get("id")) for epic in epics if epic.get("id")]

    stories_completeness = _stories_completeness(stories, epic_ids)
    stories_quality = _stories_quality(stories)
    epics_structure = _epics_structure(epics, stories)
    dependency_score = _dependency_score(stories)

    # Normalize to 1.0 (sum of 4 components: 25 + 25 + 20 + 10 = 80)
    total = stories_completeness + stories_quality + epics_structure + dependency_score
    return max(0.0, min(total / 80.0, 1.0))


def architecture_only_metric(example: Any, prediction: Any, trace=None) -> float:
    """Metric for Stage 2 (architecture only). Scales to 1.0.

    Expects prediction to have attribute: architecture_yaml.
    """
    architecture_raw = getattr(prediction, "architecture_yaml", "")
    architecture = _extract_architecture(_safe_yaml_load(architecture_raw))
    architecture_validity = _architecture_validity(architecture)  # already out of 20.0
    # Normalize 20 -> 1.0
    return max(0.0, min(architecture_validity / 20.0, 1.0))
