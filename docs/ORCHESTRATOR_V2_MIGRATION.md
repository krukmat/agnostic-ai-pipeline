# Orchestrator V2 Migration Guide

## Goal
Provide a reliable migration path from the legacy orchestrator to the new agentic runtime (`scripts/run_orchestrator_agent.py`) without losing functionality, tests, or governance.

## Migration checkpoints
1. **Audit existing tests**: Identify all `tests/scripts/test_orchestrate_*` and `tests/test_orchestrator_modes.py` suites. Each must be migrated to target the new runtime points (e.g., planner helpers, agentic CLI). Create wrappers in `tests/scripts/test_run_orchestrator_agent.py` that cover the same assertions.
2. **Preserve coverage**: Ensure each new module achieves ≥80% coverage by introducing targeted tests for:
   - `scripts/run_orchestrator_agent.py`
   - `scripts/orchestrator_runtime.py` and planner/policy helpers
   - `scripts/run_architect.py` policies and config guards
3. **Replace legacy targets**: Update docs (e.g., `docs/README.md`, `docs/AGENTIC_ORCHESTRATOR_PLAN.md`) so they no longer reference legacy CLI commands except where helpers remain.
4. **Cover `implements` metadata**: Automate story `implements` tagging via deterministic heuristics (e.g., map FR IDs by keyword or configuration file) so `features.pipeline_guard.bypass` can be disabled; use `scripts/tools/generate_implements.py` (invoked automatically by the architect stage) to regenerate `planning/stories.yaml` before executing `make po`. Once the guard is running (`pipeline_guard` script writes `artifacts/qa/pipeline_guard.json`), re-enable it by setting `features.pipeline_guard.bypass` back to `false`.
5. **Test dual-write cleanup**: Run `make cleanup-targets` and then `scripts/run_orchestrator_agent.py` to confirm no legacy targets remain; this ensures the pipeline no longer relies on outdated artifacts.
6. **Retire legacy orchestrator**: Once tests pass against the new runtime and `implements` coverage is consistent, archive `scripts/orchestrate.py` by documenting its helper-only role and eventually remove the file after smoke harnesses confirm parity.

## Verification
- Capture a smoke run with the new concept (e.g., "Auto translate movies via AI speech platforms") using `scripts/run_orchestrator_smoke_tests.sh` and inspect `artifacts/iterations/latest_orchestrator_summary.json` to confirm no legacy orchestrator log entries exist.
- Validate coverage metrics with `coverage.xml` or equivalent; performance metrics should align with previous Phase 4 benchmarks.
- Record any manual interventions (e.g., architect reruns) in `planning/task8_documentation_plan.md` to satisfy the rule that every task includes a documented plan.

## Rollback considerations
- Keep `scripts/orchestrate.py` until replacement is fully stable; mark it as deprecated in `docs/legacy_orchestrator.md` or a similar reference before deletion.
- Document the moment `features.pipeline_guard.bypass` is flipped back to `false` so future runs know the pipeline now enforces `implements` coverage.
