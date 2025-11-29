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
    """Test dev Client with simple complexity uses configured provider/model."""
    config = load_config()
    routing = config.get("routing_by_complexity", {})
    expected_provider = routing["dev"]["simple"]["provider"]
    expected_model = routing["dev"]["simple"]["model"]

    client = Client(role="dev", complexity="simple")
    assert client.provider_type == expected_provider, \
        f"Expected {expected_provider} for dev/simple, got {client.provider_type}"
    assert client.model == expected_model, \
        f"Expected {expected_model} for dev/simple, got {client.model}"


def test_dev_routing_with_real_config_medium():
    """Test dev Client with medium complexity uses configured provider/model."""
    config = load_config()
    routing = config.get("routing_by_complexity", {})
    expected_provider = routing["dev"]["medium"]["provider"]
    expected_model = routing["dev"]["medium"]["model"]

    client = Client(role="dev", complexity="medium")
    assert client.provider_type == expected_provider, \
        f"Expected {expected_provider} for dev/medium, got {client.provider_type}"
    assert client.model == expected_model, \
        f"Expected {expected_model} for dev/medium, got {client.model}"


def test_dev_routing_with_real_config_complex():
    """Test dev Client with complex complexity uses configured provider/model."""
    config = load_config()
    routing = config.get("routing_by_complexity", {})
    expected_provider = routing["dev"]["complex"]["provider"]
    expected_model = routing["dev"]["complex"]["model"]

    client = Client(role="dev", complexity="complex")
    assert client.provider_type == expected_provider, \
        f"Expected {expected_provider} for dev/complex, got {client.provider_type}"
    assert client.model == expected_model, \
        f"Expected {expected_model} for dev/complex, got {client.model}"


def test_qa_routing_with_real_config_simple():
    """Test qa Client with simple complexity uses configured provider/model."""
    config = load_config()
    routing = config.get("routing_by_complexity", {})
    expected_provider = routing["qa"]["simple"]["provider"]
    expected_model = routing["qa"]["simple"]["model"]

    client = Client(role="qa", complexity="simple")
    assert client.provider_type == expected_provider, \
        f"Expected {expected_provider} for qa/simple, got {client.provider_type}"
    assert client.model == expected_model, \
        f"Expected {expected_model} for qa/simple, got {client.model}"


def test_qa_routing_with_real_config_medium():
    """Test qa Client with medium complexity uses configured provider/model."""
    config = load_config()
    routing = config.get("routing_by_complexity", {})
    expected_provider = routing["qa"]["medium"]["provider"]
    expected_model = routing["qa"]["medium"]["model"]

    client = Client(role="qa", complexity="medium")
    assert client.provider_type == expected_provider, \
        f"Expected {expected_provider} for qa/medium, got {client.provider_type}"
    assert client.model == expected_model, \
        f"Expected {expected_model} for qa/medium, got {client.model}"


def test_qa_routing_with_real_config_complex():
    """Test qa Client with complex complexity uses configured provider/model."""
    config = load_config()
    routing = config.get("routing_by_complexity", {})
    expected_provider = routing["qa"]["complex"]["provider"]
    expected_model = routing["qa"]["complex"]["model"]

    client = Client(role="qa", complexity="complex")
    assert client.provider_type == expected_provider, \
        f"Expected {expected_provider} for qa/complex, got {client.provider_type}"
    assert client.model == expected_model, \
        f"Expected {expected_model} for qa/complex, got {client.model}"


def test_fallback_when_no_complexity_provided():
    """Test that Client falls back to defaults.complexity when story has no complexity."""
    config = load_config()
    defaults = config.get("defaults", {})
    default_complexity = defaults.get("complexity", "medium")

    # Get expected provider/model for default complexity
    routing = config.get("routing_by_complexity", {})
    expected_provider = routing["dev"][default_complexity]["provider"]
    expected_model = routing["dev"][default_complexity]["model"]

    # Create client without complexity
    client = Client(role="dev", complexity=None)

    # Should use default complexity routing
    assert client.provider_type == expected_provider, \
        f"Expected {expected_provider} for default {default_complexity}, got {client.provider_type}"
    assert client.model == expected_model, \
        f"Expected {expected_model} for default {default_complexity}, got {client.model}"


def test_routing_matrices_are_complete():
    """Verify routing matrices have all required complexity levels configured."""
    config = load_config()
    routing = config.get("routing_by_complexity", {})

    # Verify dev matrix has all complexity levels
    for complexity in ["simple", "medium", "complex"]:
        assert complexity in routing["dev"], \
            f"Dev matrix missing complexity: {complexity}"
        dev_config = routing["dev"][complexity]
        assert "provider" in dev_config and dev_config["provider"], \
            f"Dev/{complexity} missing provider"
        assert "model" in dev_config and dev_config["model"], \
            f"Dev/{complexity} missing model"

    # Verify qa matrix has all complexity levels
    for complexity in ["simple", "medium", "complex"]:
        assert complexity in routing["qa"], \
            f"QA matrix missing complexity: {complexity}"
        qa_config = routing["qa"][complexity]
        assert "provider" in qa_config and qa_config["provider"], \
            f"QA/{complexity} missing provider"
        assert "model" in qa_config and qa_config["model"], \
            f"QA/{complexity} missing model"
