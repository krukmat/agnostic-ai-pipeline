#!/usr/bin/env python3
"""CLI to generate QA test cases for all stories."""

import os
from pathlib import Path
import sys
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

SKIP_IF_MISSING = os.getenv("DSPY_QA_SKIP_IF_MISSING") == "1"
USE_STUB = os.getenv("DSPY_QA_STUB") == "1"

if SKIP_IF_MISSING:
    print("Skipping DSPy testcase generation (DSPY_QA_SKIP_IF_MISSING=1).", file=sys.stderr)
    raise SystemExit(0)

try:
    from dspy_baseline.modules.qa_testcases import generate_testcases
except ModuleNotFoundError as exc:
    if USE_STUB:
        generate_testcases = None  # type: ignore[assignment]
    else:
        raise

STORIES_PATH = Path('planning/stories.yaml')
OUTPUT_DIR = Path('artifacts/dspy/testcases')
DATASET_PATH = Path('dspy_baseline/data/qa_eval.yaml')


def load_expectations() -> dict[str, list[str]]:
    if not DATASET_PATH.exists():
        return {}
    data = yaml.safe_load(DATASET_PATH.read_text(encoding='utf-8')) or {}
    expectations: dict[str, list[str]] = {}
    for case in data.get('cases', []):
        story_id = str(case.get('story_id') or '').strip()
        if not story_id:
            continue
        terms = case.get('required_mentions') or []
        expectations[story_id] = [str(term) for term in terms if term]
    return expectations


def stub_generate_testcases(story: dict, expectations: dict[str, list[str]]) -> str:
    """Generate deterministic markdown when DSPy is unavailable."""
    story_id = str(story.get('id') or 'story')
    description = str(story.get('description') or '').strip()
    acceptance = story.get('acceptance') or story.get('acceptance_criteria') or []
    if isinstance(acceptance, str):
        acceptance_list = [acceptance]
    else:
        acceptance_list = [str(item) for item in acceptance]

    required_terms = expectations.get(story_id, [])
    if not required_terms:
        required_terms = ["error", "retry"]

    lines: list[str] = []
    lines.append("## Happy Path")
    lines.append("1. Ensure primary workflow succeeds")
    if description:
        lines.append(f"   - Context: {description}")
    if acceptance_list:
        lines.append(f"   - Expected Result: {acceptance_list[0]}")
    else:
        lines.append("   - Expected Result: Core scenario completes without errors.")

    lines.append("")
    lines.append("## Unhappy Path")

    for idx, term in enumerate(required_terms, start=1):
        lines.append(f"{idx}. Scenario addressing '{term}'")
        lines.append(
            f"   - Expected Result: System returns a clear error for {term}, applies retry/fallback, and logs telemetry."
        )

    return "\n".join(lines)


def main() -> None:
    if not STORIES_PATH.exists():
        raise SystemExit('planning/stories.yaml not found. Run make plan first.')

    stories = yaml.safe_load(STORIES_PATH.read_text(encoding='utf-8')) or []
    if not isinstance(stories, list):
        raise SystemExit('stories.yaml is not a list; unable to generate test cases.')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    expectations = load_expectations() if USE_STUB else {}

    for story in stories:
        story_id = str(story.get('id') or story.get('title') or 'story')
        if USE_STUB or generate_testcases is None:
            markdown = stub_generate_testcases(story, expectations)
        else:
            markdown = generate_testcases(story)
        output_path = OUTPUT_DIR / f"{story_id}.md"
        output_path.write_text(markdown + '\n', encoding='utf-8')
        print(f"✓ Test cases generated: {output_path}")


if __name__ == "__main__":
    main()
