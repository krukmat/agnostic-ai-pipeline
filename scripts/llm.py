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


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

try:
    from recommend.model_recommender import is_enabled as _reco_enabled, recommend_model
except Exception:  # pragma: no cover - recommender optional
    recommend_model = None  # type: ignore[assignment]
    _reco_enabled = lambda: False  # type: ignore[assignment]
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

        # CLI provider defaults
        self.cli_command = None
        self.cli_cwd = "."
        self.cli_env = {}
        self.cli_timeout = 300
        self.cli_input_format = "stdin"
        self.cli_output_clean = True

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
        elif self.provider_type == "openai":
            self.oai_base = os.environ.get("OPENAI_API_BASE") or base_url or self.oai_base
        elif self.provider_type == "codex_cli":
            self.cli_command = provider_cfg.get("command", ["codex", "chat"])
            self.cli_cwd = provider_cfg.get("cwd", self.cli_cwd)
            self.cli_env = provider_cfg.get("env", self.cli_env)
            self.cli_timeout = int(provider_cfg.get("timeout", self.cli_timeout))
            self.cli_input_format = provider_cfg.get("input_format", self.cli_input_format)
            self.cli_output_clean = bool(provider_cfg.get("output_clean", self.cli_output_clean))
            self.cli_extra_args = provider_cfg.get("extra_args", [])

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
        if recommend_model and _reco_enabled():
            prompt = f"{system.strip()}\n\n{user.strip()}"
            try:
                chosen_model = recommend_model(prompt, role=self.role)
            except Exception:
                chosen_model = None
            if chosen_model:
                self.model = chosen_model

        if self.provider_type == "codex_cli":
            return await asyncio.to_thread(self._codex_cli_chat, system, user)
        elif self.provider_type == "openai":
            return await self._openai_chat(system, user)
        else:
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

    def _codex_cli_chat(self, system: str, user: str) -> str:
        """Execute Codex CLI command and return response with timing and logging."""
        if not self.cli_command:
            raise RuntimeError("CODEX_CLI_NO_COMMAND")

        start_time = time.perf_counter()

        # Build command arguments
        cmd_args = list(self.cli_command)  # Copy the command list

        # Add any extra args from config
        if hasattr(self, 'cli_extra_args') and self.cli_extra_args:
            cmd_args.extend(self.cli_extra_args)

        # Prepare input based on format
        input_data = None
        if self.cli_input_format == "stdin":
            # Send parameters through stdin as JSON
            cmd_args.extend(["--model", self.model])
            cmd_args.extend(["--temperature", str(self.temperature)])
            cmd_args.extend(["--max-tokens", str(self.max_tokens)])
            payload = {
                "system": system,
                "user": user,
                "model": self.model,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            input_data = json.dumps(payload, ensure_ascii=False)
        else:
            # For this specific CLI: only --model flag supported, combine prompts as direct argument
            cmd_args.extend(["--model", self.model])
            combined_prompt = f"System: {system}\n\nUser: {user}\n\nSettings: temperature={self.temperature}, max_tokens={self.max_tokens}"
            cmd_args.extend([combined_prompt])

        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.cli_env)

            # Execute command with pty to handle terminal requirements
            try:
                import pty
            except ImportError:
                # Fallback without pty if not available
                result = subprocess.run(
                    cmd_args,
                    input=input_data,
                    capture_output=True,
                    text=True,
                    cwd=self.cli_cwd,
                    env=env,
                    timeout=self.cli_timeout
                )
            else:
                # Use pty to simulate terminal for CLI that requires it
                master, slave = pty.openpty()

                try:
                    proc = subprocess.Popen(
                        cmd_args,
                        stdin=slave if input_data else None,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=self.cli_cwd,
                        env=env,
                        text=True
                    )

                    if input_data:
                        os.write(master, input_data.encode('utf-8'))
                        os.close(master)

                    try:
                        stdout, stderr = proc.communicate(timeout=self.cli_timeout)
                        result = subprocess.CompletedProcess(
                            args=cmd_args,
                            returncode=proc.returncode,
                            stdout=stdout,
                            stderr=stderr
                        )
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        raise subprocess.TimeoutExpired(cmd_args, self.cli_timeout)
                finally:
                    try:
                        os.close(slave)
                    except:
                        pass
                    try:
                        os.close(master)
                    except:
                        pass

            duration = time.perf_counter() - start_time

            if result.returncode != 0:
                error_msg = result.stderr.strip()[:200] if result.stderr else "Unknown error"
                # Log timing and error for debugging
                self._log_cli_operation(cmd_args, duration, error_msg, success=False)
                raise RuntimeError(f"CODEX_CLI_FAILED: {error_msg}")

            response = result.stdout

            # Clean response if configured
            if self.cli_output_clean:
                # Remove ANSI escape codes
                response = re.sub(r'\x1b\[[0-9;]*[mG]', '', response)
                # Trim whitespace
                response = response.strip()

            if not response:
                self._log_cli_operation(cmd_args, duration, "Empty response", success=False)
                raise RuntimeError("CODEX_CLI_EMPTY_RESPONSE")

            # Log successful operation
            self._log_cli_operation(cmd_args, duration, response, success=True)

            return response

        except subprocess.TimeoutExpired:
            duration = time.perf_counter() - start_time
            self._log_cli_operation(cmd_args, duration, "Timeout", success=False)
            raise RuntimeError("CODEX_CLI_TIMEOUT")
        except FileNotFoundError:
            raise RuntimeError("CODEX_CLI_NOT_FOUND")
        except Exception as e:
            duration = time.perf_counter() - start_time
            self._log_cli_operation(cmd_args, duration, str(e), success=False)
            raise RuntimeError(f"CODEX_CLI_ERROR: {str(e)[:200]}")

    def _log_cli_operation(self, cmd_args: list, duration: float, response_or_error: str, success: bool):
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
                "provider": "codex_cli",
                "command": cmd_args,
                "duration_seconds": round(duration, 3),
                "response_length": len(response_or_error) if success else 0,
                "success": success,
                "response": response_or_error if success else None,
                "error": response_or_error if not success else None
            }

            raw_file.write_text(json.dumps(log_entry, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            # Don't let logging errors break the flow
            print(f"[CLI_LOGGING] Failed to log operation: {e}")
            pass


# Backward-compat alias
LLMClient = Client
