"""
F1-T2: Unit tests for GraphRAGEngine singleton wrapper.

TDD Approach: Tests written FIRST, implementation validated after.
Focus: Core engine behavior, lazy initialization, singleton pattern.
No mocking - real LightRAG backend integration.

Related: PLAN_implementation_distilabel_finetuning_rag.md - F1-T2
"""

import pytest
import asyncio
import tempfile
from pathlib import Path

from graph_rag.engine import GraphRAGEngine


@pytest.fixture
def temp_rag_dir():
    """Temporary directory for test KG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config(temp_rag_dir):
    """Test configuration."""
    return {
        "working_dir": str(temp_rag_dir),
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "chunk_token_size": 1200,
        "top_k": 60,
    }


@pytest.mark.asyncio
async def test_engine_initialization(config):
    """Test lazy initialization of GraphRAGEngine."""
    engine = GraphRAGEngine(config)
    assert not engine._initialized

    await engine.initialize()
    assert engine._initialized
    assert engine.rag is not None

    await engine.finalize()


@pytest.mark.asyncio
async def test_document_ingestion(config):
    """Test document insertion into KG."""
    engine = GraphRAGEngine(config)
    await engine.initialize()

    doc = "S1: Database Setup - creates PostgreSQL schema"
    await engine.ingest(doc)
    # No error = success (LightRAG handles async ingestion)

    await engine.finalize()


@pytest.mark.skip(reason="Integration test - verified in setup_graph_rag.py")
@pytest.mark.asyncio
async def test_retrieval_context_only(config):
    """Test context-only retrieval (no LLM generation)."""
    engine = GraphRAGEngine(config)
    await engine.initialize()

    # Ingest sample
    doc = "S3: User Authentication - depends_on S1"
    await engine.ingest(doc)

    # Query for context
    context = await engine.get_context_only("What authenticates users?", mode="mix")
    assert context  # Non-empty
    assert isinstance(context, str)

    await engine.finalize()


@pytest.mark.skip(reason="Integration test - verified in setup_graph_rag.py")
@pytest.mark.asyncio
async def test_retrieval_modes(config):
    """Test different retrieval modes."""
    engine = GraphRAGEngine(config)
    await engine.initialize()

    doc = "AuthService implements JWT tokens"
    await engine.ingest(doc)

    modes = ["naive", "local", "global", "hybrid", "mix"]
    for mode in modes:
        context = await engine.get_context_only("JWT", mode=mode)
        assert context, f"Mode {mode} returned empty"

    await engine.finalize()


@pytest.mark.asyncio
async def test_singleton_pattern(config):
    """Test singleton pattern (single instance across app)."""
    engine1 = GraphRAGEngine.instance(config)
    engine2 = GraphRAGEngine.instance()

    # Same instance (by identity, not just equality)
    assert engine1 is engine2


@pytest.mark.asyncio
async def test_initialization_idempotent(config):
    """Test that initialize() can be called multiple times safely."""
    engine = GraphRAGEngine(config)

    await engine.initialize()
    await engine.initialize()  # Should not error
    assert engine._initialized

    await engine.finalize()
