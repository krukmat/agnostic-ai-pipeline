import os

from recommend.model_recommender import recommend_model, _load_cfg


def test_recommender_returns_configured_model_ids(monkeypatch):
    monkeypatch.setenv("MODEL_RECO_ENABLED", "true")
    cfg = _load_cfg()
    routes = cfg.get("routes", {})
    for role, route in routes.items():
        strong = route["strong"]
        weak = route["weak"]
        out = recommend_model("hello world", role)
        assert out in {strong, weak}, f"Unexpected model '{out}' for role={role}"


def test_disable_flag_uses_weak_model(monkeypatch):
    cfg = _load_cfg()
    role, route = next(iter(cfg["routes"].items()))
    monkeypatch.setenv("MODEL_RECO_ENABLED", "false")
    out = recommend_model("anything", role)
    assert out == route["weak"]
