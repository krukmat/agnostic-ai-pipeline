import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from graph_rag.engine import GraphRAGEngine
from graph_rag.ingestion import (
    PipelineIngestion,
    _ingest_artifacts_batch,
    _ingest_single_artifact,
    auto_ingest_hook,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_initialize_with_fake_lightrag(monkeypatch, tmp_path):
    class FakeQueryParam:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeEmbeddingFunc:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeLightRAG:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def initialize_storages(self):
            return None

        async def finalize_storages(self):
            return None

        async def ainsert(self, text):
            return None

        async def aquery(self, question, param):
            return f"ok:{question}:{param.mode}"

    fake_lightrag = SimpleNamespace(LightRAG=FakeLightRAG, QueryParam=FakeQueryParam)
    fake_ollama = SimpleNamespace(
        ollama_model_complete=lambda *a, **k: "ok",
        ollama_embed=SimpleNamespace(func=lambda *a, **k: [0.1, 0.2]),
    )
    fake_utils = SimpleNamespace(EmbeddingFunc=FakeEmbeddingFunc)

    monkeypatch.setitem(__import__("sys").modules, "lightrag", fake_lightrag)
    monkeypatch.setitem(__import__("sys").modules, "lightrag.llm.ollama", fake_ollama)
    monkeypatch.setitem(__import__("sys").modules, "lightrag.utils", fake_utils)

    engine = GraphRAGEngine({"working_dir": str(tmp_path), "cache_enabled": True})
    await engine.initialize()
    assert engine._initialized is True

    await engine.ingest("doc")
    resp = await engine.query("q", mode="mix", top_k=5)
    assert "ok:q:mix" in resp


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_get_instance_importerror_fallback(monkeypatch):
    GraphRAGEngine.clear_instance()

    async def _raise_import_error(self):
        raise ImportError("missing")

    monkeypatch.setattr(GraphRAGEngine, "initialize", _raise_import_error)
    inst = await GraphRAGEngine.get_instance({"working_dir": "/tmp/x"})
    assert isinstance(inst, GraphRAGEngine)
    GraphRAGEngine.clear_instance()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_finalize_and_index_persistence(monkeypatch, tmp_path):
    engine = GraphRAGEngine({"working_dir": str(tmp_path)})
    engine._initialized = True
    engine.rag = AsyncMock()
    engine._index_metadata = {"entities": 2}

    engine.save_indices()
    metadata_file = Path(tmp_path) / ".graph_rag_indices.json"
    assert metadata_file.exists()

    engine._index_metadata = {}
    engine.load_indices()
    assert engine._index_metadata.get("entities") == 2

    await engine.finalize()
    assert engine._initialized is False


@pytest.mark.unit
def test_ingestion_load_state_corrupt_json(tmp_path):
    state_file = tmp_path / PipelineIngestion.INGESTION_STATE_FILE
    state_file.write_text("{bad json")
    engine = MagicMock()
    engine.working_dir = tmp_path
    ingestion = PipelineIngestion(engine)
    assert ingestion.ingested_hashes == {}


@pytest.mark.unit
def test_ingestion_save_state_error(monkeypatch, tmp_path):
    engine = MagicMock()
    engine.working_dir = tmp_path
    ingestion = PipelineIngestion(engine)

    def _boom(*args, **kwargs):
        raise OSError("no write")

    monkeypatch.setattr("builtins.open", _boom)
    ingestion._save_ingested_hashes()  # should not raise


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingestion_process_single_file_error_path(tmp_path):
    engine = AsyncMock()
    engine.working_dir = tmp_path
    ingestion = PipelineIngestion(engine)
    sample = tmp_path / "a.md"
    sample.write_text("content")

    engine.ingest.side_effect = RuntimeError("ingest fail")
    stats = {"new_files": 0, "skipped_files": 0, "errors": 0}
    await ingestion._process_single_file(sample, "docs", stats)
    assert stats["errors"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingestion_ingest_directory_missing_path(tmp_path):
    engine = AsyncMock()
    engine.working_dir = tmp_path
    ingestion = PipelineIngestion(engine)
    stats = await ingestion._ingest_directory("does_not_exist/", "docs")
    assert stats == {"new_files": 0, "skipped_files": 0, "errors": 0}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auto_ingest_single_artifact_branches(tmp_path):
    ingestion = AsyncMock()
    md = {"role": "dev", "step": "x", "iteration": 1}

    assert await _ingest_single_artifact(123, ingestion, md) is False
    assert await _ingest_single_artifact(tmp_path / "missing.md", ingestion, md) is False

    f = tmp_path / "ok.md"
    f.write_text("hello")
    assert await _ingest_single_artifact(f, ingestion, md) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingest_artifacts_batch_counts_and_errors(tmp_path):
    ingestion = AsyncMock()
    artifacts = [tmp_path / "a.txt", tmp_path / "b.txt"]
    artifacts[0].write_text("ok")

    count = await _ingest_artifacts_batch(ingestion, artifacts, {"role": "qa"})
    assert count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_auto_ingest_hook_paths(monkeypatch):
    async def _fake_setup(cfg):
        return AsyncMock()

    async def _fake_batch(ingestion, artifacts, metadata):
        return 2

    # config load fails -> early return
    monkeypatch.setattr("graph_rag.ingestion.load_config", lambda: (_ for _ in ()).throw(RuntimeError("cfg")), raising=False)
    await auto_ingest_hook("dev", [], {})

    # disabled -> early return
    monkeypatch.setattr("graph_rag.ingestion.load_config", lambda: {"graph_rag": {"auto_ingest": False}}, raising=False)
    await auto_ingest_hook("dev", [], {})

    # enabled success path
    monkeypatch.setattr("graph_rag.ingestion.load_config", lambda: {"graph_rag": {"auto_ingest": True}}, raising=False)
    monkeypatch.setattr("graph_rag.ingestion._setup_ingestion", _fake_setup)
    monkeypatch.setattr("graph_rag.ingestion._ingest_artifacts_batch", _fake_batch)
    await auto_ingest_hook("dev", ["a", "b"], {"role": "dev"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingestion_ingest_all_and_convenience(monkeypatch, tmp_path):
    engine = AsyncMock()
    engine.working_dir = tmp_path
    ingestion = PipelineIngestion(engine)

    async def _fake_ingest_directory(path, content_type):
        return {"new_files": 1, "skipped_files": 2, "errors": 0}

    monkeypatch.setattr(ingestion, "_ingest_directory", _fake_ingest_directory)
    stats = await ingestion.ingest_all()
    assert set(stats.keys()) == {"planning", "code", "artifacts", "docs"}

    from graph_rag.ingestion import ingest_pipeline_artifacts

    stats2 = await ingest_pipeline_artifacts(engine, tmp_path)
    assert set(stats2.keys()) == {"planning", "code", "artifacts", "docs"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingestion_should_ingest_and_text_paths(monkeypatch, tmp_path):
    engine = AsyncMock()
    engine.working_dir = tmp_path
    ingestion = PipelineIngestion(engine)

    d = tmp_path / "dir"
    d.mkdir()
    assert ingestion._should_ingest_file(d) is False

    f = tmp_path / "x.md"
    f.write_text("abc")
    assert ingestion._should_ingest_file(f) is True

    import hashlib

    h = hashlib.md5("abc".encode()).hexdigest()
    ingestion.ingested_hashes[h] = str(f)
    assert ingestion._should_ingest_file(f) is False

    monkeypatch.setattr(Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert ingestion._should_ingest_file(f) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingestion_ingest_artifact_and_text_error_branches(tmp_path):
    engine = AsyncMock()
    engine.working_dir = tmp_path
    ingestion = PipelineIngestion(engine)

    await ingestion.ingest_artifact("artifact", {"role": "dev", "step": "impl", "iteration": 2})
    engine.ingest.assert_called()

    engine.ingest.side_effect = RuntimeError("fail")
    with pytest.raises(RuntimeError):
        await ingestion.ingest_artifact("artifact", {})
    with pytest.raises(RuntimeError):
        await ingestion.ingest_text("txt", "src", "docs")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_query_context_stream_error_branches(tmp_path):
    engine = GraphRAGEngine({"working_dir": str(tmp_path), "cache_enabled": True})
    engine._initialized = True

    class FakeRag:
        async def aquery(self, *args, **kwargs):
            return "response-12345"

        async def finalize_storages(self):
            return None

    engine.rag = FakeRag()

    q = await engine.query("q1", mode="mix", top_k=2)
    c = await engine.get_context_only("q2", mode="local", top_k=3)
    assert q.startswith("response")
    assert c.startswith("response")

    chunks = [x async for x in engine.stream_query("q3")]
    assert "".join(chunks).startswith("response")
    ctx_chunks = [x async for x in engine.stream_context_only("q4")]
    assert "".join(ctx_chunks).startswith("response")

    class BrokenRag:
        async def aquery(self, *args, **kwargs):
            raise RuntimeError("rag broken")

        async def finalize_storages(self):
            raise RuntimeError("finalize broken")

    engine.query_cache.clear()
    engine.rag = BrokenRag()
    with pytest.raises(RuntimeError):
        await engine.query("boom")
    with pytest.raises(RuntimeError):
        await engine.get_context_only("boom")
    with pytest.raises(RuntimeError):
        _ = [x async for x in engine.stream_query("boom")]
    with pytest.raises(RuntimeError):
        _ = [x async for x in engine.stream_context_only("boom")]

    # finalize should swallow finalize errors
    await engine.finalize()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_engine_multilingual_and_helpers(tmp_path):
    engine = GraphRAGEngine({
        "working_dir": str(tmp_path),
        "language_detection": True,
        "supported_languages": ["en", "es"],
        "default_language": "en",
    })

    # detector unsupported -> fallback
    engine._language_detector = SimpleNamespace(detect_language=lambda _: "fr")
    assert engine.detect_query_language("bonjour") == "en"

    # detector disabled path
    engine.language_detection = False
    assert engine.detect_query_language("hola") == "en"

    # delegate methods
    async def _fake_query(*args, **kwargs):
        return "Q"

    async def _fake_context(*args, **kwargs):
        return "C"

    engine.query = _fake_query
    engine.get_context_only = _fake_context
    engine.language_detection = True
    engine._language_detector = SimpleNamespace(detect_language=lambda _: "es")
    assert await engine.query_multilingual("hola") == "Q"
    assert await engine.get_context_multilingual("hola") == "C"
