from __future__ import annotations

import os
import sys
import json
import pathlib
import asyncio
import subprocess
import time
import re
from typing import Any, Dict, Optional

import httpx
import yaml

from logger import logger  # Import the logger

try:
    from scripts.utils.complexity_router import resolve_role_model_for_complexity
except Exception:  # pragma: no cover - fallback when executed differently
    from utils.complexity_router import resolve_role_model_for_complexity  # type: ignore


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

# Add ROOT to sys.path to allow importing scripts package
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from recommend.model_recommender import is_enabled as _reco_enabled, recommend_model
except Exception as exc:  # pragma: no cover - recommender optional
    logger.warning(f"[LLM] Model recommender import failed: {exc}")
    recommend_model = None  # type: ignore[assignment]
    _reco_enabled = lambda: False  # type: ignore[assignment]

PROVIDER_REGISTRY: dict[str, Any] = {}
_providers_import_err: Exception | None = None

# TECH DEBT - High cyclomatic complexity in this module
# Current issue: High CC in _cli_chat_async, _cli_chat
# Root cause: Multiple provider handling, fallback logic, and CLI bridging mixed in main logic
# Refactor plan: Extract provider-specific logic to separate provider classes or factories
# Priority: Medium

try:
    from .providers import PROVIDER_REGISTRY  # type: ignore
except Exception as exc_relative:  # pragma: no cover - providers optional
    try:
        from scripts.providers import PROVIDER_REGISTRY  # type: ignore
    except Exception as exc_absolute:
        _providers_import_err = exc_absolute
        logger.warning(f"[LLM] Providers import failed: {exc_absolute}")

if not PROVIDER_REGISTRY and _providers_import_err:
    logger.debug(f"[LLM] Provider registry fallback unavailable: {_providers_import_err}")

CONFIG_P = ROOT / "config.yaml"


def load_config() -> Dict[str, Any]:
    if CONFIG_P.exists():
        try:
            data = yaml.safe_load(CONFIG_P.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                logger.warning("[LLM] config.yaml is not a dictionary. Returning empty config.")
                return {}
            return data
        except Exception as exc:
            logger.error(f"[LLM] Error loading config.yaml: {exc}", exc_info=True)
            return {}
    logger.info("[LLM] config.yaml not found. Returning empty config.")
    return {}


def _default_role() -> str:
    role = os.environ.get("ROLE", "").strip().lower()
    if role:
        logger.debug(f"[LLM] Role from env: {role}")
        return role
    argv0 = " ".join(sys.argv).lower()
    if "architect" in argv0:
        logger.debug("[LLM] Inferred role: architect")
        return "architect"
    if "qa" in argv0:
        logger.debug("[LLM] Inferred role: qa")
        return "qa"
    logger.debug("[LLM] Inferred role: dev")
    return "dev"


def truncate_context_hierarchically(context: str, budget: int) -> str:
    """
    R1-T3: Truncate context to fit budget, preserving paragraph boundaries.

    Splits by double newlines (paragraph separator) and includes complete paragraphs
    until budget is exceeded. Ensures truncation happens at logical boundaries,
    not mid-sentence.

    Args:
        context: Full context string
        budget: Maximum characters allowed

    Returns:
        Truncated context that fits within budget (or original if <= budget)
    """
    if len(context) <= budget:
        return context

    # Split by paragraph (double newline is typical separator)
    paragraphs = context.split("\n\n")
    truncated = ""

    for para in paragraphs:
        # Check if adding this paragraph would exceed budget
        # +2 for the separator "\n\n"
        next_length = len(truncated) + len(para) + (2 if truncated else 0)

        if next_length <= budget:
            if truncated:
                truncated += "\n\n"
            truncated += para
        else:
            # Budget exceeded - stop here with what we have
            break

    # If no paragraphs fit (first paragraph > budget), truncate that paragraph
    # at sentence boundary as fallback
    if not truncated and paragraphs:
        first_para = paragraphs[0]
        if len(first_para) > budget:
            # Try to break at last sentence before budget
            sentences = first_para.replace("! ", ".\n").replace("? ", ".\n").split(".\n")
            truncated = ""
            for sent in sentences:
                if len(truncated) + len(sent) + 2 <= budget:
                    if truncated:
                        truncated += ". "
                    truncated += sent
                else:
                    break
            if truncated and not truncated.endswith((".","!", "?")):
                truncated += "."
        else:
            truncated = first_para

    return truncated if truncated else context[:budget]


class Client:
    """
    Backward-compatible LLM client.

    New-style init:
        Client(role="architect")  # uses config.yaml to resolve provider/model

    Legacy-style init (kept for scripts that call with positional args):
        Client("ollama", "mistral:7b-instruct", 0.2, 2048, "http://localhost:11434")
        ^provider  ^model                     ^temperature ^max_tokens ^base_url
    """
    def __init__(
        self,
        role: Optional[str] = None,
        *legacy_args,
        complexity: Optional[str] = None,
        **overrides,
    ):
        cfg = load_config()
        self.cfg = cfg

        # Extract initialization steps to reduce CC
        # Detect legacy format: if role is a provider name and we have legacy_args, it's legacy mode
        is_legacy_mode = (
            isinstance(role, str) and
            role.lower().strip() in ("ollama", "openai", "codex_cli", "vertex_cli", "vertex_sdk", "claude_cli", "google_ai_gemini") and
            legacy_args
        )

        if is_legacy_mode:
            # Legacy mode: role param was actually provider, shift legacy_args left
            legacy_args = (role,) + legacy_args
            self.role = _default_role()
        else:
            self.role = (role or _default_role()).lower() if isinstance(role, str) else _default_role()

        self._initialize_defaults()
        self._initialize_provider_config(cfg, complexity)
        self._apply_legacy_overrides(legacy_args)
        self._apply_keyword_overrides(overrides)

        # Log complexity routing if applicable
        routed_provider, routed_model = resolve_role_model_for_complexity(cfg, self.role, complexity)
        if routed_provider and routed_model:
            logger.info(
                "[LLM] Complexity routing applied for role '%s' (complexity=%s) -> %s/%s",
                self.role,
                complexity or "auto",
                routed_provider,
                routed_model,
            )

        logger.debug(
            f"[LLM] Client initialized for role '{self.role}': provider={self.provider_type}, model={self.model}, temp={self.temperature}, max_tokens={self.max_tokens}"
        )

    def _initialize_defaults(self):
        """Initialize default values for model, temperature, max_tokens, and provider settings.

        Extracted from __init__ to reduce CC (lines 175-204).
        Sets defaults for:
        - Model and hyperparameter defaults
        - Provider-specific endpoints (ollama_base, oai_base, etc.)
        - CLI provider configuration defaults
        """
        # Model and hyperparameter defaults
        self.model = "qwen2.5-coder:7b"
        self.temperature = 0.3
        self.max_tokens = 2048

        # Provider defaults
        self.provider_type = "ollama"
        self.ollama_base = os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434"
        self.oai_base = os.environ.get("OPENAI_API_BASE") or "http://localhost:4010/v1"
        self.oai_key = os.environ.get("OPENAI_API_KEY", "dummy")
        self.google_api_key = os.environ.get("GEMINI_API_KEY")

        # CLI provider defaults
        self.cli_command = None
        self.cli_cwd = "."
        self.cli_env = {}
        self.cli_timeout = 300
        self.cli_input_format = "stdin"
        self.cli_output_clean = True
        self.cli_extra_args: list[str] = []
        self.cli_parse_json = False
        self.cli_append_model_flag = True
        self.cli_append_system_prompt = False
        self.cli_append_temperature_flag = False
        self.cli_append_max_tokens_flag = False
        self.cli_prompt_template: str | None = None
        self.cli_debug = False
        self.cli_debug_args: list[str] = []
        self.cli_log_stderr = False

    def _initialize_provider_config(self, cfg: dict, complexity: Optional[str]):
        """Load and apply provider configuration from config.yaml.

        Extracted from __init__ to reduce CC (lines 206-275).
        Handles role-based config resolution, provider config loading, and CLI provider setup.
        Note: self.role must be set before calling this method.
        """
        # Load from config.yaml
        roles = cfg.get("roles", {}) if isinstance(cfg.get("roles", {}), dict) else {}
        role_cfg = roles.get(self.role, {}) if isinstance(roles, dict) else {}
        providers = cfg.get("providers", {}) if isinstance(cfg.get("providers", {}), dict) else {}

        # Resolve provider configuration
        routed_provider, routed_model = resolve_role_model_for_complexity(cfg, self.role, complexity)
        provider_key = routed_provider or role_cfg.get("provider") or "ollama"
        provider_cfg = providers.get(provider_key, {"type": "ollama", "base_url": "http://localhost:11434"})

        # Apply config defaults
        if routed_model:
            self.model = routed_model
        else:
            self.model = role_cfg.get("model", self.model)
        self.temperature = float(role_cfg.get("temperature", self.temperature))
        self.max_tokens = int(role_cfg.get("max_tokens", self.max_tokens))
        self.provider_type = provider_cfg.get("type", provider_key)
        self.provider_options = provider_cfg
        base_url = provider_cfg.get("base_url")

        # Initialize provider-specific settings
        self._initialize_cli_provider(provider_cfg, base_url)

        # Apply provider base URL
        if self.provider_type == "ollama":
            self.ollama_base = os.environ.get("OLLAMA_BASE_URL") or base_url or self.ollama_base
        elif self.provider_type == "openai":
            self.oai_base = os.environ.get("OPENAI_API_BASE") or base_url or self.oai_base
            if provider_cfg.get("api_key"):
                self.oai_key = provider_cfg["api_key"]
        elif self.provider_type == "google_ai_gemini":
            if provider_cfg.get("api_key"):
                self.google_api_key = provider_cfg["api_key"]

    def _initialize_cli_provider(self, provider_cfg: dict, base_url: Optional[str]):
        """Initialize CLI provider settings (codex_cli, claude_cli).

        Extracted from __init__ to reduce CC (lines 235-275, most complex section).
        Handles CLI-specific configuration including commands, timeouts, and extra args.
        CC reduced: ~50 lines of nested if/elif → focused helper method.
        """
        if self.provider_type not in ("codex_cli", "claude_cli"):
            return

        default_command = ["codex", "chat"] if self.provider_type == "codex_cli" else ["claude", "-p", "--print"]
        self.cli_command = provider_cfg.get("command", default_command)
        self.cli_cwd = provider_cfg.get("cwd", self.cli_cwd)
        self.cli_env = provider_cfg.get("env", self.cli_env)
        self.cli_timeout = int(provider_cfg.get("timeout", self.cli_timeout))
        self.cli_input_format = provider_cfg.get("input_format", self.cli_input_format)
        self.cli_output_clean = bool(provider_cfg.get("output_clean", self.cli_output_clean))

        # Handle extra_args (list or string format)
        extra_args_cfg = provider_cfg.get("extra_args", [])
        if isinstance(extra_args_cfg, (list, tuple)):
            self.cli_extra_args = [str(arg) for arg in extra_args_cfg]
        elif isinstance(extra_args_cfg, str) and extra_args_cfg.strip():
            self.cli_extra_args = [extra_args_cfg]
        else:
            self.cli_extra_args = []

        # JSON parsing and flags
        self.cli_parse_json = bool(provider_cfg.get("parse_json", self.provider_type == "claude_cli"))
        self.cli_append_model_flag = bool(provider_cfg.get("append_model", True))
        self.cli_append_system_prompt = bool(
            provider_cfg.get("append_system_prompt", self.provider_type == "claude_cli")
        )
        self.cli_append_temperature_flag = bool(
            provider_cfg.get("append_temperature", self.provider_type == "codex_cli")
        )
        self.cli_append_max_tokens_flag = bool(
            provider_cfg.get("append_max_tokens", self.provider_type == "codex_cli")
        )

        # Prompt template
        prompt_template_default = (
            "{user}" if self.provider_type == "claude_cli" else
            "System: {system}\n\nUser: {user}\n\nSettings: temperature={temperature}, max_tokens={max_tokens}"
        )
        self.cli_prompt_template = provider_cfg.get("prompt_template", prompt_template_default)

        # Debug settings
        default_debug_args = ["--verbose", "--debug"] if self.provider_type == "claude_cli" else []
        debug_args_cfg = provider_cfg.get("debug_args", default_debug_args)
        if isinstance(debug_args_cfg, (list, tuple)):
            self.cli_debug_args = [str(arg) for arg in debug_args_cfg]
        elif isinstance(debug_args_cfg, str) and debug_args_cfg.strip():
            self.cli_debug_args = [debug_args_cfg]
        else:
            self.cli_debug_args = default_debug_args
        self.cli_debug = bool(provider_cfg.get("debug", False))
        self.cli_log_stderr = bool(provider_cfg.get("log_stderr", self.cli_debug))

    def _apply_legacy_overrides(self, legacy_args: tuple):
        """Apply legacy positional argument overrides.

        Extracted from __init__ to reduce CC (lines 277-297).
        Legacy format: Client(provider, model, temperature, max_tokens, base_url)
        Validates provider type before applying override.
        """
        if not legacy_args:
            return

        # Unpack legacy args
        prov = str(legacy_args[0]).strip().lower() if len(legacy_args) >= 1 else None
        model = legacy_args[1] if len(legacy_args) >= 2 else None
        temp = legacy_args[2] if len(legacy_args) >= 3 else None
        maxt = legacy_args[3] if len(legacy_args) >= 4 else None
        base = legacy_args[4] if len(legacy_args) >= 5 else None

        # Apply overrides with validation
        if prov in ("ollama", "openai", "codex_cli", "vertex_cli", "vertex_sdk", "claude_cli", "google_ai_gemini"):
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

    def _apply_keyword_overrides(self, overrides: dict):
        """Apply keyword argument overrides.

        Extracted from __init__ to reduce CC (lines 299-314).
        Supports: model, temperature, max_tokens, provider, base_url overrides.
        Validates provider type before applying override.
        """
        if not overrides:
            return

        if "model" in overrides and overrides["model"]:
            self.model = str(overrides["model"])
        if "temperature" in overrides and overrides["temperature"] is not None:
            self.temperature = float(overrides["temperature"])
        if "max_tokens" in overrides and overrides["max_tokens"] is not None:
            self.max_tokens = int(overrides["max_tokens"])
        if "provider" in overrides and overrides["provider"]:
            p = str(overrides["provider"]).strip().lower()
            if p in ("ollama", "openai", "codex_cli", "vertex_cli", "vertex_sdk", "claude_cli", "google_ai_gemini"):
                self.provider_type = p
        if "base_url" in overrides and overrides["base_url"]:
            if self.provider_type == "ollama":
                self.ollama_base = str(overrides["base_url"])
            else:
                self.oai_base = str(overrides["base_url"])


    async def _augment_with_graph_rag(self, user: str) -> str:
        """
        F1-T5: Optionally augment user prompt with Graph RAG context.
        R1-T3: Apply budget guard to prevent context token overflow.

        Returns: augmented user prompt (or original if RAG disabled/unavailable)
        Injection point: provides project knowledge graph context before LLM call.
        """
        try:
            cfg = load_config()
            graph_rag_cfg = cfg.get("graph_rag", {})
            if not graph_rag_cfg.get("enabled", False):
                return user

            # Lazy import to avoid hard dependency
            from graph_rag.retrieval import AgentRetriever
            from graph_rag.engine import GraphRAGEngine

            # R1-T3: Get budget settings from config
            context_budget = graph_rag_cfg.get("context_budget_chars", 4000)
            truncation_strategy = graph_rag_cfg.get("context_truncation_strategy", "hierarchical")

            engine = GraphRAGEngine.instance(graph_rag_cfg)
            retriever = AgentRetriever(engine)

            # Record timing for telemetry
            start_time = time.time()
            context = await retriever.retrieve_for_role(self.role, user)
            retrieval_time = (time.time() - start_time) * 1000  # Convert to ms

            if context:
                # R1-T3: Apply budget guard - truncate if exceeds limit
                original_size = len(context)
                if len(context) > context_budget:
                    if truncation_strategy == "hierarchical":
                        context = truncate_context_hierarchically(context, context_budget)
                    else:
                        # Fallback: simple truncation
                        context = context[:context_budget]

                # R1-T3: Log telemetry metrics
                logger.info(
                    f"[GRAPH_RAG] role={self.role} context={len(context)} chars "
                    f"(original={original_size}, budget={context_budget}), "
                    f"retrieval_latency={retrieval_time:.1f}ms"
                )

                return (
                    f"## Relevant Project Context (from Knowledge Graph)\n\n"
                    f"{context}\n\n"
                    f"---\n\n"
                    f"## Task\n\n"
                    f"{user}"
                )
        except Exception as exc:
            logger.warning(f"[LLM] Graph RAG augmentation failed for role {self.role}: {exc}")

        return user  # Fallback to original

    async def chat(self, system: str, user: str) -> str:
        # F1-T5: Graph RAG augmentation (optional)
        user = await self._augment_with_graph_rag(user)

        if recommend_model and _reco_enabled():
            prompt = f"{system.strip()}\n\n{user.strip()}"
            try:
                chosen_model = recommend_model(prompt, role=self.role)
                logger.info(f"[LLM] Model recommender chose: {chosen_model} for role {self.role}")
            except Exception as exc:
                logger.warning(f"[LLM] Model recommender failed for role {self.role}: {exc}. Falling back to default model.")
                chosen_model = None
            if chosen_model:
                self.model = chosen_model

        if self.provider_type in ("vertex_cli", "vertex_sdk") and PROVIDER_REGISTRY:
            logger.debug(f"[LLM] Using Vertex provider: {self.provider_type}")
            return await asyncio.to_thread(self._vertex_chat, system, user)

        if self.provider_type in ("codex_cli", "claude_cli"):
            logger.debug(f"[LLM] Using CLI provider: {self.provider_type}")
            # Task: fix async CLI execution - use async subprocess instead of thread pool
            return await self._cli_chat_async(system, user)
        elif self.provider_type == "openai":
            logger.debug("[LLM] Using OpenAI provider.")
            return await self._openai_chat(system, user)
        elif self.provider_type == "google_ai_gemini":
            logger.debug("[LLM] Using Google AI Gemini provider.")
            return await asyncio.to_thread(self._google_gemini_chat, system, user)
        else:
            # Ollama models should not have "ollama/" prefix
            model_name_for_ollama = self.model
            if self.provider_type == "ollama" and model_name_for_ollama.startswith("ollama/"):
                model_name_for_ollama = model_name_for_ollama[len("ollama/"):]
            logger.debug(f"[LLM] Using Ollama provider. Model name for API: {model_name_for_ollama}")


            # prefer /api/chat, fallback to /api/generate for older Ollama
            try:
                return await self._ollama_chat(system, user, model_name_for_ollama)
            except Exception as exc:
                logger.warning(f"[LLM] Ollama /api/chat failed: {exc}. Falling back to /api/generate.")
                return await self._ollama_generate(system, user, model_name_for_ollama)

    async def _ollama_chat(self, system: str, user: str, model_name: str) -> str:
        url = f"{self.ollama_base.rstrip('/')}/api/chat"
        payload = {
            "model": model_name,
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
                logger.debug(f"[OLLAMA_DEBUG] 404 Response Text (chat): {r.text}") # DEBUG
                # Check if the 404 is due to the model not being found
                if "model not found" in r.text.lower():
                    logger.error(f"[LLM] OLLAMA_MODEL_NOT_FOUND: Model '{self.model}' not found on Ollama server.")
                    raise RuntimeError(f"OLLAMA_MODEL_NOT_FOUND: {self.model}")
                else:
                    logger.error(f"[LLM] OLLAMA_CHAT_404: Endpoint not found or other 404 error for {url}. Response: {r.text}")
                    raise RuntimeError("OLLAMA_CHAT_404: Endpoint not found or other 404 error.")
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                if "message" in data and isinstance(data["message"], dict):
                    return data["message"].get("content", "")
                if "content" in data:
                    return data.get("content", "")
                if "response" in data:
                    return data["response"]
            logger.warning(f"[LLM] Unexpected Ollama chat response format: {json.dumps(data)[:200]}...")
            return r.text

    async def _ollama_generate(self, system: str, user: str, model_name: str) -> str:
        url = f"{self.ollama_base.rstrip('/')}/api/generate"
        prompt = f"System:\n{system}\n\nUser:\n{user}\n\nAssistant:"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 404:
                logger.debug(f"[OLLAMA_DEBUG] 404 Response Text (generate): {r.text}") # DEBUG
                if "model not found" in r.text.lower():
                    logger.error(f"[LLM] OLLAMA_MODEL_NOT_FOUND (generate): Model '{self.model}' not found on Ollama server.")
                    raise RuntimeError(f"OLLAMA_MODEL_NOT_FOUND: {self.model}")
                else:
                    logger.error(f"[LLM] OLLAMA_GENERATE_404: Endpoint not found or other 404 error for {url}. Response: {r.text}")
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and "response" in data:
                return data["response"]
            logger.warning(f"[LLM] Unexpected Ollama generate response format: {json.dumps(data)[:200]}...")
            return r.text

    def _vertex_chat(self, system: str, user: str) -> str:
        provider = PROVIDER_REGISTRY.get(self.provider_type)
        if provider is None:
            logger.critical(f"[LLM] FATAL: Vertex provider '{self.provider_type}' not available in registry.")
            raise RuntimeError(f"Provider '{self.provider_type}' not available")

        messages = [
            {"role": "system", "content": [{"type": "text", "text": system}]},
            {"role": "user", "content": [{"type": "text", "text": user}]},
        ]
        logger.debug(f"[LLM] Vertex chat payload prepared. Model: {self.model}")


        def _sanitize(value):
            if isinstance(value, str) and "${" in value:
                logger.warning(f"[LLM] Sanitizing Vertex option: '{value}' contains unresolved env var.")
                return None
            return value

        extra_kwargs = {}
        if isinstance(self.provider_options, dict):
            # Pass only project_id and location as extra kwargs, as others are passed directly.
            for key in ("project_id", "location"):
                if key in self.provider_options:
                    resolved = _sanitize(self.provider_options.get(key))
                    if resolved is not None:
                        extra_kwargs[key] = resolved
        logger.debug(f"[LLM] Vertex extra kwargs: {extra_kwargs}")


        return provider(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
            **extra_kwargs,
        )

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
        logger.debug(f"[LLM] OpenAI chat payload prepared. Model: {self.model}")


        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            try:
                return data["choices"][0]["message"]["content"]
            except Exception as exc:
                logger.error(f"[LLM] Unexpected OpenAI chat response format: {exc}. Full response: {json.dumps(data)[:200]}...")
                return json.dumps(data)

    def _google_gemini_chat(self, system: str, user: str) -> str:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai package not installed. Run `pip install google-genai`." ) from exc

        api_key = self.google_api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set for google_ai_gemini provider.")

        client = genai.Client(api_key=api_key)
        model_name = self.model or "gemini-2.5-pro"
        prompt = f"{system.strip()}\n\n{user.strip()}".strip()
        logger.debug(f"[LLM] Google Gemini payload prepared. Model: {model_name}")

        response = client.models.generate_content(model=model_name, contents=prompt)

        text = getattr(response, "text", None)
        if text:
            return text

        candidates = getattr(response, "candidates", None)
        if candidates:
            parts: list[str] = []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", []) or []:
                    value = getattr(part, "text", None)
                    if value:
                        parts.append(value)
            if parts:
                return "\n".join(parts)

        raise RuntimeError("Google Gemini response did not contain text output.")

    # ========================================================================
    # CLI Chat Refactoring - Helper Methods (CC Reduction)
    # ========================================================================

    def _build_cli_command_args(self, system: str, user: str, prompt_text: str) -> list:
        """
        Build CLI command arguments with flags and settings.

        Extracted helper to reduce CC in _cli_chat and _cli_chat_async.
        Handles: model flag, temperature flag, max-tokens flag, system prompt flag.

        Args:
            system: System prompt
            user: User prompt
            prompt_text: Formatted prompt text

        Returns:
            List of command arguments with all flags appended

        CC: ≤ 5 (follows Phase 1 standards)
        """
        cmd_args = list(self.cli_command)  # Copy command list
        if self.cli_extra_args:
            cmd_args.extend(self.cli_extra_args)
        if self.cli_debug and self.cli_debug_args:
            cmd_args.extend(self.cli_debug_args)

        def _has_flag(flag: str) -> bool:
            for arg in cmd_args:
                if arg == flag or arg.startswith(f"{flag}="):
                    return True
            return False

        # Append model flag
        if self.cli_append_model_flag and not _has_flag("--model"):
            cmd_args.extend(["--model", self.model])

        # Append temperature flag
        if self.cli_append_temperature_flag and not _has_flag("--temperature"):
            cmd_args.extend(["--temperature", str(self.temperature)])

        # Append max-tokens flag (provider-specific)
        if self.provider_type == "claude_cli":
            if not _has_flag("--settings"):
                settings_json = json.dumps(
                    {"max_tokens_to_sample": self.max_tokens},
                    separators=(',', ':')
                )
                cmd_args.extend(["--settings", settings_json])
        elif self.cli_append_max_tokens_flag and not _has_flag("--max-tokens"):
            cmd_args.extend(["--max-tokens", str(self.max_tokens)])

        # Append system prompt flag
        if (self.cli_append_system_prompt and
            self.provider_type != "claude_cli" and
            not _has_flag("--system-prompt")):
            cmd_args.extend(["--system-prompt", system])

        return cmd_args

    def _prepare_cli_input(
        self, system: str, user: str
    ) -> tuple:
        """
        Prepare CLI input based on format configuration.

        Extracted helper to reduce CC in _cli_chat and _cli_chat_async.
        Handles: JSON input, text input, direct argument input.

        Args:
            system: System prompt
            user: User prompt

        Returns:
            Tuple of (input_data: str|None, prompt_text: str)

        CC: ≤ 5 (follows Phase 1 standards)
        """
        # Build prompt text
        prompt_template = self.cli_prompt_template or (
            "System: {system}\n\nUser: {user}\n\n"
            "Settings: temperature={temperature}, max_tokens={max_tokens}"
        )

        if self.provider_type == "claude_cli" and self.cli_input_format == "stdin_text":
            prompt_text = f"{system}\n\n{user}"
        else:
            prompt_text = prompt_template.format(
                system=system,
                user=user,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                model=self.model,
            )

        # Prepare input based on format
        input_data = None
        normalized_format = (self.cli_input_format or "").lower()

        if normalized_format in ("stdin", "stdin_json", "json"):
            payload = {
                "system": system,
                "user": user,
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "prompt": prompt_text,
            }
            input_data = json.dumps(payload, ensure_ascii=False)
            logger.debug("[LLM] CLI input format: stdin (JSON payload)")
        elif normalized_format in ("stdin_text", "stdin-raw", "text"):
            input_data = prompt_text
            logger.debug("[LLM] CLI input format: stdin (text payload)")
        else:
            logger.debug("[LLM] CLI input format: direct argument (combined prompt)")

        return input_data, prompt_text

    def _handle_cli_error(
        self, returncode: int, stdout_text: str, stderr_text: str
    ) -> str:
        """
        Extract error message from CLI command execution.

        Extracted helper to reduce CC in _cli_chat and _cli_chat_async.
        Tries multiple sources: stdout JSON, stderr, generic message.

        Args:
            returncode: Process return code
            stdout_text: Process stdout
            stderr_text: Process stderr

        Returns:
            Error message string

        CC: ≤ 5 (follows Phase 1 standards)
        """
        error_msg = "Unknown error"

        # Try to parse JSON error from stdout (some CLIs return errors in JSON)
        if stdout_text:
            try:
                data = json.loads(stdout_text.strip())
                if isinstance(data, dict) and data.get("is_error"):
                    error_msg = data.get("result") or data.get("error") or error_msg
            except json.JSONDecodeError:
                pass

        # Fall back to stderr
        if error_msg == "Unknown error" and stderr_text:
            error_msg = stderr_text.strip()[:200]

        return error_msg

    def _process_cli_response(self, response: str) -> str:
        """
        Clean and parse CLI response.

        Extracted helper to reduce CC in _cli_chat and _cli_chat_async.
        Handles: ANSI code removal, JSON parsing, whitespace trimming.

        Args:
            response: Raw response from CLI

        Returns:
            Processed response string

        CC: ≤ 5 (follows Phase 1 standards)
        """
        # Remove ANSI escape codes if configured
        if self.cli_output_clean:
            response = re.sub(r'\x1b\[[0-9;]*[mG]', '', response)
            response = response.strip()
            logger.debug("[LLM] CLI response cleaned.")

        # Parse JSON if configured
        if self.cli_parse_json:
            parsed = self._parse_cli_json_output(response)
            if parsed is not None:
                response = parsed
            else:
                logger.warning(f"[LLM] Failed to parse JSON from response: {response[:500]}")

        return response

    def _ensure_cli_command_configured(self) -> None:
        """Validate CLI command is configured."""
        if self.cli_command:
            return
        label = self.provider_type.upper()
        logger.critical(f"[LLM] FATAL: {label}_NO_COMMAND - CLI command not configured.")
        raise RuntimeError(f"{label}_NO_COMMAND")

    def _append_prompt_if_direct_mode(self, cmd_args: list[str], prompt_text: str) -> None:
        """Append prompt directly to args when input format is argument-based."""
        normalized_format = (self.cli_input_format or "").lower()
        if normalized_format in ("stdin", "stdin_json", "json", "stdin_text", "stdin-raw", "text"):
            return
        cmd_args.append(prompt_text)

    def _prepare_cli_execution(self, system: str, user: str, method_name: str) -> tuple[float, list[str], str | None]:
        """Prepare common execution context for sync/async CLI calls."""
        self._ensure_cli_command_configured()

        start_time = time.perf_counter()
        logger.debug(f"[LLM] {method_name}: Entered for provider {self.provider_type}")
        logger.debug(f"[LLM] {method_name}: Command to execute: {self.cli_command}")

        input_data, prompt_text = self._prepare_cli_input(system, user)
        cmd_args = self._build_cli_command_args(system, user, prompt_text)
        self._append_prompt_if_direct_mode(cmd_args, prompt_text)

        logger.debug(f"[LLM] {method_name}: Full command args: {cmd_args}")
        logger.debug(f"[LLM] {method_name}: Input data length: {len(input_data) if input_data else 0} chars")
        return start_time, cmd_args, input_data

    def _build_cli_env(self, method_name: str) -> dict[str, str]:
        """Build process env for CLI execution."""
        env = os.environ.copy()
        env.update(self.cli_env)
        if self.cli_env:
            logger.debug(f"[LLM] CLI environment updated with: {self.cli_env}")
        logger.debug(f"[LLM] {method_name}: Environment prepared, timeout: {self.cli_timeout}s")
        return env

    def _handle_cli_completion(
        self,
        *,
        cmd_args: list[str],
        duration: float,
        returncode: int,
        stdout_text: str,
        stderr_text: str,
    ) -> str:
        """Handle common completion logic for sync/async CLI calls."""
        stderr_for_log = stderr_text if self.cli_log_stderr and stderr_text else None
        label = self.provider_type.upper()

        if returncode != 0:
            error_msg = self._handle_cli_error(returncode, stdout_text, stderr_text)
            self._log_cli_operation(
                cmd_args,
                duration,
                error_msg,
                success=False,
                stderr=stderr_for_log,
                debug_enabled=self.cli_debug,
            )
            logger.error(f"[LLM] {label}_FAILED: Command '{' '.join(cmd_args[:3])}...' failed. Error: {error_msg}")
            if stderr_text:
                logger.warning(f"[LLM] Stderr from {label}: {stderr_text.strip()}")
            raise RuntimeError(f"{label}_FAILED: {error_msg}")

        if stderr_text and (self.cli_log_stderr or self.cli_debug):
            logger.info(f"[LLM] Stderr from {label}: {stderr_text.strip()}")

        response = self._process_cli_response(stdout_text)
        if not response:
            self._log_cli_operation(
                cmd_args,
                duration,
                "Empty response",
                success=False,
                stderr=stderr_for_log,
                debug_enabled=self.cli_debug,
            )
            logger.error(f"[LLM] {label}_EMPTY_RESPONSE: Empty response from CLI.")
            raise RuntimeError(f"{label}_EMPTY_RESPONSE")

        self._log_cli_operation(
            cmd_args,
            duration,
            response,
            success=True,
            stderr=stderr_for_log,
            debug_enabled=self.cli_debug,
        )
        logger.debug("[LLM] CLI operation logged successfully.")
        return response

    async def _cli_chat_async(self, system: str, user: str) -> str:
        """Async version of _cli_chat using asyncio subprocess.

        Refactored to use helper methods for CC reduction.
        Uses native async subprocess instead of thread pool.
        """
        start_time, cmd_args, input_data = self._prepare_cli_execution(system, user, "_cli_chat_async")

        try:
            env = self._build_cli_env("_cli_chat_async")

            # Execute command using async subprocess
            logger.debug("[LLM] _cli_chat_async: Using asyncio.create_subprocess_exec")
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cli_cwd,
                env=env
            )

            # Communicate with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(input_data.encode('utf-8') if input_data else None),
                    timeout=self.cli_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                duration = time.perf_counter() - start_time
                self._log_cli_operation(
                    cmd_args,
                    duration,
                    "Timeout",
                    success=False,
                    stderr=None,
                    debug_enabled=self.cli_debug,
                )
                label = self.provider_type.upper()
                logger.error(f"[LLM] {label}_TIMEOUT: Command timed out after {self.cli_timeout}s.")
                raise RuntimeError(f"{label}_TIMEOUT")

            stdout_text = stdout_bytes.decode('utf-8', errors='replace')
            stderr_text = stderr_bytes.decode('utf-8', errors='replace')
            returncode = process.returncode

            logger.debug(f"[LLM] _cli_chat_async: subprocess completed. Return code: {returncode}")

            duration = time.perf_counter() - start_time
            logger.debug(
                f"[LLM] CLI command for provider '{self.provider_type}' executed in {duration:.3f} seconds. "
                f"Return code: {returncode}"
            )
            return self._handle_cli_completion(
                cmd_args=cmd_args,
                duration=duration,
                returncode=returncode,
                stdout_text=stdout_text,
                stderr_text=stderr_text,
            )

        except Exception as exc:
            if "TIMEOUT" not in str(exc) and "FAILED" not in str(exc):
                duration = time.perf_counter() - start_time
                logger.error(f"[LLM] CLI execution failed: {exc}")
            raise

    def _cli_chat(self, system: str, user: str) -> str:
        """Execute configured CLI provider command and return response with timing and logging.

        Refactored to use helper methods for CC reduction.
        """
        start_time, cmd_args, input_data = self._prepare_cli_execution(system, user, "_cli_chat")

        try:
            env = self._build_cli_env("_cli_chat")


            # Execute command directly with subprocess.run (simpler and more reliable than pty)
            logger.debug("[LLM] _cli_chat: Using subprocess.run (no pty)")
            logger.debug("[LLM] Using subprocess.run for CLI execution.")
            result = subprocess.run(
                cmd_args,
                input=input_data,
                capture_output=True,
                text=True,
                cwd=self.cli_cwd,
                env=env,
                timeout=self.cli_timeout
            )
            logger.debug(f"[LLM] _cli_chat: subprocess.run completed. Return code: {result.returncode}")

            duration = time.perf_counter() - start_time
            logger.debug(
                f"[LLM] CLI command for provider '{self.provider_type}' executed in {duration:.3f} seconds. "
                f"Return code: {result.returncode}"
            )
            return self._handle_cli_completion(
                cmd_args=cmd_args,
                duration=duration,
                returncode=result.returncode,
                stdout_text=result.stdout,
                stderr_text=result.stderr or "",
            )

        except subprocess.TimeoutExpired:
            duration = time.perf_counter() - start_time
            self._log_cli_operation(
                cmd_args,
                duration,
                "Timeout",
                success=False,
                stderr=None,
                debug_enabled=self.cli_debug,
            )
            label = self.provider_type.upper()
            logger.error(f"[LLM] {label}_TIMEOUT: Command timed out after {self.cli_timeout}s.")
            raise RuntimeError(f"{label}_TIMEOUT")
        except FileNotFoundError:
            label = self.provider_type.upper()
            logger.critical(
                f"[LLM] {label}_NOT_FOUND: Command '{cmd_args[0] if cmd_args else 'unknown'}' not found. "
                f"Ensure CLI is installed and on PATH."
            )
            raise RuntimeError(f"{label}_NOT_FOUND")
        except Exception as e:
            duration = time.perf_counter() - start_time
            self._log_cli_operation(
                cmd_args,
                duration,
                str(e),
                success=False,
                stderr=None,
                debug_enabled=self.cli_debug,
            )
            label = self.provider_type.upper()
            logger.critical(
                f"[LLM] {label}_ERROR: Unhandled exception during CLI call: {str(e)[:200]}",
                exc_info=True,
            )
            raise RuntimeError(f"{label}_ERROR: {str(e)[:200]}")

    def _parse_cli_json_output(self, raw_output: str) -> str | None:
        """Attempt to extract assistant text from JSON CLI responses, handling markdown code blocks."""
        if not raw_output:
            return None

        candidate = self._extract_json_candidate_from_output(raw_output)
        data = self._load_json_with_fallback(raw_output, candidate)
        if not data:
            return None

        return self._extract_text_from_json_payload(data)

    def _extract_json_candidate_from_output(self, raw_output: str) -> str:
        """Extract primary JSON candidate from raw CLI output."""
        # Regex to find a JSON code block, supporting both ```json and ```
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
        if json_block_match:
            return json_block_match.group(1).strip()
        return raw_output.strip()

    def _load_json_with_fallback(self, raw_output: str, candidate: str) -> Any | None:
        """Load JSON from candidate; fallback to line-delimited/streaming chunks."""
        parsed = self._safe_json_loads(candidate)
        if parsed is not None:
            return parsed

        for line in reversed(raw_output.strip().splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            parsed = self._safe_json_loads(stripped)
            if parsed is not None:
                return parsed
        return None

    def _safe_json_loads(self, value: str) -> Any | None:
        """Best-effort JSON parsing helper."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def _extract_text_segments_from_content(self, content: Any) -> list[str]:
        """Extract text fragments from content-style arrays."""
        if not isinstance(content, list):
            return []

        segments: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") != "text":
                continue
            text = part.get("text")
            if text:
                segments.append(text)
        return segments

    def _extract_text_from_json_payload(self, data: Any) -> str | None:
        """Extract assistant text from dict/list JSON payloads."""
        segments: list[str] = []

        if isinstance(data, dict):
            segments.extend(self._extract_text_segments_from_content(data.get("content")))
            if segments:
                return "\n".join(segments).strip()
            if "text" in data and isinstance(data["text"], str):
                return data["text"].strip()
            return None

        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                maybe_text = item.get("text")
                if isinstance(maybe_text, str):
                    segments.append(maybe_text)
                segments.extend(self._extract_text_segments_from_content(item.get("content")))
            if segments:
                return "\n".join(segments).strip()

        return None

    def _log_cli_operation(
        self,
        cmd_args: list,
        duration: float,
        response_or_error: str,
        success: bool,
        stderr: str | None = None,
        debug_enabled: bool | None = None,
    ):
        """Log CLI operation details for monitoring and debugging."""
        try:
            artifacts_dir = ROOT / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            raw_file = artifacts_dir / "last_raw.txt"

            timestamp = time.time()
            log_entry = {
                "timestamp": timestamp,
                "role": self.role,
                "provider": self.provider_type,
                "command": cmd_args,
                "duration_seconds": round(duration, 3),
                "response_length": len(response_or_error) if success else 0,
                "success": success,
                "response": response_or_error if success else None,
                "error": response_or_error if not success else None,
            }
            if stderr:
                log_entry["stderr"] = stderr
            if debug_enabled is not None:
                log_entry["debug"] = debug_enabled

            raw_file.write_text(json.dumps(log_entry, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.debug(f"[LLM] CLI operation log saved to {raw_file}")
        except Exception as e:
            # Don't let logging errors break the flow
            logger.error(f"[LLM] Failed to log CLI operation: {e}", exc_info=True)


# Backward-compat alias
LLMClient = Client
