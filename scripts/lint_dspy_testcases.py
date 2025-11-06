#!/usr/bin/env python3
"""Validate DSPy-generated QA testcases for coverage expectations."""

from __future__ import annotations

import os
from pathlib import Path
import re
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
TESTCASE_DIR = ROOT / "artifacts" / "dspy" / "testcases"
DATASET_PATH = ROOT / "dspy_baseline" / "data" / "qa_eval.yaml"


RE_NUMBERED = re.compile(r"^\d+\.\s", re.MULTILINE)
RE_HAPPY_HEADER = re.compile(r"^##+\s*Happy Path", re.IGNORECASE | re.MULTILINE)
RE_UNHAPPY_HEADER = re.compile(r"^##+\s*Unhappy Path", re.IGNORECASE | re.MULTILINE)
RE_FAILURE_KEYWORDS = re.compile(
    r"(error|fail|invalid|unavailable|retry|bounce|timeout|throttl)",
    re.IGNORECASE,
)

def load_expectations() -> dict[str, dict]:
    if not DATASET_PATH.exists():
        return {}
    data = yaml.safe_load(DATASET_PATH.read_text(encoding="utf-8")) or {}
    cases = data.get("cases") or []
    expectations: dict[str, dict] = {}
    for case in cases:
        story_id = str(case.get("story_id") or "").strip()
        if not story_id:
            continue
        expectations[story_id] = case
    return expectations


def main() -> int:
    skip_if_missing = os.getenv("DSPY_QA_SKIP_IF_MISSING") == "1"

    if not TESTCASE_DIR.exists():
        msg = "artifacts/dspy/testcases not found. Run make dspy-qa first."
        if skip_if_missing:
            print(f"Skipping lint: {msg}", file=sys.stderr)
            return 0
        print(msg, file=sys.stderr)
        return 1

    failures: list[str] = []

    expectations = load_expectations()

    for md_file in sorted(TESTCASE_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        lowered = content.lower()

        if not RE_HAPPY_HEADER.search(content):
            failures.append(f"{md_file}: missing Happy Path header")
        if not RE_UNHAPPY_HEADER.search(content):
            failures.append(f"{md_file}: missing Unhappy Path header")
        if not RE_NUMBERED.search(content):
            failures.append(f"{md_file}: lacks numbered list items")
        if not RE_FAILURE_KEYWORDS.search(content):
            failures.append(f"{md_file}: no failure-related keywords detected")

        story_id = md_file.stem
        case = expectations.get(story_id)
        if case:
            required_terms = case.get("required_mentions") or []
            missing_terms = [
                term for term in required_terms if term.lower() not in lowered
            ]
            if missing_terms:
                failures.append(
                    f"{md_file}: missing required mentions {missing_terms} (dataset expectation)"
                )

    if failures:
        print("DSPy QA validation failed:", file=sys.stderr)
        for msg in failures:
            print(f"  - {msg}", file=sys.stderr)
        return 2

    print("DSPy QA validation passed for all testcases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
