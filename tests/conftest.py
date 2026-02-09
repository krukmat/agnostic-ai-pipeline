"""
pytest configuration and auto-marking for Graph RAG tests.

Automatically categorize tests for CI/offline profiles.
"""

import pytest
import importlib.util


@pytest.fixture(autouse=True)
def _reset_graph_rag_singleton_between_tests():
    """
    Ensure GraphRAGEngine singleton does not leak across pytest event loops.

    This prevents RuntimeError: lock/object bound to a different event loop
    when running async Graph RAG tests in the full suite.
    """
    try:
        from graph_rag.engine import GraphRAGEngine
        GraphRAGEngine.clear_instance()
    except Exception:
        # Graph RAG is optional for many suites.
        pass

    yield

    try:
        from graph_rag.engine import GraphRAGEngine
        GraphRAGEngine.clear_instance()
    except Exception:
        pass


def pytest_collection_modifyitems(config, items):
    """
    Automatically apply markers based on test file/name patterns.

    This allows tests to be grouped for CI (fast) vs manual (comprehensive).
    """
    for item in items:
        # Determine test file
        test_file = item.fspath.basename

        # Apply markers based on file pattern
        if "e2e_real" in test_file:
            # Real E2E tests are integration tests
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)
        elif "e2e.py" in test_file:
            # Original E2E acceptance tests
            if "acceptance" in item.name or "advantages" in item.name:
                # These are quick, non-async checks
                item.add_marker(pytest.mark.unit)
        elif "remediation" in test_file:
            # All remediation tests are unit tests (mocked)
            item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.graph_rag)
        elif "test_graph_rag" in test_file:
            # Graph RAG unit tests
            if "skip" not in str(item.keywords):
                item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.graph_rag)

        # Mark skipped tests as smoke tests (verified separately)
        if "skip" in str(item.keywords):
            item.add_marker(pytest.mark.smoke)


def has_gpu_stack() -> bool:
    return importlib.util.find_spec("vllm") is not None


def has_distilabel() -> bool:
    return importlib.util.find_spec("distilabel") is not None


def pytest_runtest_setup(item):
    if "integration_gpu" in item.keywords and not has_gpu_stack():
        pytest.skip("GPU stack not available: requires vLLM and CUDA")
    if "integration_real" in item.keywords and not has_distilabel():
        pytest.skip("Distilabel package not installed")
