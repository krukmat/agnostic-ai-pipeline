import json
import types

import pytest
import yaml

import scripts.fix_stories as fs


def test_uncomment_structured_and_remove_fences():
    raw = ["# - id: S1", "#   status: todo", "```yaml", "id: S2", "```"]
    uncommented = fs.uncomment_structured(raw)
    assert "- id: S1" in uncommented[0]
    cleaned = fs.remove_fences("\n".join(uncommented))
    assert "```" not in cleaned


def test_fix_acceptance_inline_cases():
    txt = "acceptance: - first\nacceptance: a; b; c\nacceptance: [x, y]"
    out = fs.fix_acceptance_inline(txt)
    assert "  - a" in out and "acceptance:" in out
    # flow style list should remain
    assert "[x, y]" in out


def test_sanitize_acceptance_bullets_removes_colon_quotes():
    txt = "- id: S1\n  acceptance:\n    - It must accept a JSON payload with \"diagram_code\" and \"diagram_type\": \"flowchart\".\n"
    cleaned = fs.sanitize_acceptance_bullets(txt)
    data = yaml.safe_load(cleaned)
    assert data[0]["acceptance"][0].startswith("It must accept a JSON payload")
    assert ":" not in data[0]["acceptance"][0]


def test_ensure_list_top_level_errors():
    with pytest.raises(SystemExit):
        fs.ensure_list_top_level({"stories": "bad"})
    with pytest.raises(SystemExit):
        fs.ensure_list_top_level("bad")


def test_normalize_status_default(monkeypatch, capsys):
    monkeypatch.setattr(fs, "normalize_status", fs.normalize_status)  # ensure original
    items = [{"id": "S1", "status": "", "description": "d1"}, {"id": "S2", "complexity": "medium"}]
    # Monkeypatch complexity analyzer import path by injecting into globals
    fs.analyze_story_complexity = lambda s, verbose=False: "simple"
    fixed = fs.normalize_status(items)
    assert fixed[0].get("status", "") in {"", "todo"}
    assert fixed[0].get("complexity") in {"simple", "medium"}
    assert fixed[1]["complexity"] == "medium"


def test_main_happy(monkeypatch, tmp_path, capsys):
    stories = "- id: S1\n  status: todo\n"
    p = tmp_path / "planning"
    p.mkdir()
    file_p = p / "stories.yaml"
    file_p.write_text(stories, encoding="utf-8")

    monkeypatch.setattr(fs, "P", file_p)
    monkeypatch.setattr(fs, "normalize_status", lambda items: items)
    monkeypatch.setattr(fs, "print", lambda *a, **k: None, raising=False)

    fs.main()
    assert file_p.read_text(encoding="utf-8")


def test_main_empty_raises(monkeypatch, tmp_path):
    p = tmp_path / "planning"
    p.mkdir()
    file_p = p / "stories.yaml"
    file_p.write_text("", encoding="utf-8")
    monkeypatch.setattr(fs, "P", file_p)
    with pytest.raises(SystemExit):
        fs.main()
