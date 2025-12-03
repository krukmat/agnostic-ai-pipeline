import pytest

from scripts import run_ba
from scripts.utils.db_logger import DbLogger


class DummyCtx:
    def __init__(self):
        self.events = []
        self.artifacts = []
        self.enabled = True

    def log_event(self, *args, **kwargs):
        self.events.append(("event", args, kwargs))

    def save_artifact(self, *args, **kwargs):
        self.artifacts.append(("artifact", args, kwargs))


@pytest.mark.asyncio
async def test_generate_requirements_logs_to_db(monkeypatch, tmp_path):
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run_ba, "PLANNING", planning)
    monkeypatch.setattr(run_ba, "ensure_dirs", lambda: None)
    monkeypatch.setattr(run_ba, "_use_dspy", lambda: False)

    class DummyLegacy:
        async def generate_requirements(self, concept):
            (planning / "requirements.yaml").write_text("title: db", encoding="utf-8")
            return {"ok": True}

    ctx = DummyCtx()
    monkeypatch.setattr(run_ba, "_load_legacy_module", lambda: DummyLegacy())
    monkeypatch.setattr(run_ba, "get_db_context_or_default", lambda: ctx)
    monkeypatch.setattr(run_ba, "DbLogger", lambda ctx_val=None: DbLogger(ctx))

    res = await run_ba.generate_requirements("concept")
    assert res["ok"] is True
    assert any(e[0] == "event" for e in ctx.events)
    assert any(a[0] == "artifact" for a in ctx.artifacts)
