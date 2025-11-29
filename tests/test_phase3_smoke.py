"""Phase 3 smoke tests: Verify routing with feature flag enabled."""

import yaml
from pathlib import Path
from scripts.llm import Client, load_config


def test_feature_flag_is_enabled():
    """Verify routing_by_complexity_enabled is true in config."""
    config = load_config()
    features = config.get("features", {})
    assert features.get("routing_by_complexity_enabled") is True, \
        "Phase 3 requires routing_by_complexity_enabled: true"


def test_routing_matrices_configured():
    """Verify dev and qa routing matrices are configured."""
    config = load_config()
    routing = config.get("routing_by_complexity", {})

    # Check dev matrix
    assert "dev" in routing, "Dev routing matrix missing"
    dev_matrix = routing["dev"]
    assert "simple" in dev_matrix
    assert "medium" in dev_matrix
    assert "complex" in dev_matrix

    # Check qa matrix
    assert "qa" in routing, "QA routing matrix missing"
    qa_matrix = routing["qa"]
    assert "simple" in qa_matrix
    assert "medium" in qa_matrix
    assert "complex" in qa_matrix


def test_dev_routing_with_real_config_simple():
    """Test dev Client with simple complexity uses ollama/qwen2.5-coder:7b."""
    client = Client(role="dev", complexity="simple")
    assert client.provider_type == "ollama", \
        f"Expected ollama for dev/simple, got {client.provider_type}"
    assert client.model == "qwen2.5-coder:7b", \
        f"Expected qwen2.5-coder:7b for dev/simple, got {client.model}"


def test_dev_routing_with_real_config_medium():
    """Test dev Client with medium complexity uses vertex_sdk/gemini-2.5-pro."""
    client = Client(role="dev", complexity="medium")
    assert client.provider_type == "vertex_sdk", \
        f"Expected vertex_sdk for dev/medium, got {client.provider_type}"
    assert client.model == "gemini-2.5-pro", \
        f"Expected gemini-2.5-pro for dev/medium, got {client.model}"


def test_dev_routing_with_real_config_complex():
    """Test dev Client with complex complexity uses codex_cli/gpt-4-turbo."""
    client = Client(role="dev", complexity="complex")
    assert client.provider_type == "codex_cli", \
        f"Expected codex_cli for dev/complex, got {client.provider_type}"
    assert client.model == "gpt-4-turbo", \
        f"Expected gpt-4-turbo for dev/complex, got {client.model}"


def test_qa_routing_with_real_config_simple():
    """Test qa Client with simple complexity uses ollama/qwen2.5-coder:7b."""
    client = Client(role="qa", complexity="simple")
    assert client.provider_type == "ollama", \
        f"Expected ollama for qa/simple, got {client.provider_type}"
    assert client.model == "qwen2.5-coder:7b", \
        f"Expected qwen2.5-coder:7b for qa/simple, got {client.model}"


def test_qa_routing_with_real_config_medium():
    """Test qa Client with medium complexity uses vertex_cli/gemini-2.5-pro."""
    client = Client(role="qa", complexity="medium")
    assert client.provider_type == "vertex_cli", \
        f"Expected vertex_cli for qa/medium, got {client.provider_type}"
    assert client.model == "gemini-2.5-pro", \
        f"Expected gemini-2.5-pro for qa/medium, got {client.model}"


def test_qa_routing_with_real_config_complex():
    """Test qa Client with complex complexity uses claude_cli/claude-3-5-sonnet-latest."""
    client = Client(role="qa", complexity="complex")
    assert client.provider_type == "claude_cli", \
        f"Expected claude_cli for qa/complex, got {client.provider_type}"
    assert client.model == "claude-3-5-sonnet-latest", \
        f"Expected claude-3-5-sonnet-latest for qa/complex, got {client.model}"


def test_fallback_when_no_complexity_provided():
    """Test that Client falls back to defaults.complexity when story has no complexity."""
    config = load_config()
    defaults = config.get("defaults", {})
    default_complexity = defaults.get("complexity", "medium")

    # Create client without complexity
    client = Client(role="dev", complexity=None)

    # Should use default complexity routing (medium)
    if default_complexity == "medium":
        assert client.provider_type == "vertex_sdk", \
            f"Expected vertex_sdk for default medium, got {client.provider_type}"
        assert client.model == "gemini-2.5-pro", \
            f"Expected gemini-2.5-pro for default medium, got {client.model}"


def test_routing_matrices_match_documentation():
    """Verify routing matrices match the documented configuration."""
    config = load_config()
    routing = config.get("routing_by_complexity", {})

    # Expected dev matrix from docs
    expected_dev = {
        "simple": {"provider": "ollama", "model": "qwen2.5-coder:7b"},
        "medium": {"provider": "vertex_sdk", "model": "gemini-2.5-pro"},
        "complex": {"provider": "codex_cli", "model": "gpt-4-turbo"}
    }

    # Expected qa matrix from docs
    expected_qa = {
        "simple": {"provider": "ollama", "model": "qwen2.5-coder:7b"},
        "medium": {"provider": "vertex_cli", "model": "gemini-2.5-pro"},
        "complex": {"provider": "claude_cli", "model": "claude-3-5-sonnet-latest"}
    }

    # Verify dev matrix
    for complexity in ["simple", "medium", "complex"]:
        actual = routing["dev"][complexity]
        expected = expected_dev[complexity]
        assert actual["provider"] == expected["provider"], \
            f"Dev/{complexity} provider mismatch: {actual['provider']} != {expected['provider']}"
        assert actual["model"] == expected["model"], \
            f"Dev/{complexity} model mismatch: {actual['model']} != {expected['model']}"

    # Verify qa matrix
    for complexity in ["simple", "medium", "complex"]:
        actual = routing["qa"][complexity]
        expected = expected_qa[complexity]
        assert actual["provider"] == expected["provider"], \
            f"QA/{complexity} provider mismatch: {actual['provider']} != {expected['provider']}"
        assert actual["model"] == expected["model"], \
            f"QA/{complexity} model mismatch: {actual['model']} != {expected['model']}"
