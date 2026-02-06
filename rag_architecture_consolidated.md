# RAG Local-First — Consolidated Architecture Document (Decision-Grade, No Implementation)

**Role**: High-level architecture + business objective validation + audit-ready criteria  
**Scope**: Consolidation of `rag_concept_architecture.md` and `rag_implementation.md`  
**Note**: No code or implementation details. This document defines **phases, tasks, subtasks, dependencies**, and **verifiable gates**.

---

## Table of contents

1. Business objective
2. Guiding principles
3. Conceptual components
4. Metrics and Definition of Success
5. Corpus scope (sensitivity, authority, TTL)
6. Evaluation dataset (Phase 0)
7. Explicit budgets (by role and stage)
8. Retrieval framework and verifiable criteria
9. Chunking policy (PoC vs post‑PoC)
10. Query Rewriter policy (between layers)
11. Traceability (minimum schema)
12. Security, privacy, compliance (minimums)
13. Cost guardrails
14. QA gates for Python backend development
15. Business requirements validation (pipeline gates)
16. Phases, tasks, subtasks, dependencies
17. Decision table (operational)
18. RACI (decision ownership)
19. Next-cycle deliverables
20. Working branch

---

## 1. Business objective

Build a **local-first agentic RAG pipeline** that runs on **limited hardware** (baseline: **MacBook Pro M1 with 16GB**) without runtime GPU, while preserving **traceability**, **response quality**, and **mandatory citations**, and enabling **optional offline GPU** for artifact generation (embeddings, quantization, evaluation, distillation).

**Expected value**
- Improve role-specific responses (BA/PO/ARCH/DEV/QA) through evidence retrieval.
- Reduce hallucinations with **mandatory citations**, **abstention**, and **structural validation**.
- Keep costs low, with offline scaling on **Colab** (if within free limits) or **DigitalOcean** when required.

---

## 2. Guiding principles

1. **True local-first**: online execution without GPU.
2. **Offline/online separation**: ingestion/optimization off the critical path.
3. **Explicit budgets**: tokens/evidence/latency per role and task.
4. **Hybrid retrieval**: vector + lexical (BM25).
5. **End‑to‑end traceability**: retrieval decisions auditable.
6. **Knowledge versioning**: reproducible indexes and artifacts.
7. **Explicit hardware baseline**: optimized for M1/16GB in PoC.
8. **GPU offline only**: restricted to artifact generation.

---

## 3. Conceptual components (no implementation)

- **Knowledge Hub**: ingestion, normalization, chunking, embeddings, indexing, versioning.
- **Retrieval Gateway**: stable contract for agents.
- **Context Manager**: fusion, dedupe, diversity, budgets, context assembly.
- **Post‑Processing**: citations, formatting, structural validation.
- **Model Ops (offline)**: quantization, optional LoRA, distillation, evaluation.

---

## 4. Metrics and Definition of Success

### 4.1 Minimum metric suite (mandatory)
- **Latency**: p50 / p95 end‑to‑end and per stage (retrieval, assembly, generation).
- **Memory**: peak and sustained during normal queries.
- **Index size**: disk footprint including metadata/index structures.
- **Groundedness** (see 4.2).
- **Abstention** (see 4.3).

### 4.2 Groundedness rubric (0–3)
- **0**: no citations or irrelevant citations.
- **1**: partial citations; main claim unsupported.
- **2**: adequate evidence for main claim; minor gaps.
- **3**: strong evidence for main claims + explicit limitations.

**Sub‑metrics**
- **Citation coverage**: % of relevant claims with citations.
- **Citation correctness**: % of citations that support the claim.
- **Evidence sufficiency**: meets “minimum evidence” per role.

### 4.3 Abstention policy and metric
The system **must abstain** when evidence is insufficient or contradictory.

Metrics:
- **Correct abstention rate**: correct abstentions / total abstentions.
- **False answer rate**: responses with claims lacking sufficient evidence (target: 0).

---

## 5. Corpus scope (sensitivity, authority, TTL)

### 5.1 Mandatory source classification
Each source must be classified by:
- **Value**: High/Medium/Low
- **Risk**: High/Medium/Low
- **Authority**: ADR/Runbook > Official docs > Code > Tickets > Chats/Notes
- **TTL**: recommended expiry before considered stale
- **Sensitivity**: Public / Internal / Restricted

### 5.2 Minimum corpus template
| Source | Type | Value | Risk | Authority | TTL | Sensitivity | Included in PoC |
|---|---|---:|---:|---|---|---|---|
| Repo | Code | High | Medium | High | N/A | Internal | Yes |
| ADRs | Decisions | High | Low/Med | Very high | 12–24m | Internal | Yes |
| Docs | Guides | High | Low | High | 6–12m | Internal | Yes |
| Tickets | Requirements | Medium | Med/High | Medium | 3–6m | Internal/Restricted | Optional |
| Incidents | Ops | Medium | High | High | 3–6m | Restricted | No (PoC) |

**PoC rule**
- Initial volume **≤5,000 docs** or **≤500MB** total.
- If exceeded: segment by collections or cut by value/authority.

---

## 6. Evaluation dataset (Phase 0, mandatory)

### 6.1 Minimum test set
Freeze **representative queries** per role:
- **50–150 queries** total (10–30 per role).
- Include ambiguous queries, cross‑role transitions, recency needs, and “no‑answer” cases.

### 6.2 Gold evidence (when possible)
For a subset (20–40 queries), define **gold evidence**:
- Document/chunk IDs expected in top‑k or final context.

### 6.3 Version freezing
PoC evaluation is tied to:
- `corpus_version`
- `index_version`
- `testset_version`

---

## 7. Explicit budgets (by role and stage)

### 7.1 Role budgets (PoC baseline)
| Role | Top‑k (max) | Min evidence | Max context tokens | Concurrency | Policy |
|---|---:|---:|---:|---:|---|
| BA/PO | 5 | 2 | 2,000 | 2 | Prioritize clarity and traceability |
| ARCH | 8 | 3 | 3,000 | 2 | Prioritize ADRs and architecture |
| DEV | 8 | 3 | 3,500 | 2 | Prioritize code + technical docs |
| QA | 6 | 2 | 2,500 | 2 | Prioritize criteria and edge cases |

> Adjust only if Phase 0 metrics prove improvements without violating p95/memory.

### 7.2 Stage budgets (conceptual)
- **Retrieval**: limit candidates per channel (vector + BM25).
- **Assembly**: limit final chunks; aggressive dedupe.
- **Generation**: cap response length per role.

### 7.3 Minimum evidence rule (non‑negotiable)
If **min evidence** is not met with acceptable quality:
- abstain, or
- escalate (ask clarification / suggest corpus expansion).

---

## 8. Retrieval framework and verifiable criteria

### 8.1 Baseline selection
**Weaviate** baseline unless any PoC condition occurs:
- Sustained RAM > **12GB** during normal queries.
- p95 latency > **2s** with Phase 0 top‑k.
- Index size > **2x** Phase 0 limit.

### 8.2 FAISS vs Weaviate (selection criteria)
- **FAISS**: fully embedded PoC, small/medium corpus, minimal overhead, manual metadata/persistence/API handling.
- **Weaviate**: stable API, rich filters/metadata, governance features, within M1/16GB thresholds.

### 8.3 Measurement plan (audit‑ready)
Phase 0 must define:
- How to measure **sustained RAM** (time window + “normal query” definition).
- How to measure **p95** (runs, warm/cold, batch size).
- What counts as **index size** (vectors + metadata + index structures).

---

## 9. Chunking policy (PoC vs post‑PoC)

### 9.1 PoC (mandatory)
- **Deterministic heuristics** by content type.
- **LLM‑assisted chunking is prohibited** during PoC.

### 9.2 Post‑PoC (optional gate)
Enable LLM chunking only if:
- Improvement ≥ **10%** in top‑k precision or groundedness (test set).
- Ingestion cost increase ≤ **+25%**.
- No runtime latency/memory degradation.

### 9.3 Baseline chunking
- Docs: medium chunks by headings/sections.
- Code: small chunks by function/class.
- ADRs/Tickets: compact chunks centered on decision + rationale.

---

## 10. Query Rewriter policy (between layers)

**Purpose**: rewrite queries between agent → retrieval → generation to improve clarity and semantic coverage.

**PoC default**: OFF. Enable only if:
- Improvement ≥ **10–15%** (groundedness or top‑k precision) in controlled tests, and
- Added latency ≤ **150–250ms** per query, and
- Drift control passes.

**Drift control (minimum)**
- Preserve entities, constraints, and intent in an explicit list.
- If drift exceeds threshold in N consecutive cases, disable automatically.

---

## 11. Traceability (minimum schema)

**Required per request**:
- `request_id`, `timestamp`, `role`, `task_type`
- `query_original`
- `query_rewritten` + rationale (if applicable)
- `filters_applied`
- `retrieval_results_vector` (doc_id/chunk_id, score, rank)
- `retrieval_results_bm25` (doc_id/chunk_id, score, rank)
- `fusion_decisions` (dedupe/diversity/discards + reasons)
- `final_context_chunks` (chunk_id, source, token estimate)
- `budgets` (limits + consumption)
- `citations_map` (claim → chunk_id)
- `abstention_flag` + reason
- `output_validation` (structure/citations checks)

Retention and review are defined in Phase 4.

---

## 12. Security, privacy, compliance (minimums)

- **Explicit exclusion** of sources with PII/secrets if not redacted (PoC).
- Logging policy: no sensitive content in logs by default.
- Sensitivity‑based segmentation (separate collections if needed).
- Access rules for corpus indexing and querying.

---

## 13. Cost guardrails

**Primary cost drivers**
- Offline embeddings
- Storage (indexes/versions)
- Offline GPU (quantization/distillation)

**Guardrails**
- Define a PoC monthly limit (if applicable).
- **Colab** if within free limits and reproducible.
- **DigitalOcean** if resources are required and outputs are transferable.

---

## 14. QA gates for Python backend development (agent guide)

**Goal**: enforce measurable quality and maintainability gates for backend code produced by agents.

**Core metrics and tooling**
- **Test coverage**: ensure code executed by tests.
  - Tooling: `coverage.py`
- **Maintainability Index**: proxy for long‑term maintainability.
  - Tooling: `radon`
- **Cyclomatic complexity**: limit logical complexity per function/module.
  - Tooling: `radon`, `mccabe`
- **Lines of Code (LOC)**: track size growth and detect risk hotspots.
  - Tooling: `cloc`, `sloccount`
- **Code duplication**: detect redundant logic that increases maintenance cost.
  - Tooling: `radon` (limited) + optional duplication scanners
- **Code quality / linting**: enforce best practices.
  - Tooling: `pylint`, `flake8`
- **Code standards compliance**: consistent formatting and style.
  - Tooling: `pycodestyle`, `flake8`

**Quality gateways (optional integrators)**
- **SonarQube**: full‑stack quality platform (coverage, complexity, security).
- **Code Climate**: continuous code quality analysis.
- **Codacy**: static analysis for security and maintainability.

**Gate rules (baseline, adjustable)**
- Coverage: **≥80%** overall; critical modules **≥90%**.
- Cyclomatic complexity: **≤10** per function (flag at >10).
- Maintainability Index: **≥65** (flag if <65).
- Duplication: **<5%** duplicated lines (flag if ≥5%).
- Linting: **0 critical issues**, **≤5 medium issues** per module.

**Agent enforcement**
- Agents must report metrics in PR output.
- If any gate fails: fix or provide a written exception with rationale.

---

## 15. Business requirements validation (pipeline gates)

**Purpose**: validate business requirements at every pipeline stage to avoid drift and ensure traceability.

**Inputs (mandatory)**
- Business requirements list (objectives, acceptance criteria, constraints).
- Role context (BA/PO/ARCH/DEV/QA).
- Evidence requirements (minimum evidence per role).

**Outputs (mandatory)**
- Compliance status per requirement: **Met / Partially met / Not met**.
- Evidence map: requirement → cited sources.
- Failure reason for any unmet requirement.

**Stage gates**
1. **Retrieval gate**: required evidence is present in top‑k results.
2. **Context assembly gate**: selected evidence aligns to requirements and is traceable.
3. **Generation gate**: output matches acceptance criteria and required format.
4. **Post‑processing gate**: final validation; abstain if evidence is missing or contradictory.

**Validation metrics**
- **Requirement coverage**: % of requirements addressed in output.
- **Evidence coverage**: % of requirements with explicit citations.
- **Requirement pass rate**: % of requirements marked “Met”.
- **Abstention rate**: % of outputs that abstain due to unmet requirements.

**Gate rule**
- If any **critical requirement** is “Not met”, the system must abstain or request clarification.

---

## 16. Phases, tasks, subtasks, dependencies

> Phases are conceptual; no tool specifics.

### Phase 0 — Objective, scope, and measurement (critical gate)
**Purpose**: define per‑role objectives, corpus, and verifiable metrics.

**Tasks**
1. Define objectives per role and typical tasks.
2. Confirm M1/16GB baseline and budget limits.
3. Define initial corpus (include/exclude).
4. Define minimum metrics and thresholds.
5. Define test set and initial top‑k.
6. Agree on evidence sufficiency rubric.

**Mandatory Phase 0 checklist (single operational block)**
- Numeric thresholds for p95, memory, index size, groundedness.
- Corpus list (included/excluded) with sensitivity/authority/TTL.
- Frozen test set + version.
- Top‑k per role + minimum evidence.
- Gate: do not advance if any item is missing.

**Dependencies**
- Precedes contracts, chunking, budgets, and tooling decisions.

---

### Phase 1 — Retrieval Gateway contracts and policies
**Purpose**: formalize agent ↔ system interaction.

**Tasks**
1. Request contract: `query`, `role`, `task_type`, `filters`, `budgets`, `mode`.
2. Response contract: `items`, `evidence`, `trace_refs`, `abstention`.
3. Traceability and citation policies.

**Dependencies**
- Requires Phase 0.

---

### Phase 2 — Knowledge Hub conceptual
**Purpose**: ingestion, normalization, dedupe, versioning.

**Tasks**
1. Conceptual ingestion pipeline.
2. Chunking policies by content type.
3. Minimal metadata and versioning.
4. Weaviate vs FAISS decision using criteria + measurement plan.

**Dependencies**
- Requires Phases 0–1.

---

### Phase 3 — Context Manager & Post‑Processing
**Purpose**: evidence quality and format.

**Tasks**
1. Fusion/dedupe/diversity rules.
2. Role budgets + minimum evidence rule.
3. Output validation (citations mandatory, format, abstention).

**Dependencies**
- Requires Phases 1–2.

---

### Phase 4 — Evaluation and governance
**Purpose**: quality and risk loop.

**Tasks**
1. Final metric suite and measurement method.
2. Role acceptance thresholds.
3. Trace review process, update/rollback, expiry.

**Dependencies**
- Requires Phases 1–3.

---

### Phase 5 — Optimization roadmap (offline)
**Purpose**: improvements without breaking local-first.

**Tasks**
1. Offline GPU criteria (documented need + transferable outputs).
2. Transferable artifact strategy (indexes/models).
3. Priorities: quantization, specialization, distillation.

**Dependencies**
- Requires Phase 4.

---

## 17. Decision table (operational)

| Phase | Decision | Explicit criterion | Action if unmet |
|---|---|---|---|
| F0 | Hardware baseline | p95 ≤ 2s with agreed top‑k; memory within limit | Reduce corpus / adjust top‑k/budgets |
| F0 | Corpus size | ≤5,000 docs or ≤500MB | Segment or cut by value/authority |
| F1 | Contracts | Required fields defined | Revise contract |
| F2 | Weaviate viable | RAM ≤12GB sustained; p95 ≤2s; index ≤2x | Evaluate FAISS for PoC |
| F2 | LLM chunking | Post‑PoC: ≥10% improvement; cost ≤+25% | Keep heuristic |
| F3 | Query Rewriter | ≥10–15% improvement; ≤250ms; no drift | Disable |
| F4 | Minimum metrics | Groundedness/latency/memory defined | Do not advance to F5 |
| F5 | Offline GPU | Documented need + transferable outputs | Keep local-first |

---

## 18. RACI (decision ownership)

| Area | Responsible (R) | Approver (A) | Consulted (C) | Informed (I) |
|---|---|---|---|---|
| Role objectives | Product/BA | Sponsor/Stakeholders | Architecture | Team |
| Metrics + thresholds | Architecture | Sponsor | Dev/QA | Team |
| Corpus scope + sensitivity | Architecture/Security | Sponsor | BA/Legal/IT | Team |
| Gateway contracts | Architecture | Tech Lead | Dev/QA | Team |
| PoC go/no‑go | Architecture | Sponsor | Dev/QA | Team |

---

## 19. Next‑cycle deliverables

1. **Corpus document** (F0): sources, sensitivity, TTL, include/exclude.
2. **Test set + top‑k baseline** (F0): versioned queries.
3. **Retrieval Gateway contracts** (F1): request/response + policies.
4. **Chunking + metadata policies** (F2).
5. **Evaluation + trace review criteria** (F4).

---

## 20. Working branch

`architecture/rag-local-first-poc`

---

**Status**: Ready for stakeholder review and to execute Phase 0 (measurement and scope). 
