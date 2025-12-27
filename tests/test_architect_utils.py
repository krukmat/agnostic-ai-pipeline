import yaml

from scripts.architect_utils import sanitize_yaml_block, convert_stories_epics_to_yaml


def test_sanitize_yaml_block_handles_string():
    raw = "```yaml\nfoo: bar\n```"
    assert sanitize_yaml_block(raw) == "foo: bar"


def test_sanitize_yaml_block_handles_dict():
    payload = {"foo": "bar", "items": [1, 2]}
    output = sanitize_yaml_block(payload)
    assert yaml.safe_load(output) == payload


def test_convert_stories_epics_to_yaml_from_json():
    raw = '{"stories": [{"id": "S1"}], "epics": [{"id": "E1"}]}'
    stories_yaml, epics_yaml = convert_stories_epics_to_yaml(raw)
    assert yaml.safe_load(stories_yaml) == [{"id": "S1"}]
    assert yaml.safe_load(epics_yaml) == [{"id": "E1"}]


def test_convert_stories_epics_to_yaml_from_yaml():
    raw = yaml.safe_dump({"stories": [{"id": "S2"}], "epics": [{"id": "E2"}]})
    stories_yaml, epics_yaml = convert_stories_epics_to_yaml(raw)
    assert yaml.safe_load(stories_yaml) == [{"id": "S2"}]
    assert yaml.safe_load(epics_yaml) == [{"id": "E2"}]


def test_convert_stories_epics_to_yaml_empty_input():
    stories_yaml, epics_yaml = convert_stories_epics_to_yaml("")
    assert stories_yaml == ""
    assert epics_yaml == ""
