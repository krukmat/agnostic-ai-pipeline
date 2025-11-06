from __future__ import annotations

from pathlib import Path

import pytest

from scripts import lint_dspy_testcases


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(
    not (ROOT / "artifacts" / "dspy" / "testcases").exists(),
    reason="DSPy testcases not generated",
)
def test_lint_dspy_testcases_passes(monkeypatch):
    monkeypatch.setattr(
        lint_dspy_testcases,
        "TESTCASE_DIR",
        ROOT / "artifacts" / "dspy" / "testcases",
    )
    assert lint_dspy_testcases.main() == 0
