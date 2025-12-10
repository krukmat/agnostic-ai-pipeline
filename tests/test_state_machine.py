"""
Tests for State Machine module.

Tests PipelinePhase, PipelineState, and StateMachine classes.
"""

import pytest
from pathlib import Path
import yaml
import tempfile

from scripts.orchestrator.state_machine import (
    PipelinePhase,
    PipelineState,
    StateMachine,
)


class TestPipelinePhase:
    """Test PipelinePhase enum."""

    def test_phase_values(self):
        """Test all phases exist."""
        assert PipelinePhase.INIT.value == "init"
        assert PipelinePhase.REQUIREMENTS.value == "requirements"
        assert PipelinePhase.PLANNING.value == "planning"
        assert PipelinePhase.DEVELOPMENT.value == "development"
        assert PipelinePhase.INTEGRATION.value == "integration"
        assert PipelinePhase.DONE.value == "done"
        assert PipelinePhase.FAILED.value == "failed"


class TestPipelineState:
    """Test PipelineState dataclass."""

    def test_initialization(self):
        """Test state initializes with correct defaults."""
        state = PipelineState(concept="Test API")
        assert state.concept == "Test API"
        assert state.phase == PipelinePhase.INIT
        assert state.has_requirements is False
        assert state.total_stories == 0
        assert state.stories_todo == []
        assert state.stories_done == set()

    def test_get_ready_stories_no_dependencies(self):
        """Test ready stories calculation without dependencies."""
        state = PipelineState(concept="Test")
        state.stories_todo = ["S1", "S2", "S3"]
        state.story_dependencies = {}

        ready = state.get_ready_stories()
        assert set(ready) == {"S1", "S2", "S3"}

    def test_get_ready_stories_with_dependencies(self):
        """Test ready stories calculation with dependencies."""
        state = PipelineState(concept="Test")
        state.stories_todo = ["S1", "S2", "S3"]
        state.story_dependencies = {
            "S1": [],
            "S2": ["S1"],
            "S3": ["S1"],
        }

        # Initially only S1 is ready
        ready = state.get_ready_stories()
        assert ready == ["S1"]

        # Mark S1 as done
        state.stories_done.add("S1")
        state.stories_todo.remove("S1")

        # Now S2 and S3 should be ready
        ready = state.get_ready_stories()
        assert set(ready) == {"S2", "S3"}

    def test_get_ready_stories_excludes_doing(self):
        """Test that doing stories are excluded from ready."""
        state = PipelineState(concept="Test")
        state.stories_todo = ["S1", "S2"]
        state.stories_doing = {"S1": 1}

        ready = state.get_ready_stories()
        assert ready == ["S2"]

    def test_get_blocked_stories(self):
        """Test blocked stories calculation."""
        state = PipelineState(concept="Test")
        state.stories_todo = ["S1", "S2", "S3", "S4"]
        state.story_dependencies = {
            "S1": [],
            "S2": ["S1"],
            "S3": ["S2"],
            "S4": ["S2"],
        }

        # S1 fails → S2, S3, S4 are blocked
        blocked = state.get_blocked_stories()
        assert blocked == []  # No stories marked as failed yet

        # Mark S1 as failed
        state.stories_failed["S1"] = ["ImportError"]
        blocked = state.get_blocked_stories()
        assert set(blocked) == {"S2", "S3", "S4"}


class TestStateMachine:
    """Test StateMachine class."""

    def test_initialization(self):
        """Test state machine initializes in INIT phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning_dir = Path(tmpdir)
            sm = StateMachine(concept="Test API", planning_dir=planning_dir)

            assert sm.concept == "Test API"
            assert sm.state.phase == PipelinePhase.INIT
            assert sm.state.concept == "Test API"

    def test_valid_transitions(self):
        """Test valid state transitions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning_dir = Path(tmpdir)
            sm = StateMachine(concept="Test", planning_dir=planning_dir)

            # INIT → REQUIREMENTS
            assert sm.can_transition_to(PipelinePhase.REQUIREMENTS) is True
            sm.transition_to(PipelinePhase.REQUIREMENTS, "Starting BA")
            assert sm.state.phase == PipelinePhase.REQUIREMENTS

            # REQUIREMENTS → PLANNING
            assert sm.can_transition_to(PipelinePhase.PLANNING) is True
            sm.transition_to(PipelinePhase.PLANNING, "Starting Architect")
            assert sm.state.phase == PipelinePhase.PLANNING

    def test_invalid_transitions(self):
        """Test invalid transitions raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning_dir = Path(tmpdir)
            sm = StateMachine(concept="Test", planning_dir=planning_dir)

            # Cannot go directly from INIT to PLANNING
            with pytest.raises(ValueError, match="Invalid transition"):
                sm.transition_to(PipelinePhase.PLANNING, "Invalid")

    def test_sync_artifacts_from_filesystem(self):
        """Test state syncs with filesystem artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning_dir = Path(tmpdir)
            planning_dir.mkdir(exist_ok=True)

            # Create requirements.yaml
            (planning_dir / "requirements.yaml").write_text("meta:\n  test: true\n")

            sm = StateMachine(concept="Test", planning_dir=planning_dir)
            state = sm.get_state()

            assert state.has_requirements is True
            assert state.has_stories is False

    def test_load_stories_from_yaml(self):
        """Test loading stories from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning_dir = Path(tmpdir)
            planning_dir.mkdir(exist_ok=True)

            stories = [
                {
                    "id": "S1",
                    "status": "todo",
                    "depends_on": [],
                },
                {
                    "id": "S2",
                    "status": "todo",
                    "depends_on": ["S1"],
                },
                {
                    "id": "S3",
                    "status": "done",
                    "depends_on": [],
                },
            ]
            (planning_dir / "stories.yaml").write_text(yaml.dump(stories))

            sm = StateMachine(concept="Test", planning_dir=planning_dir)
            state = sm.get_state()

            assert state.total_stories == 3
            assert set(state.stories_todo) == {"S1", "S2"}
            assert state.stories_done == {"S3"}
            assert state.story_dependencies["S2"] == ["S1"]

    def test_update_from_results_ba_success(self):
        """Test state updates when BA succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning_dir = Path(tmpdir)
            planning_dir.mkdir(exist_ok=True)

            sm = StateMachine(concept="Test", planning_dir=planning_dir)
            assert sm.state.has_requirements is False

            # Simulate BA result
            results = [
                {
                    "tool": "RUN_BA",
                    "status": "ok",
                    "elapsed": 10.5,
                }
            ]
            sm.update_from_results(results)

            # Mark artifact as created
            (planning_dir / "requirements.yaml").write_text("meta: test")
            sm._sync_state_from_filesystem()

            assert sm.state.has_requirements is True

    def test_update_from_results_dev_story_success(self):
        """Test state updates when dev story succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning_dir = Path(tmpdir)
            planning_dir.mkdir(exist_ok=True)

            sm = StateMachine(concept="Test", planning_dir=planning_dir)
            sm.state.stories_todo = ["S1", "S2"]

            # Simulate dev result
            results = [
                {
                    "tool": "RUN_DEV_STORY",
                    "status": "ok",
                    "story_id": "S1",
                    "elapsed": 120.0,
                }
            ]
            sm.update_from_results(results)

            assert "S1" not in sm.state.stories_todo
            assert "S1" in sm.state.stories_doing
            assert sm.state.stories_doing["S1"] == 1

    def test_update_from_results_dev_story_failure(self):
        """Test state updates when dev story fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning_dir = Path(tmpdir)
            planning_dir.mkdir(exist_ok=True)

            sm = StateMachine(concept="Test", planning_dir=planning_dir)
            sm.state.stories_todo = ["S1"]
            sm.state.stories_doing["S1"] = 1

            # Simulate dev failure
            results = [
                {
                    "tool": "RUN_DEV_STORY",
                    "status": "failed",
                    "story_id": "S1",
                    "error": "ImportError: module not found",
                    "elapsed": 30.0,
                }
            ]
            sm.update_from_results(results)

            assert "S1" not in sm.state.stories_doing
            assert "S1" in sm.state.stories_failed
            assert "ImportError" in sm.state.stories_failed["S1"][0]

    def test_transition_all_phases(self):
        """Test complete transition through all phases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            planning_dir = Path(tmpdir)
            sm = StateMachine(concept="Test", planning_dir=planning_dir)

            # INIT → REQUIREMENTS
            sm.transition_to(PipelinePhase.REQUIREMENTS, "BA started")
            assert sm.state.phase == PipelinePhase.REQUIREMENTS

            # REQUIREMENTS → PLANNING
            sm.transition_to(PipelinePhase.PLANNING, "Architect started")
            assert sm.state.phase == PipelinePhase.PLANNING

            # PLANNING → DEVELOPMENT
            sm.transition_to(PipelinePhase.DEVELOPMENT, "Dev started")
            assert sm.state.phase == PipelinePhase.DEVELOPMENT

            # DEVELOPMENT → INTEGRATION
            sm.transition_to(PipelinePhase.INTEGRATION, "QA started")
            assert sm.state.phase == PipelinePhase.INTEGRATION

            # INTEGRATION → DONE
            sm.transition_to(PipelinePhase.DONE, "Pipeline complete")
            assert sm.state.phase == PipelinePhase.DONE
