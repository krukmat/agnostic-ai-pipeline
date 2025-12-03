from __future__ import annotations

import textwrap
import yaml
from typing import Dict, Any, Optional


def build_dev_prompt(base_system: str, story: Dict[str, Any], files_ctx: str, extra_system: str = "") -> tuple[str, str]:
    """Return (system, user) prompt for developer role."""
    system = base_system
    if extra_system:
        system = (base_system + "\n\n" + extra_system).strip()
    user = textwrap.dedent(
        f"""\
        STORY (YAML):
        ```yaml
        {yaml.safe_dump(story, sort_keys=False, allow_unicode=True)}
        ```

        REPO TREE (first lines):
        ```
        {files_ctx}
        ```
        """
    )
    return system, user


def build_architect_prompt(
    concept_value: str,
    requirements_content: str,
    complexity_tier: str,
    stories_content: str,
    detail_level: str,
    iteration_count: int,
    architect_mode: str,
    story_id: str,
) -> str:
    if architect_mode == "review_adjustment":
        user_input = (
            f"CURRENT_STORIES:\n{stories_content}\n\n"
            f"DETAIL_LEVEL: {detail_level}\nITERATION_COUNT: {iteration_count}\n"
            "INSTRUCTION: Ajusta únicamente las historias en estado in_review o bloqueadas, "
            "añadiendo criterios de aceptación técnicos y accionables."
        )
        if story_id:
            user_input += f"\nTARGET_STORY: {story_id}"
    else:
        user_input = (
            f"CONCEPT:\n{concept_value}\n\nREQUIREMENTS:\n{requirements_content}\n\n"
            f"COMPLEXITY_TIER: {complexity_tier.upper()}\n\n"
            "Follow the exact output format."
        )
    return user_input


def build_po_user_payload(concept: str, existing_vision: str, requirements: str) -> str:
    concept_section = concept or "(concept not provided)"
    vision_section = existing_vision.strip() if existing_vision else "(no existing vision)"
    return (
        f"CONCEPT:\n{concept_section}\n\n"
        f"EXISTING_VISION:\n{vision_section}\n\n"
        f"REQUIREMENTS:\n{requirements.strip()}\n\n"
        "Follow the exact output format."
    )


def build_qa_prompts(story_id: str) -> Dict[str, Any]:
    return {"story": story_id}
