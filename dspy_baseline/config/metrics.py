"""Metrics and heuristics for DSPy QA modules."""

from __future__ import annotations

import re


def evaluate_testcase_coverage(markdown: str) -> float:
    """Return a heuristic coverage score (0..1) for test cases markdown."""
    if not markdown:
        return 0.0

    text = markdown.lower()
    has_numbering = bool(re.search(r"\b\d+\.\s", markdown))
    has_happy = bool(re.search(r"\bhappy path\b|\bpositive scenario\b", text))
    has_unhappy = bool(
        re.search(r"\bunhappy path\b|\bnegative scenario\b|\berror handling\b", text)
    )
    mentions_expected = "expected" in text or "assert" in text or "resultado" in text

    score = 0.0
    if has_numbering:
        score += 0.25
    if has_happy:
        score += 0.3
    if has_unhappy:
        score += 0.3
    if mentions_expected:
        score += 0.15
    return min(score, 1.0)
