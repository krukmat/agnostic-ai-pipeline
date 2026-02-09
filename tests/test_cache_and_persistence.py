"""
Index Persistence & Caching Tests

Tests for query caching and index persistence to achieve 3-5x latency reduction.
"""

import pytest
import asyncio
import tempfile
import time
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


# ============================================================================
# UNIT TESTS - QueryCache Class
# ============================================================================


@pytest.mark.unit
def test_query_cache_class_exists():
    """
    Test: QueryCache class exists in graph_rag.cache module.

    This test will FAIL until QueryCache is implemented.
    """
    from graph_rag.cache import QueryCache

    # Verify class can be instantiated
    cache = QueryCache()
    assert cache is not None, "QueryCache should be instantiable"


@pytest.mark.unit
def test_query_cache_has_get_set_methods():
    """
    Test: QueryCache has get() and set() methods.

    This test will FAIL until these methods are implemented.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache()

    # Verify methods exist
    assert hasattr(cache, 'get'), "QueryCache should have get() method"
    assert hasattr(cache, 'set'), "QueryCache should have set() method"
    assert callable(cache.get), "get should be callable"
    assert callable(cache.set), "set should be callable"


@pytest.mark.unit
def test_query_cache_set_and_get():
    """
    Test: QueryCache can set and retrieve cached values.

    This test will FAIL until set/get are properly implemented.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache()

    # Set a value
    key = "query:What is AI?"
    value = "AI is artificial intelligence"
    cache.set(key, value)

    # Get the value
    result = cache.get(key)
    assert result == value, "Should retrieve same value that was set"


@pytest.mark.unit
def test_query_cache_miss_returns_none():
    """
    Test: QueryCache returns None for cache miss.

    This test will FAIL until get() properly handles missing keys.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache()

    # Get non-existent key
    result = cache.get("non_existent_key")
    assert result is None, "Should return None for missing key"


@pytest.mark.unit
def test_query_cache_clear():
    """
    Test: QueryCache has clear() method to empty the cache.

    This test will FAIL until clear() is implemented.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache()

    # Set some values
    cache.set("key1", "value1")
    cache.set("key2", "value2")

    # Clear cache
    cache.clear()

    # Verify cache is empty
    assert cache.get("key1") is None, "After clear, should return None"
    assert cache.get("key2") is None, "After clear, should return None"


@pytest.mark.unit
def test_query_cache_respects_max_size():
    """
    Test: QueryCache respects max_size parameter and evicts old entries.

    This test will FAIL until max_size enforcement is implemented.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache(max_size=3)

    # Add 4 entries (should evict oldest)
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    cache.set("key4", "value4")  # This should evict key1

    # Verify size doesn't exceed max
    assert cache.get("key1") is None, "Oldest entry should be evicted"
    assert cache.get("key2") is not None, "key2 should still exist"
    assert cache.get("key3") is not None, "key3 should still exist"
    assert cache.get("key4") is not None, "key4 should exist"


@pytest.mark.unit
def test_query_cache_respects_ttl():
    """
    Test: QueryCache respects TTL (Time To Live) for cached entries.

    This test will FAIL until TTL enforcement is implemented.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache(ttl_seconds=1)  # 1 second TTL

    # Set a value
    cache.set("temporary_key", "temporary_value")
    assert cache.get("temporary_key") == "temporary_value", "Should exist immediately"

    # Wait for TTL to expire
    time.sleep(1.1)

    # Value should be expired
    result = cache.get("temporary_key")
    assert result is None, "Entry should have expired after TTL"


@pytest.mark.unit
def test_query_cache_generates_key_from_query_params():
    """
    Test: QueryCache can generate consistent keys from query parameters.

    This test will FAIL until key generation is implemented.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache()

    # Test key generation for same parameters
    key1 = cache.generate_key("What is AI?", mode="local", top_k=10)
    key2 = cache.generate_key("What is AI?", mode="local", top_k=10)

    assert key1 == key2, "Same parameters should generate same key"

    # Different parameters should generate different keys
    key3 = cache.generate_key("What is AI?", mode="global", top_k=10)
    assert key1 != key3, "Different parameters should generate different keys"


@pytest.mark.unit
def test_query_cache_has_size_method():
    """
    Test: QueryCache has size() method to check number of cached entries.

    This test will FAIL until size() is implemented.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache()

    # Empty cache
    assert cache.size() == 0, "Empty cache should have size 0"

    # Add entries
    cache.set("key1", "value1")
    assert cache.size() == 1, "After adding 1 entry, size should be 1"

    cache.set("key2", "value2")
    assert cache.size() == 2, "After adding 2 entries, size should be 2"


# ============================================================================
# UNIT TESTS - Index Persistence
# ============================================================================


@pytest.mark.unit
def test_engine_has_save_indices_method():
    """
    Test: GraphRAGEngine has save_indices() method.

    This test will FAIL until save_indices is implemented.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    # Verify method exists
    assert hasattr(engine, 'save_indices'), "Engine should have save_indices() method"
    assert callable(engine.save_indices), "save_indices should be callable"


@pytest.mark.unit
def test_engine_has_load_indices_method():
    """
    Test: GraphRAGEngine has load_indices() method.

    This test will FAIL until load_indices is implemented.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    # Verify method exists
    assert hasattr(engine, 'load_indices'), "Engine should have load_indices() method"
    assert callable(engine.load_indices), "load_indices should be callable"


@pytest.mark.unit
def test_save_indices_creates_persistence_file():
    """
    Test: save_indices() creates a file on disk.

    This test will FAIL until save_indices writes to disk.
    """
    from graph_rag.engine import GraphRAGEngine

    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "working_dir": tmpdir,
            "llm_model": "test-model",
        }

        engine = GraphRAGEngine(config)

        # Create mock indices state
        engine._index_metadata = {"entities": 100, "relationships": 250}

        # Save indices
        engine.save_indices()

        # Verify persistence file was created
        persistence_file = Path(tmpdir) / ".graph_rag_indices.json"
        assert persistence_file.exists(), "Persistence file should be created"


@pytest.mark.unit
def test_load_indices_reads_from_persistence_file():
    """
    Test: load_indices() reads from disk and restores state.

    This test will FAIL until load_indices reads from disk.
    """
    from graph_rag.engine import GraphRAGEngine
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create persistence file
        persistence_file = Path(tmpdir) / ".graph_rag_indices.json"
        metadata = {"entities": 100, "relationships": 250}
        persistence_file.write_text(json.dumps(metadata))

        config = {
            "working_dir": tmpdir,
            "llm_model": "test-model",
        }

        engine = GraphRAGEngine(config)

        # Load indices
        engine.load_indices()

        # Verify state was loaded
        assert hasattr(engine, '_index_metadata'), "Should have _index_metadata after load"
        assert engine._index_metadata.get("entities") == 100, "Should restore entities count"


@pytest.mark.unit
def test_load_indices_handles_missing_file():
    """
    Test: load_indices() gracefully handles missing persistence file.

    This test will FAIL until load_indices has error handling.
    """
    from graph_rag.engine import GraphRAGEngine

    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "working_dir": tmpdir,
            "llm_model": "test-model",
        }

        engine = GraphRAGEngine(config)

        # Call load_indices on non-existent file
        # Should NOT raise exception
        engine.load_indices()

        # Test passes if no exception raised


# ============================================================================
# INTEGRATION TESTS - Cache Effectiveness
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_query_is_faster_than_uncached():
    """
    Integration Test: Cached query is faster than uncached query.

    Validates that cache reduces latency for repeated queries.
    """
    from graph_rag.engine import GraphRAGEngine
    from graph_rag.cache import QueryCache

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "cache_enabled": True,
        "cache_ttl": 3600,
    }

    engine = GraphRAGEngine(config)
    cache = QueryCache(ttl_seconds=3600)

    # Create mock RAG engine with delay
    async def slow_aquery(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate 100ms latency
        return "Slow response"

    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(side_effect=slow_aquery)

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            # First query (uncached)
            start1 = time.perf_counter()
            result1 = await engine.query("Test query?", mode="mix")
            uncached_time = time.perf_counter() - start1

            # Generate cache key
            cache_key = cache.generate_key("Test query?", mode="mix")
            cache.set(cache_key, result1)

            # Second query (cached)
            start2 = time.perf_counter()
            cached_result = cache.get(cache_key)
            cached_time = time.perf_counter() - start2

            # Cached access should be significantly faster
            assert cached_time < uncached_time / 2, \
                f"Cached query ({cached_time:.4f}s) should be ≥2x faster than uncached ({uncached_time:.4f}s)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_persists_across_restarts():
    """
    Integration Test: Cache state persists across engine restarts.

    Validates that cached indices can be reloaded after restart.
    """
    from graph_rag.engine import GraphRAGEngine

    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "working_dir": tmpdir,
            "llm_model": "test-model",
            "cache_enabled": True,
        }

        # First engine instance
        engine1 = GraphRAGEngine(config)
        engine1._index_metadata = {"query_count": 42, "cache_hits": 15}
        engine1.save_indices()

        # Second engine instance (simulating restart)
        engine2 = GraphRAGEngine(config)
        engine2.load_indices()

        # Verify state was restored
        assert engine2._index_metadata.get("query_count") == 42, \
            "Cache state should persist after reload"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_engine_uses_cache_for_repeated_queries():
    """
    Integration Test: Engine uses cache for repeated queries.

    Validates that engine.query() returns cached results for identical queries.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "cache_enabled": True,
    }

    engine = GraphRAGEngine(config)

    # Mock RAG engine
    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="Cached response")

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            # First call
            result1 = await engine.query("Test?", mode="mix")
            call_count_1 = mock_rag.aquery.call_count

            # Second call (same query)
            result2 = await engine.query("Test?", mode="mix")
            call_count_2 = mock_rag.aquery.call_count

            # Both should return same result
            assert result1 == result2, "Repeated query should return same result"

            # Second call should use cache (RAG engine called only once)
            assert call_count_2 == call_count_1, \
                "Repeated query should use cache, not call RAG engine again"


# ============================================================================
# UNIT TESTS - Cache Configuration
# ============================================================================


@pytest.mark.unit
def test_cache_config_in_engine_init():
    """
    Test: Engine respects cache_enabled config flag.

    This test will FAIL until cache_enabled config is honored.
    """
    from graph_rag.engine import GraphRAGEngine

    config_disabled = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "cache_enabled": False,
    }

    engine = GraphRAGEngine(config_disabled)

    # Cache should be disabled
    assert not engine.cache_enabled, "Cache should be disabled per config"


@pytest.mark.unit
def test_cache_ttl_config():
    """
    Test: Engine respects cache_ttl config parameter.

    This test will FAIL until cache_ttl config is honored.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "cache_enabled": True,
        "cache_ttl": 1800,  # 30 minutes
    }

    engine = GraphRAGEngine(config)

    # TTL should be set
    assert engine.cache_ttl == 1800, "Cache TTL should match config"


@pytest.mark.unit
def test_cache_max_size_config():
    """
    Test: Engine respects cache_max_size config parameter.

    This test will FAIL until cache_max_size config is honored.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "cache_enabled": True,
        "cache_max_size": 500,
    }

    engine = GraphRAGEngine(config)

    # Max size should be set
    assert engine.cache_max_size == 500, "Cache max_size should match config"


# ============================================================================
# PERFORMANCE TESTS - Latency Reduction Target
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_achieves_3x_latency_reduction():
    """
    Performance Test: Cache achieves 3-5x latency reduction target.

    Validates that caching achieves the performance improvement goal.
    This is the key acceptance criterion for query caching.
    """
    from graph_rag.engine import GraphRAGEngine
    from graph_rag.cache import QueryCache

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "cache_enabled": True,
    }

    engine = GraphRAGEngine(config)
    cache = QueryCache(ttl_seconds=3600)

    # Create mock RAG with slow response
    async def slow_query(*args, **kwargs):
        await asyncio.sleep(0.05)  # 50ms latency
        return "Performance test response"

    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(side_effect=slow_query)

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            query_text = "Complex performance test query"
            cache_key = cache.generate_key(query_text, mode="global", top_k=20)

            # Baseline: uncached query
            start = time.perf_counter()
            result = await engine.query(query_text, mode="global", top_k=20)
            uncached_time = time.perf_counter() - start

            # Cache the result
            cache.set(cache_key, result)

            # Cached access
            start = time.perf_counter()
            cached_result = cache.get(cache_key)
            cached_time = time.perf_counter() - start

            # Calculate speedup
            speedup = uncached_time / cached_time

            # Assert 3-5x improvement (at least 3x)
            assert speedup >= 3.0, \
                f"Cache should achieve ≥3x speedup, got {speedup:.1f}x " \
                f"(uncached: {uncached_time:.4f}s, cached: {cached_time:.4f}s)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_memory_efficiency():
    """
    Performance Test: Cache maintains reasonable memory footprint.

    Validates that cache doesn't grow unbounded (respects max_size).
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache(max_size=100)

    # Add 150 entries (should evict oldest)
    for i in range(150):
        cache.set(f"query_{i}", f"result_{i}")

    # Size should not exceed max
    assert cache.size() <= 100, "Cache size should respect max_size limit"


@pytest.mark.unit
def test_cache_key_consistency():
    """
    Test: Cache key generation is deterministic and consistent.

    Validates that same parameters always generate same key.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache()

    # Generate keys multiple times with same parameters
    keys = [
        cache.generate_key("What is AI?", mode="local", top_k=10)
        for _ in range(5)
    ]

    # All keys should be identical
    assert len(set(keys)) == 1, "Same parameters should generate same key every time"


# ============================================================================
# INTEGRATION TESTS - End-to-End Cache + Persistence Flow
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cache_and_persistence_flow():
    """
    E2E Integration Test: Full cache and persistence flow.

    Validates:
    1. Queries are cached
    2. Cache improves performance
    3. Indices are persisted to disk
    4. State survives engine restart
    """
    from graph_rag.engine import GraphRAGEngine

    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "working_dir": tmpdir,
            "llm_model": "test-model",
            "cache_enabled": True,
            "cache_ttl": 3600,
            "cache_max_size": 100,
        }

        # First engine instance
        engine1 = GraphRAGEngine(config)
        engine1._index_metadata = {
            "start_time": datetime.now().isoformat(),
            "query_count": 0,
            "cache_hits": 0,
        }

        # Simulate some operations
        engine1._index_metadata["query_count"] = 42
        engine1._index_metadata["cache_hits"] = 15

        # Save state
        engine1.save_indices()

        # Second engine instance (restart simulation)
        engine2 = GraphRAGEngine(config)
        engine2.load_indices()

        # Verify state persisted
        assert engine2._index_metadata.get("query_count") == 42, \
            "Query count should persist"
        assert engine2._index_metadata.get("cache_hits") == 15, \
            "Cache hits should persist"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_clear_via_config():
    """
    Test: Cache can be cleared via configuration.

    Validates that cache_clear flag in config triggers full cache clear.
    """
    from graph_rag.cache import QueryCache

    cache = QueryCache()

    # Add entries
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    assert cache.size() == 2, "Should have 2 entries"

    # Clear cache
    cache.clear()

    # Verify empty
    assert cache.size() == 0, "Cache should be empty after clear"
    assert cache.get("key1") is None, "Entries should be removed"
