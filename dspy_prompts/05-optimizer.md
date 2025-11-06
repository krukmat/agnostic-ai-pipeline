# 05 - Optimizer wrapper (MIPROv2)

Write the file `dspy/optimizers/mipro.py` that exposes a single function `optimize_program(...)`:

- import `dspy`
- define
  ```python
  def optimize_program(program, trainset, metric, *, num_candidates=8, max_iters=8, seed=0):
      opt = dspy.MIPROv2(metric=metric, num_candidates=num_candidates, seed=seed)
      compiled = opt.compile(program, trainset=trainset, max_iters=max_iters)
      return compiled
  ```

Add a docstring explaining that this will be used by CLI scripts to optimize either the BA or the QA program.

Do not add CLI parsing here.
