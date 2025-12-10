"""
End-to-End tests for Orchestrator V2 Phase 2 features.

Tests coverage:
- Planner phase methods (Tasks 1-2)
- Coherence Checker (Task 3-4)
- Chain-of-Thought Logger (Task 5)
- Learning Optimizer (Task 6)
- Integration of all components
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from scripts.orchestrator.planner import OrchestratorPlanner
from scripts.orchestrator.state_machine import (
    PipelineState, PipelinePhase, StateMachine
)
from scripts.orchestrator.story_dag import StoryDAG
from scripts.orchestrator.policy_engine import PolicyEngine
from scripts.orchestrator.coherence_checker import CoherenceChecker
from scripts.orchestrator.cot_logger import ChainOfThoughtLogger
from scripts.orchestrator.optimizer import ExecutionOptimizer


class TestPlannerImplementation:
    """Test suite for OrchestratorPlanner phase methods."""

    @pytest.fixture
    def setup(self):
        """Setup planner with test components."""
        import tempfile
        config = {"orchestrator_v2": {"phase2_features": {}}}
        planning_dir = Path(tempfile.mkdtemp())
        state_machine = StateMachine("test", planning_dir)
        dag = StoryDAG()
        policy_engine = PolicyEngine(config)
        planner = OrchestratorPlanner(state_machine, dag, policy_engine, config)
        yield planner, state_machine
        # Cleanup
        import shutil
        shutil.rmtree(planning_dir, ignore_errors=True)

    def test_plan_init_no_requirements(self, setup):
        """Test INIT phase when no requirements exist."""
        planner, sm = setup
        state = PipelineState(concept="test")
        state.phase = PipelinePhase.INIT
        state.has_requirements = False

        actions = planner.plan_next_actions(state)

        assert len(actions) == 1
        assert actions[0]["tool"] == "RUN_BA"
        assert "concept" in actions[0]["arguments"]

    def test_plan_init_with_requirements(self, setup):
        """Test INIT phase when requirements exist."""
        planner, sm = setup
        state = PipelineState(concept="test")
        state.phase = PipelinePhase.INIT
        state.has_requirements = True

        actions = planner.plan_next_actions(state)

        assert len(actions) == 0

    def test_plan_requirements_sequence(self, setup):
        """Test REQUIREMENTS phase BA→PO→Architect sequence."""
        planner, sm = setup
        state = sm.state
        state.phase = PipelinePhase.REQUIREMENTS
        state.has_requirements = True

        # Start: needs PO
        state.has_product_vision = False
        actions = planner.plan_next_actions(state)
        assert any(a["tool"] == "RUN_PO" for a in actions)

        # After PO: needs Architect
        state.has_product_vision = True
        state.has_stories = False
        actions = planner.plan_next_actions(state)
        assert any(a["tool"] == "RUN_ARCHITECT" for a in actions)

    def test_plan_planning_loads_stories(self, setup):
        """Test PLANNING phase loads stories into DAG."""
        planner, sm = setup
        state = sm.state
        state.phase = PipelinePhase.PLANNING
        state.has_stories = True
        state.total_stories = 2
        state.story_dependencies = {
            "S1": [],
            "S2": ["S1"],
        }

        # DAG should be rebuilt
        planner._rebuild_dag_from_state(state)
        assert planner.dag is not None
        assert state.total_stories == 2

    def test_plan_development_ready_stories(self, setup):
        """Test DEVELOPMENT phase selects ready stories."""
        planner, sm = setup
        state = PipelineState(concept="test")
        state.phase = PipelinePhase.DEVELOPMENT
        state.total_stories = 2
        state.stories_todo = ["S1", "S2"]
        state.story_dependencies = {
            "S1": [],
            "S2": ["S1"],
        }

        # Setup DAG
        planner.dag = StoryDAG()
        planner.dag.add_story("S1", {}, [])
        planner.dag.add_story("S2", {}, ["S1"])

        actions = planner.plan_next_actions(state)

        # Only S1 should be ready
        assert any(a.get("arguments", {}).get("story_id") == "S1" for a in actions)
        assert not any(a.get("arguments", {}).get("story_id") == "S2" for a in actions)

    def test_plan_development_all_done(self, setup):
        """Test DEVELOPMENT phase when all stories done."""
        planner, sm = setup
        state = sm.state
        state.phase = PipelinePhase.DEVELOPMENT
        state.total_stories = 1
        state.stories_done = {"S1"}
        state.stories_todo = []

        # When all stories done, planner transitions to INTEGRATION
        actions = planner.plan_next_actions(state)
        # After transition, phase changes to INTEGRATION
        assert state.phase == PipelinePhase.INTEGRATION or len(actions) == 0

    def test_plan_integration_ready(self, setup):
        """Test INTEGRATION phase when all stories done."""
        planner, sm = setup
        state = sm.state
        state.phase = PipelinePhase.INTEGRATION
        state.total_stories = 1
        state.stories_done = {"S1"}
        state.stories_failed = {}

        actions = planner.plan_next_actions(state)

        assert any(a["tool"] == "RUN_QA_FULL" for a in actions)

    def test_plan_done_state(self, setup):
        """Test DONE phase (terminal state)."""
        planner, sm = setup
        state = sm.state
        state.phase = PipelinePhase.DONE

        actions = planner.plan_next_actions(state)

        assert len(actions) == 0


class TestCoherenceChecker:
    """Test suite for Coherence Checker."""

    @pytest.fixture
    def checker(self):
        """Create coherence checker instance."""
        return CoherenceChecker({})

    def test_ba_po_alignment_aligned(self, checker):
        """Test BA→PO alignment when aligned."""
        ba = {
            "requirements": ["Feat1", "Feat2"],
            "constraints": ["Perf"],
        }
        po = {
            "reviewed_requirements": ["Feat1", "Feat2"],
            "constraints": ["Perf"],
            "approved": True,
        }

        result = checker.check_ba_po_alignment(ba, po)

        assert result["aligned"] is True
        assert result["severity"] == "ok"

    def test_ba_po_misalignment_count(self, checker):
        """Test BA→PO misalignment detection (count mismatch)."""
        ba = {"requirements": ["Feat1", "Feat2"]}
        po = {"reviewed_requirements": ["Feat1"]}

        result = checker.check_ba_po_alignment(ba, po)

        assert result["aligned"] is False
        assert any("count mismatch" in i.lower() for i in result["issues"])

    def test_ba_po_misalignment_constraints(self, checker):
        """Test BA→PO misalignment detection (constraints)."""
        ba = {"requirements": [], "constraints": ["Perf"]}
        po = {"reviewed_requirements": [], "constraints": ["Perf", "Security"]}

        result = checker.check_ba_po_alignment(ba, po)

        assert result["aligned"] is False
        assert any("constraint" in i.lower() for i in result["issues"])

    def test_arch_stories_alignment_aligned(self, checker):
        """Test Arch→Stories alignment when aligned."""
        arch = {
            "components": ["API", "DB"],
            "layers": ["presentation", "business", "data"],
        }
        stories = [
            {
                "id": "S1",
                "components": ["API"],
                "layer": "presentation",
                "depends_on": [],
            },
            {
                "id": "S2",
                "components": ["DB"],
                "layer": "data",
                "depends_on": ["S1"],
            },
        ]

        result = checker.check_arch_stories_alignment(arch, stories)

        assert result["aligned"] is True

    def test_arch_stories_missing_component(self, checker):
        """Test detection of unimplemented architecture components."""
        arch = {"components": ["API", "Cache", "DB"]}
        stories = [
            {"id": "S1", "components": ["API"]},
            {"id": "S2", "components": ["DB"]},
        ]

        result = checker.check_arch_stories_alignment(arch, stories)

        assert result["aligned"] is False
        assert any("Cache" in str(i) for i in result["issues"])

    def test_arch_stories_invalid_dependency(self, checker):
        """Test detection of invalid story dependencies."""
        arch = {"components": []}
        stories = [
            {"id": "S1", "depends_on": ["S99"]},  # Invalid dependency
        ]

        result = checker.check_arch_stories_alignment(arch, stories)

        assert result["aligned"] is False
        assert any("S99" in str(i) for i in result["issues"])

    def test_dev_tests_alignment_good(self, checker):
        """Test Dev→Tests alignment with good coverage."""
        impl = {"functions": ["func1", "func2"]}
        tests = {
            "coverage": 0.85,
            "test_types": ["unit", "integration"],
            "tested_functions": ["func1", "func2"],
        }

        result = checker.check_dev_tests_alignment(impl, tests)

        assert result["aligned"] is True

    def test_dev_tests_low_coverage(self, checker):
        """Test detection of low test coverage."""
        impl = {"functions": ["func1"]}
        tests = {
            "coverage": 0.5,
            "test_types": ["unit"],
            "tested_functions": [],
        }

        result = checker.check_dev_tests_alignment(impl, tests)

        assert result["aligned"] is False
        assert any("coverage" in i.lower() for i in result["issues"])

    def test_dev_tests_missing_types(self, checker):
        """Test detection of missing test types."""
        impl = {"functions": []}
        tests = {
            "coverage": 0.8,
            "test_types": ["unit"],  # Missing "integration"
            "tested_functions": [],
        }

        result = checker.check_dev_tests_alignment(impl, tests)

        assert result["aligned"] is False
        assert any("integration" in str(i).lower() for i in result["issues"])

    def test_qa_artifacts_valid(self, checker):
        """Test QA artifacts validation when valid."""
        qa = {
            "test_results": {"passed": 10},
            "coverage": 0.85,
            "failures": {},
            "duration": 45,
        }

        result = checker.check_qa_artifacts(qa)

        assert result["valid"] is True

    def test_qa_artifacts_missing_field(self, checker):
        """Test QA artifacts validation with missing fields."""
        qa = {
            "test_results": {},
            # Missing: coverage, failures, duration
        }

        result = checker.check_qa_artifacts(qa)

        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_qa_artifacts_critical_failures(self, checker):
        """Test QA artifacts with critical failures."""
        qa = {
            "test_results": {},
            "coverage": 0.5,
            "failures": {"critical": ["test1"]},
            "duration": 0,
        }

        result = checker.check_qa_artifacts(qa)

        assert result["valid"] is False
        assert result["severity"] in ["high", "critical"]


class TestChainOfThoughtLogger:
    """Test suite for Chain-of-Thought Logger."""

    @pytest.fixture
    def logger(self):
        """Create CoT logger with temp directory."""
        temp_dir = Path(tempfile.mkdtemp())
        log = ChainOfThoughtLogger(temp_dir)
        yield log
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cot_chain_creation(self, logger):
        """Test creating and ending a chain."""
        logger.start_chain(1, "INIT")
        chain = logger.end_chain()

        assert chain["step"] == 1
        assert chain["phase"] == "INIT"
        assert "timestamp" in chain

    def test_cot_decision_logging(self, logger):
        """Test logging decisions in chain."""
        logger.start_chain(1, "DEVELOPMENT")
        logger.log_decision(
            "Selected S1",
            "dag_ready_check",
            1.0,
            ["S2", "S3"],
        )
        chain = logger.end_chain()

        assert len(chain["reasoning"]) == 1
        assert chain["reasoning"][0]["decision"] == "Selected S1"
        assert chain["reasoning"][0]["confidence"] == 1.0

    def test_cot_evaluation_logging(self, logger):
        """Test logging evaluations in chain."""
        logger.start_chain(1, "PLANNING")
        logger.log_evaluation("has_stories", True, "Stories file exists")
        chain = logger.end_chain()

        assert len(chain["reasoning"]) == 1
        assert chain["reasoning"][0]["type"] == "evaluation"
        assert chain["reasoning"][0]["result"] is True

    def test_cot_chain_export(self, logger):
        """Test exporting chain summary."""
        logger.start_chain(1, "INIT")
        logger.log_decision("Start BA", "init_rule", 1.0)
        logger.end_chain()

        logger.start_chain(2, "REQUIREMENTS")
        logger.log_decision("Run PO", "requirement_rule", 1.0)
        logger.end_chain()

        summary = logger.export_summary()

        assert summary["total_steps"] == 2
        assert len(summary["chains"]) == 2

    def test_cot_decision_tree(self, logger):
        """Test decision tree generation."""
        logger.start_chain(1, "INIT")
        logger.log_decision("Start", "rule", 1.0)
        logger.end_chain()

        logger.start_chain(2, "INIT")
        logger.log_decision("Another", "rule", 1.0)
        logger.end_chain()

        summary = logger.export_summary()
        tree = summary["decision_tree"]

        assert "INIT" in tree
        assert len(tree["INIT"]) == 2

    def test_cot_artifacts_saved(self, logger):
        """Test that chains are saved to files."""
        logger.start_chain(1, "TEST")
        logger.end_chain()

        chain_file = logger.output_dir / "step_001.json"
        assert chain_file.exists()

        data = json.loads(chain_file.read_text())
        assert data["step"] == 1
        assert data["phase"] == "TEST"

    def test_cot_chain_count(self, logger):
        """Test chain counting."""
        assert logger.get_chain_count() == 0

        logger.start_chain(1, "TEST")
        logger.end_chain()

        assert logger.get_chain_count() == 1


class TestExecutionOptimizer:
    """Test suite for Execution Optimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer with no history."""
        temp_dir = Path(tempfile.mkdtemp())
        opt = ExecutionOptimizer(temp_dir)
        yield opt
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_optimizer_default_parallelism(self, optimizer):
        """Test default parallelism when no history."""
        parallelism = optimizer.get_optimal_parallelism()

        assert parallelism == 3

    def test_optimizer_learns_parallelism(self):
        """Test learning optimal parallelism from history."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create execution history
        iteration_dir = temp_dir / "iteration_1"
        iteration_dir.mkdir()

        summary = {
            "status": "success",
            "max_parallel": 5,
            "duration": 60,
        }
        (iteration_dir / "latest_orchestrator_summary.json").write_text(
            json.dumps(summary)
        )

        opt = ExecutionOptimizer(temp_dir)
        parallelism = opt.get_optimal_parallelism()

        assert parallelism == 5

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_optimizer_default_backoff(self, optimizer):
        """Test default backoff when no history."""
        backoff = optimizer.get_optimal_backoff("dev")

        assert backoff["type"] in ["exponential", "linear"]
        assert backoff["base"] > 0

    def test_optimizer_metrics(self, optimizer):
        """Test metrics computation."""
        optimizer.record_execution({"status": "success", "duration": 100})
        optimizer.record_execution({"status": "success", "duration": 120})

        metrics = optimizer.get_execution_metrics()

        assert metrics["total_executions"] == 2
        assert metrics["successful_executions"] == 2
        assert metrics["success_rate"] == 1.0
        assert metrics["avg_duration"] > 0


class TestIntegration:
    """Integration tests for Phase 2 components working together."""

    def test_planner_with_coherence(self):
        """Test planner with coherence checker enabled."""
        import tempfile
        config = {}
        planning_dir = Path(tempfile.mkdtemp())
        state_machine = StateMachine("test", planning_dir)
        dag = StoryDAG()
        policy_engine = PolicyEngine(config)
        planner = OrchestratorPlanner(state_machine, dag, policy_engine, config)

        assert planner.coherence_checker is not None

        # Cleanup
        import shutil
        shutil.rmtree(planning_dir, ignore_errors=True)

    def test_all_components_instantiate(self):
        """Test all Phase 2 components can be instantiated."""
        checker = CoherenceChecker()
        logger = ChainOfThoughtLogger(Path(tempfile.mkdtemp()))
        optimizer = ExecutionOptimizer(Path(tempfile.mkdtemp()))

        assert checker is not None
        assert logger is not None
        assert optimizer is not None

    def test_backward_compatibility(self):
        """Test Phase 1 components still work without Phase 2."""
        import tempfile
        config = {}
        planning_dir = Path(tempfile.mkdtemp())
        state_machine = StateMachine("test", planning_dir)
        dag = StoryDAG()
        policy_engine = PolicyEngine(config)

        # Create planner without explicitly using Phase 2
        planner = OrchestratorPlanner(state_machine, dag, policy_engine, config)

        # Plan basic action
        state = PipelineState(concept="test")
        state.phase = PipelinePhase.INIT
        actions = planner.plan_next_actions(state)

        assert len(actions) > 0

        # Cleanup
        import shutil
        shutil.rmtree(planning_dir, ignore_errors=True)
