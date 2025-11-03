#!/usr/bin/env python3
"""CLI to generate QA test cases for all stories."""

from pathlib import Path
import sys
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dspy_baseline.modules.qa_testcases import generate_testcases

STORIES_PATH = Path('planning/stories.yaml')
OUTPUT_DIR = Path('artifacts/dspy/testcases')


def main() -> None:
    if not STORIES_PATH.exists():
        raise SystemExit('planning/stories.yaml not found. Run make plan first.')

    stories = yaml.safe_load(STORIES_PATH.read_text(encoding='utf-8')) or []
    if not isinstance(stories, list):
        raise SystemExit('stories.yaml is not a list; unable to generate test cases.')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for story in stories:
        story_id = str(story.get('id') or story.get('title') or 'story')
        markdown = generate_testcases(story)
        output_path = OUTPUT_DIR / f"{story_id}.md"
        output_path.write_text(markdown + '\n', encoding='utf-8')
        print(f"✓ Test cases generated: {output_path}")


if __name__ == "__main__":
    main()
