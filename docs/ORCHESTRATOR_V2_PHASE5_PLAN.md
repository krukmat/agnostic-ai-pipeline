# Orchestrator V2 - Phase 5 Learning & CoT Expansion Plan

**Status**: 📋 PLANNING (Draft for approval)
**Scope**: Extend Phase 4 foundation with automated learning, deterministic `implements` coverage, and CoT analytics.
**Reference**: `docs/ORCHESTRATOR_V2_DESIGN.md` (Migration Path #5)
**Date**: December 10, 2025

---

## Executive Summary

Phase 5 operationalizes the CoT assets built in Phase 4. The focus is to transform the raw reasoning logs into actionable learning signals, close the remaining governance gaps (automated `implements` tagging, guard enforcement), and provide durable analytics so the orchestrator can improve without additional LLM spend. The plan introduces six tasks grouped across two batches (A = analytics + tagging, B = learning + governance) and follows the same documentation/testing rigor mandated in `AGENTS.md`.

### Key Outcomes
- Deterministic story `implements` coverage so the pipeline guard can be re-enabled.
- Learning layer that correlates FRs ↔ stories ↔ CoT outcomes, enabling targeted retries.
- CoT analytics dashboard and retention policy for long-running programs.
- Expanded smoke/coverage tests ensuring ≥80% coverage on new modules.
- Documentation + migration instructions for disabling the temporary bypass flags.

---

## Design Closure Map

| Design Section | Phase 5 Tasks | Status Goal |
|---|---|---|
| CoT Analytics & Learning Layer | Tasks 1, 3, 4 | ✅
| Deterministic Story Coverage | Task 2 | ✅
| Governance Flags Removal | Task 5 | ✅
| Extended Smoke/QA Automation | Task 6 | ✅

---

## Tasks Overview

### Task 1: CoT Analytics Aggregator
- **Files**: `scripts/orchestrator/cot_analytics.py` (new), `tests/test_cot_analytics.py`.
- **Purpose**: Parse JSONL outputs from `artifacts/cot_layer6/` and compute KPIs (story success rate per phase, failure clusters, ambiguity scores).
- **Deliverables**:
  - Data model + CLI entry (`python scripts/orchestrator/cot_analytics.py --last-run`).
  - Persisted summary `artifacts/cot_layer6/analytics.json` plus Markdown report.
- **Tests**: Fixtures simulating multiple CoT logs; coverage ≥85%.
- **Effort**: 1.5d.

### Task 2: Deterministic `implements` Tagging
- **Files**: `scripts/tools/generate_implements.py` (new), integration into `make po` / `scripts/run_product_owner.py`.
- **Purpose**: Map FR IDs to stories via keyword/config heuristics so every story has an `implements` list before Dev runs.
- **Deliverables**:
  - Configurable mapping file (e.g., `planning/fr_story_map.yaml`).
  - CLI tool invoked automatically after BA or PO steps.
- **Tests**: `tests/scripts/test_generate_implements.py` covering edge cases (missing FR, multiple matches, overrides).
- **Effort**: 2d.

### Task 3: Learning Memory Store
- **Files**: `scripts/orchestrator/learning_store.py`, `scripts/orchestrator_runtime.py` integration.
- **Purpose**: Record per-story attempts, errors, and remediation strategies to inform future runs (simple SQLite/JSON store per repo).
- **Deliverables**:
  - Append-only memory (JSONL or SQLite) with retention policy.
  - API to fetch last N outcomes when planning a story.
- **Tests**: Unit tests for read/write/retention; integration test with planner stub.
- **Effort**: 1.5d.

### Task 4: Policy Feedback Loop
- **Files**: `scripts/orchestrator/policy_feedback.py`, planner hooks.
- **Purpose**: Use analytics + learning store to auto-adjust retry strategies (e.g., bump attempts for flaky stories, escalate epics with repeated failures).
- **Deliverables**:
  - Policy engine extensions referencing analytics KPIs.
  - Config toggles under `config.yaml` (e.g., `features.policy_feedback.enabled`).
- **Tests**: Table-driven tests verifying adjustments, plus regression coverage so legacy behavior remains when disabled.
- **Effort**: 2d.

### Task 5: Guard Re-enablement & Config Cleanup
- **Files**: `config.yaml`, `scripts/run_orchestrator_agent.py`, docs.
- **Purpose**: Disable `features.pipeline_guard.bypass` and enforce coverage once deterministic `implements` exists.
- **Deliverables**:
  - Migration steps documented in `docs/ORCHESTRATOR_V2_MIGRATION.md`.
  - Pipeline validation hook ensuring guard passes before Dev.
- **Tests**: Integration test simulating guard failure/success, plus config schema updates.
- **Effort**: 1d.

### Task 6: Enhanced Smoke + Coverage Automation
- **Files**: `scripts/run_orchestrator_smoke_tests.sh`, `tests/smoke/test_agentic_orchestrator.py`, CI configs (if present).
- **Purpose**: Add scenarios verifying `implements` tagging, guard enforcement, and learning-store lookups.
- **Deliverables**:
  - New smoke scenario concept (e.g., multi-epic project) stored under `concepts.txt`.
  - Coverage enforcement script ensuring new modules ≥80%.
- **Tests**: Additional PyTest smoke cases; maybe GitHub Action step if CI is active.
- **Effort**: 1.5d.

---

## Implementation Order

| Batch | Tasks | Notes |
|---|---|---|
| Batch A | 1 (Analytics), 2 (`implements`), 6 (Smoke hooks) | Parallelizable; unblock guard removal. |
| Batch B | 3 (Learning store), 4 (Policy feedback), 5 (Guard/config cleanup) | Sequential, depends on analytics/tagging. |

All tasks must have individual planning artifacts under `planning/` before development (per AGENTS.md). Each code change requires unit tests and ≥80% coverage.

---

## Success Criteria
1. `features.pipeline_guard.bypass` can be set to `false` by default without breaking Dev runs.
2. `artifacts/cot_layer6/analytics.json` exists for every agentic loop execution with accuracy validated via tests.
3. Stories generated by PO automatically include `implements` arrays referencing FR IDs.
4. Learning store shows queryable history for each story; planner uses it when deciding retries.
5. Smoke harness passes new scenarios, capturing guard on/off behavior and learning adjustments.
6. Documentation updated (Usage, Migration, README) to describe Phase 5 features and toggles.

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Incorrect FR/story mapping inflates guard failures | Medium | Medium | Provide override config + tests; log warnings for manual review |
| Learning store adds I/O overhead | Low | Medium | Use batched writes; allow disabling via config |
| Analytics data growth | Medium | Low | Retention policy configurable (e.g., keep last N runs) |
| Smoke harness runtime increases | Low | Low | Parallelize or mark optional; reuse cached concepts |

---

## Verification & Documentation
- Unit tests under `tests/scripts/` for every new module, plus updates to smoke tests.
- Update `PHASE5_TASKS_CHECKLIST.md` (to be created) mirroring the structure of Phase 4.
- Extend `PHASE4_DOCUMENTS_INDEX.md`/README when Phase 5 begins, referencing this plan.
- Capture metrics in `coverage.xml`, `artifacts/cot_layer6/analytics.json`, and `artifacts/iterations/latest_orchestrator_summary.json`.

---

## Next Steps
1. Obtain approval for this Phase 5 plan.
2. Create `planning/phase5_tasks.csv` (or similar) describing Batches A/B with owners.
3. Begin Batch A once approval is granted, following the repo’s plan-before-dev rule.
4. Report progress via documented plan updates and commit summaries referencing this file.
