# Project Memory – Orchestrator V2

This file collects the essential artifacts that describe the current state of the **Orchestrator V2 pipeline**, summarizing the CoT/logging story, learning layer, governance, and related docs so visitors can read a single “memory” document instead of digging through every file.

## Key Layers & Deliverables

| Layer | Deliverable | Description | Primary Document |
|---|---|---|---|
| Chain of Thought | `scripts/orchestrator/cot_tracker.py` + `cot_analytics.py` | Logs every planner/policy/LLM decision, exports JSONL/Markdown analytics, and supports CoT review. | `docs/ORCHESTRATOR_V2_PHASE4_COMPLETION.md`, `docs/ORCHESTRATOR_V2_DESIGN.md` |
| Planning & Governance | `scripts/orchestrator/planner.py` with `PolicyFeedback` + guard reports | Prioritizes ready stories, escalates flapping work, uses learning history, and enforces the `pipeline_guard`. | `docs/ORCHESTRATOR_V2_PHASE5_PLAN.md`, `docs/ORCHESTRATOR_V2_USAGE.md` |
| Deterministic Coverage | `scripts/tools/generate_implements.py` | Tags every story with the matching FR IDs via overrides + heuristics so coverage guards can stay on. | `docs/ORCHESTRATOR_V2_MIGRATION.md` |
| Learning Memory | `scripts/orchestrator/learning_store.py` | Records story outcomes + retention policy for policy feedback + analytics. | `docs/ORCHESTRATOR_V2_USAGE.md` |
| Smoke & Validation | `scripts/run_orchestrator_smoke_tests.sh` + guard scenario | Runs BA→PO→Architect→Dev→QA, enforces ≥80% coverage for new modules, and documents the guard artifacts. | `docs/ORCHESTRATOR_V2_USAGE.md`, `planning/task8_documentation_plan.md` |

## Phase Tracking

- **Phase 4** – Closed in `docs/ORCHESTRATOR_V2_PHASE4_COMPLETION.md`. CoT tracker, DnD policy blockers, agentic CLI, and smoke coverage are delivered.  
- **Phase 5** – Finalized via `docs/ORCHESTRATOR_V2_PHASE5_PLAN.md` (learning, tagging, guard).  
- **Phase 5 Checklist** – `planning/phase5_tasks_checklist.md` lists A1‑A3 + B1‑B3 with statuses.

## Tests & Quality

- Unit suites: `tests/scripts/test_cot_analytics.py`, `tests/scripts/test_generate_implements.py`, `tests/test_learning_store.py`, `tests/test_policy_feedback.py`.  
- Smoke guard scenario: `./scripts/run_orchestrator_smoke_tests.sh guard` writes `artifacts/iterations/latest_orchestrator_summary.json` and `logs/pipeline.log`.  
- Pipeline guard runs: `PYTHONPATH=. CHECK_ARCHITECTURE=0 ALLOW_EMPTY_STORIES=1 python scripts/checks/pipeline_guard.py` writes `artifacts/qa/pipeline_guard.json`.

## Docs Map

- **Design + Execution**: `docs/ORCHESTRATOR_V2_DESIGN.md`, `docs/ORCHESTRATOR_V2_PHASE4_PLAN.md`, `docs/ORCHESTRATOR_V2_PHASE5_PLAN.md`.  
- **Usage & Migration**: `docs/ORCHESTRATOR_V2_USAGE.md`, `docs/ORCHESTRATOR_V2_MIGRATION.md`.  
- **Planning / Memory**: `planning/phase5/`, `planning/task8_documentation_plan.md`, `docs/PROJECT_MEMORY.md`.

## Next Considerations

1. Keep `features.pipeline_guard.bypass` false once the learning/policy stack proves stable.  
2. Store CoT analytics in `artifacts/cot_layer6/` after each smoke run for traceability.  
3. Update this document whenever planning or component architecture evolves; it should remain the single “memory” snapshot for the team.
