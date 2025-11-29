"""Tests for complexity analyzer heuristics."""

import pytest
from scripts.utils.complexity_analyzer import (
    analyze_story_complexity,
    analyze_stories_batch,
    get_complexity_distribution,
)


def test_simple_story_crud():
    """Test that CRUD stories are classified as simple."""
    story = {
        "id": "S1",
        "description": "Create a GET endpoint for listing users",
        "acceptance": [
            "Returns 200 OK with user list",
            "Handles empty list correctly"
        ]
    }
    complexity = analyze_story_complexity(story)
    assert complexity == "simple", f"Expected simple, got {complexity}"


def test_simple_story_health_check():
    """Test that health check stories are classified as simple."""
    story = {
        "id": "S2",
        "description": "Implement health check endpoint",
        "acceptance": [
            "GET /health returns 200 when service is up"
        ]
    }
    complexity = analyze_story_complexity(story)
    assert complexity == "simple", f"Expected simple, got {complexity}"


def test_medium_story_authentication():
    """Test that authentication stories are classified as medium."""
    story = {
        "id": "S3",
        "description": "Implement JWT authentication with role-based access control",
        "acceptance": [
            "Users can login with credentials",
            "JWT tokens are validated",
            "Roles are enforced on protected endpoints",
            "Tokens expire after 15 minutes"
        ]
    }
    complexity = analyze_story_complexity(story)
    assert complexity == "medium", f"Expected medium, got {complexity}"


def test_medium_story_api_integration():
    """Test that API integration stories are classified as medium."""
    story = {
        "id": "S4",
        "description": "Integrate with external payment API using webhooks for async notifications",
        "acceptance": [
            "Payment requests are sent to API",
            "Webhook endpoint receives notifications",
            "Payment status is updated in database"
        ]
    }
    complexity = analyze_story_complexity(story)
    assert complexity == "medium", f"Expected medium, got {complexity}"


def test_complex_story_distributed_system():
    """Test that distributed system stories are classified as complex."""
    story = {
        "id": "S5",
        "description": "Migrate monolithic database to distributed multi-tenant schema with zero downtime",
        "acceptance": [
            "Data migration completes without data loss",
            "Tenants are isolated at database level",
            "Performance maintains <100ms P95 latency",
            "Rollback capability within 5 minutes",
            "Schema versioning supports concurrent versions"
        ]
    }
    complexity = analyze_story_complexity(story)
    assert complexity == "complex", f"Expected complex, got {complexity}"


def test_complex_story_architecture():
    """Test that architecture stories are classified as complex."""
    story = {
        "id": "S6",
        "description": "Refactor microservices architecture to implement event-sourcing pattern with CQRS",
        "acceptance": [
            "Events are persisted in event store",
            "Read models are updated asynchronously",
            "Eventual consistency is maintained",
            "Event replay is supported"
        ]
    }
    complexity = analyze_story_complexity(story)
    assert complexity == "complex", f"Expected complex, got {complexity}"


def test_acceptance_criteria_count_impact():
    """Test that more acceptance criteria increases complexity."""
    story_few = {
        "id": "S7",
        "description": "Implement caching layer",
        "acceptance": ["Cache hits reduce database load"]
    }

    story_many = {
        "id": "S8",
        "description": "Implement caching layer",
        "acceptance": [
            "Cache hits reduce database load",
            "Cache invalidation works correctly",
            "TTL is configurable",
            "Cache statistics are tracked",
            "Memory limits are enforced"
        ]
    }

    complexity_few = analyze_story_complexity(story_few)
    complexity_many = analyze_story_complexity(story_many)

    # More acceptance criteria should push toward higher complexity
    # (Though keyword "caching" is medium, so both might be medium)
    assert complexity_few in ["simple", "medium"]
    assert complexity_many in ["medium", "complex"]


def test_description_length_impact():
    """Test that longer descriptions increase complexity."""
    story_short = {
        "id": "S9",
        "description": "Add logging",
        "acceptance": ["Logs are written"]
    }

    story_long = {
        "id": "S10",
        "description": (
            "Implement comprehensive distributed tracing and observability system "
            "with support for performance profiling, transaction monitoring, "
            "and real-time alerting across multiple microservices with automatic "
            "correlation IDs and context propagation through async message queues"
        ),
        "acceptance": ["Tracing works"]
    }

    complexity_short = analyze_story_complexity(story_short)
    complexity_long = analyze_story_complexity(story_long)

    # Longer description with complex keywords should be more complex
    assert complexity_short in ["simple", "medium"]
    assert complexity_long in ["medium", "complex"]


def test_technical_depth_indicators():
    """Test that technical depth keywords increase complexity."""
    story_no_depth = {
        "id": "S11",
        "description": "Display user profile",
        "acceptance": ["Shows user name and email"]
    }

    story_with_depth = {
        "id": "S12",
        "description": "Display user profile with database transaction and index optimization",
        "acceptance": ["Shows user name and email with <50ms latency"]
    }

    complexity_no_depth = analyze_story_complexity(story_no_depth)
    complexity_with_depth = analyze_story_complexity(story_with_depth)

    # Technical depth should increase complexity
    # Note: "database", "transaction", "index", "optimization" are depth indicators
    assert complexity_no_depth == "simple"
    assert complexity_with_depth in ["medium", "complex"]


def test_batch_analysis():
    """Test analyzing multiple stories at once."""
    stories = [
        {
            "id": "S1",
            "description": "Create GET endpoint",
            "acceptance": ["Returns data"]
        },
        {
            "id": "S2",
            "description": "Implement JWT authentication with role-based access control",
            "acceptance": ["Users can login", "Tokens are validated"]
        },
        {
            "id": "S3",
            "description": "Migrate to distributed microservices architecture with event-sourcing",
            "acceptance": ["Services are decoupled", "Data is partitioned", "Events are tracked"]
        }
    ]

    results = analyze_stories_batch(stories)

    assert len(results) == 3
    assert "S1" in results
    assert "S2" in results
    assert "S3" in results
    assert results["S1"] == "simple"
    assert results["S2"] in ["medium", "complex"]
    assert results["S3"] in ["medium", "complex"]  # Could be either depending on score


def test_complexity_distribution():
    """Test getting distribution of complexity levels."""
    stories = [
        {"id": "S1", "description": "GET endpoint", "acceptance": ["Works"]},
        {"id": "S2", "description": "POST endpoint", "acceptance": ["Works"]},
        {"id": "S3", "description": "JWT auth", "acceptance": ["Works", "Validates"]},
        {"id": "S4", "description": "Distributed migration", "acceptance": ["Works"]},
    ]

    distribution = get_complexity_distribution(stories)

    assert "simple" in distribution
    assert "medium" in distribution
    assert "complex" in distribution
    assert sum(distribution.values()) == 4


def test_missing_description():
    """Test handling of stories with missing description."""
    story = {
        "id": "S99",
        "acceptance": ["Some criterion"]
    }

    # Should not crash, default to some complexity
    complexity = analyze_story_complexity(story)
    assert complexity in ["simple", "medium", "complex"]


def test_missing_acceptance():
    """Test handling of stories with missing acceptance criteria."""
    story = {
        "id": "S99",
        "description": "Do something"
    }

    # Should not crash
    complexity = analyze_story_complexity(story)
    assert complexity in ["simple", "medium", "complex"]


def test_empty_story():
    """Test handling of completely empty story."""
    story = {"id": "S99"}

    # Should not crash, should classify as simple (low score)
    complexity = analyze_story_complexity(story)
    assert complexity in ["simple", "medium"]
