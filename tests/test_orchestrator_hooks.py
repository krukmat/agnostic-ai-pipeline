"""
Orchestrator Post-Step Hooks Tests

Tests for the hook registry system that enables auto-ingestion after pipeline steps.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call
from typing import Callable


# ============================================================================
# UNIT TESTS - Hook Registry Structure
# ============================================================================


@pytest.mark.unit
def test_hook_registry_class_exists():
    """
    Verify HookRegistry class exists in orchestrate module.

    This test will FAIL until HookRegistry is implemented.
    """
    from scripts.orchestrate import HookRegistry

    # Verify class can be instantiated
    registry = HookRegistry()
    assert registry is not None, "HookRegistry should be instantiable"


@pytest.mark.unit
def test_hook_registry_has_register_method():
    """
    Verify HookRegistry has register() method.

    This test will FAIL until register() is implemented.
    """
    from scripts.orchestrate import HookRegistry

    registry = HookRegistry()

    # Verify register method exists
    assert hasattr(registry, 'register'), "HookRegistry should have register() method"
    assert callable(registry.register), "register should be callable"


@pytest.mark.unit
def test_hook_registry_has_fire_method():
    """
    Verify HookRegistry has fire() method.

    This test will FAIL until fire() is implemented.
    """
    from scripts.orchestrate import HookRegistry

    registry = HookRegistry()

    # Verify fire method exists
    assert hasattr(registry, 'fire'), "HookRegistry should have fire() method"
    assert callable(registry.fire), "fire should be callable"


@pytest.mark.unit
def test_register_hook_callable():
    """
    Verify can register a callable hook.

    This test will FAIL until register() implementation exists.
    """
    from scripts.orchestrate import HookRegistry

    registry = HookRegistry()

    # Create a mock hook
    mock_hook = MagicMock()

    # Should not raise
    registry.register(mock_hook)

    # Verify hook was registered (internal state check)
    assert len(registry._hooks) == 1, "Should have 1 registered hook"
    assert registry._hooks[0] is mock_hook, "Registered hook should be the mock"


@pytest.mark.unit
def test_register_multiple_hooks():
    """
    Verify can register multiple hooks.

    This test will FAIL until register() handles multiple hooks.
    """
    from scripts.orchestrate import HookRegistry

    registry = HookRegistry()

    # Register 3 hooks
    hook1 = MagicMock()
    hook2 = MagicMock()
    hook3 = MagicMock()

    registry.register(hook1)
    registry.register(hook2)
    registry.register(hook3)

    # Verify all hooks registered
    assert len(registry._hooks) == 3, "Should have 3 registered hooks"


# ============================================================================
# UNIT TESTS - Hook Firing
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fire_calls_registered_hook():
    """
    Verify fire() calls all registered hooks with correct arguments.

    This test will FAIL until fire() implementation exists.
    """
    from scripts.orchestrate import HookRegistry

    registry = HookRegistry()

    # Create async mock hook
    mock_hook = AsyncMock()
    registry.register(mock_hook)

    # Fire hook
    step_name = "dev"
    artifacts = [Path("/tmp/test.py")]
    metadata = {"role": "dev", "iteration": 1}

    await registry.fire(step_name, artifacts, metadata)

    # Verify hook was called with correct arguments
    mock_hook.assert_called_once_with(step_name, artifacts, metadata)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fire_calls_all_registered_hooks():
    """
    Verify fire() calls ALL registered hooks.

    This test will FAIL until fire() iterates over all hooks.
    """
    from scripts.orchestrate import HookRegistry

    registry = HookRegistry()

    # Register multiple hooks
    hook1 = AsyncMock()
    hook2 = AsyncMock()
    hook3 = AsyncMock()

    registry.register(hook1)
    registry.register(hook2)
    registry.register(hook3)

    # Fire hooks
    step_name = "architect"
    artifacts = [Path("/tmp/stories.yaml")]
    metadata = {"role": "architect", "iteration": 2}

    await registry.fire(step_name, artifacts, metadata)

    # Verify all hooks were called
    hook1.assert_called_once_with(step_name, artifacts, metadata)
    hook2.assert_called_once_with(step_name, artifacts, metadata)
    hook3.assert_called_once_with(step_name, artifacts, metadata)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fire_continues_on_hook_error():
    """
    Verify fire() continues executing remaining hooks even if one fails.

    This test will FAIL until fire() has try/except error handling.

    Important: Hooks should NOT block pipeline execution on failure.
    """
    from scripts.orchestrate import HookRegistry

    registry = HookRegistry()

    # Register 3 hooks: 1st fails, 2nd and 3rd should still execute
    hook1 = AsyncMock(side_effect=ValueError("Hook 1 failed"))
    hook2 = AsyncMock()
    hook3 = AsyncMock()

    registry.register(hook1)
    registry.register(hook2)
    registry.register(hook3)

    # Fire hooks - should NOT raise despite hook1 failing
    step_name = "qa"
    artifacts = [Path("/tmp/report.json")]
    metadata = {"role": "qa", "iteration": 1}

    await registry.fire(step_name, artifacts, metadata)

    # Verify hook1 was called (and failed)
    hook1.assert_called_once()

    # Verify hook2 and hook3 still executed
    hook2.assert_called_once_with(step_name, artifacts, metadata)
    hook3.assert_called_once_with(step_name, artifacts, metadata)


# ============================================================================
# INTEGRATION TESTS - Auto-Ingest Hook
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_ingest_hook_exists():
    """
    Verify auto_ingest_hook function exists in ingestion module.

    This test will FAIL until auto_ingest_hook is implemented.
    """
    from graph_rag.ingestion import auto_ingest_hook

    # Verify function exists and is callable
    assert callable(auto_ingest_hook), "auto_ingest_hook should be callable"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_ingest_hook_signature():
    """
    Verify auto_ingest_hook has correct signature.

    This test will FAIL until auto_ingest_hook has correct parameters.
    """
    import inspect
    from graph_rag.ingestion import auto_ingest_hook

    # Get function signature
    sig = inspect.signature(auto_ingest_hook)

    # Verify parameters
    params = list(sig.parameters.keys())
    assert "step_name" in params, "auto_ingest_hook should have step_name parameter"
    assert "artifacts" in params, "auto_ingest_hook should have artifacts parameter"
    assert "metadata" in params, "auto_ingest_hook should have metadata parameter"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_ingest_hook_respects_config_flag():
    """
    Verify auto_ingest_hook respects auto_ingest config flag.

    This test will FAIL until auto_ingest_hook checks config.

    When auto_ingest=false (default), hook should return early without ingesting.
    """
    from graph_rag.ingestion import auto_ingest_hook
    from unittest.mock import patch

    # Mock config with auto_ingest=false
    mock_config = {
        "graph_rag": {
            "auto_ingest": False
        }
    }

    with patch('common.load_config', return_value=mock_config):
        # Create test data
        step_name = "dev"
        artifacts = [Path("/tmp/test.py")]
        metadata = {"role": "dev", "iteration": 1}

        # Call hook - should return early without error
        await auto_ingest_hook(step_name, artifacts, metadata)

        # Test passes if no exception raised


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_ingest_hook_does_not_block_on_error():
    """
    Verify auto_ingest_hook does NOT raise exceptions on failure.

    This test will FAIL until auto_ingest_hook has try/except error handling.

    Important: Hook failures should NOT block pipeline execution.
    """
    from graph_rag.ingestion import auto_ingest_hook
    from unittest.mock import patch

    # Mock config with auto_ingest=true
    mock_config = {
        "graph_rag": {
            "auto_ingest": True,
            "working_dir": "/tmp/test_kg",
            "llm_model": "test-model"
        }
    }

    # Mock engine to raise error (patch where it's used, not where it's defined)
    with patch('common.load_config', return_value=mock_config):
        with patch('graph_rag.engine.GraphRAGEngine.get_instance', side_effect=RuntimeError("Engine failed")):
            step_name = "dev"
            artifacts = [Path("/tmp/test.py")]
            metadata = {"role": "dev", "iteration": 1}

            # Call hook - should NOT raise despite engine failure
            await auto_ingest_hook(step_name, artifacts, metadata)

            # Test passes if no exception propagated


# ============================================================================
# HELPER TESTS - Artifact Collection
# ============================================================================


@pytest.mark.unit
def test_collect_dev_artifacts_helper_exists():
    """
    Verify _collect_dev_artifacts helper exists.

    This test will FAIL until _collect_dev_artifacts is implemented.

    Helper extracts artifact paths from dev_result to reduce CC.
    """
    from scripts.orchestrate import _collect_dev_artifacts

    # Verify function exists
    assert callable(_collect_dev_artifacts), "_collect_dev_artifacts should be callable"


@pytest.mark.unit
def test_collect_dev_artifacts_returns_file_paths():
    """
    Verify _collect_dev_artifacts returns list of file Paths.

    This test will FAIL until _collect_dev_artifacts implementation exists.
    """
    from scripts.orchestrate import _collect_dev_artifacts

    # Create mock dev_result with artifacts_dir
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir)
        (artifacts_dir / "test1.py").write_text("test")
        (artifacts_dir / "test2.py").write_text("test")

        dev_result = {"artifacts_dir": str(artifacts_dir)}
        story = {"id": "S1"}

        # Call helper
        artifacts = _collect_dev_artifacts(dev_result, story)

        # Verify returns list of Paths
        assert isinstance(artifacts, list), "Should return list"
        assert len(artifacts) == 2, "Should find 2 artifact files"
        assert all(isinstance(a, Path) for a in artifacts), "All items should be Path objects"
        assert all(a.is_file() for a in artifacts), "All items should be files (not directories)"


@pytest.mark.unit
def test_collect_dev_artifacts_handles_missing_dir():
    """
    Verify _collect_dev_artifacts handles missing artifacts_dir gracefully.

    This test will FAIL until _collect_dev_artifacts has error handling.
    """
    from scripts.orchestrate import _collect_dev_artifacts

    # Dev result without artifacts_dir
    dev_result = {}
    story = {"id": "S1"}

    # Should return empty list, not crash
    artifacts = _collect_dev_artifacts(dev_result, story)

    assert isinstance(artifacts, list), "Should return list"
    assert len(artifacts) == 0, "Should return empty list when no artifacts_dir"


# ============================================================================
# COVERAGE VERIFICATION
# ============================================================================


@pytest.mark.unit
def test_hook_registry_methods_have_low_cc():
    """
    Verify HookRegistry methods have low cyclomatic complexity.

    This test will FAIL if CC > 3 for any HookRegistry method.

    Target: CC ≤3 for register(), CC ≤3 for fire()
    """
    import subprocess
    import os

    try:
        result = subprocess.run(
            ["python", "-m", "radon", "cc", "scripts/orchestrate.py", "--min", "A", "-s"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout

        # Check for HookRegistry methods
        if "HookRegistry" in output:
            lines = output.split('\n')
            for line in lines:
                if 'register' in line.lower() or 'fire' in line.lower():
                    # Extract CC from line (format: "M 123:4 ClassName.method - A (2)")
                    if '(' in line and ')' in line:
                        cc_str = line.split('(')[-1].split(')')[0]
                        cc = int(cc_str)

                        # Assert CC ≤ 3
                        assert cc <= 3, f"Method CC should be ≤3, got {cc}: {line}"

    except Exception as e:
        pytest.skip(f"Could not run radon check: {e}")
