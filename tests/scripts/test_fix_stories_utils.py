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


def test_normalize_status_without_analyzer_uses_default(monkeypatch):
    stories = [{"id": "S1", "status": "todo"}]
    # Force import failure by injecting a module without the expected symbol
    import types, sys
    dummy_mod = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "scripts.utils.complexity_analyzer", dummy_mod)
    out = fs.normalize_status(stories)
    assert out[0]["complexity"] in {"medium", "simple", "p0", "p1", "p2", "p3"}  # default path


def test_repair_broken_id_lines_handles_dashes():
    txt = "- id - S2\n- id – S3"
    fixed = fs.repair_broken_id_lines(txt)
    assert "- id: S2" in fixed
    assert "- id: S3" in fixed


def test_sanitize_acceptance_bullets_stops_on_outdent():
    txt = "- id: S1\n  acceptance:\n    - first: ok\nother: value\n"
    cleaned = fs.sanitize_acceptance_bullets(txt)
    # acceptance bullet cleaned, following key preserved
    assert "first - ok" in cleaned
    assert "other: value" in cleaned
