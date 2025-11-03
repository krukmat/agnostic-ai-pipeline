"""Helpers for the local DSPy baseline integrations."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_CACHE_DIR = (
    Path(__file__).resolve().parent.parent / "artifacts" / "dspy" / "cache"
)

try:
    _DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # If creation fails we fall back to library defaults.
    pass
else:
    os.environ.setdefault("DSPY_CACHEDIR", str(_DEFAULT_CACHE_DIR))


__all__ = ["_DEFAULT_CACHE_DIR"]
