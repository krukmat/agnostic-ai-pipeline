from scripts.llm import Client


def _base_providers():
    return {
        "ollama": {"type": "ollama", "base_url": "http://localhost:11434"},
        "codex_cli": {
            "type": "codex_cli",
            "command": ["codex", "chat"],
            "cwd": ".",
            "timeout": 30,
            "input_format": "stdin_text",
            "output_clean": True,
        },
    }


def test_client_uses_complexity_routing(monkeypatch):
    config = {
        "features": {"routing_by_complexity_enabled": True},
        "routing_by_complexity": {
            "dev": {
                "simple": {"provider": "ollama", "model": "qwen2.5-coder:7b"},
            }
        },
        "providers": _base_providers(),
        "roles": {"dev": {"provider": "codex_cli", "model": "default"}},
    }
    monkeypatch.setattr("scripts.llm.load_config", lambda: config)
    client = Client(role="dev", complexity="simple")
    assert client.provider_type == "ollama"
    assert client.model == "qwen2.5-coder:7b"


def test_client_falls_back_when_routing_disabled(monkeypatch):
    config = {
        "features": {"routing_by_complexity_enabled": False},
        "providers": _base_providers(),
        "roles": {"dev": {"provider": "codex_cli", "model": "default"}},
    }
    monkeypatch.setattr("scripts.llm.load_config", lambda: config)
    client = Client(role="dev", complexity="simple")
    assert client.provider_type == "codex_cli"
    assert client.model == "default"
