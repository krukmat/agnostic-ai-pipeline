import yaml

import pytest

from scripts.orchestrator.planner import OrchestratorPlanner
from scripts.orchestrator.policy_engine import PolicyEngine
from scripts.orchestrator.state_machine import PipelinePhase, PipelineState, StateMachine
from scripts.orchestrator.story_dag import StoryDAG
from scripts.orchestrator.learning_store import LearningStore


def _make_planner(tmp_path, config=None):
    config = config or {}
    state_machine = StateMachine("test", tmp_path)
    dag = StoryDAG()
    policy_engine = PolicyEngine(config)
    planner = OrchestratorPlanner(state_machine, dag, policy_engine, config)
    return planner, state_machine


def test_plan_next_actions_unknown_phase(tmp_path):
    planner, _ = _make_planner(tmp_path)
    state = PipelineState(concept="test")
    state.phase = PipelinePhase.FAILED
    assert planner.plan_next_actions(state) == []


def test_plan_development_blocked_uses_llm_fallback(tmp_path):
    planner, state_machine = _make_planner(tmp_path)
    state = state_machine.state
    state.phase = PipelinePhase.DEVELOPMENT
    state.total_stories = 4
    state.stories_failed = {"S1": ["boom"]}

    planner.dag.add_story("S1", {}, [])
    for sid in ("S2", "S3", "S4"):
        planner.dag.add_story(sid, {}, ["S1"])

    actions = planner.plan_next_actions(state)

    assert actions
    assert actions[0]["tool"] == "RUN_ARCHITECT"
    assert actions[0]["decision_method"] == "llm_fallback"


def test_plan_development_blocked_transitions_to_planning(tmp_path):
    planner, state_machine = _make_planner(tmp_path)
    state = state_machine.state
    state.phase = PipelinePhase.DEVELOPMENT
    state.total_stories = 2
    state.stories_failed = {"S1": ["boom"]}

    planner.dag.add_story("S1", {}, [])
    planner.dag.add_story("S2", {}, ["S1"])

    actions = planner.plan_next_actions(state)

    assert actions == []
    assert state.phase == PipelinePhase.PLANNING


def test_plan_development_policy_feedback_remediation(tmp_path):
    config = {"features": {"policy_feedback": {"enabled": True, "failure_threshold": 1}}}
    planner, state_machine = _make_planner(tmp_path, config)
    planner.learning_store = LearningStore(path=tmp_path / "learning_store.jsonl", retention_per_story=5)
    planner.policy_feedback.learning_store = planner.learning_store
    planner.policy_feedback.failure_threshold = 1

    state = state_machine.state
    state.phase = PipelinePhase.DEVELOPMENT
    state.stories_failed = {"S1": ["boom"]}

    planner.learning_store.record_story_result(
        story_id="S1",
        phase="development",
        status="failed",
        attempt=1,
        error="boom",
    )

    actions = planner.plan_next_actions(state)

    assert actions
    assert actions[0]["tool"] == "RUN_ARCHITECT"
    assert actions[0]["decision_method"] == "policy_feedback"


def test_plan_development_escalation_policy_triggers_architect(tmp_path):
    config = {
        "pipeline": {
            "escalation_policies": [
                {"condition": "dev_attempts >= 0", "action": "escalate_to_architect"}
            ]
        }
    }
    planner, state_machine = _make_planner(tmp_path, config)
    state = state_machine.state
    state.phase = PipelinePhase.DEVELOPMENT
    state.total_stories = 1

    planner.dag.add_story("S1", {}, [])

    actions = planner.plan_next_actions(state)

    assert actions
    assert actions[0]["tool"] == "RUN_ARCHITECT"


def test_check_and_log_coherence_records_requirements_issue(tmp_path, monkeypatch):
    planner, _ = _make_planner(tmp_path)
    state = PipelineState(concept="test")
    state.phase = PipelinePhase.REQUIREMENTS

    planning_dir = tmp_path / "planning"
    planning_dir.mkdir()
    (planning_dir / "requirements.yaml").write_text(
        yaml.safe_dump({"requirements": ["A", "B"], "constraints": []})
    )
    (planning_dir / "product_owner_review.yaml").write_text(
        yaml.safe_dump({"reviewed_requirements": ["A"], "approved": True})
    )

    monkeypatch.chdir(tmp_path)
    planner._check_and_log_coherence(state)

    assert hasattr(state, "coherence_issues")
    assert any("BA" in issue.get("check", "") for issue in state.coherence_issues)


def test_check_and_log_coherence_records_planning_issue(tmp_path, monkeypatch):
    planner, _ = _make_planner(tmp_path)
    state = PipelineState(concept="test")
    state.phase = PipelinePhase.PLANNING

    planning_dir = tmp_path / "planning"
    planning_dir.mkdir()
    (planning_dir / "architecture.yaml").write_text(
        yaml.safe_dump({"components": ["api"], "layers": ["service"]})
    )
    (planning_dir / "stories.yaml").write_text(
        yaml.safe_dump([{"id": "S1", "components": ["ui"], "layer": "frontend"}])
    )

    monkeypatch.chdir(tmp_path)
    planner._check_and_log_coherence(state)

    assert hasattr(state, "coherence_issues")
    assert any("Arch" in issue.get("check", "") for issue in state.coherence_issues)


def test_load_artifact_yaml_json_invalid(tmp_path):
    planner, _ = _make_planner(tmp_path)

    yaml_path = tmp_path / "artifact.yaml"
    yaml_path.write_text(yaml.safe_dump({"a": 1}))
    json_path = tmp_path / "artifact.json"
    json_path.write_text("{\"b\": 2}")
    bad_yaml_path = tmp_path / "bad.yaml"
    bad_yaml_path.write_text("a: [")

    assert planner._load_artifact(str(yaml_path)) == {"a": 1}
    assert planner._load_artifact(str(json_path)) == {"b": 2}
    assert planner._load_artifact(str(bad_yaml_path)) is None
