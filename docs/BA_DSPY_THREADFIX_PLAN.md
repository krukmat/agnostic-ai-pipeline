# BA DSPy Thread Fix Plan (2025-11-17)

## Issue Summary
- Running `make ba` fails when DSPy is enabled because `scripts/run_ba.py` calls `_run_dspy` inside `asyncio.to_thread()`, and `dspy.configure()` refuses to run in that worker thread. Error: `dspy.settings can only be changed by the thread that initially configured it.`

## Plan
1. Update `scripts/run_ba.py` so `_run_dspy` executes on the main thread when DSPy is enabled (`return _run_dspy(concept)`), eliminating the thread context swap.
2. Keep legacy path asynchronous if needed, but DSPy path will be synchronous to maintain compatibility.
3. After patching, rerun `make ba` with a sample concept and capture logs under `logs/mipro/ba/` to confirm success.
4. Update `docs/fase9_multi_role_dspy_plan.md` to reference this fix plan and record completion once verified.

## Notes
- No external dependencies change; the fix is purely in `scripts/run_ba.py`.
- If later we need non-blocking behavior, revisit DSPy configuration or provide a dedicated orchestrator instead of `asyncio.to_thread()`.


## DSPy Local LM Plan (2025-11-17)
1. Añadir variables `DSPY_BA_LM`, `DSPY_BA_MAX_TOKENS`, `DSPY_BA_TEMPERATURE` en `scripts/run_ba.py` y usar `ollama/granite4` como default.
2. Configurar DSPy en el hilo principal con el LM local y pasar `lm=None` a `dsp_generate` para evitar reconfigurar internamente.
3. Documentar en `docs/fase9_multi_role_dspy_plan.md` que BA ahora usa el mismo mecanismo que PO (`DSPY_<ROL>_LM`).
4. Validar con `CONCEPT=... make ba DSPY_BA_LM=ollama/granite4` y guardar log bajo `logs/mipro/ba/`.
5. Cuando haya red, se podrá cambiar `DSPY_BA_LM` a Vertex u otro provider sin tocar el código.

## Verification Attempts
- 2025-11-17 11:51: `make ba` no longer triggers the thread error, but fails later because the configured LLM `dspy_baseline` uses `litellm` and tries to reach the remote provider. Without outbound network/credentials, it stops at `[Errno 1] Operation not permitted`.
- Next step when network is available: rerun `make ba` (same concept) and capture success log under `logs/mipro/ba/`.
