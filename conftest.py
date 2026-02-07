"""Global pytest hooks for optional dependency-aware collection.

This prevents hard collection failures when optional dependencies are not
installed in the current environment.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _missing_optional_deps_for_test(file_text: str) -> list[str]:
    """Infer optional deps needed by a test module from its imports.

    Heuristic by design: good enough to avoid collection-time hard failures.
    """
    missing: list[str] = []

    needs_uvicorn = any(
        key in file_text
        for key in (
            "scripts.orchestrate",
            "scripts.run_orchestrator_agent",
            "scripts.orchestrator_runtime",
            "from a2a",
            "import a2a",
        )
    )
    if needs_uvicorn and not _has_module("uvicorn"):
        missing.append("uvicorn")

    needs_psutil = "scripts.orchestrator" in file_text
    if needs_psutil and not _has_module("psutil"):
        missing.append("psutil")

    needs_rorf = "recommend.model_recommender" in file_text
    if needs_rorf and not _has_module("rorf"):
        missing.append("rorf")

    needs_dspy = any(
        key in file_text
        for key in (
            "dspy_baseline",
            "scripts.run_ba",
            "scripts.run_product_owner",
            "scripts.architect.dataset_cli",
        )
    )
    if needs_dspy and not _has_module("dspy"):
        missing.append("dspy")

    needs_google_genai = any(
        key in file_text
        for key in (
            "scripts.providers import vertex_cli, vertex_sdk",
            "scripts.providers.vertex_sdk",
            "google import genai",
        )
    )
    if needs_google_genai and not _has_module("google.genai"):
        missing.append("google-genai")

    return sorted(set(missing))


def pytest_ignore_collect(collection_path: Path, config) -> bool:  # type: ignore[override]
    """Skip collecting tests that require missing optional dependencies.

    We log with error-level severity for visibility in CI logs, then skip.
    """
    path = Path(str(collection_path))

    # Never collect virtualenv/vendor paths
    path_str = str(path)
    if any(part in path_str for part in (
        "/.venv/",
        "/venv/",
        "/site-packages/",
        "/dist-packages/",
    )):
        return True
    if path.suffix != ".py" or not path.name.startswith("test_"):
        return False

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    missing = _missing_optional_deps_for_test(text)
    if not missing:
        return False

    logger.error(
        "Skipping collection for %s due to missing optional dependencies: %s",
        path,
        ", ".join(missing),
    )
    return True
