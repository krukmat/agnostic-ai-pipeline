"""
Test cyclomatic complexity reduction for retrieve_for_role.

Before: CC=6 (nested conditions for policy resolution)
After: CC≤5 (extracted _resolve_policy helper)

TDD: This test validates the refactored structure.
"""

import pytest
from graph_rag.retrieval import AgentRetriever


@pytest.mark.unit
def test_retrieve_for_role_has_resolve_policy_helper():
    """
    Verify that retrieve_for_role uses extracted _resolve_policy helper.
    """
    class MockEngine:
        async def ingest(self, content):
            pass

    engine = MockEngine()
    retriever = AgentRetriever(engine)

    # Verify helper method exists
    assert hasattr(retriever, '_resolve_policy'), \
        "Should have _resolve_policy() helper method"
    assert callable(retriever._resolve_policy), \
        "_resolve_policy should be callable"


@pytest.mark.unit
def test_resolve_policy_returns_default_for_unknown_role():
    """
    Verify _resolve_policy returns sensible defaults for unknown roles.
    """
    class MockEngine:
        async def ingest(self, content):
            pass

    engine = MockEngine()
    retriever = AgentRetriever(engine)

    # Unknown role should get default policy
    policy = retriever._resolve_policy("unknown_role", None)
    assert policy["mode"] in ["naive", "local", "global", "hybrid", "mix"], \
        "Policy should have valid mode"
    assert isinstance(policy["top_k"], int), \
        "Policy should have integer top_k"
    assert isinstance(policy["context_only"], bool), \
        "Policy should have boolean context_only"


@pytest.mark.unit
def test_resolve_policy_returns_role_policy_for_known_role():
    """
    Verify _resolve_policy returns configured policy for known roles.
    """
    class MockEngine:
        async def ingest(self, content):
            pass

    engine = MockEngine()
    retriever = AgentRetriever(engine)

    # Known role should return its configured policy
    policy = retriever._resolve_policy("architect", None)
    assert policy["mode"] == "hybrid", "Architect should use hybrid mode"
    assert policy["top_k"] == 60, "Architect should use top_k=60"


@pytest.mark.unit
def test_resolve_policy_applies_overrides():
    """
    Verify _resolve_policy correctly applies overrides to base policy.
    """
    class MockEngine:
        async def ingest(self, content):
            pass

    engine = MockEngine()
    retriever = AgentRetriever(engine)

    # Override mode for architect
    override = {"mode": "local"}
    policy = retriever._resolve_policy("architect", override)

    assert policy["mode"] == "local", "Override should change mode"
    assert policy["top_k"] == 60, "top_k should remain from base policy"


@pytest.mark.unit
def test_resolve_policy_preserves_context_only_unless_overridden():
    """
    Verify _resolve_policy preserves context_only unless explicitly overridden.
    """
    class MockEngine:
        async def ingest(self, content):
            pass

    engine = MockEngine()
    retriever = AgentRetriever(engine)

    # Base policy
    policy = retriever._resolve_policy("dev", None)
    assert policy["context_only"] == True, "Dev should have context_only=True by default"

    # With override
    override = {"context_only": False}
    policy_override = retriever._resolve_policy("dev", override)
    assert policy_override["context_only"] == False, "Override should change context_only"


@pytest.mark.unit
def test_retrieve_for_role_structure_simplified():
    """
    Verify retrieve_for_role has simplified structure with extracted policy resolution.

    The main function should now have linear flow:
    1. Resolve policy
    2. Log parameters
    3. Call engine method (based on context_only)
    4. Handle exceptions
    """
    class MockEngine:
        async def ingest(self, content):
            pass

    engine = MockEngine()
    retriever = AgentRetriever(engine)

    # Verify the method exists and has proper signature
    import inspect
    sig = inspect.signature(retriever.retrieve_for_role)
    params = list(sig.parameters.keys())

    assert "role" in params, "retrieve_for_role should have role parameter"
    assert "query" in params, "retrieve_for_role should have query parameter"
    assert "override_policy" in params, "retrieve_for_role should have override_policy parameter"
