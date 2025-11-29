from scripts.utils.complexity_router import resolve_role_model_for_complexity


def test_routing_disabled_returns_none():
    config = {"features": {"routing_by_complexity_enabled": False}}
    provider, model = resolve_role_model_for_complexity(config, "dev", "simple")
    assert provider is None
    assert model is None


def test_routing_simple_story():
    config = {
        "features": {"routing_by_complexity_enabled": True},
        "routing_by_complexity": {
            "dev": {
                "simple": {"provider": "ollama", "model": "qwen2.5-coder:7b"},
            }
        },
    }
    provider, model = resolve_role_model_for_complexity(config, "dev", "simple")
    assert provider == "ollama"
    assert model == "qwen2.5-coder:7b"


def test_missing_complexity_uses_default_medium():
    config = {
        "features": {"routing_by_complexity_enabled": True},
        "defaults": {"complexity": "medium"},
        "routing_by_complexity": {
            "dev": {
                "medium": {"provider": "vertex_sdk", "model": "gemini-2.5-pro"},
            }
        },
    }
    provider, model = resolve_role_model_for_complexity(config, "dev", None)
    assert provider == "vertex_sdk"
    assert model == "gemini-2.5-pro"


def test_incomplete_routing_returns_none():
    config = {
        "features": {"routing_by_complexity_enabled": True},
        "routing_by_complexity": {"dev": {"simple": {"provider": "ollama"}}},
    }
    provider, model = resolve_role_model_for_complexity(config, "dev", "simple")
    assert provider is None
    assert model is None
