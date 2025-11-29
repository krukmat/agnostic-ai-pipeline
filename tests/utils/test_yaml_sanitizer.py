from __future__ import annotations

import yaml

from scripts.utils import yaml_sanitizer


def test_sanitize_yaml_block_string_strips_fences():
    raw = "```yaml\n- id: S1\n```"
    assert yaml_sanitizer.sanitize_yaml_block(raw) == "- id: S1"


def test_sanitize_yaml_block_object_dump():
    data = {"a": 1}
    out = yaml_sanitizer.sanitize_yaml_block(data)
    assert "a: 1" in out


def test_sanitize_po_yaml_basic():
    raw = "- a: 1\n- b: 2"
    cleaned = yaml_sanitizer.sanitize_po_yaml(raw)
    assert yaml.safe_load(cleaned) == [{"a": 1}, {"b": 2}]


def test_sanitize_po_yaml_with_backticks():
    raw = "- `a`: 1"
    cleaned = yaml_sanitizer.sanitize_po_yaml(raw)
    assert yaml.safe_load(cleaned) == [{"a": 1}]


def test_normalize_po_yaml_quotes_specials():
    raw = "- %foo: bar"
    norm = yaml_sanitizer.normalize_po_yaml(raw)
    assert norm.startswith("- \"")


def test_normalize_po_yaml_handles_thin_space():
    thin = "\u202f"
    raw = f"- {thin}item: 1"
    norm = yaml_sanitizer.normalize_po_yaml(raw)
    assert thin not in norm
