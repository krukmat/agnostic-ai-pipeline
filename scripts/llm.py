from __future__ import annotations

import os
import sys
import json
import pathlib
from typing import Any, Dict, Optional

import httpx
import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG_P = ROOT / "config.yaml"


def load_config() -> Dict[str, Any]:
    if CONFIG_P.exists():
        try:
            data = yaml.safe_load(CONFIG_P.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                return {}
            return data
        except Exception:
            return {}
    return {}


def _default_role() -> str:
    role = os.environ.get("ROLE", "").strip().lower()
    if role:
        return role
    argv0 = " ".join(sys.argv).lower()
    if "architect" in argv0:
        return "architect"
    if "qa" in argv0:
        return "qa"
    return "dev"


class Client:
    """
    Backward-compatible LLM client.

    New-style init:
        Client(role="architect")  # uses config.yaml to resolve provider/model

    Legacy-style init (kept for scripts that call with positional args):
        Client("ollama", "mistral:7b-instruct", 0.2, 2048, "http://localhost:11434")
        ^provider  ^model                     ^temperature ^max_tokens ^base_url
    """
    def __init__(self, role: Optional[str] = None, *legacy_args, **overrides):
        cfg = load_config()
        self.cfg = cfg

        # Defaults
        self.role = (role or _default_role()).lower() if isinstance(role, str) else _default_role()
        self.model = "qwen2.5-coder:7b"
        self.temperature = 0.3
        self.max_tokens = 2048

        # Provider defaults
        self.provider_type = "ollama"
        self.ollama_base = os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        self.oai_base = os.environ.get("OPENAI_API_BASE") or "http://localhost:4010/v1"
        self.oai_key = os.environ.get("OPENAI_API_KEY", "dummy")

        # Load from config.yaml (roles/providers)
        roles = cfg.get("roles", {}) if isinstance(cfg.get("roles", {}), dict) else {}
        role_cfg = roles.get(self.role, {}) if isinstance(roles, dict) else {}
        providers = cfg.get("providers", {}) if isinstance(cfg.get("providers", {}), dict) else {}
        provider_key = role_cfg.get("provider") or "ollama"
        provider_cfg = providers.get(provider_key, {"type": "ollama", "base_url": "http://localhost:11434"})

        # Apply config defaults
        self.model = role_cfg.get("model", self.model)
        self.temperature = float(role_cfg.get("temperature", self.temperature))
        self.max_tokens = int(role_cfg.get("max_tokens", self.max_tokens))
        self.provider_type = provider_cfg.get("type", "ollama")
        base_url = provider_cfg.get("base_url")

        if self.provider_type == "ollama":
            self.ollama_base = os.environ.get("OLLAMA_BASE_URL") or base_url or self.ollama_base
        else:
            self.oai_base = os.environ.get("OPENAI_API_BASE") or base_url or self.oai_base

        # Legacy positional override (provider, model, temp, max_tokens, base_url)
        if legacy_args:
            prov = str(legacy_args[0]).strip().lower() if len(legacy_args) >= 1 else None
            model = legacy_args[1] if len(legacy_args) >= 2 else None
            temp = legacy_args[2] if len(legacy_args) >= 3 else None
            maxt = legacy_args[3] if len(legacy_args) >= 4 else None
            base = legacy_args[4] if len(legacy_args) >= 5 else None

            if prov in ("ollama", "openai"):
                self.provider_type = prov
            if isinstance(model, str) and model:
                self.model = model
            if isinstance(temp, (int, float)):
                self.temperature = float(temp)
            if isinstance(maxt, (int, float)):
                self.max_tokens = int(maxt)
            if isinstance(base, str) and base:
                if self.provider_type == "ollama":
                    self.ollama_base = base
                else:
                    self.oai_base = base

        # Keyword overrides (model=..., temperature=..., max_tokens=..., provider="..." base_url="...")
        if "model" in overrides and overrides["model"]:
            self.model = str(overrides["model"])
        if "temperature" in overrides and overrides["temperature"] is not None:
            self.temperature = float(overrides["temperature"])
        if "max_tokens" in overrides and overrides["max_tokens"] is not None:
            self.max_tokens = int(overrides["max_tokens"])
        if "provider" in overrides and overrides["provider"]:
            p = str(overrides["provider"]).strip().lower()
            if p in ("ollama", "openai"):
                self.provider_type = p
        if "base_url" in overrides and overrides["base_url"]:
            if self.provider_type == "ollama":
                self.ollama_base = str(overrides["base_url"])
            else:
                self.oai_base = str(overrides["base_url"])

    async def chat(self, system: str, user: str) -> str:
        if self.provider_type == "openai":
            return await self._openai_chat(system, user)
        # prefer /api/chat, fallback to /api/generate for older Ollama
        try:
            return await self._ollama_chat(system, user)
        except Exception:
            return await self._ollama_generate(system, user)

    async def _ollama_chat(self, system: str, user: str) -> str:
        url = f"{self.ollama_base.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 404:
                raise RuntimeError("OLLAMA_CHAT_404")
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                if "message" in data and isinstance(data["message"], dict):
                    return data["message"].get("content", "")
                if "content" in data:
                    return data.get("content", "")
                if "response" in data:
                    return data["response"]
            return r.text

    async def _ollama_generate(self, system: str, user: str) -> str:
        url = f"{self.ollama_base.rstrip('/')}/api/generate"
        prompt = f"System:\n{system}\n\nUser:\n{user}\n\nAssistant:"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and "response" in data:
                return data["response"]
            return r.text

    async def _openai_chat(self, system: str, user: str) -> str:
        url = f"{self.oai_base.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.oai_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            try:
                return data["choices"][0]["message"]["content"]
            except Exception:
                return json.dumps(data)


# Backward-compat alias
LLMClient = Client
