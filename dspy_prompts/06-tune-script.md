# 06 - Tuning script with MLflow

Create the file `dspy/scripts/tune.py` that:

- imports `mlflow` and `dspy`
- configures dspy to use an LM (e.g. `dspy.OpenAI(model="gpt-4.1")`) BUT leaves a TODO to read model from env var
- imports one of the programs (e.g. `from dspy.modules.ba_requirements import BA_PROGRAM`)
- imports `optimize_program` from `dspy.optimizers.mipro`
- loads a tiny trainset from `dspy.modules.common` (if not present, create a placeholder list of dicts and leave TODO)
- loads a metric from `dspy.config.metrics`
- enables `mlflow.dspy.autolog()`
- runs the optimization
- saves the resulting program to `artifacts/ba_program.json` (create folder if needed)

Use only relative imports from the repo root. If the path is ambiguous, add a TODO.
