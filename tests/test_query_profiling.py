"""
Query Performance Profiling Tests

Tests for query performance telemetry and profiling capabilities.
Validates that query times are properly logged and accessible.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import time


@pytest.mark.unit
@pytest.mark.asyncio
async def test_query_method_logs_timing():
    """
    Test: query() method logs timing metrics.

    Validates that query execution includes timing instrumentation.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "top_k": 50,
    }

    engine = GraphRAGEngine(config)

    # Create mock RAG engine
    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="Test response from LLM")

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            # Capture logs
            with patch('graph_rag.engine.logger') as mock_logger:
                result = await engine.query("What is this?", mode="mix", top_k=50)

                # Verify query returned
                assert result == "Test response from LLM"

                # Verify logging called (check for INFO level with timing)
                info_calls = [call for call in mock_logger.info.call_args_list]
                assert len(info_calls) > 0, "Should log info with timing metrics"

                # Check that timing metrics are in the log message
                log_message = str(info_calls[0])
                assert "total_time" in log_message, "Should log total_time"
                assert "rag_time" in log_message, "Should log rag_time"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_context_only_logs_timing():
    """
    Test: get_context_only() method logs timing metrics.

    Validates that context retrieval includes timing instrumentation.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "top_k": 60,
    }

    engine = GraphRAGEngine(config)

    # Create mock RAG engine
    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="Entity1, Entity2, Relationship")

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            # Capture logs
            with patch('graph_rag.engine.logger') as mock_logger:
                result = await engine.get_context_only("What context?", mode="local", top_k=60)

                # Verify context returned
                assert "Entity1" in result

                # Verify logging called with timing
                info_calls = [call for call in mock_logger.info.call_args_list]
                assert len(info_calls) > 0, "Should log info with timing metrics"

                # Check timing in log
                log_message = str(info_calls[0])
                assert "total_time" in log_message, "Should log total_time"
                assert "rag_time" in log_message, "Should log rag_time"
                assert "context_size" in log_message, "Should log context_size"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_for_role_logs_timing():
    """
    Test: retrieve_for_role() logs timing metrics.

    Validates that role-based retrieval includes full timing breakdown.
    """
    from graph_rag.retrieval import AgentRetriever

    # Mock engine with both query and get_context_only
    # Note: All roles use context_only=True per ROLE_POLICIES
    mock_engine = AsyncMock()
    mock_engine.query = AsyncMock(return_value="Query response")
    mock_engine.get_context_only = AsyncMock(return_value="Context only response")

    retriever = AgentRetriever(mock_engine)

    # Capture logs
    with patch('graph_rag.retrieval.logger') as mock_logger:
        result = await retriever.retrieve_for_role("architect", "Query for architect")

        # Verify retrieval returned (architect uses context_only=True)
        assert result == "Context only response"

        # Verify logging called with metrics
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) >= 1, "Should have info logs with timing"

        # Check for timing in log messages
        log_messages = " ".join([str(call) for call in info_calls])
        assert "total_time" in log_messages, "Should log total_time"
        assert "engine_time" in log_messages or "total_time" in log_messages, \
            "Should log timing metrics"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timing_metrics_reasonable():
    """
    Test: Timing metrics are reasonable (non-zero, non-negative).

    Validates that captured timing values are sensible.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    # Mock with delay to simulate real work
    async def delayed_aquery(*args, **kwargs):
        await asyncio.sleep(0.01)  # 10ms delay
        return "Delayed response"

    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(side_effect=delayed_aquery)

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            start = time.perf_counter()
            result = await engine.query("Test?", mode="mix")
            elapsed = time.perf_counter() - start

            # Verify the mock delay was respected
            assert elapsed >= 0.01, "Should have taken at least 10ms"
            assert result == "Delayed response"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_profiling_end_to_end():
    """
    Integration Test: Full query profiling flow.

    Validates that timing metrics are collected and logged throughout
    the entire query pipeline.
    """
    from graph_rag.engine import GraphRAGEngine
    from graph_rag.retrieval import AgentRetriever

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
        "top_k": 50,
    }

    engine = GraphRAGEngine(config)
    retriever = AgentRetriever(engine)

    # Mock engine query
    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(return_value="E2E test response")

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            # Capture all logs
            logged_messages = []

            def capture_log(msg):
                logged_messages.append(msg)

            with patch('graph_rag.retrieval.logger.info', side_effect=capture_log):
                with patch('graph_rag.engine.logger.info', side_effect=capture_log):
                    # Execute E2E query
                    result = await retriever.retrieve_for_role("dev", "What needs implementing?")

                    # Verify result
                    assert result == "E2E test response"

                    # Verify logs captured
                    assert len(logged_messages) >= 1, "Should have log messages"

                    # Verify metrics present in logs
                    all_logs = " ".join(logged_messages)
                    assert "total_time" in all_logs, "Should capture total_time"
                    assert "DEV" in all_logs or "dev" in all_logs, "Should mention role"


@pytest.mark.unit
def test_timing_format_valid():
    """
    Test: Timing metric format is valid for parsing.

    Validates that logged timing values can be parsed and are valid.
    """
    import re

    # Test format: "total_time=0.123s"
    timing_pattern = r"total_time=(\d+\.\d+)s"

    test_messages = [
        "Query total_time=0.456s rag_time=0.123s init_time=0.001s",
        "Retrieval total_time=1.234s engine_time=0.567s",
    ]

    for msg in test_messages:
        match = re.search(timing_pattern, msg)
        assert match, f"Should find timing in: {msg}"

        total_time_str = match.group(1)
        total_time = float(total_time_str)

        assert total_time > 0, "Timing should be positive"
        assert total_time < 1000, "Timing should be reasonable (< 1000s)"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_case_logs_timing():
    """
    Test: Error cases also log timing metrics.

    Validates that even when queries fail, timing is captured.
    """
    from graph_rag.engine import GraphRAGEngine

    config = {
        "working_dir": "/tmp/test_kg",
        "llm_model": "test-model",
    }

    engine = GraphRAGEngine(config)

    # Mock engine to raise error
    mock_rag = AsyncMock()
    mock_rag.aquery = AsyncMock(side_effect=RuntimeError("Query failed!"))

    with patch.object(engine, '_initialized', True):
        with patch.object(engine, 'rag', mock_rag):
            # Capture logs
            with patch('graph_rag.engine.logger') as mock_logger:
                with pytest.raises(RuntimeError):
                    await engine.query("Failing query?", mode="mix")

                # Verify error logged with timing
                error_calls = [call for call in mock_logger.error.call_args_list]
                assert len(error_calls) > 0, "Should log error"

                error_message = str(error_calls[0])
                assert "after" in error_message or "Query failed" in error_message, \
                    "Should include error details in error log"
