from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dspy_baseline.metrics.product_owner_metrics import product_owner_metric


BLOG_REQUIREMENTS = dedent(
    """
    meta:
      original_request: Lightweight tech blog
    title: Tech Blog Lite
    description: A lightweight platform for publishing and moderating technology-focused posts.
    functional_requirements:
    - id: FR001
      description: Users can create posts with predefined categories.
      priority: High
    - id: FR002
      description: Users can edit and update their own posts.
      priority: High
    - id: FR003
      description: Visitors can comment on existing posts.
      priority: Medium
    non_functional_requirements:
    - id: NFR001
      description: Requests must complete in under 500ms.
      priority: High
    - id: NFR002
      description: Interface must comply with WCAG AA.
      priority: Medium
    constraints:
    - id: C001
      description: Deployment limited to EU-hosted infrastructure.
      priority: Medium
    - id: C002
      description: No third-party comment widgets allowed.
      priority: Low
    """
).strip()


BLOG_VISION = dedent(
    """
    product_name: Tech Blog Lite
    product_summary: Build a lightweight publication hub for technology articles where authors can draft, edit and publish posts while readers interact through moderated comments.
    target_users:
    - Independent tech writers
    - Developer advocates from small startups
    value_proposition:
    - Publish posts quickly without heavy CMS overhead.
    - Encourage thoughtful discussion with simple, moderated comments.
    key_capabilities:
    - Create, edit and delete posts with predefined categories.
    - Comment on existing posts with markdown support.
    non_goals:
    - Multimedia hosting for long-form video.
    - Deep analytics dashboards or SEO tooling.
    success_metrics:
    - Weekly number of published posts.
    - Ratio of comments to unique readers.
    last_updated: 2025-11-09 00:00:00+00:00
    """
).strip()


BLOG_REVIEW = dedent(
    """
    status: aligned
    summary:
    - The requirements cover CRUD for posts, categories and moderated comments.
    - Non-goals in the vision match the constraints listed by the BA.
    requirements_alignment:
      aligned:
      - FR001 (Users can create posts with categories)
      - FR002 (Users can edit their existing posts)
      - FR003 (System supports deletion and comment threads)
      gaps:
      - Accessibility requirement NFR002 should be referenced in the KPIs.
      conflicts:
      - None identified
    recommended_actions:
    - Prioritize NFR001 and NFR002 in the next iteration.
    - Maintain the stated non-goals to avoid CMS scope creep.
    narrative: The BA deliverable and product vision match closely, covering editorial workflows and moderation. No blocking issues detected beyond reiterating accessibility acceptance tests.
    """
).strip()


INVENTORY_REQUIREMENTS = dedent(
    """
    meta:
      original_request: Inventory management API
    title: InventorySync API
    description: REST API to manage inventory items, categories and stock levels for e-commerce operators.
    functional_requirements:
    - id: FR101
      description: Provide CRUD endpoints for inventory items with stock levels.
      priority: High
    - id: FR102
      description: Support categorization and filtering of items.
      priority: High
    - id: FR103
      description: Allow retrieval of audit history per item.
      priority: Medium
    non_functional_requirements:
    - id: NFR101
      description: Enforce authentication via JWT.
      priority: High
    - id: NFR102
      description: Average response time below 300ms under peak load.
      priority: Medium
    constraints:
    - id: C101
      description: Deploy on existing Kubernetes cluster with PostgreSQL.
      priority: Medium
    """
).strip()


INVENTORY_VISION = dedent(
    """
    product_name: Inventory API
    product_summary: A RESTful API service designed to manage inventory data for e-commerce platforms, enabling secure CRUD operations and seamless integration with backend systems.
    target_users:
    - Backend developers working on e-commerce applications.
    - Integration engineers who sync inventory with marketplaces.
    value_proposition:
    - Offer a streamlined way to handle inventory without custom databases.
    - Ensure consistent REST practices so downstream tooling remains predictable.
    key_capabilities:
    - Full CRUD functionality for inventory items including stock adjustments.
    - Support for categorizing inventory into predefined groups to improve filtering.
    non_goals:
    - Automated content generation or publishing workflows.
    - External payment or analytics integrations.
    success_metrics:
    - Weekly number of successful CRUD transactions.
    - Average API latency under 300 milliseconds.
    last_updated: 2025-11-09 00:00:00+00:00
    """
).strip()


INVENTORY_REVIEW = dedent(
    """
    status: aligned
    summary:
    - The requirements document directly supports the product vision with CRUD, category management and strict REST conventions.
    requirements_alignment:
      aligned:
      - Manage inventory items through authenticated endpoints.
      - Enforce predictable REST conventions for create, update, delete and retrieve operations.
      gaps:
      - No explicit mention of real-time stock updates or multi-tenant isolation.
      conflicts:
      - None identified; requirements complement the vision.
    recommended_actions:
    - Consider real-time syncing and tenant separation safeguards before production rollout.
    narrative: The requirements align with the inventory API goals and highlight the next logical enhancements (real-time stock sync, tenant isolation). No blocking conflicts.
    """
).strip()


def _example(requirements: str) -> SimpleNamespace:
    return SimpleNamespace(requirements=requirements)


def _prediction(vision: str, review: str) -> SimpleNamespace:
    return SimpleNamespace(vision_yaml=vision, review_yaml=review)


def test_product_owner_metric_high_score_for_complete_blog_example() -> None:
    example = _example(BLOG_REQUIREMENTS)
    prediction = _prediction(BLOG_VISION, BLOG_REVIEW)
    score = product_owner_metric(example, prediction)
    assert score > 0.85


def test_product_owner_metric_handles_semantic_alignment_without_ids() -> None:
    example = _example(INVENTORY_REQUIREMENTS)
    prediction = _prediction(INVENTORY_VISION, INVENTORY_REVIEW)
    score = product_owner_metric(example, prediction)
    assert score > 0.7


def test_product_owner_metric_penalizes_incomplete_outputs() -> None:
    bad_vision = "product_name: Foo"
    bad_review = "status: aligned"
    example = _example(BLOG_REQUIREMENTS)
    prediction = _prediction(bad_vision, bad_review)
    score = product_owner_metric(example, prediction)
    assert score < 0.3
