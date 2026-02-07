"""
AP-2-T1: Integration tests for AgentRetriever without mocking engine.

Tests retrieval with real policy application (not mocked).
Validates that role-specific policies actually affect engine calls.

Before: Mocked engine, couldn't verify actual policy→engine flow
After: Local engine mock that tracks policy parameters passed to it
"""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock

from graph_rag.retrieval import AgentRetriever


class LocalEngineForIntegration:
    """
    Local engine mock that tracks actual calls for integration testing.

    Unlike AsyncMock, this allows us to verify that policies are actually
    applied and passed to the engine, not just that the method is called.
    """

    def __init__(self):
        self.calls = []  # Track all calls with their parameters
        self.working_dir = Path(tempfile.gettempdir())

    async def get_context_only(self, question: str, mode: str, top_k: int):
        """Track parameters and return synthetic context."""
        self.calls.append({
            "method": "get_context_only",
            "question": question,
            "mode": mode,
            "top_k": top_k,
        })
        return f"Context for query '{question}' with mode={mode}, top_k={top_k}"

    async def query(self, question: str, mode: str, top_k: int):
        """Track parameters and return synthetic response."""
        self.calls.append({
            "method": "query",
            "question": question,
            "mode": mode,
            "top_k": top_k,
        })
        return f"Response for query '{question}' with mode={mode}, top_k={top_k}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_architect_policy_actually_applied():
    """
    AP-2-T1: Verify that architect role's policy (hybrid mode, top_k=60) is actually passed to engine.

    This validates the contract: policy defined → policy passed → engine receives it.
    """
    engine = LocalEngineForIntegration()
    retriever = AgentRetriever(engine)

    # Query as architect
    result = await retriever.retrieve_for_role("architect", "What is our design?")

    # Verify engine was called
    assert len(engine.calls) == 1, "Should make exactly one engine call"
    call = engine.calls[0]

    # Verify policy parameters were passed
    assert call["method"] == "get_context_only", "Architect uses get_context_only"
    assert call["mode"] == "hybrid", "Architect policy specifies hybrid mode"
    assert call["top_k"] == 60, "Architect policy specifies top_k=60"
    assert "What is our design?" in call["question"], "Query should be passed through"

    # Verify result includes the parameters
    assert "mode=hybrid" in result, "Result should reflect the mode used"
    assert "top_k=60" in result, "Result should reflect the top_k used"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_different_roles_use_different_modes():
    """
    AP-2-T1: Verify that different roles use their configured modes.

    Architect: hybrid, Dev: local, BA/PO/QA: mix
    """
    engine = LocalEngineForIntegration()
    retriever = AgentRetriever(engine)

    role_configs = {
        "architect": ("hybrid", 60),
        "dev": ("local", 40),
        "ba": ("mix", 30),
        "qa": ("mix", 50),
    }

    for role, (expected_mode, expected_top_k) in role_configs.items():
        # Clear previous calls
        engine.calls = []

        # Query as this role
        await retriever.retrieve_for_role(role, f"Question for {role}")

        # Verify policy was applied
        assert len(engine.calls) == 1
        call = engine.calls[0]
        assert call["mode"] == expected_mode, \
            f"{role} should use {expected_mode}, got {call['mode']}"
        assert call["top_k"] == expected_top_k, \
            f"{role} should use top_k={expected_top_k}, got {call['top_k']}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_override_policy_replaces_role_policy():
    """
    AP-2-T1: Verify that override_policy actually overrides role policy.

    Test that passing override_policy={'mode': 'local'} changes the mode
    from architect's default 'hybrid' to 'local'.
    """
    engine = LocalEngineForIntegration()
    retriever = AgentRetriever(engine)

    # Architect normally uses hybrid
    override = {"mode": "local"}
    result = await retriever.retrieve_for_role(
        "architect",
        "Design question",
        override_policy=override
    )

    # Verify override was applied
    call = engine.calls[0]
    assert call["mode"] == "local", "Override should change mode to local"
    assert call["top_k"] == 60, "top_k should remain from base policy (not overridden)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_top_k_parameter_actually_affects_retrieval():
    """
    AP-2-T1: Verify that top_k parameter from policy is actually passed to engine.

    This is critical for role-based personalization: different roles need different
    numbers of results.
    """
    engine = LocalEngineForIntegration()
    retriever = AgentRetriever(engine)

    # BA uses top_k=30
    await retriever.retrieve_for_role("ba", "BA question")
    ba_call = engine.calls[0]
    assert ba_call["top_k"] == 30

    # Architect uses top_k=60
    engine.calls = []
    await retriever.retrieve_for_role("architect", "Architect question")
    arch_call = engine.calls[0]
    assert arch_call["top_k"] == 60

    # QA uses top_k=50
    engine.calls = []
    await retriever.retrieve_for_role("qa", "QA question")
    qa_call = engine.calls[0]
    assert qa_call["top_k"] == 50

    # Verify they're different
    assert ba_call["top_k"] != arch_call["top_k"], \
        "Different roles should get different top_k values"
    assert arch_call["top_k"] != qa_call["top_k"], \
        "Different roles should get different top_k values"
