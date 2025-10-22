from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import yaml
from rorf.controller import Controller


CONFIG_PATH = os.getenv("MODEL_RECO_CONFIG", "config/model_recommender.yaml")


def is_enabled() -> bool:
    return os.getenv("MODEL_RECO_ENABLED", "true").lower() == "true"


RECO_ENABLED = is_enabled()


@dataclass(frozen=True)
class RoleRoute:
    router_id: str
    strong: str
    weak: str
    threshold: float


@lru_cache(maxsize=1)
def _load_cfg() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=16)
def _build_controller(router_id: str, strong: str, weak: str, threshold: float) -> Controller:
    return Controller(router=router_id, model_a=strong, model_b=weak, threshold=threshold)


def _role_route(role: Optional[str]) -> RoleRoute:
    cfg = _load_cfg()
    routes = cfg.get("routes", {}) or {}
    default_threshold = float(cfg.get("default_threshold", 0.30))

    key = (role or "default")
    role_cfg = routes.get(key)
    if not role_cfg:
        if not routes:
            raise RuntimeError("No routes configured in model_recommender.yaml")
        key, role_cfg = next(iter(routes.items()))

    router_id = role_cfg["router_id"]
    strong = role_cfg["strong"]
    weak = role_cfg["weak"]
    threshold = float(role_cfg.get("threshold", default_threshold))
    return RoleRoute(router_id, strong, weak, threshold)


def recommend_model(prompt: str, role: Optional[str] = None) -> str:
    """Return a model id for this prompt, optionally conditioned on role."""
    rr = _role_route(role)

    if not is_enabled():
        return rr.weak

    controller = _build_controller(rr.router_id, rr.strong, rr.weak, rr.threshold)
    return controller.route(prompt)
