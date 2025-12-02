import yaml

from scripts import fix_stories as fs


def test_uncomment_structured_only_yaml_lines():
    lines = ["# - id: S1", "#   status: todo", "# comment", "plain"]
    out = fs.uncomment_structured(lines)
    assert "- id: S1" in out
    assert "plain" in out
    # comment-only line should drop
    assert not any("comment" == line.strip() for line in out)


def test_remove_fences_and_fix_acceptance_inline():
    txt = "```yaml\n- id: S1\n  acceptance: do X; do Y\n```"
    cleaned = fs.remove_fences(txt)
    fixed = fs.fix_acceptance_inline(cleaned)
    data = yaml.safe_load(fixed)
    assert isinstance(data, list)
    assert data[0]["acceptance"] == ["do X", "do Y"]


def test_ensure_list_top_level_handles_dict_and_list():
    data = {"stories": [{"id": "S1"}]}
    assert fs.ensure_list_top_level(data) == [{"id": "S1"}]
    assert fs.ensure_list_top_level([{"id": "S2"}]) == [{"id": "S2"}]
    try:
        fs.ensure_list_top_level("invalid")
    except SystemExit:
        assert True


def test_normalize_status_autosets_complexity(monkeypatch):
    stories = [{"id": "S1", "status": "todo"}]
    monkeypatch.setattr(fs, "analyze_story_complexity", lambda s, verbose=False: "medium", raising=False)
    out = fs.normalize_status(stories)
    assert out[0]["status"] == "todo"
    assert out[0]["complexity"] == "medium"
