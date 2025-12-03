import os

from scripts.utils.qa_prompt_builder import load_qa_defaults, build_qa_config


def test_load_qa_defaults_missing_config(monkeypatch):
    monkeypatch.setenv("NONEXISTENT", "1")  # no effect
    allow, run = load_qa_defaults()
    assert isinstance(allow, bool) and isinstance(run, bool)


def test_build_qa_config_defaults(monkeypatch):
    monkeypatch.delenv("ALLOW_NO_TESTS", raising=False)
    monkeypatch.delenv("QA_RUN_TESTS", raising=False)
    story, allow, run = build_qa_config("")
    assert story.startswith("qa-run-")
    assert isinstance(allow, bool)
    assert isinstance(run, bool)


def test_build_qa_config_env_override(monkeypatch):
    monkeypatch.setenv("ALLOW_NO_TESTS", "0")
    monkeypatch.setenv("QA_RUN_TESTS", "1")
    story, allow, run = build_qa_config("S1")
    assert story == "S1"
    assert allow is False
    assert run is True
