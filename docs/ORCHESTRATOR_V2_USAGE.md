# Orchestrator V2 Agentic Usage Guide

## Purpose
This guide explains how to run the agentic orchestrator loop (BA→PO→Architect→Dev→QA) using the new CLI, which entries to inspect for observability, and how to configure key policy flags.

## Running the loop
1. Source the virtualenv: `source .venv/bin/activate` (or run via `./.venv/bin/python`).
2. Ensure `config.yaml` defines the desired providers and flags (`make set-role`, `make set-quality`).
3. Launch the agentic loop with:
   ```bash
   python scripts/run_orchestrator_agent.py --concept "Your concept summary"
   ```
   - Concept text feeds BA and PO phases; omit only for quick smoke runs where `concept` is already stored under `artifacts/iterations/latest_orchestrator_summary.json`.
   - The CLI orchestrates BA, PO, Architect, Dev, and QA in sequence.
4. Monitor `logs/pipeline.log` and `artifacts/iterations/latest_orchestrator_summary.json` for phase updates and decisions.

## CoT and observability
- `scripts/orchestrator/cot_tracker.py` logs planner/policy/LLM decisions when invoked via the agentic runtime.
- Outputs appear under `artifacts/cot_layer6/` as:
  - `thoughts.jsonl` (machine-readable stream)
  - `reasoning_chain.md` (human summary)
  - `summary.json` (counts by phase/layer)
- Run the analytics aggregator to summarize those logs after each smoke run:
  ```bash
  python -m scripts.orchestrator.cot_analytics --input artifacts/cot_layer6/thoughts.jsonl
  ```
  This generates `analytics.json` and `analytics.md` with distribution stats, escalations per story, and low-confidence LLM decisions to review.
- Review these after a run to audit decisions or gather justification for QA handoffs.
- Learning memory store: `scripts/orchestrator/learning_store.py` records every story attempt to `artifacts/learning/learning_store.jsonl`. Use `LearningStore` directly or tail the JSONL file to understand retries/errors before policy feedback adjusts confidence. Retention defaults to 20 entries per story and is configurable via `features.learning_store.retention_per_story` in `config.yaml`.

## Configuration notes
- `pipeline.allow_architect_with_po_needs_adjustment`: when true, Architect will proceed even if PO reports `needs_adjustment`, honoring the flag documented in `docs/AGENTIC_ORCHESTRATOR_PLAN.md`.
- `features.pipeline_guard.bypass`: toggles the coverage/implements guard; now that deterministic `implements` tagging + learning/policy feedback exist, this flag defaults to `false`. When the guard runs it writes `artifacts/qa/pipeline_guard.json` and will fail if stories lack `implements` or FR coverage, so inspect that file plus `logs/pipeline.log` for the failure details.
- `features.policy_feedback.enabled`: when true, the planner consults recent history before executing stories and may escalate repeated failures to `RUN_ARCHITECT` while reprioritizing ready stories. Tune `failure_threshold` if you want faster escalation or more retries.
- Dual-write is disabled by default via `database.enabled: false`; if you enable persistence, run `make cleanup-targets` (see Makefile) before reruns.
- Deterministic `implements`: the architect stage now invokes `scripts/tools/generate_implements.py` automatically. Customize overrides via `planning/fr_story_map.yaml` and you can re-run manually with:
  ```bash
  python -m scripts.tools.generate_implements --stories planning/stories.yaml --requirements planning/requirements.yaml
  ```

## Smoke harness
- Use `scripts/run_orchestrator_smoke_tests.sh` to exercise the agentic CLI end-to-end with recorded concepts (Calculator API, Auto translate movies via AI speech platforms, multi-epic subtitle orchestration, etc.).
- The harness executes `tests/smoke/test_agentic_orchestrator.py` and captures artifacts under `artifacts/iterations/<concept>`. Check `logs/pipeline.log` after completion for evidence that Architect, Dev, and QA phases ran via the agentic CLI.
- Pass `guard` to run a dedicated multi-epic scenario directly via `scripts/run_orchestrator_agent.py`; this run takes longer but, when complete, the script validates that every story in `planning/stories.yaml` includes an `implements` list.
- Always rerun the harness when changing planners or config flags so coverage stays at least 80% for new modules.

## Testing expectations
- Run `./.venv/bin/pytest -q` to exercise unit/integration suites that target orchestrator modules (CoT tracker, planner, policy modules).
- For front-end tests (`project/web-express`), run `npm test -- --passWithNoTests` if the repo contains a `package.json`.
- Do not mock orchestrator internals unless external dependencies (LLM services, databases) cannot be satisfied; prefer deterministic stubs embedded in the test suites.
