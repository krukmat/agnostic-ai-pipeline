import yaml

from scripts.utils.prompt_builders import build_dev_prompt, build_architect_prompt, build_po_user_payload


def test_build_dev_prompt():
    story = {"id": "S1", "status": "todo"}
    system, user = build_dev_prompt("BASE", story, "tree", "EXTRA")
    assert "BASE" in system and "EXTRA" in system
    assert "S1" in user and "tree" in user


def test_build_architect_prompt_review():
    user = build_architect_prompt("concept", "reqs", "medium", "stories", "high", 2, "review_adjustment", "S1")
    assert "CURRENT_STORIES" in user and "TARGET_STORY" in user


def test_build_architect_prompt_normal():
    user = build_architect_prompt("concept", "reqs", "medium", "stories", "high", 2, "normal", "")
    assert "CONCEPT" in user and "COMPLEXITY_TIER" in user


def test_build_po_user_payload():
    user = build_po_user_payload("Concept", "Vision", "Reqs")
    assert "CONCEPT" in user and "Vision" in user and "Reqs" in user
