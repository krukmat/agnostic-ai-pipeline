from __future__ import annotations

"""Lightweight guardrail to catch artifact drift before Architect/Dev runs."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from common import ART, PLANNING, ensure_dirs
from scripts.utils.config_loader import load_config_base, normalize_bool
from scripts.utils.story_manager import load_stories


GUARD_REPORT = ART / "qa" / "pipeline_guard.json"


@dataclass
class GuardResult:
    passed: bool = True
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    replan_required: bool = False

    def fail(self, message: str) -> None:
        self.passed = False
        self.issues.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def _load_yaml(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_review() -> Dict[str, Any]:
    review_path = PLANNING / "product_owner_review.yaml"
    data = _load_yaml(review_path)
    return data if isinstance(data, dict) else {}


def _load_requirements() -> Dict[str, Any]:
    requirements_path = PLANNING / "requirements.yaml"
    data = _load_yaml(requirements_path)
    return data if isinstance(data, dict) else {}


def _load_architecture() -> Dict[str, Any]:
    arch_path = PLANNING / "architecture.yaml"
    data = _load_yaml(arch_path)
    return data if isinstance(data, dict) else {}


def _load_epics() -> List[Dict[str, Any]]:
    epics_path = PLANNING / "epics.yaml"
    data = _load_yaml(epics_path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "epics" in data and isinstance(data["epics"], list):
        return data["epics"]
    return []


def _check_po_status(result: GuardResult) -> None:
    review = _load_review()
    status = review.get("status")
    if status != "approved":
        result.fail("product_owner_review.status != approved (ejecuta make ba-revise && make po)")


def _check_architecture_presence(result: GuardResult) -> None:
    arch = _load_architecture()
    epics = _load_epics()
    if not arch:
        result.fail("planning/architecture.yaml no existe o está vacío")
    if not epics:
        result.fail("planning/epics.yaml no existe o está vacío")


def _check_story_integrity(result: GuardResult, allow_empty_stories: bool) -> None:
    requirements = _load_requirements()
    frs = requirements.get("functional_requirements", [])
    fr_ids = [fr.get("id") for fr in frs if isinstance(fr, dict) and fr.get("id")]

    stories = load_stories(recover_comments=True)
    if not stories:
        if allow_empty_stories:
            result.warn("planning/stories.yaml vacío; se omite validación de stories (allow_empty_stories=1)")
            return
        result.fail("planning/stories.yaml vacío o ilegible")
        return

    # Duplicate IDs
    seen = set()
    duplicates = set()
    for story in stories:
        sid = str(story.get("id", "")).strip()
        if not sid:
            result.fail(f"Story sin id: {story}")
            continue
        if sid in seen:
            duplicates.add(sid)
        seen.add(sid)
    if duplicates:
        result.fail(f"IDs de stories duplicados: {sorted(duplicates)}")

    # Implements presence
    coverage: Dict[str, List[str]] = {fid: [] for fid in fr_ids}
    for story in stories:
        sid = story.get("id")
        implements = story.get("implements", [])
        if implements is None:
            implements = []
        if not isinstance(implements, list):
            implements = [implements]
        implements_clean = [str(it).strip() for it in implements if str(it).strip()]
        if not implements_clean:
            result.fail(f"Story {sid} sin campo implements o vacío")
            result.replan_required = True
        for fid in implements_clean:
            if fid in coverage:
                coverage[fid].append(str(sid))

    uncovered = [fid for fid, ids in coverage.items() if not ids]
    if uncovered:
        result.fail(f"FRs sin cobertura en stories: {uncovered}")
        result.replan_required = True


def _should_bypass() -> bool:
    env_flag = os.environ.get("PIPELINE_GUARD_BYPASS")
    if env_flag is not None and env_flag.strip() != "":
        return env_flag.strip().lower() in {"1", "true", "yes"}
    try:
        cfg = load_config_base()
        features = cfg.get("features", {}) if isinstance(cfg, dict) else {}
        pg = features.get("pipeline_guard", {}) if isinstance(features, dict) else {}
        return normalize_bool(pg.get("bypass"), default=False)
    except Exception:
        return False


def run_guard(check_architecture: bool = True, allow_empty_stories: bool = False) -> GuardResult:
    """
    Run validations.

    Set check_architecture=False before the first Architect run.
    Set allow_empty_stories=True para permitir planificaciones iniciales.
    """
    if _should_bypass():
        return GuardResult(passed=True, warnings=["pipeline_guard bypassed via env"])
    ensure_dirs()
    result = GuardResult()
    _check_po_status(result)
    if check_architecture:
        _check_architecture_presence(result)
    _check_story_integrity(result, allow_empty_stories)
    report = {
        "passed": result.passed,
        "issues": result.issues,
        "warnings": result.warnings,
    }
    GUARD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    GUARD_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return result


def main() -> None:
    check_arch_env = os.environ.get("CHECK_ARCHITECTURE", "1").strip().lower()
    check_architecture = check_arch_env not in {"0", "false", "no"}
    allow_empty = os.environ.get("ALLOW_EMPTY_STORIES", "0").strip().lower() in {"1", "true", "yes"}
    result = run_guard(check_architecture=check_architecture, allow_empty_stories=allow_empty)
    if result.passed:
        print("pipeline_guard: OK")
    else:
        print("pipeline_guard: FAILED")
        for issue in result.issues:
            print(f"- {issue}")
        for warning in result.warnings:
            print(f"(warn) {warning}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
