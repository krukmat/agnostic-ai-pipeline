from __future__ import annotations

"""Stage-specific DSPy programs for two-stage MiPRO (Architect).

Stage 1: StoriesProgram — optimizes StoriesEpicsModule only.
Stage 2: ArchitectureProgramStage — optimizes ArchitectureModule given seeded stories/epics.
"""

import json
from typing import Tuple

import dspy
import yaml

from dspy_baseline.modules.architect import (
    StoriesEpicsModule,
    ArchitectureModule,
)


def _json_to_yaml_pairs(raw_text: str) -> Tuple[str, str]:
    if not raw_text or not raw_text.strip():
        return "", ""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text.strip(), ""
    if isinstance(data, dict):
        stories = data.get("stories", [])
        epics = data.get("epics", [])
    else:
        stories, epics = [], []
    stories_yaml = yaml.safe_dump(stories, sort_keys=False, allow_unicode=True, default_flow_style=False).strip()
    epics_yaml = yaml.safe_dump(epics, sort_keys=False, allow_unicode=True, default_flow_style=False).strip()
    return stories_yaml, epics_yaml


class StoriesProgram(dspy.Module):
    """Stage 1 program: generate stories/epics only.

    Inputs:
      - concept, requirements_yaml, product_vision, complexity_tier
    Outputs (attributes on prediction):
      - stories_yaml, epics_yaml
    """

    def __init__(self) -> None:
        super().__init__()
        self._stories = StoriesEpicsModule()

    def forward(self, concept: str, requirements_yaml: str, product_vision: str = "", complexity_tier: str = "medium"):
        s = self._stories(
            concept=concept,
            requirements_yaml=requirements_yaml,
            product_vision=product_vision or "",
            complexity_tier=complexity_tier or "medium",
        )
        stories_epics_json = getattr(s, "stories_epics_json", "") or ""
        stories_yaml, epics_yaml = _json_to_yaml_pairs(stories_epics_json)

        class _Prediction:
            pass

        pred = _Prediction()
        pred.stories_yaml = stories_yaml
        pred.epics_yaml = epics_yaml
        return pred


class ArchitectureProgramStage(dspy.Module):
    """Stage 2 program: optimize architecture using seeded stories/epics.

    Inputs:
      - concept, requirements_yaml, product_vision, complexity_tier
      - stories_yaml_seed, epics_yaml_seed (seeded from dataset)
    Output:
      - architecture_yaml
    """

    def __init__(self) -> None:
        super().__init__()
        self._arch = ArchitectureModule()

    def forward(
        self,
        concept: str,
        requirements_yaml: str,
        product_vision: str = "",
        complexity_tier: str = "medium",
        stories_yaml_seed: str = "",
        epics_yaml_seed: str = "",
    ):
        try:
            stories = yaml.safe_load(stories_yaml_seed) or []
        except Exception:
            stories = []
        try:
            epics = yaml.safe_load(epics_yaml_seed) or []
        except Exception:
            epics = []
        if not isinstance(stories, list):
            stories = []
        if not isinstance(epics, list):
            epics = []

        stories_epics_json = json.dumps({"stories": stories, "epics": epics}, ensure_ascii=False)

        a = self._arch(
            concept=concept,
            requirements_yaml=requirements_yaml,
            product_vision=product_vision or "",
            complexity_tier=complexity_tier or "medium",
            stories_epics_json=stories_epics_json,
        )

        class _Prediction:
            pass

        pred = _Prediction()
        pred.architecture_yaml = getattr(a, "architecture_yaml", "") or ""
        return pred

