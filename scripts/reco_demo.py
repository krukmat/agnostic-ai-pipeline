#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

from recommend.model_recommender import recommend_model


EXAMPLES = [
    ("ba", "Summarize this long stakeholder requirement into 5 bullets."),
    ("plan", "Break down this epic into sprints and user stories."),
    ("dev", "Write a Python function to parse a CSV of invoices and compute VAT."),
    ("qa", "Generate high-value regression tests for date parsing edge cases."),
]


def main() -> None:
    for role, prompt in EXAMPLES:
        model = recommend_model(prompt, role=role)
        print(f"[{role}] -> {model}")


if __name__ == "__main__":
    main()
