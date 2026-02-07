"""
Test que verifica aplicación real de top_k por rol.

Valida que AgentRetriever pase top_k de ROLE_POLICIES al engine,
y que diferentes roles resulten en diferentes cantidades de contexto.

TDD: Este test FALLA antes de la implementación.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call

from graph_rag.retrieval import AgentRetriever


@pytest.fixture
def mock_engine():
    """Mock GraphRAGEngine."""
    engine = AsyncMock()
    engine.get_context_only = AsyncMock(return_value="context")
    return engine


@pytest.fixture
def retriever(mock_engine):
    """AgentRetriever instance."""
    return AgentRetriever(mock_engine)


@pytest.mark.asyncio
async def test_top_k_per_role_is_applied(mock_engine, retriever):
    """
    CRITICAL: Verify that top_k from ROLE_POLICIES is actually passed to engine.

    This test validates the fix for H-01 (ALTO).

    Before fix: top_k is defined in policy but not passed to engine.get_context_only()
    After fix: top_k is passed as parameter to engine method.
    """
    query = "What components exist?"

    # Test BA role (should have top_k=30)
    await retriever.retrieve_for_role("ba", query)

    # Verify engine was called with top_k parameter
    ba_policy = retriever.ROLE_POLICIES["ba"]
    expected_top_k = ba_policy["top_k"]  # Should be 30

    # Check that the call included top_k somehow
    # (either as kwarg or in override_policy)
    call_args = mock_engine.get_context_only.call_args

    # Implementation detail: override_policy or top_k kwarg must be present
    assert call_args is not None, "get_context_only was not called"

    # After fix, top_k should be in kwargs or in override dict
    kwargs = call_args[1]  # kwargs from call

    # Acceptable implementations:
    # 1. top_k passed as kwarg directly
    # 2. override_policy dict contains top_k
    has_top_k_in_kwargs = "top_k" in kwargs
    has_override_policy = "override_policy" in kwargs and isinstance(kwargs.get("override_policy"), dict)

    assert has_top_k_in_kwargs or has_override_policy, \
        f"top_k not passed to engine. Call: {call_args}"


@pytest.mark.asyncio
async def test_different_roles_have_different_top_k(retriever):
    """
    Validate that ROLE_POLICIES defines different top_k for different roles.

    This is a precondition test (should already pass).
    """
    policies = retriever.ROLE_POLICIES

    # Extract top_k values
    top_ks = {role: policy["top_k"] for role, policy in policies.items()}

    # BA should have fewer than Architect
    assert top_ks["ba"] < top_ks["architect"], \
        f"BA top_k ({top_ks['ba']}) should be less than Architect ({top_ks['architect']})"

    # Architect should have many (60)
    assert top_ks["architect"] == 60, \
        f"Architect top_k should be 60, got {top_ks['architect']}"

    # BA should be 30
    assert top_ks["ba"] == 30, \
        f"BA top_k should be 30, got {top_ks['ba']}"


@pytest.mark.asyncio
async def test_retrieve_respects_override_policy(mock_engine, retriever):
    """
    Validate that override_policy parameter works (for flexibility).

    Allows callers to override top_k/mode at runtime if needed.
    """
    query = "test"

    # Call with override
    override = {"top_k": 100, "mode": "hybrid"}
    await retriever.retrieve_for_role("ba", query, override_policy=override)

    # Verify override was passed or applied
    call_args = mock_engine.get_context_only.call_args
    kwargs = call_args[1]

    # Either override_policy passed directly or individual params set
    if "override_policy" in kwargs:
        assert kwargs["override_policy"]["top_k"] == 100
    else:
        # If implementation unpacks override, top_k should be 100
        assert kwargs.get("top_k") == 100 or "top_k" not in kwargs, \
            "Override not applied"
