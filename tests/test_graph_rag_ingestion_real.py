"""Tests de integración real para PipelineIngestion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from graph_rag.engine import GraphRAGEngine
from graph_rag.ingestion import PipelineIngestion
from tests.utils.real_env import is_real_rag_env_ready


READY, REASON = is_real_rag_env_ready()
pytestmark = [
    pytest.mark.integration,
    pytest.mark.integration_real,
    pytest.mark.skipif(not READY, reason=REASON),
]


def _cfg(tmp_path):
    return {
        "working_dir": str(tmp_path / "graph_rag_ingestion_real"),
        "llm_model": "qwen2.5:7b-instruct",
        "embedding_model": "bge-m3",
        "embedding_dim": 1024,
        "top_k": 20,
    }


@pytest.fixture
def project_tree(tmp_path):
    (tmp_path / "planning").mkdir()
    (tmp_path / "project").mkdir()
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "docs").mkdir()

    (tmp_path / "planning" / "requirements.yaml").write_text("vision: auth service\n")
    (tmp_path / "project" / "auth.py").write_text("class Auth: pass\n")
    (tmp_path / "artifacts" / "qa_report.json").write_text('{"ok": true}\n')
    (tmp_path / "docs" / "ARCH.md").write_text("Architecture doc\n")
    return tmp_path


@pytest.mark.asyncio
async def test_real_ingest_all_creates_state_and_stats(project_tree, monkeypatch):
    monkeypatch.chdir(project_tree)
    engine = GraphRAGEngine(_cfg(project_tree))
    await engine.initialize()
    try:
        ingestion = PipelineIngestion(engine)
        stats = await ingestion.ingest_all()
        assert set(stats.keys()) == {"planning", "code", "artifacts", "docs"}

        state_file = Path(engine.working_dir) / PipelineIngestion.INGESTION_STATE_FILE
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert len(state) >= 3
    finally:
        await engine.finalize()


@pytest.mark.asyncio
async def test_real_second_ingest_has_more_skips_than_new(project_tree, monkeypatch):
    monkeypatch.chdir(project_tree)
    engine = GraphRAGEngine(_cfg(project_tree))
    await engine.initialize()
    try:
        ingestion = PipelineIngestion(engine)
        first = await ingestion.ingest_all()
        second = await ingestion.ingest_all()

        first_new = sum(v["new_files"] for v in first.values())
        second_new = sum(v["new_files"] for v in second.values())
        second_skipped = sum(v["skipped_files"] for v in second.values())

        assert first_new > 0
        assert second_new == 0
        assert second_skipped > 0
    finally:
        await engine.finalize()
