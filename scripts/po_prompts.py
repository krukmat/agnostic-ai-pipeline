"""
Reusable prompt templates for the Product Owner role.
"""

from __future__ import annotations

from textwrap import dedent


PO_BASE_PROMPT = dedent(
    """
    You are the Product Owner agent. Using the provided concept and requirements, generate both YAML blocks exactly as specified.

    IMPORTANT:
    1. Always emit two fenced YAML blocks in this order (VISION first, REVIEW second) with no extra prose.
    2. Each block MUST be valid YAML. If information is missing, use [] or concise placeholders, but never omit a key.
    3. In `requirements_alignment`, every bullet must explicitly mention the requirement ID (FRxxx, NFRxxx, Cxxx, CONxxx, etc.).
    4. `recommended_actions` must include at least two concrete, action-oriented items (start with verbs).
    5. `narrative` must be a concise paragraph (≤120 words) summarizing alignment + gaps.
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
      - FR001 covers the collaborative planning workspace and reporting boards
      - FR002 maps to the dependency and risk indicators the vision requires
      gaps:
      - FR003 lacks telemetry acceptance criteria to confirm success metrics
      conflicts:
      - C001 proposes deep ERP integration, which contradicts the non-goal of replacing finance systems
    recommended_actions:
    - Add FR005 to capture access-control granularity (roles + audit logging)
    - Update FR003 with measurable latency/error budgets for risk indicators
    narrative: The scope matches the collaboration hub vision; only telemetry metrics and the ERP integration constraint require clarification before moving into implementation.
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
