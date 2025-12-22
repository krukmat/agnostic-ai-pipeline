#!/usr/bin/env python3
"""
Smoke-style tests for the iteration orchestration pipeline.

These tests mock the heavy shell commands so we can verify argument handling,
environment propagation, and control-flow decisions without executing the full
BA→Architect→Dev→QA loop.
"""
from __future__ import annotations

import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock

# Make sure we can import the sibling module when executed directly.
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import run_iteration  # noqa: E402


class IterationScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_environ = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._original_environ)

    def test_cli_arguments_full_flow(self) -> None:
        """Agentic iteration should invoke orchestrator with provided args and snapshot."""
        snapshots: List[Tuple[str, str, int, bool]] = []
        orchestrator_calls: List[Tuple[str, int, int]] = []

        def fake_snapshot(name: str, concept: str, loops: int, allow: bool) -> None:
            snapshots.append((name, concept, loops, allow))

        async def fake_agentic(concept: str, max_steps: int, max_actions_per_step: int):
            orchestrator_calls.append((concept, max_steps, max_actions_per_step))

        with mock.patch.object(run_iteration, "snapshot_iteration", side_effect=fake_snapshot), mock.patch.object(
            run_iteration, "run_agentic_orchestrator", side_effect=fake_agentic
        ):
            exit_code = run_iteration.main(
                ["--concept", "Demo", "--loops", "2", "--allow-no-tests", "--iteration-name", "custom-iter"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual([("Demo", 2, 2)], orchestrator_calls)
        self.assertEqual([("custom-iter", "Demo", 2, True)], snapshots)

    def test_environment_defaults_and_skips(self) -> None:
        """Environment variables should provide defaults for concept/loops and run agentic orchestrator."""
        os.environ["CONCEPT"] = "Env Product"
        os.environ["LOOPS"] = "3"
        os.environ["ALLOW_NO_TESTS"] = "1"
        os.environ["SKIP_BA"] = "1"

        orchestrator_calls: List[Tuple[str, int, int]] = []

        async def fake_agentic(concept: str, max_steps: int, max_actions_per_step: int):
            orchestrator_calls.append((concept, max_steps, max_actions_per_step))

        with mock.patch.object(run_iteration, "run_agentic_orchestrator", side_effect=fake_agentic), mock.patch.object(
            run_iteration, "snapshot_iteration", return_value=None
        ):
            exit_code = run_iteration.main(["--skip-plan"])

        self.assertEqual(exit_code, 0)
        self.assertEqual([("Env Product", 3, 2)], orchestrator_calls)

    def test_missing_concept_assigns_default(self) -> None:
        """When concept missing and BA is skipped, agentic iteration should still run."""
        orchestrator_calls: List[Tuple[str, int, int]] = []

        async def fake_agentic(concept: str, max_steps: int, max_actions_per_step: int):
            orchestrator_calls.append((concept, max_steps, max_actions_per_step))

        os.environ["SKIP_BA"] = "1"
        with mock.patch.object(run_iteration, "run_agentic_orchestrator", side_effect=fake_agentic), mock.patch.object(
            run_iteration, "snapshot_iteration", return_value=None
        ):
            exit_code = run_iteration.main([])

        self.assertEqual(exit_code, 0)
        # Default concept applied
        self.assertEqual(orchestrator_calls[0][0], "agentic-adhoc")


if __name__ == "__main__":
    unittest.main()
