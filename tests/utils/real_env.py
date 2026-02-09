"""Helpers para detectar si el entorno de integración real está listo."""

from __future__ import annotations

import importlib.util
import shutil
import socket
import subprocess
from typing import Iterable, Tuple


def has_lightrag() -> bool:
    return importlib.util.find_spec("lightrag") is not None


def has_ollama_cli() -> bool:
    return shutil.which("ollama") is not None


def is_ollama_server_up(host: str = "127.0.0.1", port: int = 11434, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _installed_ollama_models() -> set[str]:
    if not has_ollama_cli():
        return set()
    try:
        res = subprocess.run(
            ["ollama", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return set()

    if res.returncode != 0:
        return set()

    models: set[str] = set()
    for line in res.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if parts:
            models.add(parts[0])
    return models


def has_required_models(required_models: Iterable[str]) -> Tuple[bool, str]:
    installed = _installed_ollama_models()
    missing = [m for m in required_models if m not in installed]
    if missing:
        return False, f"Modelos Ollama faltantes: {missing}"
    return True, "ok"


def is_real_rag_env_ready() -> Tuple[bool, str]:
    """Valida precondiciones para tests integration_real de Graph RAG."""
    if not has_lightrag():
        return False, "lightrag no instalado"
    if not has_ollama_cli():
        return False, "ollama CLI no disponible"
    if not is_ollama_server_up():
        return False, "ollama server no está escuchando en :11434"

    ok, reason = has_required_models(["qwen2.5:7b-instruct", "bge-m3"])
    if not ok:
        return False, reason
    return True, "Entorno real listo"
