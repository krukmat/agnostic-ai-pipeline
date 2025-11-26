from __future__ import annotations

"""Shared configuration loader helpers for role scripts.

Provides small strategy-style helpers to return config alongside commonly
accessed sub-sections (drivers, targets) and a bool normalizer used across
roles.
"""

from typing import Any, Dict, Tuple

from common import load_config


def _load_base_config() -> Dict[str, Any]:
    """Load config.yaml defensively (never raise)."""
    try:
        cfg = load_config()
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def load_config_base() -> Dict[str, Any]:
    """Return raw config dict (defensive)."""
    return _load_base_config()


def load_config_with_drivers() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (config, drivers_config) tuple for Dev-like consumers."""
    cfg = _load_base_config()
    drv_cfg = cfg.get("drivers") or {}
    return cfg, drv_cfg


def load_qa_config() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Return (config, drivers_config, targets) tuple for QA-like consumers."""
    cfg = _load_base_config()
    drv_cfg = cfg.get("drivers") or {}
    targets = (cfg.get("project") or {}).get("targets") or {}
    return cfg, drv_cfg, targets


def normalize_bool(value: Any, default: bool = False) -> bool:
    """Normalize various representations of boolean to bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)
