import types

import pytest

import scripts.orchestrator_runtime as runtime


class DummyExecutor:
    def __init__(self):
        self.payload = None

    async def execute(self, payload):
        self.payload = payload
        return {"status": "ok", "payload": payload}


@pytest.mark.asyncio
async def test_local_business_analyst_requires_concept():
    result = await runtime._local_business_analyst_handler(concept="  ")
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_local_business_analyst_success(monkeypatch):
    async def fake_generate_requirements(concept):
        return {"requirements": [concept]}

    monkeypatch.setattr(runtime, "generate_requirements", fake_generate_requirements)
    result = await runtime._local_business_analyst_handler(concept="test")
    assert result["status"] == "ok"
    assert result["requirements"] == ["test"]


@pytest.mark.asyncio
async def test_local_product_owner_system_exit(monkeypatch):
    async def fake_run_po():
        raise SystemExit(2)

    monkeypatch.setattr(runtime, "run_po", fake_run_po)
    result = await runtime._local_product_owner_handler()
    assert result["status"] == "error"
    assert result["exit_code"] == 2


@pytest.mark.asyncio
async def test_local_developer_handler_error(monkeypatch):
    async def fake_implement_story(story_id, retries):
        return {"status": "error", "story_id": story_id, "retries": retries}

    monkeypatch.setattr(runtime, "implement_story", fake_implement_story)
    result = await runtime._local_developer_handler(story_id="S1", retries="bad")
    assert result["status"] == "error"
    assert result["story_id"] == "S1"
    assert result["retries"] == 3


@pytest.mark.asyncio
async def test_local_qa_handler_allowno_tests_parsing(monkeypatch):
    def fake_quality_checks(allow_no_tests, story):
        return {"status": "ok", "allow_no_tests": allow_no_tests, "story": story}

    monkeypatch.setattr(runtime, "run_quality_checks", fake_quality_checks)
    result = await runtime._local_qa_handler(allow_no_tests="false", story_id="S1")
    assert result["status"] == "ok"
    assert result["allow_no_tests"] is False
    assert result["story"] == "S1"


def test_get_executor_for_role_unknown():
    with pytest.raises(KeyError):
        runtime._get_executor_for_role("unknown")


@pytest.mark.asyncio
async def test_execute_role_includes_drivers(monkeypatch):
    runtime._ROLE_EXECUTORS.clear()
    monkeypatch.setattr(runtime, "instrumented", lambda role: (lambda func: func))

    def fake_load_config():
        return {
            "drivers": {"enabled": True},
            "project": {"targets": {"backend": "fastapi"}},
        }

    class DummyDriver:
        id = "drv-1"
        category = "backend"
        language = "python"
        framework = "fastapi"
        artifact_paths = ["project/backend-fastapi"]
        build = types.SimpleNamespace(command="build")
        test = types.SimpleNamespace(command="test")
        lint = types.SimpleNamespace(command="lint")
        board = None
        flash_command = None
        monitor_command = None
        gpu_arch = None

    async def fake_execute(payload):
        return {"status": "ok", "payload": payload}

    dummy_executor = DummyExecutor()
    monkeypatch.setattr(runtime, "load_config", fake_load_config)
    monkeypatch.setattr(runtime, "load_driver", lambda cat, sel: DummyDriver())
    monkeypatch.setattr(runtime, "get_executor", lambda role, handler, skill_id: dummy_executor)

    result = await runtime.execute_role("qa", {"story_id": "S1"})
    assert result["status"] == "ok"
    assert "drivers" in dummy_executor.payload
    assert dummy_executor.payload["drivers"]["backend"]["id"] == "drv-1"


@pytest.mark.asyncio
async def test_execute_role_driver_load_failure(monkeypatch):
    runtime._ROLE_EXECUTORS.clear()
    monkeypatch.setattr(runtime, "instrumented", lambda role: (lambda func: func))

    def fake_load_config():
        return {
            "drivers": {"enabled": True},
            "project": {"targets": {"backend": "bad"}},
        }

    dummy_executor = DummyExecutor()
    monkeypatch.setattr(runtime, "load_config", fake_load_config)
    monkeypatch.setattr(runtime, "load_driver", lambda cat, sel: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(runtime, "get_executor", lambda role, handler, skill_id: dummy_executor)

    result = await runtime.execute_role("qa", {"story_id": "S1"})
    assert result["status"] == "ok"
    assert "drivers" not in dummy_executor.payload
