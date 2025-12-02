import asyncio
from scripts import run_architect


class DummyClient:
    def __init__(self, role=None):
        self.calls = 0
        self.provider_type = "dummy"
        self.model = "dummy"
        self.temperature = 0.0
        self.max_tokens = 0

    async def chat(self, system: str, user: str):
        self.calls += 1
        return "STORIES\n```yaml STORIES\n- id: S1\n  status: todo\n```\n"


async def _fake_classify(*args, **kwargs):
    return "simple"


def test_parse_architect_response_basic(monkeypatch, tmp_path):
    # Patch directories
    monkeypatch.setattr(run_architect, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(run_architect, "DEBUG_DIR", tmp_path / "debug")
    run_architect.PLANNING.mkdir(parents=True, exist_ok=True)
    run_architect.DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    # Use dummy client and classifier
    monkeypatch.setattr(run_architect, "Client", lambda role="architect": DummyClient(role))
    monkeypatch.setattr(run_architect, "classify_complexity_with_llm", _fake_classify)

    async def _run():
        return await run_architect.run_architect_job(concept="demo", architect_mode="normal", iteration_count=1)

    result = asyncio.run(_run())
    assert "stories" in result.get("outputs", {})
    assert (run_architect.PLANNING / "stories.yaml").exists()
