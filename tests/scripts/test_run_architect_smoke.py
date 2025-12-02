import yaml
from pathlib import Path

from scripts import run_architect


def test_get_architect_prompt_override(tmp_path, monkeypatch):
    override = tmp_path / "override.md"
    override.write_text("OVERRIDE_PROMPT", encoding="utf-8")
    # Patch config loader to point to override
    monkeypatch.setattr(
        run_architect,
        "_load_config",
        lambda: {"features": {"architect": {"use_optimized_prompt": True, "prompt_override_file": str(override)}}},
    )
    prompt = run_architect.get_architect_prompt("normal", "medium")
    assert "OVERRIDE_PROMPT" in prompt


def test_extract_original_concept():
    data = {
        "meta": {"original_request": "Build a task API"},
        "requirements": [],
    }
    text = yaml.safe_dump(data, sort_keys=False)
    concept = run_architect.extract_original_concept(text)
    assert concept == "Build a task API"
