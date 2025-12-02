import os

from scripts import run_product_owner as po


def test_extract_original_concept_from_meta():
    req = """
meta:
  original_request: Build an API
"""
    assert po.extract_original_concept(req) == "Build an API"


def test_build_user_payload_contains_sections():
    out = po.build_user_payload("Concept", "Vision", "Reqs")
    assert "CONCEPT:" in out and "EXISTING_VISION:" in out and "REQUIREMENTS:" in out


def test_grab_block_matches_markdown():
    text = "```yaml VISION\nhello\n```"
    assert po.grab_block(text, "yaml", "VISION") == "hello"


def test_use_dspy_po_env_override(monkeypatch):
    monkeypatch.setattr(po, "load_config_base", lambda: {"features": {"use_dspy_product_owner": False}})
    monkeypatch.setenv("USE_DSPY_PO", "1")
    assert po._use_dspy_po() is True
    monkeypatch.delenv("USE_DSPY_PO", raising=False)
