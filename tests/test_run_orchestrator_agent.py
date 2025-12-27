import json

import pytest

import scripts.run_orchestrator_agent as agent


def test_parse_response_strips_markdown():
    raw = "```json\n{\"state_update\":{},\"next_actions\":[],\"termination\":{}}\n```"
    parsed = agent._parse_response(raw)
    assert parsed["next_actions"] == []


def test_parse_response_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        agent._parse_response("not-json")


def test_update_story_state_done_and_failed():
    stories_state = {}
    results = [
        {"tool": "RUN_DEV_STORY", "status": "ok", "story_id": "S1"},
        {"tool": "RUN_QA_STORY", "status": "tests_failed", "story_id": "S2", "error": "boom"},
    ]
    agent._update_story_state(stories_state, results)
    assert stories_state["S1"]["status"] == "done"
    assert stories_state["S2"]["status"] == "failed"
    assert stories_state["S2"]["last_error"] == "boom"


@pytest.mark.asyncio
async def test_dispatch_actions_skips_unknown(monkeypatch):
    async def fake_execute_role(role, payload):
        return {"status": "ok"}

    monkeypatch.setattr(agent, "execute_role", fake_execute_role)
    results = await agent._dispatch_actions([{"tool": "RUN_UNKNOWN"}])
    assert results[0]["status"] == "skipped"


@pytest.mark.asyncio
async def test_dispatch_actions_executes_role(monkeypatch):
    async def fake_execute_role(role, payload):
        return {"status": "ok", "story_id": payload.get("story_id")}

    monkeypatch.setattr(agent, "execute_role", fake_execute_role)
    results = await agent._dispatch_actions([
        {"tool": "RUN_QA_FULL", "arguments": {}},
        {"tool": "RUN_DEV_STORY", "arguments": {"story_id": "S1"}},
    ])
    assert results[0]["tool"] == "RUN_QA_FULL"
    assert results[1]["story_id"] == "S1"


def test_build_context_includes_artifacts(tmp_path, monkeypatch):
    planning_dir = tmp_path / "planning"
    planning_dir.mkdir()
    (planning_dir / "requirements.yaml").write_text("foo: bar")

    qa_dir = tmp_path / "artifacts" / "qa"
    qa_dir.mkdir(parents=True)
    (qa_dir / "last_report.json").write_text(json.dumps({"status": "ok"}))

    dev_dir = tmp_path / "artifacts" / "dev" / "S1"
    dev_dir.mkdir(parents=True)
    (dev_dir / "error.txt").write_text("fail")

    monkeypatch.setattr(agent, "PLANNING", planning_dir)
    monkeypatch.setattr(agent, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(agent, "load_stories", lambda: [{"id": "S1", "title": "t", "status": "todo"}])

    context = agent._build_context("concept", [], {"max_steps": 1}, {})
    data = json.loads(context)
    assert data["artifacts"]["requirements"]["present"] is True
    assert data["qa_summary"]["status"] == "ok"
    assert data["dev_errors"]["S1"] == "fail"


def test_get_v2_role_handlers_has_keys():
    handlers = agent._get_v2_role_handlers()
    assert handlers["RUN_DEV_STORY"] is handlers["RUN_DEV"]
    assert "RUN_QA_FULL" in handlers


def test_main_v2_path(monkeypatch, tmp_path):
    monkeypatch.setattr(agent, "ensure_dirs", lambda: None)
    monkeypatch.setattr(agent, "load_config", lambda: {"pipeline": {"use_v2_orchestrator": True}})
    monkeypatch.setattr(agent, "save_metrics", lambda: None)
    monkeypatch.setattr(agent, "ITERATIONS_DIR", tmp_path)

    async def fake_run_orchestrator_v2(concept, max_steps, handlers):
        return {"steps": [], "final_state": "done"}

    monkeypatch.setattr(agent, "run_orchestrator_v2", fake_run_orchestrator_v2)
    monkeypatch.setattr(agent, "parse_args", lambda: type("Args", (), {"concept": "c", "max_steps": 1, "max_actions_per_step": 1, "use_v2": True})())
    assert agent.main() == 0


def test_main_requires_concept(monkeypatch):
    monkeypatch.setattr(agent, "parse_args", lambda: type("Args", (), {"concept": "", "max_steps": 1, "max_actions_per_step": 1, "use_v2": False})())
    assert agent.main() == 1
