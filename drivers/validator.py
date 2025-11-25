from __future__ import annotations

"""Driver schema validator (v1) and conventions (P4.2).

Keeps validation concerns separate from I/O and CLI.
"""

import re
from typing import Any, Dict

VALID_CATEGORIES = {"backend", "frontend", "mobile", "embedded", "gpu"}


def _require(d: Dict[str, Any], key: str, typ):
    if key not in d:
        raise ValueError(f"missing required key '{key}'")
    if not isinstance(d[key], typ):
        raise ValueError(f"key '{key}' must be {typ}, got {type(d[key])}")


def validate_driver_dict(d: Dict[str, Any]) -> None:
    """Validate a driver mapping against schema v1 and conventions.

    Raises ValueError when invalid.
    """
    _require(d, "id", str)
    _require(d, "category", str)
    _require(d, "language", str)
    _require(d, "framework", str)

    # Category and ID conventions
    if d["category"] not in VALID_CATEGORIES:
        raise ValueError(f"invalid category '{d['category']}'")
    if not re.fullmatch(r"[a-z0-9_]+", d["id"]):
        raise ValueError("id must match ^[a-z0-9_]+$ (lowercase, digits, underscore)")

    # Templates
    if "templates" in d:
        if not isinstance(d["templates"], list):
            raise ValueError("templates must be a list")
        for t in d["templates"]:
            if not isinstance(t, dict) or "path" not in t or "source" not in t:
                raise ValueError("each template must be a dict with 'path' and 'source'")

    # Commands (build/test/lint) must be dicts with non-empty 'command'
    for k in ("build", "test", "lint"):
        if k in d:
            if not isinstance(d[k], dict) or "command" not in d[k] or not isinstance(d[k]["command"], str):
                raise ValueError(f"{k} must be a dict with 'command': str")
            if not d[k]["command"].strip():
                raise ValueError(f"{k}.command must be a non-empty string")
            _validate_command_string(d[k]["command"].strip(), k)

    # artifact_paths (optional)
    if "artifact_paths" in d and not isinstance(d["artifact_paths"], list):
        raise ValueError("artifact_paths must be a list of strings")

    # Embedded specifics
    if d.get("category") == "embedded":
        if "board" in d and not isinstance(d["board"], str):
            raise ValueError("embedded.board must be a string")
        if "flash_command" in d and not isinstance(d["flash_command"], str):
            raise ValueError("embedded.flash_command must be a string")
        if "monitor_command" in d and not isinstance(d["monitor_command"], str):
            raise ValueError("embedded.monitor_command must be a string")

    # GPU specifics
    if d.get("category") == "gpu":
        arch = d.get("gpu_arch") or d.get("arch")
        if arch is not None and not isinstance(arch, str):
            raise ValueError("gpu.gpu_arch must be a string")
        if arch and not (arch.startswith("sm_") or arch.startswith("gfx")):
            raise ValueError("gpu.gpu_arch seems invalid (expected 'sm_XX' or 'gfxXXXX')")


_DISALLOWED_TOKENS = ("&&", "||", ";", "|", ">", "<")


def _validate_command_string(cmd: str, field: str) -> None:
    """Basic hardening: disallow chaining/redirection and enforce sane first token.

    This is a conservative validator intended to prevent obviously unsafe patterns
    in driver YAMLs. It does not try to be a full shell parser.
    """
    # No newlines in a single command
    if "\n" in cmd or "\r" in cmd:
        raise ValueError(f"{field}.command must be a single line")
    # No chaining or redirection operators
    lowered = cmd.strip()
    if any(tok in lowered for tok in _DISALLOWED_TOKENS):
        raise ValueError(f"{field}.command contains disallowed shell operators (use single commands)")
    # First token should be a binary/script name (alnum, ._:-/ allowed)
    first = lowered.split()[0]
    if not re.fullmatch(r"[A-Za-z0-9._:\\/-]+", first):
        raise ValueError(f"{field}.command starts with an invalid token: {first}")
