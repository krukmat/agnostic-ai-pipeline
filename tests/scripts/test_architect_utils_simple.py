from scripts import architect_utils as au


def test_sanitize_yaml_block_handles_strings_and_dict():
    assert au.sanitize_yaml_block("```yaml\nkey: val\n```") == "key: val"
    dumped = au.sanitize_yaml_block({"a": 1})
    assert "a:" in dumped


def test_convert_stories_epics_to_yaml_json_input():
    payload = {"stories": [{"id": "S1"}], "epics": [{"id": "E1"}]}
    stories_yaml, epics_yaml = au.convert_stories_epics_to_yaml(au.json.dumps(payload))
    # Both blocks should contain the IDs when dumped to YAML
    assert "S1" in stories_yaml
    assert "E1" in epics_yaml
