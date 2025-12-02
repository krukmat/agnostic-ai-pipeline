from scripts.utils import yaml_sanitizer as ys


def test_sanitize_yaml_block_handles_markdown():
    raw = "```yaml\nkey: val\n```"
    assert ys.sanitize_yaml_block(raw) == "key: val"
    assert ys.sanitize_yaml_block({"a": 1}).startswith("a:")


def test_sanitize_po_yaml_recovers_on_failure():
    messy = "bad: [unclosed"
    out = ys.sanitize_po_yaml(messy)
    assert isinstance(out, str)
    assert "bad" in out


def test_sanitize_requirements_yaml_strips_bold():
    raw = "**Title**: Hello"
    assert "Title" in ys.sanitize_requirements_yaml(raw)
    assert "**" not in ys.sanitize_requirements_yaml(raw)


def test_normalize_po_yaml_quotes_special_tokens():
    raw = "- 100% complete\n- foo: bar\n- <note>\n"
    norm = ys.normalize_po_yaml(raw)
    assert "%" not in norm.splitlines()[0] or '"' in norm.splitlines()[0]
    assert "<note>" not in norm.splitlines()[2] or '"' in norm.splitlines()[2]
