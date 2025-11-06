# 02 - DSPy folder structure

Create the following directory and file structure inside the repository:

```text
dspy/
  __init__.py
  config/
    __init__.py
    provider.example.yaml
    metrics.py
  modules/
    __init__.py
    ba_requirements.py
    qa_testcases.py
    common.py
  optimizers/
    __init__.py
    mipro.py
  scripts/
    __init__.py
    run_ba.py
    run_qa.py
    tune.py
  data/
    __init__.py
    demos/
      __init__.py
      ba_demo.json
    eval/
      __init__.py
      ba_eval.json
```

Constraints:
- Use Python 3 style imports.
- Assume DSPy is installed as `dspy` (`pip install dspy-ai`).
- Each module must have at least one callable function that can be imported by scripts.
- Do NOT invent external services.
- Where integration is needed with existing code, add `# TODO` comments.
