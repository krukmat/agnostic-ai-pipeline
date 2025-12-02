import asyncio

from scripts import orchestrate as orch


class DummyExecutor:
    def __init__(self, payload=None):
        self.payload = payload or {}
        self.called = False

    async def execute(self, payload):
        self.called = True
        return {"echo": payload}


def test_execute_role_uses_executor(monkeypatch):
    dummy = DummyExecutor()
    monkeypatch.setattr(orch, "_get_executor_for_role", lambda role: dummy)
    monkeypatch.setattr(orch, "instrumented", lambda role: (lambda fn: fn))
    monkeypatch.setattr(orch, "load_config", lambda: {})
    result = asyncio.run(orch.execute_role("developer", {"a": 1}))
    assert result["echo"]["a"] == 1
    assert dummy.called
