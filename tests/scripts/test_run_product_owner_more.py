import asyncio
import json
from pathlib import Path

import pytest

from scripts import run_product_owner as po


def test_use_dspy_po_env_override(monkeypatch):
    monkeypatch.setenv("USE_DSPY_PO", "true")
    monkeypatch.setattr(po, "load_config_base", lambda: {"features": {"use_dspy_product_owner": False}})
    assert po._use_dspy_po() is True

def test_extract_original_concept_invalid_yaml(caplog):
    bad = "meta: ["
    assert po.extract_original_concept(bad) == ""
    assert any("[PO] Failed to parse requirements metadata" in rec.message for rec in caplog.records)


def test_build_user_payload():
    payload = po.build_user_payload("Concept", "Vision text", "reqs")
    assert "CONCEPT" in payload and "Vision text" in payload


def test_grab_block_missing_returns_empty():
    out = po.grab_block("no fences here", "yaml", "VISION")
    assert out == ""


@pytest.mark.asyncio
async def test_main_retry_on_missing_review(monkeypatch, tmp_path):
    # Redirect paths
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(po, "ROOT", tmp_path)
    monkeypatch.setattr(po, "VISION_PATH", po.PLANNING / "product_vision.yaml")
    monkeypatch.setattr(po, "REVIEW_PATH", po.PLANNING / "product_owner_review.yaml")
    monkeypatch.setattr(po, "DEBUG_PATH", po.ART / "debug" / "debug_po.txt")
    monkeypatch.setattr(po, "PO_PROMPT", "PROMPT")
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    po.ART.mkdir(parents=True, exist_ok=True)
    (po.PLANNING / "requirements.yaml").write_text("meta:\n  original_request: Demo\n", encoding="utf-8")

    # Simulate first response missing REVIEW, second includes it
    responses = [
        "```yaml VISION\nname: v1\n```",
        "```yaml VISION\nname: v2\n```\n```yaml REVIEW\nitems: []\n```",
    ]

    class DummyClient:
        def __init__(self, role=None):
            self.calls = 0
            self.provider_type = "dummy"
            self.model = "m"
            self.temperature = 0.1
            self.max_tokens = 256

        async def chat(self, system, user):
            resp = responses[self.calls]
            self.calls += 1
            return resp

    monkeypatch.setattr(po, "Client", DummyClient)
    monkeypatch.setattr(po, "save_text", lambda *a, **k: None)
    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
    monkeypatch.setattr(po, "get_db_context_or_default", lambda: DummyCtx())

    await po.main()
    # After retry, both files should exist
    assert (po.PLANNING / "product_vision.yaml").exists()
    assert (po.PLANNING / "product_owner_review.yaml").exists()


@pytest.mark.asyncio
async def test_main_aborts_when_review_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(po, "ROOT", tmp_path)
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    po.ART.mkdir(parents=True, exist_ok=True)
    (po.PLANNING / "requirements.yaml").write_text("meta:\n  original_request: Demo\n", encoding="utf-8")

    class DummyClient:
        def __init__(self, role=None):
            self.provider_type = "dummy"
            self.model = "m"
            self.temperature = 0.1
            self.max_tokens = 256
        async def chat(self, system, user):
            return "```yaml VISION\nname: v1\n```"

    monkeypatch.setattr(po, "Client", DummyClient)
    monkeypatch.setattr(po, "save_text", lambda *a, **k: None)
    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
    monkeypatch.setattr(po, "get_db_context_or_default", lambda: DummyCtx())

    with pytest.raises(SystemExit):
        await po.main()


@pytest.mark.asyncio
async def test_main_uses_concept_env(monkeypatch, tmp_path):
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(po, "ROOT", tmp_path)
    monkeypatch.setattr(po, "VISION_PATH", po.PLANNING / "product_vision.yaml")
    monkeypatch.setattr(po, "REVIEW_PATH", po.PLANNING / "product_owner_review.yaml")
    monkeypatch.setattr(po, "DEBUG_PATH", po.ART / "debug" / "debug_po.txt")
    monkeypatch.setattr(po, "PO_PROMPT", "PROMPT")
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    po.ART.mkdir(parents=True, exist_ok=True)
    (po.PLANNING / "requirements.yaml").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("CONCEPT", "FromEnv")

    class DummyClient:
        def __init__(self, role=None):
            self.provider_type = "dummy"
            self.model = "m"
            self.temperature = 0.1
            self.max_tokens = 256
        async def chat(self, system, user):
            assert "FromEnv" in user
            return "```yaml VISION\nname: v\n```\n```yaml REVIEW\nitems: []\n```"

    monkeypatch.setattr(po, "Client", DummyClient)
    monkeypatch.setattr(po, "save_text", lambda *a, **k: None)
    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
    monkeypatch.setattr(po, "get_db_context_or_default", lambda: DummyCtx())

    await po.main()
    assert (po.PLANNING / "product_vision.yaml").exists()


@pytest.mark.asyncio
async def test_run_dspy_program_missing_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(po, "ROOT", tmp_path)
    with pytest.raises(SystemExit):
        await po.run_dspy_program("reqs", "concept", "vision")


@pytest.mark.asyncio
async def test_main_concept_env_diff_logs(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(po, "ROOT", tmp_path)
    monkeypatch.setattr(po, "VISION_PATH", po.PLANNING / "product_vision.yaml")
    monkeypatch.setattr(po, "REVIEW_PATH", po.PLANNING / "product_owner_review.yaml")
    monkeypatch.setattr(po, "DEBUG_PATH", po.ART / "debug" / "debug_po.txt")
    monkeypatch.setattr(po, "PO_PROMPT", "PROMPT")
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    po.ART.mkdir(parents=True, exist_ok=True)
    (po.PLANNING / "requirements.yaml").write_text("meta:\n  original_request: Meta\n", encoding="utf-8")
    monkeypatch.setenv("CONCEPT", "Env")

    class DummyClient:
        def __init__(self, role=None):
            self.provider_type = "dummy"
            self.model = "m"
            self.temperature = 0.1
            self.max_tokens = 256
        async def chat(self, system, user):
            return "```yaml VISION\nname: v\n```\n```yaml REVIEW\nitems: []\n```"

    monkeypatch.setattr(po, "Client", DummyClient)
    monkeypatch.setattr(po, "save_text", lambda *a, **k: None)
    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
    monkeypatch.setattr(po, "get_db_context_or_default", lambda: DummyCtx())

    await po.main()
    assert any("differs from requirements meta" in rec.message for rec in caplog.records)
    assert po.VISION_PATH.exists()


@pytest.mark.asyncio
async def test_main_use_dspy_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("USE_DSPY_PO", "1")
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(po, "ROOT", tmp_path)
    monkeypatch.setattr(po, "VISION_PATH", po.PLANNING / "product_vision.yaml")
    monkeypatch.setattr(po, "REVIEW_PATH", po.PLANNING / "product_owner_review.yaml")
    monkeypatch.setattr(po, "DEBUG_PATH", po.ART / "debug" / "debug_po.txt")
    monkeypatch.setattr(po, "PO_PROMPT", "PROMPT")
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    po.ART.mkdir(parents=True, exist_ok=True)
    (po.PLANNING / "requirements.yaml").write_text("{}", encoding="utf-8")

    called = {"dspy": 0}
    async def fake_dspy(reqs, concept, vision):
        called["dspy"] += 1
        raise RuntimeError("fail dspy")
    monkeypatch.setattr(po, "run_dspy_program", fake_dspy)

    class DummyClient:
        def __init__(self, role=None):
            self.provider_type = "dummy"
            self.model = "m"
            self.temperature = 0.1
            self.max_tokens = 256
        async def chat(self, system, user):
            return "```yaml VISION\nname: v\n```\n```yaml REVIEW\nitems: []\n```"

    monkeypatch.setattr(po, "Client", DummyClient)
    monkeypatch.setattr(po, "save_text", lambda *a, **k: None)
    class DummyCtx:
        enabled = False
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
    monkeypatch.setattr(po, "get_db_context_or_default", lambda: DummyCtx())

    await po.main()
    assert called["dspy"] == 1
    assert po.VISION_PATH.exists()


@pytest.mark.asyncio
async def test_main_db_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(po, "ROOT", tmp_path)
    monkeypatch.setattr(po, "VISION_PATH", po.PLANNING / "product_vision.yaml")
    monkeypatch.setattr(po, "REVIEW_PATH", po.PLANNING / "product_owner_review.yaml")
    monkeypatch.setattr(po, "DEBUG_PATH", po.ART / "debug" / "debug_po.txt")
    monkeypatch.setattr(po, "PO_PROMPT", "PROMPT")
    po.PLANNING.mkdir(parents=True, exist_ok=True)
    po.ART.mkdir(parents=True, exist_ok=True)
    (po.PLANNING / "requirements.yaml").write_text("{}", encoding="utf-8")

    class DummyClient:
        def __init__(self, role=None):
            self.provider_type = "dummy"
            self.model = "m"
            self.temperature = 0.1
            self.max_tokens = 256
        async def chat(self, system, user):
            return "```yaml REVIEW\nitems: []\n```"  # missing vision triggers warning

    monkeypatch.setattr(po, "Client", DummyClient)
    monkeypatch.setattr(po, "save_text", lambda *a, **k: None)

    class DummyCtx:
        enabled = True
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k):
            raise RuntimeError("db fail")
    monkeypatch.setattr(po, "get_db_context_or_default", lambda: DummyCtx())

    # Should not raise even if DB fails and vision missing
    await po.main()
    assert po.REVIEW_PATH.exists()


@pytest.mark.asyncio
async def test_run_dspy_program_success(monkeypatch, tmp_path):
    # Build fake snapshot structure
    monkeypatch.setattr(po, "ROOT", tmp_path)
    program_dir = tmp_path / "artifacts" / "dspy" / "po_optimized_full_snapshot_20251117T105427" / "product_owner"
    program_dir.mkdir(parents=True, exist_ok=True)
    components = {"modules": {"generate": {"instructions": "do x", "demos": [{"concept": "c", "requirements_yaml": "r", "existing_vision": "v", "product_vision": "pv", "product_owner_review": "pr"}]}}}
    (program_dir / "program_components.json").write_text(json.dumps(components), encoding="utf-8")

    # Patch paths
    monkeypatch.setattr(po, "PLANNING", tmp_path / "planning")
    monkeypatch.setattr(po, "ART", tmp_path / "artifacts")
    monkeypatch.setattr(po, "VISION_PATH", po.PLANNING / "product_vision.yaml")
    monkeypatch.setattr(po, "REVIEW_PATH", po.PLANNING / "product_owner_review.yaml")
    po.PLANNING.mkdir(parents=True, exist_ok=True)

    # Stub dspy and module
    class DummyExample:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def with_inputs(self, *a):
            return self

    class DummyModule:
        def __init__(self):
            self.generate = type("G", (), {"signature": type("S", (), {"instructions": None})(), "demos": []})()
        def __call__(self, concept, requirements_yaml, existing_vision):
            return type("P", (), {"product_vision": "pv_out", "product_owner_review": "pr_out"})()

    monkeypatch.setattr(po, "ProductOwnerModule", DummyModule)
    monkeypatch.setattr(po, "build_lm_for_role", lambda role: "lm")
    monkeypatch.setattr(po, "sanitize_po_yaml", lambda x: x)
    monkeypatch.setattr(po, "dspy", type("D", (), {"configure": lambda **k: None, "Example": DummyExample}))

    class DummyCtx:
        enabled = True
        def log_event(self, *a, **k): ...
        def save_artifact(self, *a, **k): ...
    monkeypatch.setattr(po, "get_db_context_or_default", lambda: DummyCtx())

    await po.run_dspy_program("reqs", "concept", "vision")
    assert po.VISION_PATH.exists()
    assert po.REVIEW_PATH.exists()
