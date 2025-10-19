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
        """Full iteration with explicit CLI args should fan out to BA, plan, and loop."""
        commands: List[Tuple[List[str], Dict[str, str] | None]] = []
        snapshots: List[Tuple[str, str, int, bool]] = []

        def fake_run(cmd: List[str], env=None) -> int:
            commands.append((cmd, deepcopy(env) if env else None))
            return 0

        def fake_snapshot(name: str, concept: str, loops: int, allow: bool) -> None:
            snapshots.append((name, concept, loops, allow))

        with mock.patch.object(run_iteration, "run_command", side_effect=fake_run), mock.patch.object(
            run_iteration, "snapshot_iteration", side_effect=fake_snapshot
        ):
            exit_code = run_iteration.main(
                ["--concept", "Demo", "--loops", "2", "--allow-no-tests", "--iteration-name", "custom-iter"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(commands), 3)

        ba_cmd, ba_env = commands[0]
        self.assertEqual(ba_cmd, ["make", "ba"])
        self.assertIsNotNone(ba_env)
        self.assertEqual(ba_env.get("CONCEPT"), "Demo")

        plan_cmd, plan_env = commands[1]
        self.assertEqual(plan_cmd, ["make", "plan"])
        self.assertIsNotNone(plan_env)
        self.assertEqual(plan_env.get("CONCEPT"), "Demo")

        loop_cmd, loop_env = commands[2]
        self.assertEqual(loop_cmd, ["make", "loop"])
        self.assertIsNotNone(loop_env)
        self.assertEqual(loop_env.get("MAX_LOOPS"), "2")
        self.assertEqual(loop_env.get("ALLOW_NO_TESTS"), "1")
        self.assertEqual(loop_env.get("CONCEPT"), "Demo")

        self.assertEqual(len(snapshots), 1)
        snap_name, snap_concept, snap_loops, snap_allow = snapshots[0]
        self.assertEqual(snap_name, "custom-iter")
        self.assertEqual(snap_concept, "Demo")
        self.assertEqual(snap_loops, 2)
        self.assertTrue(snap_allow)

    def test_environment_defaults_and_skips(self) -> None:
        """Environment variables should provide defaults and skip flags."""
        os.environ["CONCEPT"] = "Env Product"
        os.environ["LOOPS"] = "3"
        os.environ["ALLOW_NO_TESTS"] = "1"
        os.environ["SKIP_BA"] = "1"

        commands: List[Tuple[List[str], Dict[str, str] | None]] = []

        def fake_run(cmd: List[str], env=None) -> int:
            commands.append((cmd, deepcopy(env) if env else None))
            return 0

        with mock.patch.object(run_iteration, "run_command", side_effect=fake_run), mock.patch.object(
            run_iteration, "snapshot_iteration", return_value=None
        ):
            exit_code = run_iteration.main(["--skip-plan"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(commands), 1)  # Only loop should run

        loop_cmd, loop_env = commands[0]
        self.assertEqual(loop_cmd, ["make", "loop"])
        self.assertIsNotNone(loop_env)
        self.assertEqual(loop_env.get("MAX_LOOPS"), "3")
        self.assertEqual(loop_env.get("ALLOW_NO_TESTS"), "1")
        self.assertEqual(loop_env.get("CONCEPT"), "Env Product")

    def test_missing_concept_requires_flag(self) -> None:
        """When BA runs, concept is mandatory."""
        with mock.patch.object(run_iteration, "run_command") as mocked_run, mock.patch.object(
            run_iteration, "snapshot_iteration"
        ) as mocked_snapshot:
            exit_code = run_iteration.main([])

        mocked_run.assert_not_called()
        mocked_snapshot.assert_not_called()
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
