from __future__ import annotations

import os
import datetime
from typing import Tuple

import yaml

from logger import logger
from common import ROOT
from scripts.utils.config_loader import load_config_base
from scripts.utils.orchestrator_facade import default_iteration_name


def load_qa_defaults() -> Tuple[bool, bool]:
    """Load QA defaults (allow_no_tests, run_tests) from config.yaml with safe fallbacks."""
    try:
        cfg = load_config_base()
        qa_cfg = cfg.get("qa", {}) if isinstance(cfg, dict) else {}
        allow_no_tests = bool(qa_cfg.get("allow_no_tests", True))
        run_tests = bool(qa_cfg.get("run_tests", False))
        return allow_no_tests, run_tests
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"[QA] Could not load QA defaults: {exc}")
        return True, False


def build_qa_config(story_env: str = "") -> Tuple[str, bool, bool]:
    """Resolve story_id, allow_no_tests, run_tests with env overriding config defaults."""
    allow_no_tests_cfg, run_tests_cfg = load_qa_defaults()

    allow_no_tests = os.environ.get("ALLOW_NO_TESTS")
    if allow_no_tests is None:
        allow_no_tests = "1" if allow_no_tests_cfg else "0"
    allow_no_tests = allow_no_tests == "1"

    run_tests_env = os.environ.get("QA_RUN_TESTS")
    if run_tests_env is None:
        run_tests = bool(run_tests_cfg)
    else:
        run_tests = run_tests_env == "1"

    story_id = story_env.strip() or f"qa-run-{default_iteration_name()}"
    return story_id, allow_no_tests, run_tests
