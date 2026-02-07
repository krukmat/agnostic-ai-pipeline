"""Utilities for optional dependency handling in tests."""

from __future__ import annotations

import importlib.util
import logging

import pytest


logger = logging.getLogger(__name__)


def require_optional_dep(module_name: str, level: str = "error") -> None:
    """Skip current test module if optional dependency is not installed.

    Args:
        module_name: Import path to check, e.g. ``psutil`` or ``google.genai``.
        level: Logging level to emit before skipping (``warning``/``error``).
    """
    if importlib.util.find_spec(module_name) is not None:
        return

    msg = f"Skipping tests: optional dependency '{module_name}' is not installed"
    if level == "warning":
        logger.warning(msg)
    else:
        logger.error(msg)

    pytest.skip(msg, allow_module_level=True)
