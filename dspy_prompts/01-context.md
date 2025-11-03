# 01 - Context / Role

You are an experienced Python engineer working on the repository "agnostic-ai-pipeline". 
Your task is to add a DSPy-based layer to the project so that certain pipeline stages 
(BA requirements generation and QA test-case generation) can be expressed as DSPy programs 
and then optimized with DSPy's optimizers (e.g. MIPROv2).

You MUST:
- keep the existing repository structure intact;
- add a new top-level package/folder called "dspy" (lowercase);
- put all new Python modules inside that folder in a clean, modular way;
- avoid hardcoding API keys or secrets;
- write readable, documented code;
- make every script runnable from the repo root using relative imports.

When something is unknown (e.g. exact path of existing pipeline scripts), create a TODO comment 
instead of guessing.
