# 09 - DSPy README (short)

## What
This directory adds a DSPy-based layer to the "agnostic-ai-pipeline" so that some pipeline stages 
(BA requirements generation, QA test-case generation) can be expressed as DSPy programs and optimized.

## How to run
1. Install deps:
   ```bash
   pip install dspy-ai mlflow pyyaml
   ```
2. Configure an LM provider (OpenAI, Anthropic, local) via env vars or YAML in `dspy/config/provider.example.yaml`.
3. Run a BA generation:
   ```bash
   make dspy-ba
   ```
4. Run an optimization:
   ```bash
   make dspy-tune-ba
   ```

## Notes
- MLflow autologging is enabled in the tuning script.
- Exact integration with the existing pipeline is left as TODOs to be wired to your CLI.
