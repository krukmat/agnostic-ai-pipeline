from scripts.utils import complexity_analyzer as ca
from scripts.utils import complexity_router as cr


def test_analyze_story_complexity_tiers():
    simple = {"id": "S1", "description": "simple CRUD get endpoint", "acceptance": ["a", "b"]}
    medium = {"id": "S2", "description": "API with auth and pagination", "acceptance": ["a", "b", "c"]}
    complex_story = {"id": "S3", "description": "distributed microservice with migration and orchestration", "acceptance": ["a"] * 6}

    assert ca.analyze_story_complexity(simple) == "simple"
    assert ca.analyze_story_complexity(medium) == "medium"
    assert ca.analyze_story_complexity(complex_story) == "complex"

    dist = ca.get_complexity_distribution([simple, medium, complex_story])
    assert dist == {"simple": 1, "medium": 1, "complex": 1}


def test_complexity_router_resolves_and_falls_back():
    cfg = {
        "features": {"routing_by_complexity_enabled": True},
        "defaults": {"complexity": "medium"},
        "routing_by_complexity": {
            "dev": {
                "simple": {"provider": "p1", "model": "m1"},
                "medium": {"provider": "p2", "model": "m2"},
            }
        },
    }
    assert cr.resolve_role_model_for_complexity(cfg, "dev", "simple") == ("p1", "m1")
    # Missing provider/model returns fallbacks
    cfg["routing_by_complexity"]["dev"]["complex"] = {"provider": "", "model": ""}
    assert cr.resolve_role_model_for_complexity(cfg, "dev", "complex") == (None, None)
    # Disabled feature returns None
    cfg_disabled = {**cfg, "features": {"routing_by_complexity_enabled": False}}
    assert cr.resolve_role_model_for_complexity(cfg_disabled, "dev", "simple") == (None, None)
