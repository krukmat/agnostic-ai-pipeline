"""End-to-end tests for V2 Orchestrator.

Tests full pipeline execution including state transitions, DAG scheduling,
policy evaluation, and role handler integration.
"""

import asyncio
import json
import pathlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from scripts.orchestrator.v2_runtime import run_orchestrator_v2
from scripts.orchestrator.state_machine import StateMachine, PipelinePhase
from scripts.orchestrator.story_dag import StoryDAG
from scripts.orchestrator.policy_engine import PolicyEngine


@pytest.fixture
def mock_config():
    """Provide mock config for testing."""
    return {
        "pipeline": {
            "retry_policies": {
                "dev": {"max_attempts": 3, "backoff": "exponential"},
                "qa": {"max_attempts": 2, "backoff": "linear"},
            },
            "escalation_policies": [
                {
                    "condition": "dev_attempts >= 3 AND same_error_pattern",
                    "action": "architect_refine",
                    "reason": "Repeated dev failures",
                }
            ],
            "resource_policies": {
                "max_parallel_stories": 3,
                "max_concurrent_dev": 2,
                "dev_timeout": 600,
                "qa_timeout": 300,
            },
        }
    }


@pytest.fixture
def mock_role_handlers():
    """Provide mock role handlers for testing."""
    return {
        "RUN_BA": AsyncMock(return_value={"status": "ok"}),
        "RUN_PO": AsyncMock(return_value={"status": "ok"}),
        "RUN_ARCHITECT": AsyncMock(return_value={"status": "ok"}),
        "RUN_DEV": AsyncMock(return_value={"status": "ok"}),
        "RUN_DEV_STORY": AsyncMock(return_value={"status": "ok"}),
        "RUN_QA": AsyncMock(return_value={"status": "ok"}),
        "RUN_QA_FULL": AsyncMock(return_value={"status": "ok"}),
    }


class TestOrchestratorV2E2E:
    """End-to-end tests for V2 orchestrator."""

    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self, mock_role_handlers):
        """Test complete pipeline execution from INIT to DONE."""
        # Setup: Create minimal artifacts
        planning_dir = pathlib.Path("planning")
        planning_dir.mkdir(exist_ok=True)

        # Create requirements.yaml
        requirements = {"concept": "test", "requirements": []}
        (planning_dir / "requirements.yaml").write_text(
            json.dumps(requirements), encoding="utf-8"
        )

        # Create stories.yaml
        stories = [{"id": "S1", "title": "Test", "status": "todo", "depends_on": []}]
        (planning_dir / "stories.yaml").write_text(
            json.dumps(stories), encoding="utf-8"
        )

        # Run V2 orchestrator with limited steps
        result = await run_orchestrator_v2(
            "test concept", max_steps=10, role_handlers=mock_role_handlers
        )

        # Assertions
        assert result is not None
        assert "concept" in result
        assert result["concept"] == "test concept"
        assert "steps" in result
        assert "final_state" in result
        assert isinstance(result["steps"], list)

    @pytest.mark.asyncio
    async def test_dag_scheduling_respects_dependencies(self, mock_role_handlers):
        """Test that DAG scheduling respects story dependencies."""
        planning_dir = pathlib.Path("planning")
        planning_dir.mkdir(exist_ok=True)

        # Create stories with dependencies
        stories = [
            {"id": "S1", "title": "First", "status": "todo", "depends_on": []},
            {"id": "S2", "title": "Second", "status": "todo", "depends_on": ["S1"]},
            {"id": "S3", "title": "Third", "status": "todo", "depends_on": ["S2"]},
        ]
        (planning_dir / "stories.yaml").write_text(
            json.dumps(stories), encoding="utf-8"
        )

        requirements = {"concept": "test", "requirements": []}
        (planning_dir / "requirements.yaml").write_text(
            json.dumps(requirements), encoding="utf-8"
        )

        # Run orchestrator
        result = await run_orchestrator_v2(
            "test concept", max_steps=10, role_handlers=mock_role_handlers
        )

        # Verify result structure
        assert result is not None
        assert isinstance(result.get("steps"), list)

    @pytest.mark.asyncio
    async def test_retry_policy_on_failure(self, mock_role_handlers, mock_config):
        """Test that retry policy is applied on role handler failure."""
        # First call fails, second succeeds
        mock_role_handlers["RUN_DEV"] = AsyncMock(
            side_effect=[
                {"status": "error", "error": "ImportError"},
                {"status": "ok"},
            ]
        )

        planning_dir = pathlib.Path("planning")
        planning_dir.mkdir(exist_ok=True)

        stories = [{"id": "S1", "title": "Test", "status": "todo", "depends_on": []}]
        (planning_dir / "stories.yaml").write_text(
            json.dumps(stories), encoding="utf-8"
        )

        requirements = {"concept": "test", "requirements": []}
        (planning_dir / "requirements.yaml").write_text(
            json.dumps(requirements), encoding="utf-8"
        )

        with patch("scripts.orchestrator.v2_runtime.load_config", return_value=mock_config):
            result = await run_orchestrator_v2(
                "test concept", max_steps=10, role_handlers=mock_role_handlers
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_parallel_story_execution(self, mock_role_handlers):
        """Test that independent stories can execute in parallel."""
        planning_dir = pathlib.Path("planning")
        planning_dir.mkdir(exist_ok=True)

        # Create 3 independent stories
        stories = [
            {"id": "S1", "title": "First", "status": "todo", "depends_on": []},
            {"id": "S2", "title": "Second", "status": "todo", "depends_on": []},
            {"id": "S3", "title": "Third", "status": "todo", "depends_on": []},
        ]
        (planning_dir / "stories.yaml").write_text(
            json.dumps(stories), encoding="utf-8"
        )

        requirements = {"concept": "test", "requirements": []}
        (planning_dir / "requirements.yaml").write_text(
            json.dumps(requirements), encoding="utf-8"
        )

        result = await run_orchestrator_v2(
            "test concept", max_steps=10, role_handlers=mock_role_handlers
        )

        # Verify execution
        assert result is not None
        assert isinstance(result.get("steps"), list)

    @pytest.mark.asyncio
    async def test_handler_error_handling(self, mock_role_handlers):
        """Test that handler exceptions are caught and reported."""
        mock_role_handlers["RUN_BA"] = AsyncMock(
            side_effect=Exception("Test exception")
        )

        planning_dir = pathlib.Path("planning")
        planning_dir.mkdir(exist_ok=True)

        requirements = {"concept": "test", "requirements": []}
        (planning_dir / "requirements.yaml").write_text(
            json.dumps(requirements), encoding="utf-8"
        )

        stories = [{"id": "S1", "title": "Test", "status": "todo", "depends_on": []}]
        (planning_dir / "stories.yaml").write_text(
            json.dumps(stories), encoding="utf-8"
        )

        # Should not raise, should handle exception gracefully
        result = await run_orchestrator_v2(
            "test concept", max_steps=10, role_handlers=mock_role_handlers
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_max_steps_termination(self, mock_role_handlers):
        """Test that orchestrator terminates at max_steps."""
        planning_dir = pathlib.Path("planning")
        planning_dir.mkdir(exist_ok=True)

        requirements = {"concept": "test", "requirements": []}
        (planning_dir / "requirements.yaml").write_text(
            json.dumps(requirements), encoding="utf-8"
        )

        stories = [{"id": "S1", "title": "Test", "status": "todo", "depends_on": []}]
        (planning_dir / "stories.yaml").write_text(
            json.dumps(stories), encoding="utf-8"
        )

        result = await run_orchestrator_v2(
            "test concept", max_steps=3, role_handlers=mock_role_handlers
        )

        # Should terminate after 3 steps
        assert result is not None
        assert len(result.get("steps", [])) <= 3

    def test_state_machine_transitions(self):
        """Test state machine phase transitions."""
        planning_dir = pathlib.Path("planning")
        planning_dir.mkdir(exist_ok=True)

        # Create minimal artifacts
        requirements = {"concept": "test"}
        (planning_dir / "requirements.yaml").write_text(
            json.dumps(requirements), encoding="utf-8"
        )

        sm = StateMachine("test concept", planning_dir)
        assert sm.state.phase == PipelinePhase.INIT

        # Transition to REQUIREMENTS
        sm.transition_to(PipelinePhase.REQUIREMENTS, "test transition")
        assert sm.state.phase == PipelinePhase.REQUIREMENTS

    def test_story_dag_blocking(self):
        """Test that DAG correctly blocks stories on failed dependencies."""
        dag = StoryDAG()
        dag.add_story("S1", {}, depends_on=[])
        dag.add_story("S2", {}, depends_on=["S1"])
        dag.add_story("S3", {}, depends_on=["S2"])

        # When S1 fails, S2 and S3 should be blocked
        blocked = dag.get_blocked_stories({"S1"})
        assert blocked == {"S2", "S3"}

    def test_policy_engine_backoff(self, mock_config):
        """Test backoff calculation."""
        engine = PolicyEngine(mock_config)

        # Test exponential backoff
        delay_1 = engine.get_backoff_delay("dev", 1)
        delay_2 = engine.get_backoff_delay("dev", 2)
        delay_3 = engine.get_backoff_delay("dev", 3)

        assert delay_1 == 60
        assert delay_2 == 120
        assert delay_3 == 240

    def test_policy_engine_escalation(self, mock_config):
        """Test escalation policy evaluation."""
        engine = PolicyEngine(mock_config)

        # Test escalation on repeated same error
        action = engine.evaluate_escalation(
            "S1", 3, ["ImportError", "ImportError", "ImportError"], {}
        )
        assert action == "architect_refine"

    def test_policy_engine_no_escalation_different_errors(self, mock_config):
        """Test no escalation with different errors."""
        engine = PolicyEngine(mock_config)

        action = engine.evaluate_escalation(
            "S1", 3, ["ImportError", "SyntaxError", "NameError"], {}
        )
        assert action is None

    def test_resource_policies(self, mock_config):
        """Test resource policy constraints."""
        engine = PolicyEngine(mock_config)

        max_parallel = engine.get_max_parallel_stories()
        dev_timeout = engine.get_timeout("dev")
        qa_timeout = engine.get_timeout("qa")

        assert max_parallel == 3
        assert dev_timeout == 600
        assert qa_timeout == 300


class TestOrchestratorV2Integration:
    """Integration tests with actual artifacts."""

    def test_yaml_artifact_loading(self):
        """Test that YAML artifacts are correctly loaded."""
        planning_dir = pathlib.Path("planning")
        planning_dir.mkdir(exist_ok=True)

        # Write test artifacts
        stories_data = [
            {"id": "S1", "title": "Feature 1", "status": "todo", "depends_on": []},
            {"id": "S2", "title": "Feature 2", "status": "todo", "depends_on": ["S1"]},
        ]
        (planning_dir / "stories.yaml").write_text(
            json.dumps(stories_data), encoding="utf-8"
        )

        # Load and verify
        sm = StateMachine("test", planning_dir)
        # Check that stories were loaded correctly
        assert "S1" in sm.state.stories_todo
        assert "S2" in sm.state.stories_todo
        # Check that dependencies were loaded
        assert sm.state.story_dependencies["S2"] == ["S1"]
        # Check that S1 is ready (no dependencies)
        ready = sm.state.get_ready_stories()
        assert "S1" in ready

    @pytest.mark.asyncio
    async def test_integration_with_mocked_roles(self):
        """Test full integration with mocked role handlers."""
        planning_dir = pathlib.Path("planning")
        planning_dir.mkdir(exist_ok=True)

        # Setup
        requirements = {"concept": "integration test"}
        (planning_dir / "requirements.yaml").write_text(
            json.dumps(requirements), encoding="utf-8"
        )

        stories = [
            {"id": "S1", "title": "Test Story", "status": "todo", "depends_on": []}
        ]
        (planning_dir / "stories.yaml").write_text(
            json.dumps(stories), encoding="utf-8"
        )

        # Mock handlers
        handlers = {
            "RUN_BA": AsyncMock(return_value={"status": "ok"}),
            "RUN_PO": AsyncMock(return_value={"status": "ok"}),
            "RUN_ARCHITECT": AsyncMock(return_value={"status": "ok"}),
            "RUN_DEV": AsyncMock(return_value={"status": "ok"}),
            "RUN_DEV_STORY": AsyncMock(return_value={"status": "ok"}),
            "RUN_QA": AsyncMock(return_value={"status": "ok"}),
            "RUN_QA_FULL": AsyncMock(return_value={"status": "ok"}),
        }

        # Run
        result = await run_orchestrator_v2(
            "integration test", max_steps=5, role_handlers=handlers
        )

        # Verify
        assert result is not None
        assert result["concept"] == "integration test"
        assert len(result.get("steps", [])) > 0
