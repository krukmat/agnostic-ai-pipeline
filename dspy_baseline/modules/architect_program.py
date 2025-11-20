from __future__ import annotations

"""Composite DSPy program for the Architect role used in MIPROv2 tuning.

The program composes the existing StoriesEpicsModule and ArchitectureModule.
Inputs:
  - concept: str
  - requirements_yaml: str
  - product_vision: str
  - complexity_tier: str
Outputs:
  - stories_yaml: str
  - epics_yaml: str
  - architecture_yaml: str
"""

import dspy

from dspy_baseline.modules.architect import (
    StoriesEpicsModule,
    ArchitectureModule,
)


class ArchitectProgram(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self._stories = StoriesEpicsModule()
        self._arch = ArchitectureModule()

    def forward(
        self,
        concept: str,
        requirements_yaml: str,
        product_vision: str = "",
        complexity_tier: str = "medium",
    ):
        # stories/epics first
        s = self._stories(
            concept=concept,
            requirements_yaml=requirements_yaml,
            product_vision=product_vision or "",
            complexity_tier=complexity_tier or "medium",
        )
        stories_epics_json = getattr(s, "stories_epics_json", "") or ""

        # architecture
        a = self._arch(
            concept=concept,
            requirements_yaml=requirements_yaml,
            product_vision=product_vision or "",
            complexity_tier=complexity_tier or "medium",
            stories_epics_json=stories_epics_json,
        )

        # Convert stories/epics JSON to YAML strings using a lightweight helper
        stories_yaml, epics_yaml = _json_to_yaml_pairs(stories_epics_json)
        arch_yaml = getattr(a, "architecture_yaml", "") or ""

        # Return a simple object with expected attributes for the metric
        class _Prediction:
            pass

        pred = _Prediction()
        pred.stories_yaml = stories_yaml
        pred.epics_yaml = epics_yaml
        pred.architecture_yaml = arch_yaml
        return pred


def _json_to_yaml_pairs(raw_text: str) -> tuple[str, str]:
    import json, yaml
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

