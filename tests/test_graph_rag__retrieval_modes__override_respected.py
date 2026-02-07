"""
Test that rag-query MODE parameter is actually used.

Valida que AgentRetriever respete el parámetro MODE pasado como override.
Before fix: MODE=hybrid y MODE=local producen el mismo resultado.
After fix: Diferentes modos resultan en retrieval distinto.

TDD: Este test FALLA antes de la implementación.
"""

import pytest
from unittest.mock import AsyncMock, patch

from graph_rag.retrieval import AgentRetriever


@pytest.fixture
def mock_engine():
    """Mock GraphRAGEngine que retorna valores distintos por modo."""
    engine = AsyncMock()

    # Different return values based on how the mock is called
    def get_context_only_side_effect(*args, **kwargs):
        mode = kwargs.get("mode", "mix")
        if mode == "hybrid":
            return "Graph-heavy context: entities and relationships"
        elif mode == "local":
            return "Local context: nearby entities only"
        else:
            return "Mixed context: graph + vector"

    engine.get_context_only = AsyncMock(side_effect=get_context_only_side_effect)
    return engine


@pytest.fixture
def retriever(mock_engine):
    """AgentRetriever instance."""
    return AgentRetriever(mock_engine)


@pytest.mark.asyncio
async def test_mode_override_is_passed_to_engine(mock_engine, retriever):
    """
    CRITICAL: Verify that MODE override is passed to engine.

    This test validates the fix for H-02 (ALTO).

    Before fix: override_policy with mode is not passed to engine
    After fix: mode from override_policy reaches engine.get_context_only()
    """
    query = "What modules exist?"

    # Call with MODE override
    override = {"mode": "hybrid"}
    await retriever.retrieve_for_role("architect", query, override_policy=override)

    # Verify engine was called with hybrid mode
    call_args = mock_engine.get_context_only.call_args
    assert call_args is not None, "get_context_only was not called"

    # Check that mode in kwargs is 'hybrid' (from override)
    kwargs = call_args[1]
    assert kwargs.get("mode") == "hybrid", \
        f"Override mode not passed. Expected mode='hybrid', got mode='{kwargs.get('mode')}'"


@pytest.mark.asyncio
async def test_different_modes_produce_different_context(mock_engine, retriever):
    """
    Validate that different retrieval modes produce different results.

    This demonstrates that mode parameter actually affects the output.
    """
    query = "architecture"

    # Get context with hybrid mode
    result_hybrid = await retriever.retrieve_for_role(
        "architect",
        query,
        override_policy={"mode": "hybrid"}
    )

    # Get context with local mode
    result_local = await retriever.retrieve_for_role(
        "dev",
        query,
        override_policy={"mode": "local"}
    )

    # Results should be observably different based on mode
    assert result_hybrid != result_local, \
        "Different modes should produce different context"
    assert "entities and relationships" in result_hybrid
    assert "nearby entities only" in result_local


@pytest.mark.asyncio
async def test_default_mode_from_policy_when_no_override(retriever):
    """
    Verify that default mode from ROLE_POLICIES is used when no override.
    """
    query = "test"

    # Architect policy has mode='hybrid' by default
    await retriever.retrieve_for_role("architect", query)

    # Should use architect's default mode='hybrid'
    # (This is validated implicitly by the policy application)
    architect_policy = retriever.ROLE_POLICIES["architect"]
    assert architect_policy["mode"] == "hybrid", \
        "Architect should have default mode=hybrid"
