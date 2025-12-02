import pytest


class DummyClient:
    def __init__(self, role="architect", provider=None):
        # Use provided provider override if given
        if provider:
            self.provider_type = provider
        elif role == "architect":
            self.provider_type = "codex_cli"
        else:
            self.provider_type = "ollama"
        self.cli_command = "codex"
        self.model = "stub-model"
        self.cli_timeout = 5
        self.cli_input_format = "json"

    async def chat(self, system: str, user: str):
        return "hola"


@pytest.mark.asyncio
async def test_codex_cli_basic_branch(monkeypatch):
    import scripts.test_codex_cli as mod

    # Patch Client to avoid real LLM calls
    monkeypatch.setattr(mod, "Client", DummyClient)

    result = await mod.test_codex_cli_basic()
    assert result is True
