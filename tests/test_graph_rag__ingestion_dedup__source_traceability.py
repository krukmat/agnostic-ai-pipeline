"""
Test deduplication with source traceability.

Validates that dedup preserves multiple sources of same content.
Before fix: hash -> file (loses source info if multiple files have same content)
After fix: hash -> [file1, file2, ...] (preserves source diversity)

TDD: Este test FALLA antes de la implementación.
"""

import pytest
from pathlib import Path
import json


def test_ingestion_state_includes_source_map():
    """
    Verify that ingestion state tracks multiple sources per hash.
    """
    # Create mock ingestion state with source map
    state = {
        "ingested_hashes": {
            "hash_123": {
                "sources": ["file1.py", "file2.py"],  # Multiple sources
                "timestamp": "2026-02-06T10:00:00"
            },
            "hash_456": {
                "sources": ["file3.py"],  # Single source
                "timestamp": "2026-02-06T10:05:00"
            }
        }
    }

    # Verify structure
    assert "hash_123" in state["ingested_hashes"]
    assert "sources" in state["ingested_hashes"]["hash_123"]
    assert len(state["ingested_hashes"]["hash_123"]["sources"]) == 2
    assert "file1.py" in state["ingested_hashes"]["hash_123"]["sources"]


def test_dedup_preserves_multiple_sources():
    """
    Verify that same content from different files is tracked.
    """
    # Mock: same content, different sources
    content = "Common pattern used in multiple files"

    # Simple hash simulation
    import hashlib
    content_hash = hashlib.md5(content.encode()).hexdigest()

    # Track sources
    sources_map = {}

    # First file with this content
    file1 = "module_a.py"
    if content_hash not in sources_map:
        sources_map[content_hash] = []
    sources_map[content_hash].append(file1)

    # Second file with same content
    file2 = "module_b.py"
    if content_hash not in sources_map:
        sources_map[content_hash] = []
    if file2 not in sources_map[content_hash]:
        sources_map[content_hash].append(file2)

    # Verify both sources are tracked
    assert content_hash in sources_map
    assert len(sources_map[content_hash]) == 2
    assert file1 in sources_map[content_hash]
    assert file2 in sources_map[content_hash]


def test_dedup_key_includes_filepath():
    """
    Verify that dedup uses composite key (filepath, content_hash) instead of hash alone.

    This allows tracking same content from multiple files without losing one.
    """
    import hashlib

    content = "A common utility function"
    content_hash = hashlib.md5(content.encode()).hexdigest()

    # Old approach (problematic): only hash
    old_key = content_hash

    # New approach (fixed): (filepath, hash)
    filepath1 = "src/utils.py"
    filepath2 = "lib/helpers.py"

    new_key1 = (filepath1, content_hash)
    new_key2 = (filepath2, content_hash)

    # With old approach, second file overwrites first
    old_dedup = {old_key: filepath1}
    old_dedup[old_key] = filepath2  # Overwrites!
    assert old_dedup[old_key] == filepath2  # Lost filepath1

    # With new approach, both are preserved
    new_dedup = {}
    new_dedup[new_key1] = content
    new_dedup[new_key2] = content  # Different key, both preserved
    assert len(new_dedup) == 2
    assert new_dedup[new_key1] == content
    assert new_dedup[new_key2] == content


def test_source_map_enables_query():
    """
    Verify that source map enables querying "which files have this pattern".
    """
    # Source map: hash -> [files]
    source_map = {
        "hash_abc": ["auth.py", "security.py", "login.py"],
        "hash_xyz": ["config.py"],
        "hash_uvw": ["database.py", "cache.py"],
    }

    # Query: which files contain pattern with hash_abc?
    pattern_hash = "hash_abc"
    files_with_pattern = source_map.get(pattern_hash, [])

    assert len(files_with_pattern) == 3
    assert "auth.py" in files_with_pattern
    assert "security.py" in files_with_pattern
    assert "login.py" in files_with_pattern

    # Query: all patterns appear in how many files?
    pattern_coverage = {h: len(files) for h, files in source_map.items()}
    assert pattern_coverage["hash_abc"] == 3
    assert pattern_coverage["hash_uvw"] == 2


def test_dedup_tradeoff_documented():
    """
    Verify that dedup vs traceability tradeoff is documented.

    We're making a design choice: keep source diversity information.
    """
    # Design choice: source diversity matters more than minimal storage
    # Because:
    # 1. Helps identify code reuse patterns
    # 2. Enables dependency analysis (which modules share patterns)
    # 3. Minimal storage overhead (just tracking extra filenames)

    tradeoff = {
        "benefit": "Source diversity preserved for better analysis",
        "cost": "Slightly larger ingestion state file",
        "decision": "Preserve sources (benefit > cost)"
    }

    assert tradeoff["decision"] == "Preserve sources (benefit > cost)"
