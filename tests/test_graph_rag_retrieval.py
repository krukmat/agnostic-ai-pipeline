"""
F1-T4: Unit tests for AgentRetriever (role-based policies).

Focus: Policy routing, context_only flag, role-specific behavior.
No mocking for policy logic - verify actual policy dict structure.
"""

import pytest
from unittest.mock import AsyncMock

from graph_rag.retrieval import AgentRetriever


@pytest.fixture
def mock_engine():
    """Mock GraphRAGEngine."""
    engine = AsyncMock()
    engine.get_context_only = AsyncMock(return_value="context")
    engine.query = AsyncMock(return_value="response")
    return engine


@pytest.fixture
def retriever(mock_engine):
    """AgentRetriever instance."""
    return AgentRetriever(mock_engine)


def test_role_policies_exist(retriever):
    """Test all roles have defined policies."""
    expected_roles = ["ba", "product_owner", "architect", "dev", "qa"]
    for role in expected_roles:
        assert role in retriever.ROLE_POLICIES


def test_policy_has_required_fields(retriever):
    """Test policy dict structure (mode, top_k, context_only)."""
    for role, policy in retriever.ROLE_POLICIES.items():
        assert "mode" in policy, f"{role} missing 'mode'"
        assert "top_k" in policy, f"{role} missing 'top_k'"
        assert "context_only" in policy, f"{role} missing 'context_only'"
        assert policy["mode"] in ["naive", "local", "global", "hybrid", "mix"]
        assert isinstance(policy["top_k"], int)
        assert isinstance(policy["context_only"], bool)


@pytest.mark.asyncio
async def test_retrieve_calls_context_only_when_configured(mock_engine, retriever):
    """Test that context_only flag routes to get_context_only()."""
    # BA has context_only=True
    await retriever.retrieve_for_role("ba", "requirements exist?")

    # Should call get_context_only, not query
    assert mock_engine.get_context_only.called
    assert not mock_engine.query.called


@pytest.mark.asyncio
async def test_retrieve_respects_role_mode(mock_engine, retriever):
    """Test that each role's mode is passed to engine."""
    await retriever.retrieve_for_role("architect", "design decision?")

    # Architect should use hybrid mode
    args, kwargs = mock_engine.get_context_only.call_args
    assert kwargs.get("mode") == "hybrid" or args[-1] == "hybrid"


def test_explain_modes(retriever):
    """Test retrieval mode explanations."""
    modes = retriever.explain_modes()
    expected = ["naive", "local", "global", "hybrid", "mix"]
    for mode in expected:
        assert mode in modes
        assert len(modes[mode]) > 0  # Has description


@pytest.mark.asyncio
async def test_unknown_role_fallback(mock_engine, retriever):
    """Test unknown role falls back to default policy."""
    await retriever.retrieve_for_role("unknown_role", "something?")

    # Should not error, should use default
    assert mock_engine.get_context_only.called
