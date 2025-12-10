# Project Memory – Agentic Orchestrator & Chain-of-Thought

This document focuses on the **agentic orchestrator** and its **Chain‑of‑Thought (CoT), guardrails, and learning layer** on top of the BA→PO→Architect→Dev→QA loop. It is the compact reference for how the new orchestrator behaves and which artifacts it touches, without overloading the README.

## 1. What the agentic orchestrator does

- Drives the full cycle **Business Analyst → Product Owner → Architect → Developer → QA** starting from a `CONCEPT`.
- Calls the role runners (`scripts/run_ba.py`, `scripts/run_product_owner.py`, `scripts/run_architect.py`, `scripts/run_dev.py`, `scripts/run_qa.py`) according to an internal policy and the current state of artifacts.
- Uses `scripts/run_orchestrator_agent.py` as the main entrypoint (wrapped by `make agentic-iteration`) and writes a step‑by‑step summary to `artifacts/iterations/latest_orchestrator_summary.json`.
- Keeps the legacy one‑shot helpers (`scripts/run_iteration.py`, direct `make iteration`) available, but the recommended path for experiments and guardrails is the **agentic orchestrator** via `make agentic-iteration`.

Typical agentic iteration:

```bash
make agentic-iteration CONCEPT="Inventory system for a coffee shop" MAX_STEPS=4 MAX_ACTIONS=2
```

## 2. Chain‑of‑Thought tracking & learning layer

The orchestrator records its reasoning and decisions so you can inspect and reuse them:

- `scripts/orchestrator/cot_tracker.py` logs every tool/role decision with enough context to rebuild the CoT; artifacts are stored under `artifacts/cot_layer6/`.
- `scripts/orchestrator/cot_analytics.py` summarizes those traces into JSON/Markdown reports so you can quickly see what the agent tried, why it backtracked, and how it converged.
- `scripts/orchestrator/learning_store.py` keeps per‑story history (attempts, failures, recoveries) so policies can learn from past runs.
- `scripts/orchestrator/policy_feedback.py` reads the learning store and reprioritizes work:
  - promotes “ready” stories when recent attempts were successful,
  - deprioritizes or escalates stories that repeatedly fail,
  - feeds signals back into routing and guard decisions.

These CoT and learning artifacts are append‑only: they help you debug and improve the orchestration while keeping the core BA→PO→Arch→Dev→QA loop deterministic.

## 3. Guardrails and deterministic `implements` coverage

On top of the CoT layer, the orchestrator relies on deterministic guardrails to avoid running Dev on a broken plan:

- The **pipeline guard** (`scripts/checks/pipeline_guard.py`) validates that:
  - `planning/product_owner_review.yaml` exists and is approved.
  - `planning/architecture.yaml` / `planning/epics.yaml` exist when required.
  - Every story in `planning/stories.yaml` exposes an `implements` field that covers the functional requirements in `planning/requirements.yaml`.
- `scripts/tools/generate_implements.py` and related helpers normalize and (re)generate `implements` so coverage is reproducible and does not depend on free‑form LLM output.
- The guard writes a structured report to `artifacts/qa/pipeline_guard.json` and fails fast when coverage or structure is incomplete.

Typical explicit guard run:

```bash
PYTHONPATH=. CHECK_ARCHITECTURE=0 ALLOW_EMPTY_STORIES=1 \
  python scripts/checks/pipeline_guard.py
```

If it passes you see `pipeline_guard: OK` and a JSON report under `artifacts/qa/pipeline_guard.json`. The agentic orchestrator can consult this status before giving Dev new work.

## 4. How information flows (Orchestrator view)

From the orchestrator’s perspective, the important artifacts are:

1. **BA (`scripts/run_ba.py`)**
   - Input: `CONCEPT`
   - Output: `planning/requirements.yaml` (functional requirements and context)
2. **PO (`scripts/run_product_owner.py`)**
   - Input: `planning/requirements.yaml`
   - Output: `planning/product_owner_review.yaml` plus product vision updates
3. **Architect (`scripts/run_architect.py`)**
   - Input: requirements + PO review
   - Output:
     - `planning/stories.yaml` (stories with `implements` slots),
     - `planning/epics.yaml`, `planning/architecture.yaml`
4. **Guard (`scripts/checks/pipeline_guard.py`)**
   - Input: requirements, stories, architecture/epics
   - Output: `artifacts/qa/pipeline_guard.json` and a pass/fail decision
5. **Dev & QA (`scripts/run_dev.py`, `scripts/run_qa.py`)**
   - Input: validated stories and configuration
   - Output: code/tests under `project/` and reports under `artifacts/qa/`

The orchestrator stitches these steps together, recording CoT/logs in `logs/` and `artifacts/iterations/` so you can reconstruct the full decision path for any iteration.

## 5. How to use this in practice

Recommended workflow when working with the agentic orchestrator:

```bash
make setup
make agentic-iteration CONCEPT="..." MAX_STEPS=4 MAX_ACTIONS=2
PYTHONPATH=. python scripts/checks/pipeline_guard.py  # optional explicit guard run
```

If something fails or you want to inspect the behavior:

- Check `logs/pipeline.log` to see which phase or tool failed.
- Inspect `artifacts/iterations/latest_orchestrator_summary.json` to see the sequence of steps and actions.
- Browse `artifacts/cot_layer6/` for CoT traces and learning artifacts.
- Look at `artifacts/qa/pipeline_guard.json` to understand guard decisions (e.g., missing `implements`, uncovered FRs, or structural issues).

## 6. Where to read more (without bloating the README)

If you need deeper design details:

- `README.md` – high‑level overview, quick start, and main commands.
- `docs/PIPELINE_IMPROVES.md` – historical guardrail and robustness ideas.
- `docs/AGENTIC_ORCHESTRATOR_PLAN.md`, `docs/LEGACY_ORCHESTRATOR_REMOVAL_PLAN.md` – internal plans and migration notes for the orchestrator.

This file (`docs/PROJECT_MEMORY.md`) is the main public memory for the **agentic orchestrator + CoT/guardrails**. When that behavior changes, update this document first; keep additional design docs small and only link them when strictly necessary.
