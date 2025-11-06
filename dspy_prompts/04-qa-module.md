# 04 - QA Testcases DSPy module

Write the file `dspy/modules/qa_testcases.py` with the following behavior:

- Import `dspy`.
- Define a DSPy signature `QATestCases` with:
  - input: `story_title` (str), `story_description` (str), `acceptance_criteria` (str)
  - output: `test_cases_md` (str)

The output is a Markdown string with:
- at least 1 happy path test
- at least 1 negative/unhappy path test
- numbering

- Define
  ```python
  QA_PROGRAM = dspy.ChainOfThought(QATestCases)
  ```
  so the model reasons step by step.

- Define a function `generate_testcases(story: dict) -> str` that:
  - extracts title, description, ac from the dict
  - calls the program
  - returns the markdown
  - optionally calls a metric helper (to be defined in `dspy/config/metrics.py`) to check coverage
  - if the metric is low, leave a TODO to re-run with a different model

Document in the file that this program is meant to be optimized with MIPROv2 using a small eval set.
