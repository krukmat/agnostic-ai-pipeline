"""Tests de integración real para AgentRetriever."""

from __future__ import annotations

import pytest

from graph_rag.engine import GraphRAGEngine
from graph_rag.ingestion import PipelineIngestion
from graph_rag.retrieval import AgentRetriever
from tests.utils.real_env import is_real_rag_env_ready


READY, REASON = is_real_rag_env_ready()
pytestmark = [
    pytest.mark.integration,
    pytest.mark.integration_real,
    pytest.mark.skipif(not READY, reason=REASON),
]


def _cfg(tmp_path):
    return {
        "working_dir": str(tmp_path / "graph_rag_retrieval_real"),
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "top_k": 30,
    }


@pytest.fixture
async def real_engine(tmp_path):
    engine = GraphRAGEngine(_cfg(tmp_path))
    await engine.initialize()
    ingestion = PipelineIngestion(engine)
    await ingestion.ingest_text(
        "S1: login JWT. S2 depends on S1. Architect focuses on dependencies.",
        source="seed",
        content_type="planning",
    )
    yield engine
    await engine.finalize()


@pytest.mark.asyncio
async def test_real_role_policies_apply(real_engine):
    retriever = AgentRetriever(real_engine)

    arch = await retriever.retrieve_for_role("architect", "Explain dependencies")
    dev = await retriever.retrieve_for_role("dev", "Explain dependencies")

    assert arch
    assert dev
    assert retriever.ROLE_POLICIES["architect"]["mode"] == "hybrid"
    assert retriever.ROLE_POLICIES["dev"]["mode"] == "local"
    assert retriever.ROLE_POLICIES["architect"]["top_k"] > retriever.ROLE_POLICIES["dev"]["top_k"]


@pytest.mark.asyncio
async def test_real_batch_retrieve_parallel_and_sequential(real_engine):
    retriever = AgentRetriever(real_engine)
    queries = ["What is S1?", "What depends on S1?"]

    parallel_res = await retriever.batch_retrieve("architect", queries, parallel=True)
    seq_res = await retriever.batch_retrieve("architect", queries, parallel=False)

    assert len(parallel_res) == 2
    assert len(seq_res) == 2
    assert all(r for r in parallel_res)
    assert all(r for r in seq_res)
