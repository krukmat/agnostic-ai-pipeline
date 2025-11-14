"""
Reusable prompt templates for the Product Owner role.
"""

from __future__ import annotations

from textwrap import dedent


PO_BASE_PROMPT = dedent(
    """
    You are the Product Owner agent. Using the provided concept and requirements, generate both YAML blocks exactly as specified.

    IMPORTANT:
    1. Always emit two fenced YAML blocks in this order:
       ```yaml VISION
       ...
       ```
       ```yaml REVIEW
       ...
       ```
    2. If information is missing, use empty lists [] or concise placeholders, but never omit a block.
    3. The REVIEW block must include: status, summary (list), requirements_alignment (aligned/gaps/conflicts lists), recommended_actions (list), and narrative (string).
    4. Do not add any explanation outside of the two fenced YAML blocks.
    """
).strip()


PO_SAMPLE_OUTPUT = dedent(
    """
    ```yaml VISION
    product_name: Sample Collaboration Hub
    product_summary: A lightweight workspace that lets distributed teams plan releases,
      share updates, and monitor delivery health from a single dashboard.
    target_users:
    - Delivery managers coordinating cross-team initiatives
    - Product owners who need rapid visibility into scope changes
    value_proposition:
    - Consolidates planning signals into one hub to reduce status churn
    - Surfaces risks early through automated dependency tracking
    key_capabilities:
    - Sprint and release timeline views with colored risk indicators
    - Lightweight requirement editor with YAML export
    - Activity stream that highlights recent scope or priority changes
    non_goals:
    - Full-featured issue tracking or code review workflows
    - Deep financial forecasting functionality
    success_metrics:
    - Reduce time spent compiling status updates by 40% within two months
    - Increase on-time release delivery by 15% per quarter
    last_updated: 2025-01-01
    ```
    ```yaml REVIEW
    status: aligned
    summary:
    - Requirements reinforce the vision's focus on lightweight planning and visibility
    - No conflicts detected between requested features and stated non-goals
    requirements_alignment:
      aligned:
      - FR-001 covers the collaborative planning workspace
      - FR-002 maps to the dependency and risk indicators
      gaps:
      - Missing explicit success metrics or telemetry requirements
      conflicts: []
    recommended_actions:
    - Add acceptance criteria for risk indicator latency and accuracy
    - Capture a non-functional requirement for access control
    narrative: The scope is coherent with the collaboration hub vision; only minor telemetry and access control clarifications are required before implementation.
    ```
    """
).strip()


def build_po_prompt(concept: str, requirements: str, include_example: bool = False) -> str:
    """Return the full prompt for the Product Owner model."""
    concept_block = concept.strip() or "(concept missing)"
    requirements_block = requirements.strip() or "(requirements missing)"

    prompt = [PO_BASE_PROMPT]
    if include_example:
        prompt.append("EXAMPLE OUTPUT:\n" + PO_SAMPLE_OUTPUT)

    prompt.append(
        f"CONCEPT:\n{concept_block}\n\n"
        f"REQUIREMENTS:\n{requirements_block}\n\n"
        "Respond only with the two fenced YAML blocks shown above."
    )
    return "\n\n".join(prompt)
