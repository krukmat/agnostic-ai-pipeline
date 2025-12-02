import os
import sys
import types

if "dspy" not in sys.modules:
    class DummyLM:
        def __init__(self, model, **kwargs):
            self.model = model
            for key, value in kwargs.items():
                setattr(self, key, value)

    sys.modules["dspy"] = types.SimpleNamespace(LM=DummyLM)

from scripts import dspy_lm_helper as lm_helper


def test_build_lm_vertex(monkeypatch):
    cfg = {
        "providers": {
            "vertex_sdk": {"project_id": "p", "location": "loc"},
        },
        "roles": {"dev": {"provider": "vertex_sdk", "model": "gem"}}
    }
    monkeypatch.setattr(lm_helper, "_load_config", lambda: cfg)
    lm = lm_helper.build_lm_for_role("dev")
    assert "vertex_ai" in lm.model  # underlying spec contains provider


def test_build_lm_openai(monkeypatch):
    cfg = {
        "providers": {"openai": {"base_url": "http://localhost:4010/v1", "api_key": "x"}},
        "roles": {"qa": {"provider": "openai", "model": "gpt-4"}}
    }
    monkeypatch.setattr(lm_helper, "_load_config", lambda: cfg)
    lm = lm_helper.build_lm_for_role("qa")
    assert "openai" in lm.model


def test_get_role_output_cap_mipro_env(monkeypatch):
    cfg = {"roles": {"qa": {"max_tokens": 512}}}
    monkeypatch.setattr(lm_helper, "_load_config", lambda: cfg)
    monkeypatch.setitem(lm_helper.os.environ, "DSPY_MIPRO_MODE", "1")
    monkeypatch.setitem(lm_helper.os.environ, "DSPY_MIPRO_MAX_TOKENS", "256")

    cap = lm_helper.get_role_output_cap("qa", "stories", default_ratio=0.1, default_min_tokens=64)
    # Cap comes from ratio/min_tokens, MIPRO override applies at pick_max_tokens layer
    assert cap == 64
    assert lm_helper.pick_max_tokens_for("qa", cap) == 256

    monkeypatch.delenv("DSPY_MIPRO_MODE", raising=False)
    monkeypatch.delenv("DSPY_MIPRO_MAX_TOKENS", raising=False)
