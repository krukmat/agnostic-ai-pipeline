"""Test that Architect prompt includes complexity field instructions."""

from pathlib import Path


def test_architect_prompt_has_complexity_in_dspy_header():
    """Verify DSPy header includes complexity field."""
    prompt_path = Path("prompts/architect.md")
    content = prompt_path.read_text(encoding="utf-8")

    # Check DSPy header section (lines 4-13)
    assert "[[ ## stories_yaml ## ]]" in content

    # Find the DSPy header section
    dspy_section_start = content.find("[[ ## stories_yaml ## ]]")
    dspy_section_end = content.find("[[ ## epics_yaml ## ]]")
    dspy_section = content[dspy_section_start:dspy_section_end]

    # Verify complexity field is present in DSPy header
    assert "complexity:" in dspy_section, "DSPy header should include complexity field"


def test_architect_prompt_has_complexity_in_stories_example():
    """Verify STORIES format example includes complexity field."""
    prompt_path = Path("prompts/architect.md")
    content = prompt_path.read_text(encoding="utf-8")

    # Check STORIES example section
    assert "```yaml STORIES" in content

    # Find the STORIES section
    stories_section_start = content.find("```yaml STORIES")
    stories_section_end = content.find("```yaml ARCHITECTURE")
    stories_section = content[stories_section_start:stories_section_end]

    # Verify complexity field is present in examples
    assert "complexity: medium" in stories_section or "complexity: simple" in stories_section or "complexity: complex" in stories_section, \
        "STORIES example should include complexity field with value"

    # Verify multiple stories have complexity
    complexity_count = stories_section.count("complexity:")
    assert complexity_count >= 2, f"Expected at least 2 stories with complexity, found {complexity_count}"


def test_architect_prompt_has_complexity_guidelines():
    """Verify prompt includes complexity classification guidelines."""
    prompt_path = Path("prompts/architect.md")
    content = prompt_path.read_text(encoding="utf-8")

    # Check for complexity guidelines in FORMAT REQUIREMENTS section
    assert "complexity: simple | medium | complex" in content, \
        "Prompt should specify complexity values: simple | medium | complex"

    # Verify it's mentioned as a requirement
    assert "complexity:" in content

    # Verify the three values are documented
    assert "simple" in content.lower()
    assert "medium" in content.lower()
    assert "complex" in content.lower()


def test_architect_prompt_format_requirements_include_complexity():
    """Verify FORMAT REQUIREMENTS section explicitly mentions complexity."""
    prompt_path = Path("prompts/architect.md")
    content = prompt_path.read_text(encoding="utf-8")

    # Find FORMAT REQUIREMENTS section
    format_req_start = content.find("FORMAT REQUIREMENTS:")
    format_req_end = content.find("OUTPUT STRICTLY IN THIS FORMAT:")
    format_req_section = content[format_req_start:format_req_end]

    # Verify complexity is mentioned in requirements
    assert "complexity:" in format_req_section, \
        "FORMAT REQUIREMENTS should explicitly mention complexity field"

    # Verify the allowed values are specified
    assert "simple | medium | complex" in format_req_section, \
        "FORMAT REQUIREMENTS should specify complexity values"
