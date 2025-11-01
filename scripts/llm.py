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

from logger import logger # Import the logger


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
        self.ollama_base = os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434"
        self.oai_base = os.environ.get("OPENAI_API_BASE") or "http://localhost:4010/v1"
        self.oai_key = os.environ.get("OPENAI_API_KEY", "dummy")

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
        self.provider_type = provider_cfg.get("type", provider_key)
        self.provider_options = provider_cfg
        base_url = provider_cfg.get("base_url")

        if self.provider_type == "ollama":
            self.ollama_base = os.environ.get("OLLAMA_BASE_URL") or base_url or self.ollama_base
        elif self.provider_type == "openai":
            self.oai_base = os.environ.get("OPENAI_API_BASE") or base_url or self.oai_base
        elif self.provider_type in ("codex_cli", "claude_cli"):
            default_command = ["codex", "chat"] if self.provider_type == "codex_cli" else ["claude", "-p", "--print"]
            self.cli_command = provider_cfg.get("command", default_command)
            self.cli_cwd = provider_cfg.get("cwd", self.cli_cwd)
            self.cli_env = provider_cfg.get("env", self.cli_env)
            self.cli_timeout = int(provider_cfg.get("timeout", self.cli_timeout))
            self.cli_input_format = provider_cfg.get("input_format", self.cli_input_format)
            self.cli_output_clean = bool(provider_cfg.get("output_clean", self.cli_output_clean))
            extra_args_cfg = provider_cfg.get("extra_args", [])
            if isinstance(extra_args_cfg, (list, tuple)):
                self.cli_extra_args = [str(arg) for arg in extra_args_cfg]
            elif isinstance(extra_args_cfg, str) and extra_args_cfg.strip():
                self.cli_extra_args = [extra_args_cfg]
            else:
                self.cli_extra_args = []
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
            prompt_template_default = (
                "{user}" if self.provider_type == "claude_cli" else
                "System: {system}\n\nUser: {user}\n\nSettings: temperature={temperature}, max_tokens={max_tokens}"
            )
            self.cli_prompt_template = provider_cfg.get("prompt_template", prompt_template_default)
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

        # Legacy positional override (provider, model, temp, max_tokens, base_url)
        if legacy_args:
            prov = str(legacy_args[0]).strip().lower() if len(legacy_args) >= 1 else None
            model = legacy_args[1] if len(legacy_args) >= 2 else None
            temp = legacy_args[2] if len(legacy_args) >= 3 else None
            maxt = legacy_args[3] if len(legacy_args) >= 4 else None
            base = legacy_args[4] if len(legacy_args) >= 5 else None

            if prov in ("ollama", "openai", "codex_cli", "vertex_cli", "vertex_sdk", "claude_cli"):
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
            if p in ("ollama", "openai", "codex_cli", "vertex_cli", "vertex_sdk", "claude_cli"):
                self.provider_type = p
        if "base_url" in overrides and overrides["base_url"]:
            if self.provider_type == "ollama":
                self.ollama_base = str(overrides["base_url"])
            else:
                self.oai_base = str(overrides["base_url"])
        logger.debug(f"[LLM] Client initialized for role '{self.role}': provider={self.provider_type}, model={self.model}, temp={self.temperature}, max_tokens={self.max_tokens}")


    async def chat(self, system: str, user: str) -> str:
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
            return await asyncio.to_thread(self._cli_chat, system, user)
        elif self.provider_type == "openai":
            logger.debug("[LLM] Using OpenAI provider.")
            return await self._openai_chat(system, user)
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
            for key in ("project_id", "location", "temperature", "max_output_tokens"):
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

    def _cli_chat(self, system: str, user: str) -> str:
        """Execute configured CLI provider command and return response with timing and logging."""
        logger.debug(f"[LLM] _cli_chat: Entered for provider {self.provider_type}")
        if not self.cli_command:
            label = self.provider_type.upper()
            logger.critical(f"[LLM] FATAL: {label}_NO_COMMAND - CLI command not configured.")
            raise RuntimeError(f"{label}_NO_COMMAND")

        start_time = time.perf_counter()
        logger.debug(f"[LLM] _cli_chat: Command to execute: {self.cli_command}")
        logger.debug(f"[LLM] Starting CLI chat for provider '{self.provider_type}'. Command: {self.cli_command}")


        # Build command arguments
        cmd_args = list(self.cli_command)  # Copy the command list
        if self.cli_extra_args:
            cmd_args.extend(self.cli_extra_args)

        if self.cli_debug and self.cli_debug_args:
            cmd_args.extend(self.cli_debug_args)

        logger.debug(f"[LLM] _cli_chat: Full command args: {cmd_args}")

        def _has_flag(flag: str) -> bool:
            for arg in cmd_args:
                if arg == flag or arg.startswith(f"{flag}="):
                    return True
            return False

        if self.cli_append_model_flag and not _has_flag("--model"):
            cmd_args.extend(["--model", self.model])

        if self.cli_append_temperature_flag and not _has_flag("--temperature"):
            cmd_args.extend(["--temperature", str(self.temperature)])

        if self.provider_type == "claude_cli":
            if not _has_flag("--settings"):
                # The Claude CLI uses the API parameter name `max_tokens_to_sample` within its settings.
                # Wrap in quotes to ensure proper shell interpretation.
                settings_json = json.dumps({"max_tokens_to_sample": self.max_tokens}, separators=(',', ':'))
                # The settings_json is already a string, it will be properly quoted by subprocess
                cmd_args.extend(["--settings", settings_json])
        elif self.cli_append_max_tokens_flag and not _has_flag("--max-tokens"):
            cmd_args.extend(["--max-tokens", str(self.max_tokens)])

        # The system prompt is now combined with the user prompt for stdin_text format
        if self.cli_append_system_prompt and self.provider_type != "claude_cli" and not _has_flag("--system-prompt"):
            cmd_args.extend(["--system-prompt", system])

        prompt_template = self.cli_prompt_template or (
            "System: {system}\n\nUser: {user}\n\nSettings: temperature={temperature}, max_tokens={max_tokens}"
        )
        
        # For claude_cli with stdin_text, we combine system and user prompts.
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
            cmd_args.append(prompt_text)
            logger.debug("[LLM] CLI input format: direct argument (combined prompt)")


        logger.debug(f"[LLM] _cli_chat: About to execute subprocess. Input format: {self.cli_input_format}")
        logger.debug(f"[LLM] _cli_chat: Input data length: {len(input_data) if input_data else 0} chars")

        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.cli_env)
            if self.cli_env:
                logger.debug(f"[LLM] CLI environment updated with: {self.cli_env}")
            logger.debug(f"[LLM] _cli_chat: Environment prepared, timeout: {self.cli_timeout}s")


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

            stderr_text = result.stderr or ""
            stderr_for_log = stderr_text if self.cli_log_stderr and stderr_text else None


            if result.returncode != 0:
                error_msg = "Unknown error"
                # Claude CLI can return errors in stdout as JSON, even with a non-zero exit code.
                if result.stdout:
                    try:
                        data = json.loads(result.stdout.strip())
                        if isinstance(data, dict) and data.get("is_error"):
                            error_msg = data.get("result") or data.get("error") or error_msg
                    except json.JSONDecodeError:
                        pass  # Not a JSON error, fall back to stderr.

                if error_msg == "Unknown error" and result.stderr:
                    error_msg = result.stderr.strip()[:200]

                # Log timing and error for debugging
                self._log_cli_operation(
                    cmd_args,
                    duration,
                    error_msg,
                    success=False,
                    stderr=stderr_for_log,
                    debug_enabled=self.cli_debug,
                )
                label = self.provider_type.upper()
                logger.error(f"[LLM] {label}_FAILED: Command '{' '.join(cmd_args[:3])}...' failed. Error: {error_msg}")
                if result.stderr:
                    logger.warning(f"[LLM] Stderr from {label}: {result.stderr.strip()}")
                raise RuntimeError(f"{label}_FAILED: {error_msg}")

            response = result.stdout
            if result.stderr and (self.cli_log_stderr or self.cli_debug):
                logger.info(f"[LLM] Stderr from {self.provider_type.upper()}: {result.stderr.strip()}")

            # Clean response if configured
            if self.cli_output_clean:
                # Remove ANSI escape codes
                response = re.sub(r'\x1b\[[0-9;]*[mG]', '', response)
                # Trim whitespace
                response = response.strip()
                logger.debug("[LLM] CLI response cleaned.")

            if self.cli_parse_json:
                parsed = self._parse_cli_json_output(response)
                if parsed is not None:
                    response = parsed

            if not response:
                self._log_cli_operation(
                    cmd_args,
                    duration,
                    "Empty response",
                    success=False,
                    stderr=stderr_for_log,
                    debug_enabled=self.cli_debug,
                )
                label = self.provider_type.upper()
                logger.error(f"[LLM] {label}_EMPTY_RESPONSE: Empty response from CLI.")
                raise RuntimeError(f"{label}_EMPTY_RESPONSE")

            # Log successful operation
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

        # Regex to find a JSON code block, supporting both ```json and ```
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
        
        candidate = raw_output.strip()
        if json_block_match:
            candidate = json_block_match.group(1).strip()

        data = None
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            # Fallback for streaming or line-delimited JSON
            for line in reversed(raw_output.strip().splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    break 
                except json.JSONDecodeError:
                    continue

        if not data:
            return None

        if isinstance(data, dict):
            content = data.get("content")
            if isinstance(content, list):
                segments = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text = part.get("text")
                        if text:
                            segments.append(text)
                if segments:
                    return "\n".join(segments).strip()
            if "text" in data and isinstance(data["text"], str):
                return data["text"].strip()

        if isinstance(data, list):
            segments = []
            for item in data:
                if isinstance(item, dict):
                    maybe_text = item.get("text")
                    if isinstance(maybe_text, str):
                        segments.append(maybe_text)
                    content = item.get("content")
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text = part.get("text")
                                if text:
                                    segments.append(text)
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
            role_dir = re.sub(r"[^a-z0-9_\-]", "-", (self.role or "generic"))
            if not role_dir:
                role_dir = "generic"

            artifacts_dir = ROOT / "artifacts" / role_dir
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
