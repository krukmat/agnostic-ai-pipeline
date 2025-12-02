import yaml

from scripts import fix_stories as fs


def test_uncomment_and_acceptance_fix():
    txt = "- id: S1\n  acceptance: do X; do Y\n"
    fixed = fs.fix_acceptance_inline(txt)
    data = yaml.safe_load(fixed + "\n")
    assert isinstance(data, list)
    assert data[0]["acceptance"] == ["do X", "do Y"]


def test_normalize_status_adds_complexity(monkeypatch):
    stories = [{"id": "S1", "status": "todo"}]
    monkeypatch.setattr(fs, "analyze_story_complexity", lambda s, verbose=False: "medium", raising=False)
    out = fs.normalize_status(stories)
    assert out[0]["complexity"] == "medium"
