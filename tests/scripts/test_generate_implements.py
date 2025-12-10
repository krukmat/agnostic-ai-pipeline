import yaml
from pathlib import Path

from scripts.tools.generate_implements import apply_implements


def write_yaml(path: Path, data) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_apply_implements_uses_keywords_and_overrides(tmp_path):
    req_path = tmp_path / "requirements.yaml"
    requirements = {
        "functional_requirements": [
            {"id": "FR1", "title": "Subtitle uploads", "description": "Upload SRT files"},
            {"id": "FR2", "title": "Auto translation", "description": "Translate movies"},
        ]
    }
    write_yaml(req_path, requirements)

    stories_path = tmp_path / "stories.yaml"
    stories = [
        {"id": "S1", "title": "Allow subtitle upload", "summary": "Users upload srt"},
        {"id": "S2", "title": "Translation runner", "summary": "Auto translate movies"},
        {"id": "S3", "title": "Analytics"},
    ]
    write_yaml(stories_path, stories)

    map_path = tmp_path / "map.yaml"
    overrides = {
        "FR2": {"stories": ["S2"]},
        "FR3": {"keywords": ["analytics"]},
    }
    write_yaml(map_path, overrides)

    changed = apply_implements(
        stories_path=stories_path,
        requirements_path=req_path,
        mapping_path=map_path,
    )
    assert changed is True

    updated = read_yaml(stories_path)
    assert updated[0]["implements"] == ["FR1"]  # keyword match from requirements
    assert updated[1]["implements"] == ["FR2"]  # explicit override
    assert updated[2]["implements"] == ["FR3"]  # keyword override


def test_apply_implements_handles_missing_requirements(tmp_path):
    stories_path = tmp_path / "stories.yaml"
    stories = [
        {"id": "S1", "title": "Misc feature"},
    ]
    write_yaml(stories_path, stories)

    map_path = tmp_path / "map.yaml"
    write_yaml(map_path, {"FRX": {"stories": ["S1"]}})

    changed = apply_implements(
        stories_path=stories_path,
        requirements_path=tmp_path / "missing.yaml",
        mapping_path=map_path,
    )
    assert changed is True
    updated = read_yaml(stories_path)
    assert updated[0]["implements"] == ["FRX"]
