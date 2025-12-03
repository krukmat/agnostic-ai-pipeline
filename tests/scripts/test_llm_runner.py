import pytest

from scripts.utils.llm_runner import LLMRunner


class DummyClient:
    def __init__(self, text="ok", fail=False, provider="p", model="m"):
        self.text = text
        self.fail = fail
        self.provider_type = provider
        self.model = model
        self.calls = 0

    async def chat(self, system=None, user=None):
        self.calls += 1
        if self.fail:
            raise RuntimeError("boom")
        return self.text


@pytest.mark.asyncio
async def test_llm_runner_primary_success():
    client = DummyClient(text="hello", provider="prov", model="mod")
    runner = LLMRunner([client])
    text, info = await runner.chat(system="s", user="u")
    assert text == "hello"
    assert info["provider"] == "prov"
    assert client.calls == 1


@pytest.mark.asyncio
async def test_llm_runner_uses_backup_on_failure():
    primary = DummyClient(fail=True)
    backup = DummyClient(text="fallback", provider="bprov", model="bmod")
    runner = LLMRunner.from_client(primary, backups=[lambda: backup])
    text, info = await runner.chat(system="s", user="u")
    assert text == "fallback"
    assert info["provider"] == "bprov"
    assert primary.calls >= 1


@pytest.mark.asyncio
async def test_llm_runner_retries_before_fallback():
    primary = DummyClient(fail=True)
    backup = DummyClient(text="fallback")
    runner = LLMRunner([primary, backup])
    text, _ = await runner.chat(system="s", user="u", retries=2)
    assert text == "fallback"
    assert primary.calls == 2  # retried before moving on


@pytest.mark.asyncio
async def test_llm_runner_no_clients_errors():
    runner = LLMRunner([])
    with pytest.raises(RuntimeError):
        await runner.chat(system="s", user="u")
