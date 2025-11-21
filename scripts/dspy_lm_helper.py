"""Utilities to build DSPy LMs from config.yaml per role."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml
import dspy


ROOT = Path(__file__).resolve().parents[1]
_CONFIG_CACHE: Dict[str, Any] | None = None


def _load_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    config_path = ROOT / "config.yaml"
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            data = {}
    except FileNotFoundError:
        data = {}
    _CONFIG_CACHE = data
    return data


def _coerce_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_role_config(role: str) -> Dict[str, Any]:
    config = _load_config()
    roles_cfg = config.get("roles", {}) if isinstance(config.get("roles", {}), dict) else {}
    role_cfg = roles_cfg.get(role, {})
    return role_cfg if isinstance(role_cfg, dict) else {}


def build_lm_for_role(role: str, **override_kwargs) -> dspy.LM:
    config = _load_config()
    providers_cfg = config.get("providers", {}) if isinstance(config.get("providers", {}), dict) else {}
    role_cfg = _get_role_config(role)

    provider = str(role_cfg.get("provider", "ollama")).lower()
    model = role_cfg.get("model", "granite4")
    temperature = float(role_cfg.get("temperature", 0.3))
    max_tokens = int(role_cfg.get("max_tokens", 4096))

    lm_kwargs: Dict[str, Any] = {
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    for key, value in override_kwargs.items():
        if value is not None:
            lm_kwargs[key] = value

    if provider == "ollama":
        base_url = providers_cfg.get("ollama", {}).get("base_url")
        base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        lm_kwargs["base_url"] = base_url
        lm_spec = f"ollama/{model}"
    elif provider in {"vertex_cli", "vertex_sdk"}:
        vertex_cfg = providers_cfg.get(provider, {})
        project = vertex_cfg.get("project_id")
        location = vertex_cfg.get("location")
        lm_kwargs["project"] = project
        lm_kwargs["location"] = location
        lm_spec = f"vertex_ai/{model}"
    elif provider == "openai":
        lm_spec = f"openai/{model}"
    elif provider == "claude_cli":
        lm_spec = f"anthropic/{model}"
    else:
        base_url = providers_cfg.get("ollama", {}).get("base_url")
        base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        lm_kwargs["base_url"] = base_url
        lm_spec = f"ollama/{model}"

    return dspy.LM(lm_spec, **lm_kwargs)


def get_role_output_cap(
    role: str,
    cap_name: str,
    *,
    default_ratio: float = 0.08,
    default_min_tokens: int = 600,
) -> int:
    """Return max output tokens for a sub-module (e.g., architect stories)."""
    role_cfg = _get_role_config(role)
    base_max_tokens = int(role_cfg.get("max_tokens", 4096))
    caps_cfg = role_cfg.get("output_caps", {})
    cap_cfg = caps_cfg.get(cap_name) if isinstance(caps_cfg, dict) else None

    resolved_min = default_min_tokens
    ratio = default_ratio
    tokens: int | None = None

    if isinstance(cap_cfg, dict):
        if isinstance(cap_cfg.get("tokens"), (int, float)):
            tokens = int(cap_cfg["tokens"])
        elif isinstance(cap_cfg.get("ratio"), (int, float)):
            ratio = float(cap_cfg["ratio"])
        if isinstance(cap_cfg.get("min_tokens"), (int, float)):
            resolved_min = int(cap_cfg["min_tokens"])
    elif isinstance(cap_cfg, (int, float)):
        if cap_cfg > 1:
            tokens = int(cap_cfg)
        else:
            ratio = float(cap_cfg)

    if tokens is None:
        tokens = int(base_max_tokens * ratio)
    return max(resolved_min, tokens)


def get_role_max_tokens(role: str, default: int = 4096) -> int:
    role_cfg = _get_role_config(role)
    try:
        return int(role_cfg.get("max_tokens", default))
    except Exception:
        return default


def pick_max_tokens_for(role: str, cap_tokens: int) -> int:
    """Pick max tokens for LM based on context.

    - In MiPRO mode (DSPY_MIPRO_MODE=1), prefer a higher ceiling to avoid truncation:
      * use env DSPY_MIPRO_MAX_TOKENS if present,
      * else roles.<role>.max_tokens from config,
      * else fallback to cap_tokens.
    - In normal mode, return cap_tokens.
    """
    if os.environ.get("DSPY_MIPRO_MODE") == "1":
        env_tok = os.environ.get("DSPY_MIPRO_MAX_TOKENS")
        if env_tok:
            try:
                return int(env_tok)
            except Exception:
                pass
        return get_role_max_tokens(role, default=cap_tokens)
    return cap_tokens
