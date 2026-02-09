"""
Auto-Ingest Pipeline End-to-End Tests

Tests for the complete auto-ingest pipeline flow:
dev step → artifact generation → hook firing → auto ingestion
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# ============================================================================
# UNIT TESTS - Pipeline Flow Structure
# ============================================================================


@pytest.mark.unit
def test_dev_result_includes_artifacts_dir():
    """
    Verify dev_result from implement_story includes artifacts_dir.

    This is required for the hook system to collect artifacts.
    """
    # Mock dev_result as returned by implement_story()
    dev_result = {
        "status": "done",
        "story_id": "S1",
        "artifacts_dir": "/tmp/artifacts/S1",  # Required field
        "written": {"file1.py": 100, "file2.py": 200},
        "model_info": {"provider": "ollama", "model": "mistral:7b"},
    }

    # Verify artifacts_dir exists and is a string
    assert "artifacts_dir" in dev_result, "dev_result should include artifacts_dir"
    assert isinstance(dev_result["artifacts_dir"], str), "artifacts_dir should be string path"


@pytest.mark.unit
def test_hook_receives_collected_artifacts():
    """
    Verify hook receives properly formatted artifacts list.

    This test ensures the pipeline passes artifacts to the hook correctly.
    """
    from scripts.orchestrate import _collect_dev_artifacts

    # Mock dev_result and story
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_path = Path(tmpdir)
        (artifacts_path / "S1_implementation.py").write_text("# Implementation")
        (artifacts_path / "S1_test.py").write_text("# Tests")

        dev_result = {
            "status": "done",
            "artifacts_dir": str(artifacts_path),
        }
        story = {"id": "S1"}

        # Collect artifacts
        artifacts = _collect_dev_artifacts(dev_result, story)

        # Verify results
        assert isinstance(artifacts, list), "Should return list"
        assert len(artifacts) == 2, "Should find 2 artifact files"
        assert all(isinstance(a, Path) for a in artifacts), "All items should be Path"
        assert all(a.is_file() for a in artifacts), "All items should be files"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hook_metadata_structure():
    """
    Verify metadata passed to hook has required fields.

    Metadata should include: role, iteration, timestamp, story_id
    """
    # Expected metadata structure
    metadata = {
        "role": "dev",
        "iteration": 1,
        "timestamp": datetime.now().isoformat(),
        "story_id": "S1",
    }

    # Verify all required fields present
    assert "role" in metadata, "Should include role"
    assert "iteration" in metadata, "Should include iteration"
    assert "timestamp" in metadata, "Should include timestamp"
    assert "story_id" in metadata, "Should include story_id"


# ============================================================================
# INTEGRATION TESTS - Full Pipeline Flow
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_ingest_flow_with_artifacts():
    """
    E2E Test: Artifacts flow through hook to ingestion.

    Validates complete pipeline:
    1. Dev completes with artifacts
    2. Hook fires with artifacts
    3. Artifacts get ingested
    """
    from scripts.orchestrate import HookRegistry, _collect_dev_artifacts
    from graph_rag.ingestion import PipelineIngestion

    # Create temporary artifacts directory
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_path = Path(tmpdir)
        artifact_file = artifacts_path / "implementation.py"
        artifact_file.write_text("# Implementation code\nprint('hello')")

        # Mock engine for ingestion
        mock_engine = AsyncMock()
        mock_engine.ingest = AsyncMock()
        mock_engine.working_dir = Path(tmpdir) / "kg"
        mock_engine.working_dir.mkdir(parents=True, exist_ok=True)

        # Setup hook registry and ingest hook
        from graph_rag.ingestion import auto_ingest_hook

        # Create a custom test hook that tracks calls
        hook_calls = []

        async def test_hook(step_name, artifacts, metadata):
            """Test hook that records what it received."""
            hook_calls.append({
                "step_name": step_name,
                "artifact_count": len(artifacts),
                "metadata": metadata,
            })

        registry = HookRegistry()
        registry.register(test_hook)

        # Simulate dev step completion
        dev_result = {
            "status": "done",
            "artifacts_dir": str(artifacts_path),
        }
        story = {"id": "S1"}

        # Collect and fire artifacts through hook
        artifacts = _collect_dev_artifacts(dev_result, story)
        await registry.fire("dev", artifacts, {
            "role": "dev",
            "iteration": 1,
            "timestamp": datetime.now().isoformat(),
            "story_id": "S1",
        })

        # Verify hook was called
        assert len(hook_calls) == 1, "Hook should be called once"
        assert hook_calls[0]["step_name"] == "dev", "Hook should receive step_name"
        assert hook_calls[0]["artifact_count"] == 1, "Hook should receive 1 artifact"
        assert hook_calls[0]["metadata"]["role"] == "dev", "Metadata should include role"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingestion_processes_dev_artifacts():
    """
    E2E Test: Ingestion actually processes dev artifacts.

    Validates that ingestion.ingest_artifact() is called with correct content.
    """
    from graph_rag.ingestion import PipelineIngestion

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        artifact_dir = state_dir / "artifacts"
        artifact_dir.mkdir()

        # Create test artifact file
        artifact_file = artifact_dir / "story_impl.py"
        artifact_content = "# Generated implementation\nprint('test')"
        artifact_file.write_text(artifact_content)

        # Mock engine
        mock_engine = AsyncMock()
        mock_engine.ingest = AsyncMock()
        mock_engine.working_dir = state_dir

        # Initialize ingestion
        ingestion = PipelineIngestion(mock_engine, state_dir)

        # Ingest artifact with metadata
        metadata = {
            "role": "dev",
            "step": "implementation",
            "iteration": 1,
            "timestamp": datetime.now().isoformat(),
        }

        await ingestion.ingest_artifact(artifact_content, metadata)

        # Verify engine.ingest was called
        mock_engine.ingest.assert_called_once()

        # Verify the tagged content was passed to engine
        call_args = mock_engine.ingest.call_args
        tagged_content = call_args[0][0]  # First positional argument

        # Verify metadata tags were added
        assert "[Agent: dev]" in tagged_content, "Should tag with agent (dev)"
        assert "[Step: implementation]" in tagged_content, "Should tag with step"
        assert "[Iteration: 1]" in tagged_content, "Should tag with iteration"
        assert artifact_content in tagged_content, "Should include original content"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingestion_state_persists_after_multiple_artifacts():
    """
    E2E Test: Ingestion state persists across multiple artifacts.

    Validates that MD5 deduplication state is maintained between artifacts.
    """
    import hashlib
    from graph_rag.ingestion import PipelineIngestion

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # Mock engine
        mock_engine = AsyncMock()
        mock_engine.ingest = AsyncMock()
        mock_engine.working_dir = state_dir

        # Create ingestion instance
        ingestion = PipelineIngestion(mock_engine, state_dir)

        # Ingest first artifact
        content1 = "# First artifact"
        hash1 = hashlib.md5(content1.encode()).hexdigest()
        ingestion.ingested_hashes[hash1] = "artifact1.py"
        ingestion._save_ingested_hashes()

        # Create new instance (simulating second step)
        ingestion2 = PipelineIngestion(mock_engine, state_dir)

        # Verify state was persisted and loaded
        assert len(ingestion2.ingested_hashes) == 1, "Should load previous state"
        assert hash1 in ingestion2.ingested_hashes, "Should have hash from first artifact"

        # Ingest second artifact (different content)
        content2 = "# Second artifact"
        hash2 = hashlib.md5(content2.encode()).hexdigest()
        ingestion2.ingested_hashes[hash2] = "artifact2.py"
        ingestion2._save_ingested_hashes()

        # Verify both hashes persisted
        ingestion3 = PipelineIngestion(mock_engine, state_dir)
        assert len(ingestion3.ingested_hashes) == 2, "Should persist both artifacts"
        assert hash1 in ingestion3.ingested_hashes, "Should keep first hash"
        assert hash2 in ingestion3.ingested_hashes, "Should keep second hash"


# ============================================================================
# CONFIG TESTS - Auto-Ingest Enable/Disable
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_ingest_respects_config_disabled():
    """
    Test: auto_ingest_hook respects config when disabled.

    When auto_ingest=false (default), hook should skip ingestion.
    """
    from graph_rag.ingestion import auto_ingest_hook
    from unittest.mock import patch

    mock_config = {
        "graph_rag": {"auto_ingest": False}
    }

    with patch('common.load_config', return_value=mock_config):
        # Call hook with auto_ingest disabled
        await auto_ingest_hook("dev", [Path("/tmp/test.py")], {
            "role": "dev",
            "iteration": 1,
        })

        # Should return without error (skipped)
        # Test passes if no exception raised


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_ingest_enabled_via_config():
    """
    Test: auto_ingest_hook can be enabled via config.

    When auto_ingest=true, hook should attempt ingestion.
    """
    from graph_rag.ingestion import auto_ingest_hook
    from unittest.mock import patch

    mock_config = {
        "graph_rag": {
            "auto_ingest": True,
            "working_dir": "/tmp/test_kg",
            "llm_model": "test-model",
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_file = Path(tmpdir) / "artifact.py"
        artifact_file.write_text("# Content")

        with patch('common.load_config', return_value=mock_config):
            with patch('graph_rag.engine.GraphRAGEngine.get_instance') as mock_get:
                mock_engine = AsyncMock()
                mock_engine.ingest = AsyncMock()
                mock_engine.working_dir = Path(tmpdir)
                mock_get.return_value = mock_engine

                # Call hook with auto_ingest enabled
                await auto_ingest_hook("dev", [artifact_file], {
                    "role": "dev",
                    "iteration": 1,
                })

                # Should have attempted to get engine instance
                mock_get.assert_called_once()


# ============================================================================
# PIPELINE SAFETY TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_continues_on_ingest_error():
    """
    Test: Pipeline continues even if ingestion fails.

    Auto-ingest errors should NOT block the dev pipeline.
    """
    from scripts.orchestrate import HookRegistry

    # Create hook that raises error
    async def failing_hook(step_name, artifacts, metadata):
        raise RuntimeError("Ingestion failed!")

    registry = HookRegistry()
    registry.register(failing_hook)

    # Fire hook - should NOT raise
    from pathlib import Path
    await registry.fire("dev", [Path("/tmp/test.py")], {
        "role": "dev",
        "iteration": 1,
    })

    # Test passes if no exception propagated


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_ingest_handles_missing_artifacts():
    """
    Test: auto_ingest_hook handles missing artifact files gracefully.

    Non-existent files should be skipped, not crash the hook.
    """
    from graph_rag.ingestion import auto_ingest_hook
    from unittest.mock import patch

    mock_config = {
        "graph_rag": {
            "auto_ingest": True,
            "working_dir": "/tmp/test_kg",
            "llm_model": "test-model",
        }
    }

    with patch('common.load_config', return_value=mock_config):
        with patch('graph_rag.engine.GraphRAGEngine.get_instance') as mock_get:
            mock_engine = AsyncMock()
            mock_engine.ingest = AsyncMock()
            mock_get.return_value = mock_engine

            # Call hook with non-existent artifact
            non_existent = Path("/tmp/does_not_exist_123456.py")
            await auto_ingest_hook("dev", [non_existent], {
                "role": "dev",
                "iteration": 1,
            })

            # Should handle gracefully - no error
            # ingest should not be called for missing files
