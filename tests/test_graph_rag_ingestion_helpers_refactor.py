"""
Test cyclomatic complexity reduction for _ingest_directory.

Before: CC=8 (multiple nested conditions)
After: CC≤5 (extracted helper functions)

TDD: This test validates the refactored structure.
"""

import pytest
from pathlib import Path
import tempfile
import asyncio
from graph_rag.ingestion import PipelineIngestion


@pytest.mark.unit
async def test_ingest_directory_refactored_structure():
    """
    Verify that _ingest_directory uses extracted helper functions.

    Validates the refactored structure:
    - _should_ingest_file() encapsulates dedup/file check logic
    - _build_file_metadata() encapsulates tagging logic
    """
    # Create minimal mock engine
    class MockEngine:
        async def ingest(self, content):
            pass

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        engine = MockEngine()
        ingestion = PipelineIngestion(engine, state_dir)

        # Verify helper methods exist
        assert hasattr(ingestion, '_should_ingest_file'), \
            "Should have _should_ingest_file() helper method"
        assert hasattr(ingestion, '_build_file_metadata'), \
            "Should have _build_file_metadata() helper method"

        # Verify they're callable
        assert callable(ingestion._should_ingest_file), \
            "_should_ingest_file should be callable"
        assert callable(ingestion._build_file_metadata), \
            "_build_file_metadata should be callable"


@pytest.mark.unit
async def test_should_ingest_file_skips_duplicates():
    """
    Verify _should_ingest_file correctly identifies duplicates.
    """
    class MockEngine:
        async def ingest(self, content):
            pass

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        # Create a test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("content")

        engine = MockEngine()
        ingestion = PipelineIngestion(engine, state_dir)

        # First check: should be ingested
        should_ingest_1 = ingestion._should_ingest_file(test_file)
        assert should_ingest_1 is True, "New file should be marked for ingestion"

        # Simulate that it was ingested (add hash to ingested_hashes)
        import hashlib
        content = test_file.read_text()
        file_hash = hashlib.md5(content.encode()).hexdigest()
        ingestion.ingested_hashes[file_hash] = str(test_file)

        # Second check: should be skipped (already ingested)
        should_ingest_2 = ingestion._should_ingest_file(test_file)
        assert should_ingest_2 is False, "Duplicate file should be skipped"


@pytest.mark.unit
def test_build_file_metadata_formats_correctly():
    """
    Verify _build_file_metadata formats content with source/type tags.
    """
    class MockEngine:
        async def ingest(self, content):
            pass

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        test_file = Path(tmpdir) / "test.yaml"
        test_file.write_text("key: value")

        engine = MockEngine()
        ingestion = PipelineIngestion(engine, state_dir)

        content = test_file.read_text()
        tagged = ingestion._build_file_metadata(test_file, content, "planning")

        # Verify format
        assert "[Source:" in tagged, "Should include source tag"
        assert str(test_file) in tagged, "Should include file path"
        assert "[Type: planning]" in tagged, "Should include type tag"
        assert "key: value" in tagged, "Should include original content"


@pytest.mark.unit
async def test_ingest_directory_flow_with_helpers():
    """
    Verify the main flow using extracted helpers is correct.
    """
    class MockEngine:
        def __init__(self):
            self.ingested_contents = []

        async def ingest(self, content):
            self.ingested_contents.append(content)

    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        # Change to temp directory to make relative paths work
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Create test structure
            state_dir = Path(tmpdir) / "state"
            state_dir.mkdir()

            planning_dir = Path("planning")
            planning_dir.mkdir()

            test_file1 = planning_dir / "story.yaml"
            test_file1.write_text("- id: S1\n  title: Test")

            test_file2 = planning_dir / "story2.yaml"
            test_file2.write_text("- id: S2\n  title: Another")

            engine = MockEngine()
            ingestion = PipelineIngestion(engine, state_dir)

            # Ingest the directory
            stats = await ingestion._ingest_directory("planning", "planning")

            # Verify stats
            assert stats["new_files"] == 2, f"Should ingest 2 new files, got {stats['new_files']}"
            assert stats["skipped_files"] == 0, "Should skip 0 files initially"
            assert len(engine.ingested_contents) == 2, "Engine should receive 2 contents"

            # Second ingest should skip all
            stats2 = await ingestion._ingest_directory("planning", "planning")
            assert stats2["new_files"] == 0, "Should ingest 0 new files (already ingested)"
            assert stats2["skipped_files"] == 2, "Should skip 2 files (already ingested)"
        finally:
            os.chdir(old_cwd)


@pytest.mark.unit
def test_should_ingest_file_rejects_directories():
    """
    Verify _should_ingest_file correctly rejects directories.
    """
    class MockEngine:
        async def ingest(self, content):
            pass

    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        test_dir = Path(tmpdir) / "subdir"
        test_dir.mkdir()

        engine = MockEngine()
        ingestion = PipelineIngestion(engine, state_dir)

        # Directory should not be ingested
        should_ingest = ingestion._should_ingest_file(test_dir)
        assert should_ingest is False, "Directories should not be ingested"
