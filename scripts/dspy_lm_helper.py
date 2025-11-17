"""Utilities to build DSPy LMs from config.yaml per role."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml
import dspy


ROOT = Path(__file__).resolve().parents[1]


def _load_config() -> Dict[str, Any]:
    config_path = ROOT / "config.yaml"
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            return {}
        return data
    except FileNotFoundError:
        return {}


def _env_prefix(role: str) -> str:
    return f"DSPY_{role.upper().replace('-', '_')}"


def _parse_lm_override(spec: str) -> Tuple[str, str]:
    if "/" in spec:
        provider, model = spec.split("/", 1)
    elif ":" in spec:
        provider, model = spec.split(":", 1)
    else:
        provider, model = "ollama", spec
    return provider.strip().lower(), model.strip()


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


def build_lm_for_role(role: str) -> dspy.LM:
    config = _load_config()
    roles_cfg = config.get("roles", {}) if isinstance(config.get("roles", {}), dict) else {}
    providers_cfg = config.get("providers", {}) if isinstance(config.get("providers", {}), dict) else {}

    role_cfg = roles_cfg.get(role, {}) if isinstance(roles_cfg, dict) else {}

    provider = str(role_cfg.get("provider", "ollama")).lower()
    model = role_cfg.get("model", "granite4")
    temperature = float(role_cfg.get("temperature", 0.3))
    max_tokens = int(role_cfg.get("max_tokens", 4096))

    prefix = _env_prefix(role)
    lm_override = os.environ.get(f"{prefix}_LM")
    if lm_override:
        override_provider, override_model = _parse_lm_override(lm_override)
        provider, model = override_provider or provider, override_model or model

    temp_override = _coerce_float(os.environ.get(f"{prefix}_TEMPERATURE"))
    if temp_override is not None:
        temperature = temp_override

    max_tokens_override = _coerce_int(os.environ.get(f"{prefix}_MAX_TOKENS"))
    if max_tokens_override is not None:
        max_tokens = max_tokens_override

    lm_kwargs: Dict[str, Any] = {
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if provider == "ollama":
        base_url = providers_cfg.get("ollama", {}).get("base_url")
        base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        lm_kwargs["base_url"] = base_url
        lm_spec = f"ollama/{model}"
    elif provider in {"vertex_cli", "vertex_sdk"}:
        vertex_cfg = providers_cfg.get(provider, {})
        project = vertex_cfg.get("project_id") or os.environ.get("GCP_PROJECT", "agnostic-pipeline-476015")
        location = vertex_cfg.get("location") or os.environ.get("VERTEX_LOCATION", "us-central1")
        lm_kwargs["project"] = project
        lm_kwargs["location"] = location
        lm_spec = f"vertex_ai/{model}"
    elif provider == "openai":
        lm_spec = f"openai/{model}"
    elif provider == "claude_cli":
        lm_spec = f"anthropic/{model}"
    elif provider == "codex_cli":
        lm_spec = f"codex_cli/{model}"
    else:
        base_url = providers_cfg.get("ollama", {}).get("base_url")
        base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        lm_kwargs["base_url"] = base_url
        lm_spec = f"ollama/{model}"

    return dspy.LM(lm_spec, **lm_kwargs)
