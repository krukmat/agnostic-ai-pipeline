"""
AP-2-T2: Integration tests for PipelineIngestion without mocking engine.

Tests ingestion with real state management and validation.
Validates that metadata is correctly tagged and state is persisted.

Before: Mocked engine.ingest, couldn't verify actual flow
After: Local engine that validates ingestion happens correctly
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock

from graph_rag.ingestion import PipelineIngestion


class LocalEngineForIngestionIntegration:
    """
    Local engine mock that simulates real ingestion for integration testing.

    Tracks ingested content and validates state persistence.
    """

    def __init__(self, state_dir: Path):
        self.working_dir = state_dir
        self.ingested_contents = []  # Track all ingested content
        self.ingestion_log = self.working_dir / ".ingestion_log.json"

    async def ingest(self, content: str):
        """Track ingested content and persist."""
        self.ingested_contents.append(content)

        # Simulate real ingestion: persist to log
        logs = []
        if self.ingestion_log.exists():
            logs = json.loads(self.ingestion_log.read_text())

        logs.append({
            "content_length": len(content),
            "has_source_tag": "[Source:" in content,
            "has_type_tag": "[Type:" in content,
        })

        self.ingestion_log.write_text(json.dumps(logs, indent=2))

    async def finalize(self):
        """Cleanup method."""
        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_artifact_metadata_validation():
    """
    AP-2-T2: Verify that artifacts are correctly tagged with metadata.

    Test validates:
    1. Metadata tags ([Agent:], [Step:], [Iteration:]) are added
    2. Original content is preserved
    3. Engine receives the complete tagged content
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        engine = LocalEngineForIngestionIntegration(state_dir)
        ingestion = PipelineIngestion(engine, state_dir)

        # Prepare artifact
        metadata = {
            "role": "architect",
            "step": "design_phase",
            "iteration": 2,
            "timestamp": "2026-02-06T12:00:00Z"
        }
        artifact_text = "Design Decision Record: Implement CQRS pattern"

        # Ingest artifact
        await ingestion.ingest_artifact(artifact_text, metadata)

        # Verify engine received tagged content
        assert len(engine.ingested_contents) == 1, "Should ingest exactly once"
        tagged = engine.ingested_contents[0]

        # Verify metadata tags
        assert "[Agent: architect]" in tagged, "Should include agent tag"
        assert "[Step: design_phase]" in tagged, "Should include step tag"
        assert "[Iteration: 2]" in tagged, "Should include iteration tag"

        # Verify original content is preserved
        assert "Design Decision Record" in tagged, "Should preserve original content"
        assert "CQRS pattern" in tagged, "Should preserve original content"

        # Verify structure
        assert tagged.startswith("[Agent:"), "Tags should be at start"
        lines = tagged.split("\n")
        assert len(lines) >= 3, "Should have metadata lines + content"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_text_with_source_tags():
    """
    AP-2-T2: Verify that ingest_text correctly tags content with source and type.

    Validates that source identification ([Source:]) is preserved for traceability.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        engine = LocalEngineForIngestionIntegration(state_dir)
        ingestion = PipelineIngestion(engine, state_dir)

        # Ingest raw text with source
        text = "Feature: User Authentication\nScenario: Valid credentials"
        source = "requirements.yaml"
        content_type = "planning"

        await ingestion.ingest_text(text, source, content_type)

        # Verify engine received tagged content
        assert len(engine.ingested_contents) == 1
        tagged = engine.ingested_contents[0]

        # Verify source and type tags
        assert "[Source: requirements.yaml]" in tagged, "Should tag source"
        assert "[Type: planning]" in tagged, "Should tag content type"

        # Verify content
        assert "User Authentication" in tagged, "Should preserve content"
        assert "Valid credentials" in tagged, "Should preserve content"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingestion_state_persists_across_instances():
    """
    AP-2-T2: Verify that ingestion state is persisted and reloaded.

    Validates that deduplication state persists across multiple PipelineIngestion instances.
    """
    import hashlib

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)

        # First ingestion instance
        engine1 = LocalEngineForIngestionIntegration(state_dir)
        ingestion1 = PipelineIngestion(engine1, state_dir)

        # Manually add a hash (simulating _ingest_directory behavior)
        content = "Content A"
        content_hash = hashlib.md5(content.encode()).hexdigest()
        ingestion1.ingested_hashes[content_hash] = "source1.txt"
        ingestion1._save_ingested_hashes()

        # Get the hash that was saved
        saved_hashes_1 = ingestion1.ingested_hashes.copy()
        assert len(saved_hashes_1) == 1, "Should have 1 hash after first ingest"

        # Second ingestion instance (should load state)
        engine2 = LocalEngineForIngestionIntegration(state_dir)
        ingestion2 = PipelineIngestion(engine2, state_dir)

        # Verify state was loaded
        assert len(ingestion2.ingested_hashes) == 1, "Should load state from first instance"
        assert saved_hashes_1 == ingestion2.ingested_hashes, \
            "Should load same hashes as first instance saved"

        # Verify the content hash is in the reloaded state
        assert content_hash in ingestion2.ingested_hashes, \
            "Previous content hash should be in state for dedup"
        assert ingestion2.ingested_hashes[content_hash] == "source1.txt", \
            "Should preserve source mapping"
