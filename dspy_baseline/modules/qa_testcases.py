"""DSPy module for generating QA test cases from user stories."""

from typing import Dict

import dspy

from dspy_baseline.config.metrics import evaluate_testcase_coverage
from dspy_baseline.scripts.run_ba import load_llm_config

dspy.configure(lm=load_llm_config())

BASE_GUIDANCE = (
    "\n\nQA Instructions:\n"
    "- Output markdown with '## Happy Path' and '## Unhappy Path' headings.\n"
    "- Number each test case using the format '1. ', '2. ', etc.\n"
    "- Every test must include a short step list and an explicit expected result.\n"
    "- Always describe at least one unhappy-path scenario covering validation errors, service outages, or security issues."
)

EMAIL_GUIDANCE = (
    "\n\nEmail Notification Edge Cases:\n"
    "- Include scenarios where the email service is unavailable or returns a 5xx error.\n"
    "- Cover invalid recipient addresses and bounced emails with user-visible feedback.\n"
    "- Validate logging/telemetry for delivery failures."
)

RETRY_GUIDANCE = (
    "\n\nRetry focus: ensure both sections exist with numbered cases, and add explicit failure "
    "scenarios (SMTP downtime, invalid address, bounced email, notification queue delays) alongside "
    "accessibility and telemetry expectations."
)


class QATestCases(dspy.Signature):
    """Generate QA test cases (markdown) for a user story."""

    story_title: str = dspy.InputField(
        desc="Concise story title or identifier"
    )
    story_description: str = dspy.InputField(
        desc="Story details explaining functionality"
    )
    acceptance_criteria: str = dspy.InputField(
        desc="Acceptance criteria bullet list or paragraphs"
    )

    test_cases_md: str = dspy.OutputField(
        desc="Markdown list of numbered test cases, covering happy and unhappy paths"
    )


QA_PROGRAM = dspy.ChainOfThought(QATestCases)


def generate_testcases(story: Dict) -> str:
    """Generate QA test cases in markdown for the provided story dict."""
    title = story.get("id") or story.get("title") or story.get("story_title", "")
    description = story.get("description", "")
    ac = story.get("acceptance") or story.get("acceptance_criteria") or ""

    story_text = str(description)
    base_guidance = BASE_GUIDANCE

    combined_acceptance = "\n".join(ac) if isinstance(ac, list) else str(ac)
    acceptance_lower = combined_acceptance.lower()
    description_lower = story_text.lower()

    if "email" in acceptance_lower or "email" in description_lower:
        base_guidance += EMAIL_GUIDANCE
    if "notification" in acceptance_lower or "notification" in description_lower:
        base_guidance += (
            "\n\nNotification Reliability:\n"
            "- Add tests for delayed delivery and retries when providers throttle or queue messages."
        )

    def _run(extra_guidance: str = "") -> str:
        response = QA_PROGRAM(
            story_title=str(title),
            story_description=story_text + base_guidance + extra_guidance,
            acceptance_criteria=combined_acceptance,
        )
        return str(response.test_cases_md).strip()

    markdown = _run()

    # Evaluate coverage using heuristic metric; leave TODO if coverage is low.
    coverage_score = evaluate_testcase_coverage(markdown)
    if coverage_score < 0.75:
        markdown = _run(RETRY_GUIDANCE)
        coverage_score = evaluate_testcase_coverage(markdown)

    if coverage_score < 0.5:
        markdown += "\n\n"
        markdown += "\n".join([
            "- **Note**: Coverage metric indicates missing scenarios (consider re-running or adjusting prompts)."
        ])

    return markdown
