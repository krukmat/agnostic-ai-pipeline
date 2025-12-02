"""Tests for run_architect.py helper functions to increase coverage."""
import json
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from scripts import run_architect


def test_load_config_returns_empty_on_error(monkeypatch):
    """Test _load_config() returns empty dict when load_config_base() fails."""
    def mock_load_config_base():
        raise Exception("Config loading failed")
    
    monkeypatch.setattr("scripts.run_architect.load_config_base", mock_load_config_base)
    
    cfg = run_architect._load_config()
    assert cfg == {}


def test_load_config_returns_config(monkeypatch):
    """Test _load_config() returns config correctly."""
    def mock_load_config_base():
        return {"features": {"use_dspy_architect": True}}
    
    monkeypatch.setattr("scripts.run_architect.load_config_base", mock_load_config_base)
    
    cfg = run_architect._load_config()
    assert cfg["features"]["use_dspy_architect"] is True


def test_use_dspy_architect_from_config(monkeypatch):
    """Test _use_dspy_architect() reads from config."""
    def mock_load_config_base():
        return {"features": {"use_dspy_architect": True}}
    
    monkeypatch.setattr("scripts.run_architect.load_config_base", mock_load_config_base)
    
    assert run_architect._use_dspy_architect() is True


def test_use_dspy_architect_env_override(monkeypatch):
    """Test _use_dspy_architect() respects env override."""
    def mock_load_config_base():
        return {"features": {"use_dspy_architect": False}}
    
    monkeypatch.setattr("scripts.run_architect.load_config_base", mock_load_config_base)
    monkeypatch.setenv("USE_DSPY_ARCHITECT", "true")
    
    assert run_architect._use_dspy_architect() is True


def test_use_dspy_architect_default_false(monkeypatch):
    """Test _use_dspy_architect() defaults to False."""
    def mock_load_config_base():
        return {}
    
    monkeypatch.setattr("scripts.run_architect.load_config_base", mock_load_config_base)
    
    assert run_architect._use_dspy_architect() is False


def test_extract_original_concept_from_meta():
    """Test extract_original_concept() extracts from metadata."""
    requirements_text = """
meta:
  original_request: "Build a TODO app"
requirements:
  - id: REQ1
    description: "Test requirement"
"""
    
    concept = run_architect.extract_original_concept(requirements_text)
    assert concept == "Build a TODO app"


def test_extract_original_concept_missing_meta():
    """Test extract_original_concept() handles missing metadata."""
    requirements_text = """
requirements:
  - id: REQ1
    description: "Test requirement"
"""
    
    concept = run_architect.extract_original_concept(requirements_text)
    assert concept == ""


def test_extract_original_concept_invalid_yaml():
    """Test extract_original_concept() handles invalid YAML."""
    requirements_text = "invalid: yaml: content: [[[["
    
    concept = run_architect.extract_original_concept(requirements_text)
    assert concept == ""


def test_extract_original_concept_empty_text():
    """Test extract_original_concept() handles empty text."""
    concept = run_architect.extract_original_concept("")
    assert concept == ""


def test_build_architect_context_complete(tmp_path, monkeypatch):
    """Test _build_architect_context() builds complete context."""
    planning = tmp_path / "planning"
    planning.mkdir()
    
    # Create requirements file
    req_file = planning / "requirements.yaml"
    req_file.write_text("meta:\n  original_request: 'Build app'\nrequirements: []", encoding="utf-8")
    
    # Create product vision file
    vision_file = planning / "product_vision.yaml"
    vision_file.write_text("vision: 'Great product'", encoding="utf-8")
    
    # Create stories file
    stories_file = planning / "stories.yaml"
    stories_file.write_text("- id: S1\n  status: todo", encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.PLANNING", planning)
    monkeypatch.setattr("scripts.run_architect.STORIES_PATH", stories_file)
    
    ctx = run_architect._build_architect_context(
        concept="My concept",
        architect_mode="normal",
        story_id="",
        detail_level="medium",
        iteration_count=1
    )
    
    assert ctx["concept_value"] == "My concept"
    assert "Build app" in ctx["requirements_content"]
    assert "Great product" in ctx["vision_content"]
    assert "S1" in ctx["stories_content"]
    assert ctx["architect_mode"] == "normal"
    assert ctx["detail_level"] == "medium"
    assert ctx["iteration_count"] == 1


def test_build_architect_context_missing_files(tmp_path, monkeypatch):
    """Test _build_architect_context() handles missing files."""
    planning = tmp_path / "planning"
    planning.mkdir()
    
    stories_file = planning / "stories.yaml"
    
    monkeypatch.setattr("scripts.run_architect.PLANNING", planning)
    monkeypatch.setattr("scripts.run_architect.STORIES_PATH", stories_file)
    
    ctx = run_architect._build_architect_context(
        concept="My concept",
        architect_mode="normal",
        story_id="",
        detail_level="medium",
        iteration_count=1
    )
    
    assert ctx["concept_value"] == "My concept"
    assert ctx["requirements_content"] == ""
    assert ctx["vision_content"] == ""
    assert ctx["stories_content"] == ""


def test_build_architect_context_uses_meta_concept(tmp_path, monkeypatch):
    """Test _build_architect_context() uses meta concept when concept param is empty."""
    planning = tmp_path / "planning"
    planning.mkdir()
    
    req_file = planning / "requirements.yaml"
    req_file.write_text("meta:\n  original_request: 'Meta concept'\nrequirements: []", encoding="utf-8")
    
    stories_file = planning / "stories.yaml"
    
    monkeypatch.setattr("scripts.run_architect.PLANNING", planning)
    monkeypatch.setattr("scripts.run_architect.STORIES_PATH", stories_file)
    
    ctx = run_architect._build_architect_context(
        concept=None,
        architect_mode="normal",
        story_id="",
        detail_level="medium",
        iteration_count=1
    )
    
    assert ctx["concept_value"] == "Meta concept"


def test_extract_qa_failure_context_no_report(tmp_path, monkeypatch):
    """Test extract_qa_failure_context() handles missing QA report."""
    monkeypatch.setattr("scripts.run_architect.ROOT", tmp_path)
    
    context = run_architect.extract_qa_failure_context("S1")
    assert "No QA report available" in context


def test_extract_qa_failure_context_wrong_story(tmp_path, monkeypatch):
    """Test extract_qa_failure_context() handles wrong story context."""
    root = tmp_path
    qa_dir = root / "artifacts" / "qa"
    qa_dir.mkdir(parents=True)
    
    report = qa_dir / "last_report.json"
    report.write_text(json.dumps({
        "story_context": "S2",
        "failure_details": {}
    }), encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.ROOT", root)
    
    context = run_architect.extract_qa_failure_context("S1")
    assert "S2" in context
    assert "not S1" in context


def test_extract_qa_failure_context_with_failures(tmp_path, monkeypatch):
    """Test extract_qa_failure_context() extracts failure details."""
    root = tmp_path
    qa_dir = root / "artifacts" / "qa"
    qa_dir.mkdir(parents=True)
    
    report = qa_dir / "last_report.json"
    report.write_text(json.dumps({
        "story_context": "S1",
        "failure_details": {
            "backend": {
                "errors": [
                    {"test": "test_create_user", "error": "AssertionError: expected 201, got 500"}
                ],
                "warnings": ["Deprecated API usage"]
            }
        }
    }), encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.ROOT", root)
    
    context = run_architect.extract_qa_failure_context("S1")
    assert "BACKEND" in context
    assert "test_create_user" in context
    assert "AssertionError" in context
    assert "Deprecated API usage" in context


def test_extract_qa_failure_context_handles_exception(tmp_path, monkeypatch):
    """Test extract_qa_failure_context() handles exceptions."""
    root = tmp_path
    qa_dir = root / "artifacts" / "qa"
    qa_dir.mkdir(parents=True)
    
    # Create invalid JSON
    report = qa_dir / "last_report.json"
    report.write_text("invalid json {{{", encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.ROOT", root)
    
    context = run_architect.extract_qa_failure_context("S1")
    assert "Error extracting QA context" in context


def test_try_programmatic_adjustment_story_not_found(tmp_path, monkeypatch):
    """Test try_programmatic_adjustment() handles story not found."""
    planning = tmp_path / "planning"
    planning.mkdir()
    
    stories_file = planning / "stories.yaml"
    stories_file.write_text("- id: S1\n  status: todo", encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.PLANNING", planning)
    monkeypatch.setattr("scripts.run_architect.STORIES_PATH", stories_file)
    
    result = run_architect.try_programmatic_adjustment("S999", "high")
    assert result is False


def test_try_programmatic_adjustment_high_level(tmp_path, monkeypatch):
    """Test try_programmatic_adjustment() adds high detail criteria."""
    planning = tmp_path / "planning"
    planning.mkdir()
    
    stories_file = planning / "stories.yaml"
    stories_file.write_text("""
- id: S1
  status: in_review
  acceptance:
    - Basic validation
""", encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.PLANNING", planning)
    monkeypatch.setattr("scripts.run_architect.STORIES_PATH", stories_file)
    
    # Mock save_stories to write to our temp file
    def mock_save_stories(stories):
        stories_file.write_text(yaml.safe_dump(stories, sort_keys=False, allow_unicode=True), encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.save_stories", mock_save_stories)
    
    result = run_architect.try_programmatic_adjustment("S1", "high")
    assert result is True
    
    # Verify story was updated
    updated_stories = yaml.safe_load(stories_file.read_text(encoding="utf-8"))
    assert updated_stories[0]["status"] == "todo"
    assert len(updated_stories[0]["acceptance"]) > 1
    assert any("validaciones exhaustivas" in str(item).lower() for item in updated_stories[0]["acceptance"])


def test_try_programmatic_adjustment_maximum_level(tmp_path, monkeypatch):
    """Test try_programmatic_adjustment() adds maximum detail criteria."""
    planning = tmp_path / "planning"
    planning.mkdir()
    
    stories_file = planning / "stories.yaml"
    stories_file.write_text("""
- id: S1
  status: in_review
  acceptance:
    - Basic validation
""", encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.PLANNING", planning)
    monkeypatch.setattr("scripts.run_architect.STORIES_PATH", stories_file)
    
    # Mock save_stories to write to our temp file
    def mock_save_stories(stories):
        stories_file.write_text(yaml.safe_dump(stories, sort_keys=False, allow_unicode=True), encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.save_stories", mock_save_stories)
    
    result = run_architect.try_programmatic_adjustment("S1", "maximum")
    assert result is True
    
    # Verify technical requirements were added
    updated_stories = yaml.safe_load(stories_file.read_text(encoding="utf-8"))
    assert updated_stories[0]["status"] == "todo"
    assert len(updated_stories[0]["acceptance"]) > 1


def test_mark_story_todo_success(tmp_path, monkeypatch):
    """Test mark_story_todo() marks story as todo."""
    planning = tmp_path / "planning"
    planning.mkdir()
    
    stories_file = planning / "stories.yaml"
    stories_file.write_text("""
- id: S1
  status: in_review
""", encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.PLANNING", planning)
    monkeypatch.setattr("scripts.run_architect.STORIES_PATH", stories_file)
    
    # Mock save_stories to write to our temp file
    def mock_save_stories(stories):
        stories_file.write_text(yaml.safe_dump(stories, sort_keys=False, allow_unicode=True), encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.save_stories", mock_save_stories)
    
    result = run_architect.mark_story_todo("S1")
    assert result is True
    
    # Verify status changed
    updated_stories = yaml.safe_load(stories_file.read_text(encoding="utf-8"))
    assert updated_stories[0]["status"] == "todo"


def test_mark_story_todo_story_not_found(tmp_path, monkeypatch):
    """Test mark_story_todo() handles story not found."""
    planning = tmp_path / "planning"
    planning.mkdir()
    
    stories_file = planning / "stories.yaml"
    stories_file.write_text("- id: S1\n  status: todo", encoding="utf-8")
    
    monkeypatch.setattr("scripts.run_architect.PLANNING", planning)
    monkeypatch.setattr("scripts.run_architect.STORIES_PATH", stories_file)
    
    result = run_architect.mark_story_todo("S999")
    assert result is False


def test_mark_story_todo_no_stories(tmp_path, monkeypatch):
    """Test mark_story_todo() handles no stories file."""
    planning = tmp_path / "planning"
    planning.mkdir()
    
    stories_file = planning / "stories.yaml"
    
    monkeypatch.setattr("scripts.run_architect.PLANNING", planning)
    monkeypatch.setattr("scripts.run_architect.STORIES_PATH", stories_file)
    
    result = run_architect.mark_story_todo("S1")
    assert result is False


def test_get_architect_prompt_review_adjustment():
    """Test get_architect_prompt() returns review adjustment prompt."""
    prompt = run_architect.get_architect_prompt("review_adjustment", "medium")
    assert len(prompt) > 0
    # Review adjustment prompt should contain specific keywords
    assert "INSTRUCTION" in prompt or "Ajusta" in prompt or "adjust" in prompt.lower()


def test_get_architect_prompt_simple_tier():
    """Test get_architect_prompt() returns simple tier prompt."""
    prompt = run_architect.get_architect_prompt("normal", "simple")
    assert len(prompt) > 0
    assert prompt == run_architect.ARCHITECT_PROMPTS["simple"]


def test_get_architect_prompt_medium_tier():
    """Test get_architect_prompt() returns medium tier prompt."""
    prompt = run_architect.get_architect_prompt("normal", "medium")
    assert len(prompt) > 0
    assert prompt == run_architect.ARCHITECT_PROMPTS["medium"]


def test_get_architect_prompt_corporate_tier():
    """Test get_architect_prompt() returns corporate tier prompt."""
    prompt = run_architect.get_architect_prompt("normal", "corporate")
    assert len(prompt) > 0
    assert prompt == run_architect.ARCHITECT_PROMPTS["corporate"]
