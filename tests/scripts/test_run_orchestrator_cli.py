import json
from pathlib import Path

from typer.testing import CliRunner

import scripts.run_orchestrator as mod

runner = CliRunner()


class DummyClient:
    def __init__(self):
        self.payloads = []

    def send_task(self, role, skill, payload):
        self.payloads.append((role, skill, payload))
        return {"status": "ok", "echo": payload}


def test_execute_command(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(mod, "A2AClient", lambda: dummy)
    result = runner.invoke(mod.app, ["execute", "--concept", "demo-concept"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert dummy.payloads == [("orchestrator", "execute_pipeline", {"concept": "demo-concept"})]


def test_serve_command(monkeypatch):
    calls = {}

    def fake_card():
        calls["card"] = True
        return ("card", {"handlers": True})

    def fake_run_agent(name, card, handlers, reload=False):
        calls["run"] = (name, card, handlers, reload)

    # Inject stub modules to avoid importing heavy a2a.cards dependencies
    import types, sys

    fake_cards = types.SimpleNamespace(orchestrator_card=fake_card)
    fake_runtime = types.SimpleNamespace(run_agent=fake_run_agent)
    sys.modules["a2a.cards"] = fake_cards
    sys.modules["a2a.runtime"] = fake_runtime

    result = runner.invoke(mod.app, ["serve", "--reload"])
    assert result.exit_code == 0
    assert calls["run"][0] == "orchestrator"
    assert calls["run"][3] is True
