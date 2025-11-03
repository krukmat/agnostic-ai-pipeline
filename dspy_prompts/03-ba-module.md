# 03 - BA Requirements DSPy module

Write the file `dspy/modules/ba_requirements.py` with the following behavior:

- Import `dspy`.
- Define a DSPy signature called `BARequirements` that describes:
  - input: `concept` (str)
  - output: `requirements_yaml` (str)
  The output is expected to be YAML describing: product/solution name, epics, user stories, and acceptance criteria per story.

- Define a predictor:
  ```python
  BA_PROGRAM = dspy.Predict(BARequirements)
  ```

- Define a function `generate_requirements(concept: str) -> str` that:
  1. calls `BA_PROGRAM(concept=concept)`
  2. retrieves `.requirements_yaml`
  3. validates that it is non-empty
  4. optionally calls a helper from `dspy/modules/common.py` to validate YAML shape
     (if the helper does not exist yet, import it and add a TODO in `common.py`)

- Add a module-level docstring explaining that this is the first DSPy program to be optimized.

Do not hardcode YAML schemas. Just add a simple shape check and leave a TODO for stricter validation.
