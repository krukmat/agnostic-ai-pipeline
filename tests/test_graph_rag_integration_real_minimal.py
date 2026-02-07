"""Suite mínima de integración real para GraphRAGEngine."""

from __future__ import annotations

import time

import pytest

from graph_rag.engine import GraphRAGEngine
from tests.utils.real_env import is_real_rag_env_ready


READY, REASON = is_real_rag_env_ready()
pytestmark = [
    pytest.mark.integration,
    pytest.mark.integration_real,
    pytest.mark.skipif(not READY, reason=REASON),
]


def _cfg(tmp_path):
    return {
        "working_dir": str(tmp_path / "graph_rag_real"),
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "top_k": 20,
        "cache_enabled": True,
        "cache_ttl": 3600,
    }


@pytest.mark.asyncio
async def test_real_initialize_finalize(tmp_path):
    engine = GraphRAGEngine(_cfg(tmp_path))
    await engine.initialize()
    assert engine._initialized is True
    await engine.finalize()


@pytest.mark.asyncio
async def test_real_ingest_query_verify_cycle(tmp_path):
    engine = GraphRAGEngine(_cfg(tmp_path))
    await engine.initialize()
    try:
        await engine.ingest(
            "[Source: req] [Type: planning]\n\n"
            "S1: User login with JWT token and role-based access."
        )
        context = await engine.get_context_only("How is JWT login implemented?", mode="mix", top_k=10)
        assert context
        assert any(k in context.lower() for k in ["jwt", "login", "token", "user"])
    finally:
        await engine.finalize()


@pytest.mark.asyncio
async def test_real_query_cache_second_hit_is_faster(tmp_path):
    engine = GraphRAGEngine(_cfg(tmp_path))
    await engine.initialize()
    try:
        await engine.ingest("[Source: x] [Type: docs]\n\nArchitecture uses service layer and database.")

        q = "What architecture is used?"
        t1 = time.perf_counter()
        r1 = await engine.query(q, mode="mix", top_k=10)
        dt1 = time.perf_counter() - t1

        t2 = time.perf_counter()
        r2 = await engine.query(q, mode="mix", top_k=10)
        dt2 = time.perf_counter() - t2

        assert r1 and r2
        assert r1 == r2
        # Umbral suave para evitar flakes en distintas máquinas
        assert dt2 <= dt1
    finally:
        await engine.finalize()


@pytest.mark.asyncio
async def test_real_stream_query_smoke(tmp_path):
    engine = GraphRAGEngine(_cfg(tmp_path))
    await engine.initialize()
    try:
        await engine.ingest("[Source: y] [Type: docs]\n\nSystem has auth, api and db modules.")
        chunks = [c async for c in engine.stream_query("Describe system modules", mode="mix", top_k=10)]
        assert chunks
        assert len("".join(chunks)) > 0
    finally:
        await engine.finalize()
