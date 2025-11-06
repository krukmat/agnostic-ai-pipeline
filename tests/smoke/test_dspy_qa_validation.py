from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts to path for imports
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import lint_dspy_testcases


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
