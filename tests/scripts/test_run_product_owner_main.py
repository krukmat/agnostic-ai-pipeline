import asyncio
from pathlib import Path

import pytest

from scripts import run_product_owner as po


class DummyClient:
    def __init__(self, role=None):
        self.role = role
        self.provider_type = "dummy"
        self.model = "dummy"
        self.temperature = 0.1
        self.max_tokens = 100

    async def chat(self, system=None, user=None):
        return """```yaml VISION
title: Demo
``` 
```yaml REVIEW
ok: true
```"""


class DummyDb:
    enabled = False
    def log_event(self, *a, **k): ...
    def save_artifact(self, *a, **k): ...


@pytest.mark.asyncio
async def test_main_llm_happy_path(tmp_path, monkeypatch):
    # Redirect paths to temp
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    po.ART.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(po, "VISION_PATH", po.PLANNING / "product_vision.yaml")
    monkeypatch.setattr(po, "REVIEW_PATH", po.PLANNING / "product_owner_review.yaml")
    # Seed requirements.yaml
    (po.PLANNING / "requirements.yaml").write_text("meta:\n  original_request: demo\n", encoding="utf-8")
    # Stub helpers
    monkeypatch.setattr(po, "ensure_dirs", lambda: None)
    monkeypatch.setattr(po, "_use_dspy_po", lambda: False)
    monkeypatch.setattr(po, "Client", DummyClient)
    monkeypatch.setattr(po, "get_db_context_or_default", lambda: DummyDb())

    await po.main()
    # Files should be written
    assert (po.PLANNING / "product_vision.yaml").exists()
    assert (po.PLANNING / "product_owner_review.yaml").exists()
