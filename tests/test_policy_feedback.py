from scripts.orchestrator.learning_store import LearningStore
from scripts.orchestrator.policy_feedback import PolicyFeedback


class FakeState:
    def __init__(self, failed=None):
        self.stories_failed = failed or {}


def test_plan_remediation_triggers_escalation(tmp_path):
    store = LearningStore(path=tmp_path / "store.jsonl", retention_per_story=5)
    store.record_story_result(
        story_id="S1",
        phase="development",
        status="failed",
        attempt=1,
        error="syntax",
    )
    store.record_story_result(
        story_id="S1",
        phase="development",
        status="failed",
        attempt=2,
        error="syntax",
    )
    config = {
        "features": {
            "policy_feedback": {"enabled": True, "failure_threshold": 2}
        }
    }
    feedback = PolicyFeedback(learning_store=store, config=config)
    state = FakeState(failed={"S1": ["syntax"]})
    actions = feedback.plan_remediation(state)
    assert actions
    assert actions[0]["tool"] == "RUN_ARCHITECT"


def test_prioritize_ready_stories_orders_by_failures(tmp_path):
    store = LearningStore(path=tmp_path / "store.jsonl", retention_per_story=5)
    store.record_story_result(
        story_id="S1",
        phase="development",
        status="failed",
    )
    store.record_story_result(
        story_id="S2",
        phase="development",
        status="ok",
    )
    config = {
        "features": {
            "policy_feedback": {"enabled": True, "failure_threshold": 2}
        }
    }
    feedback = PolicyFeedback(learning_store=store, config=config)
    ordered = feedback.prioritize_ready_stories(["S2", "S1"])
    assert ordered[0] == "S1"


def test_policy_feedback_disabled_by_config(tmp_path):
    store = LearningStore(path=tmp_path / "store.jsonl", retention_per_story=5)
    config = {"features": {"policy_feedback": {"enabled": False}}}
    feedback = PolicyFeedback(learning_store=store, config=config)
    assert feedback.plan_remediation(FakeState({"S1": ["error"]})) == []
    assert feedback.prioritize_ready_stories(["S2", "S1"]) == ["S2", "S1"]
