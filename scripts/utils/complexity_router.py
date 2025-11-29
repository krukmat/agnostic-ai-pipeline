from __future__ import annotations

"""Helpers to resolve provider/model based on story complexity."""

from typing import Any, Dict, Optional, Tuple

from logger import logger


def _as_dict(candidate: Any) -> Dict[str, Any]:
    """Return candidate if dict, else empty dict."""
    return candidate if isinstance(candidate, dict) else {}


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def resolve_role_model_for_complexity(
    config: Optional[Dict[str, Any]],
    role: Optional[str],
    complexity: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Return (provider, model) for role/complexity or (None, None) if disabled/missing."""
    cfg = config if isinstance(config, dict) else {}
    role_key = _normalize(role)
    if not role_key:
        logger.debug("[ROUTING] Missing role, using defaults.")
        return (None, None)

    features = _as_dict(cfg.get("features"))
    if not bool(features.get("routing_by_complexity_enabled")):
        logger.debug(f"[ROUTING] Complexity routing disabled for role={role_key}.")
        return (None, None)

    defaults = _as_dict(cfg.get("defaults"))
    complexity_key = _normalize(complexity) or _normalize(defaults.get("complexity")) or "medium"
    if complexity and not complexity_key:
        logger.debug(f"[ROUTING] Empty complexity provided for role={role_key}, using default.")

    routing = _as_dict(cfg.get("routing_by_complexity"))
    role_routing = _as_dict(routing.get(role_key))
    if not role_routing:
        logger.debug(f"[ROUTING] No routing entry for role={role_key}.")
        return (None, None)

    complexity_cfg = _as_dict(role_routing.get(complexity_key))
    provider = complexity_cfg.get("provider")
    model = complexity_cfg.get("model")

    if isinstance(provider, str) and provider.strip() and isinstance(model, str) and model.strip():
        provider = provider.strip()
        model = model.strip()
        logger.info(
            "[ROUTING] %s/%s -> %s/%s",
            role_key,
            complexity_key,
            provider,
            model,
        )
        return (provider, model)

    logger.debug(
        f"[ROUTING] Incomplete routing for role={role_key}, complexity={complexity_key}. Falling back to defaults."
    )
    return (None, None)
