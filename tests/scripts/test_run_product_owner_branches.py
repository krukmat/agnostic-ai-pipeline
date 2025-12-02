import asyncio
import json
from pathlib import Path

import pytest

from scripts import run_product_owner as po


class DummyCtx:
    def __init__(self):
        self.events = []
        self.artifacts = []
        self.enabled = True

    def log_event(self, *a, **k):
        self.events.append((a, k))

    def save_artifact(self, *a, **k):
        self.artifacts.append((a, k))

    def log_attempt(self, *a, **k):
        pass


class RetryClient:
    def __init__(self, role=None):
        self.calls = 0
        self.provider_type = "dummy"
        self.model = "dummy"
        self.temperature = 0.2
        self.max_tokens = 256

    async def chat(self, system=None, user=None):
        self.calls += 1
        if self.calls == 1:
            return "```yaml VISION\nok: true\n```"
        return "```yaml VISION\nok: true\n```\n```yaml REVIEW\nok: true\n```"


@pytest.mark.asyncio
async def test_main_retries_when_review_missing(tmp_path, monkeypatch):
    # Redirect paths
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(po, "VISION_PATH", po.PLANNING / "product_vision.yaml")
    monkeypatch.setattr(po, "REVIEW_PATH", po.PLANNING / "product_owner_review.yaml")
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    po.ART.mkdir(parents=True, exist_ok=True)
    (po.PLANNING / "requirements.yaml").write_text("meta:\n  original_request: demo\n", encoding="utf-8")

    monkeypatch.setattr(po, "ensure_dirs", lambda: None)
    monkeypatch.setattr(po, "_use_dspy_po", lambda: False)
    client = RetryClient()
    monkeypatch.setattr(po, "Client", lambda role=None: client)
    ctx = DummyCtx()
    monkeypatch.setattr(po, "get_db_context_or_default", lambda: ctx)

    await po.main()
    assert client.calls == 2  # retried
    assert po.VISION_PATH.exists()
    assert po.REVIEW_PATH.exists()
    assert ctx.events  # db logging happened


@pytest.mark.asyncio
async def test_dspy_path_missing_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(po, "ROOT", tmp_path)
    # When _use_dspy_po returns True, missing snapshot should raise SystemExit
    monkeypatch.setattr(po, "_use_dspy_po", lambda: True)
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    (po.PLANNING / "requirements.yaml").write_text("meta:\n  original_request: demo\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        await po.main()
