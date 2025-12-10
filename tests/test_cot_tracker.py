"""Tests for Layer 6: CoT Tracker (Chain of Thought Tracker)

TDD approach - tests written first, implementation follows.
No mocks - uses real file I/O and actual data structures.
"""
import json
import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from scripts.orchestrator.cot_tracker import ThoughtEntry, ChainOfThoughtTracker


# ==============================================================================
# TEST SUITE 1: ThoughtEntry Dataclass
# ==============================================================================

class TestThoughtEntry:
    """Test ThoughtEntry dataclass creation and validation."""

    def test_thought_entry_creation(self):
        """Create a ThoughtEntry with all required fields."""
        entry = ThoughtEntry(
            timestamp="2025-12-10T14:30:45Z",
            phase="PLANNING",
            layer="state_machine",
            kind="transition",
            message="State transition from REQUIREMENTS to PLANNING",
            details={"from": "REQUIREMENTS", "to": "PLANNING"},
            inputs={"concept": "test"},
            reasoning_steps=["check", "validate"],
            output="PLANNING",
            confidence=1.0
        )

        assert entry.timestamp == "2025-12-10T14:30:45Z"
        assert entry.phase == "PLANNING"
        assert entry.layer == "state_machine"
        assert entry.kind == "transition"
        assert entry.confidence == 1.0

    def test_thought_entry_with_llm_confidence(self):
        """Create entry with LLM confidence score (<1.0)."""
        entry = ThoughtEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            phase="PLANNING",
            layer="llm",
            kind="decision",
            message="LLM decision for escalation",
            details={"model": "claude-opus"},
            inputs={"prompt": "escalate?"},
            reasoning_steps=["analyze", "decide"],
            output={"action": "escalate"},
            confidence=0.87
        )

        assert entry.layer == "llm"
        assert entry.confidence == 0.87
        assert entry.confidence < 1.0


# ==============================================================================
# TEST SUITE 2: ChainOfThoughtTracker Initialization
# ==============================================================================

class TestCoTTrackerInitialization:
    """Test tracker initialization and directory setup."""

    def test_tracker_init_creates_directories(self):
        """Initialize tracker and verify output directories created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            assert tracker.output_dir == Path(tmpdir)
            assert Path(tmpdir).exists()
            assert len(tracker.thoughts) == 0

    def test_tracker_init_without_output_dir(self):
        """Initialize tracker with default output dir."""
        tracker = ChainOfThoughtTracker()

        assert tracker.output_dir is not None
        assert len(tracker.thoughts) == 0


# ==============================================================================
# TEST SUITE 3: Logging Methods
# ==============================================================================

class TestLoggingMethods:
    """Test all logging methods for correctness."""

    @pytest.fixture
    def tracker(self):
        """Provide tracker instance for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ChainOfThoughtTracker(output_dir=Path(tmpdir))

    def test_log_state_transition(self, tracker):
        """Log state machine transition."""
        tracker.log_state_transition(
            from_phase="INIT",
            to_phase="REQUIREMENTS",
            reason="concept_received"
        )

        assert len(tracker.thoughts) == 1
        thought = tracker.thoughts[0]
        assert thought.kind == "transition"
        assert thought.layer == "state_machine"
        assert thought.phase == "REQUIREMENTS"
        assert "INIT" in thought.details["from_phase"]
        assert "REQUIREMENTS" in thought.details["to_phase"]

    def test_log_dag_decision(self, tracker):
        """Log DAG batch selection decision."""
        tracker.log_dag_decision(
            ready_stories=["S1", "S2", "S3"],
            batch=["S1", "S3"],
            reason="dependency_order"
        )

        assert len(tracker.thoughts) == 1
        thought = tracker.thoughts[0]
        assert thought.kind == "decision"
        assert thought.layer == "dag"
        assert thought.output == ["S1", "S3"]
        assert thought.details["reason"] == "dependency_order"

    def test_log_policy_evaluation(self, tracker):
        """Log policy engine evaluation."""
        tracker.log_policy_evaluation(
            policy_name="max_retries_policy",
            condition="retries >= 3",
            matched=True,
            context={"current_retries": 3, "max": 3}
        )

        assert len(tracker.thoughts) == 1
        thought = tracker.thoughts[0]
        assert thought.kind == "policy_eval"
        assert thought.layer == "policy"
        assert thought.output is True

    def test_log_llm_decision(self, tracker):
        """Log LLM call and response."""
        tracker.log_llm_decision(
            prompt="Should we escalate this story?",
            response="Yes, due to repeated failures",
            parsed={"action": "escalate", "confidence": 0.92}
        )

        assert len(tracker.thoughts) == 1
        thought = tracker.thoughts[0]
        assert thought.kind == "llm_call"
        assert thought.layer == "llm"
        assert thought.confidence < 1.0  # LLM decisions always < 1.0
        assert thought.output["confidence"] == 0.92

    def test_log_escalation_decision(self, tracker):
        """Log escalation decision."""
        tracker.log_escalation_decision(
            story_id="S1",
            action="escalate_to_architect",
            reason="repeated_failures"
        )

        assert len(tracker.thoughts) == 1
        thought = tracker.thoughts[0]
        assert thought.kind == "escalation"
        assert thought.output == "escalate_to_architect"
        assert thought.details["story_id"] == "S1"

    def test_log_planner_decision(self, tracker):
        """Log planner decision with alternatives."""
        tracker.log_planner_decision(
            decision_type="action_selection",
            alternatives=["A1", "A2", "A3"],
            chosen="A2",
            confidence=0.85
        )

        assert len(tracker.thoughts) == 1
        thought = tracker.thoughts[0]
        assert thought.kind == "decision"
        assert thought.layer == "planner"
        assert thought.output == "A2"
        assert thought.confidence == 0.85
        assert len(thought.inputs["alternatives"]) == 3


# ==============================================================================
# TEST SUITE 4: JSONL Export
# ==============================================================================

class TestExportJsonl:
    """Test JSONL export format and validity."""

    def test_export_jsonl_format(self):
        """Export to JSONL and verify format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            # Add 3 thoughts
            tracker.log_state_transition("INIT", "REQUIREMENTS", "start")
            tracker.log_dag_decision(["S1", "S2"], ["S1"], "batch")
            tracker.log_policy_evaluation("max_retries", "x >= 3", True, {})

            # Export
            export_path = Path(tmpdir) / "test.jsonl"
            tracker.export_jsonl(export_path)

            # Verify file exists and has 3 lines
            assert export_path.exists()
            lines = export_path.read_text().strip().split("\n")
            assert len(lines) == 3

            # Verify each line is valid JSON
            for line in lines:
                data = json.loads(line)
                assert "timestamp" in data
                assert "phase" in data
                assert "layer" in data
                assert "kind" in data

    def test_export_jsonl_fields(self):
        """Verify all fields in JSONL export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))
            tracker.log_planner_decision(
                "test",
                ["A", "B"],
                "A",
                0.9
            )

            export_path = Path(tmpdir) / "export.jsonl"
            tracker.export_jsonl(export_path)

            line = export_path.read_text().strip()
            data = json.loads(line)

            assert data["phase"] == "DEVELOPMENT"
            assert data["layer"] == "planner"
            assert data["kind"] == "decision"
            assert data["message"]
            assert data["details"]
            assert data["inputs"]
            assert data["reasoning_steps"]
            assert data["output"] == "A"
            assert data["confidence"] == 0.9


# ==============================================================================
# TEST SUITE 5: Markdown Export
# ==============================================================================

class TestExportMarkdown:
    """Test Markdown export format and readability."""

    def test_export_markdown_creates_file(self):
        """Export to Markdown and verify file created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            tracker.log_state_transition("INIT", "REQUIREMENTS", "start")
            tracker.log_dag_decision(["S1", "S2"], ["S1"], "batch")

            export_path = Path(tmpdir) / "reasoning.md"
            tracker.export_markdown(export_path)

            assert export_path.exists()
            content = export_path.read_text()
            assert len(content) > 0
            assert "Chain of Thought Report" in content or "Reasoning" in content

    def test_export_markdown_contains_phases(self):
        """Markdown export groups by phases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            # Simulate different phases
            tracker.log_state_transition("INIT", "REQUIREMENTS", "start")
            tracker.phase = "PLANNING"
            tracker.log_dag_decision(["S1"], ["S1"], "batch")
            tracker.phase = "DEVELOPMENT"
            tracker.log_policy_evaluation("policy", "cond", True, {})

            export_path = Path(tmpdir) / "reasoning.md"
            tracker.export_markdown(export_path)

            content = export_path.read_text()
            # Should contain phase headers
            assert "REQUIREMENTS" in content or "PLANNING" in content

    def test_export_markdown_readable_format(self):
        """Markdown export is human-readable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            tracker.log_state_transition("A", "B", "reason")

            export_path = Path(tmpdir) / "reasoning.md"
            tracker.export_markdown(export_path)

            content = export_path.read_text()
            # Should have markdown elements
            assert "#" in content  # Headers
            assert "timestamp" in content.lower() or "time" in content.lower()


# ==============================================================================
# TEST SUITE 6: Statistics Methods
# ==============================================================================

class TestStatisticsMethods:
    """Test statistics and aggregation methods."""

    def test_get_thought_count(self):
        """Get total number of thoughts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            assert tracker.get_thought_count() == 0

            tracker.log_state_transition("A", "B", "test")
            assert tracker.get_thought_count() == 1

            tracker.log_dag_decision([], [], "test")
            assert tracker.get_thought_count() == 2

    def test_get_thoughts_by_layer(self):
        """Get thought count grouped by layer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            # Add thoughts from different layers
            tracker.log_state_transition("A", "B", "test")  # state_machine
            tracker.log_dag_decision([], [], "test")         # dag
            tracker.log_policy_evaluation("p", "c", True, {})  # policy
            tracker.log_policy_evaluation("p", "c", True, {})  # policy

            by_layer = tracker.get_thoughts_by_layer()

            assert by_layer["state_machine"] == 1
            assert by_layer["dag"] == 1
            assert by_layer["policy"] == 2

    def test_get_thoughts_by_phase(self):
        """Get thoughts grouped by phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            tracker.log_state_transition("INIT", "REQUIREMENTS", "test")

            by_phase = tracker.get_thoughts_by_phase()

            assert "REQUIREMENTS" in by_phase
            assert isinstance(by_phase["REQUIREMENTS"], list)

    def test_statistics_with_empty_tracker(self):
        """Statistics work with empty tracker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            assert tracker.get_thought_count() == 0
            assert len(tracker.get_thoughts_by_layer()) == 0
            assert len(tracker.get_thoughts_by_phase()) == 0


# ==============================================================================
# TEST SUITE 7: Integration Tests
# ==============================================================================

class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_workflow_with_exports(self):
        """Complete workflow: log, export JSONL, export Markdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            # Log various thoughts
            tracker.log_state_transition("INIT", "REQUIREMENTS", "start")
            tracker.log_dag_decision(["S1", "S2"], ["S1"], "batch")
            tracker.log_policy_evaluation("policy", "cond", True, {})
            tracker.log_escalation_decision("S1", "escalate", "failure")

            # Export both formats
            jsonl_path = Path(tmpdir) / "thoughts.jsonl"
            md_path = Path(tmpdir) / "reasoning.md"

            tracker.export_jsonl(jsonl_path)
            tracker.export_markdown(md_path)

            # Verify both files exist and have content
            assert jsonl_path.exists()
            assert md_path.exists()
            assert len(jsonl_path.read_text()) > 0
            assert len(md_path.read_text()) > 0

            # Verify thought count
            assert tracker.get_thought_count() == 4

    def test_statistics_accuracy(self):
        """Statistics methods return accurate counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            # Add 10 thoughts with specific distribution
            for _ in range(3):
                tracker.log_state_transition("A", "B", "test")
            for _ in range(4):
                tracker.log_dag_decision([], [], "test")
            for _ in range(3):
                tracker.log_policy_evaluation("p", "c", True, {})

            # Verify total
            assert tracker.get_thought_count() == 10

            # Verify by layer
            by_layer = tracker.get_thoughts_by_layer()
            assert sum(by_layer.values()) == 10
            assert by_layer["state_machine"] == 3
            assert by_layer["dag"] == 4
            assert by_layer["policy"] == 3

    def test_multithread_safety_sequential(self):
        """Tracker handles sequential calls correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ChainOfThoughtTracker(output_dir=Path(tmpdir))

            # Simulate rapid-fire logging (like in real orchestration)
            for i in range(20):
                if i % 3 == 0:
                    tracker.log_state_transition(f"P{i}", f"P{i+1}", f"test{i}")
                elif i % 3 == 1:
                    tracker.log_dag_decision([], [], f"test{i}")
                else:
                    tracker.log_policy_evaluation(f"policy{i}", "cond", True, {})

            assert tracker.get_thought_count() == 20
            assert len(tracker.get_thoughts_by_layer()) == 3
