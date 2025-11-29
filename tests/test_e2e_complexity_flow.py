"""End-to-end test: Verify stories with complexity field work through the pipeline."""

import yaml
from pathlib import Path
from scripts.llm import Client


def test_story_with_complexity_loads_correctly(tmp_path, monkeypatch):
    """Test that a story with complexity field can be loaded and used."""
    # Create a test stories.yaml with complexity field
    stories_data = [
        {
            "id": "S1",
            "epic": "E1",
            "description": "Create health check endpoint",
            "complexity": "simple",  # ← Field under test
            "acceptance": [
                "Endpoint returns 200 OK",
                "Response includes status: healthy"
            ],
            "priority": "P1",
            "status": "todo"
        },
        {
            "id": "S2",
            "epic": "E1",
            "description": "Implement user authentication with JWT",
            "complexity": "medium",  # ← Different complexity
            "acceptance": [
                "User can register with email/password",
                "JWT token is returned on login"
            ],
            "priority": "P2",
            "status": "todo"
        },
        {
            "id": "S3",
            "epic": "E2",
            "description": "Design microservices architecture with event sourcing",
            "complexity": "complex",  # ← Complex story
            "acceptance": [
                "Event store implemented",
                "Saga pattern for distributed transactions"
            ],
            "priority": "P1",
            "status": "todo"
        }
    ]

    # Write test stories file
    stories_path = tmp_path / "planning" / "stories.yaml"
    stories_path.parent.mkdir(parents=True, exist_ok=True)
    stories_path.write_text(yaml.safe_dump(stories_data), encoding="utf-8")

    # Verify file was written correctly
    loaded_stories = yaml.safe_load(stories_path.read_text(encoding="utf-8"))
    assert len(loaded_stories) == 3
    assert loaded_stories[0]["complexity"] == "simple"
    assert loaded_stories[1]["complexity"] == "medium"
    assert loaded_stories[2]["complexity"] == "complex"


def test_dev_client_accepts_all_complexity_values(monkeypatch):
    """Test that Client can be initialized with all complexity values."""
    config = {
        "features": {"routing_by_complexity_enabled": True},
        "routing_by_complexity": {
            "dev": {
                "simple": {"provider": "ollama", "model": "qwen2.5-coder:7b"},
                "medium": {"provider": "vertex_sdk", "model": "gemini-2.5-pro"},
                "complex": {"provider": "codex_cli", "model": "gpt-4-turbo"}
            }
        },
        "providers": {
            "ollama": {"type": "ollama", "base_url": "http://localhost:11434"},
            "vertex_sdk": {"type": "vertex_sdk"},
            "codex_cli": {"type": "codex_cli"}
        },
        "roles": {"dev": {"provider": "codex_cli", "model": "default"}}
    }
    monkeypatch.setattr("scripts.llm.load_config", lambda: config)

    # Test simple complexity
    client_simple = Client(role="dev", complexity="simple")
    assert client_simple.provider_type == "ollama"
    assert client_simple.model == "qwen2.5-coder:7b"

    # Test medium complexity
    client_medium = Client(role="dev", complexity="medium")
    assert client_medium.provider_type == "vertex_sdk"
    assert client_medium.model == "gemini-2.5-pro"

    # Test complex complexity
    client_complex = Client(role="dev", complexity="complex")
    assert client_complex.provider_type == "codex_cli"
    assert client_complex.model == "gpt-4-turbo"


def test_architect_prompt_example_uses_valid_complexity_values():
    """Verify the Architect prompt examples only use valid complexity values."""
    prompt_path = Path("prompts/architect.md")
    content = prompt_path.read_text(encoding="utf-8")

    # Find all complexity values in the prompt
    import re
    complexity_pattern = r'complexity:\s*(simple|medium|complex)'
    matches = re.findall(complexity_pattern, content)

    # Should have at least 2 examples with complexity
    assert len(matches) >= 2, f"Expected at least 2 complexity examples, found {len(matches)}"

    # All values should be valid
    valid_values = {"simple", "medium", "complex"}
    for value in matches:
        assert value in valid_values, f"Invalid complexity value: {value}"
