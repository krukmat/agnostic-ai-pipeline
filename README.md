# AGNOSTIC AI PIPELINE 🏗️

Ship product increments through repeatable cycles: BA → PO → Architect → Dev → QA.

Learn more (Medium): Why an Agentic, Model‑Agnostic Pipeline beats a pile of scripts → https://medium.com/@iotforce/why-an-agentic-model-agnostic-pipeline-beats-a-pile-of-scripts-b57661276505

## Contents
- [Why this pipeline](#why-this-pipeline)
- [Configure Providers (examples)](#configure-providers-examples)
- [Quick Start](#quick-start)
- [Modes: Legacy vs DSPy](#modes-legacy-vs-dspy)
- [DSPy: Programs and Tuning](#dspy-programs-and-tuning-core-idea)
  - Datasets & Tuning (detailed)
- [Database Layer (optional)](#database-layer-optional)
- [Driver Layer (full guide)](#driver-layer)
- [Docs & Articles](#docs--articles)

## Product Concept

The purpose of this project is to automate the entire software development lifecycle, from the conception of an idea to its validation by QA. The pipeline generates code, tests, and planning artifacts ready for delivery.

- **Involved Roles** – A Business Analyst, Product Owner, Architect, Developer, QA, and an Orchestrator collaborate to transform a concept into a functional product.
- **Generated Artifacts** – The system produces planning files (`requirements.yaml`, `stories.yaml`), source code and tests (in `project/`), and QA reports (`artifacts/qa/`).
- **Workflow** – You can run a full cycle with `make iteration` or `make loop`, or run each role independently for debugging and granular control.

```mermaid
flowchart LR
    Concept[Business Concept] --> BA[Business Analyst]
    BA --> PO[Product Owner]
    PO --> ARCH[Architect]
    ARCH --> DEV[Developer]
    DEV --> QA[QA]
    QA --> Snapshot[Snapshot & Release Artifacts]
```

## Why this pipeline

- Model‑agnostic by design: swap providers without changing code.
- Practical economics: mix local OSS models with cloud LLMs per role.
- Built‑in resilience: fallback routing keeps loops moving.
- Measurable quality: DSPy + metrics enable prompt/program tuning.

## Configure Providers (examples)

### Vertex AI (Gemini)
To use Google's models via Vertex AI.
```bash
make set-role role=architect provider=vertex_cli model="gemini-1.0-pro"
```
*See `vertex_ai_gemini_provider_via_gcloud_implementation_guide_for_codex.md` for more configuration details.*

### OpenAI (GPT)
To use models like GPT-4 through a Codex-compatible CLI.
```bash
make set-role role=dev provider=codex_cli model="gpt-4-turbo"
```

### Claude Code CLI (Anthropic)
To call Anthropic's Claude Code via its local CLI (no direct API integration required).
```bash
make set-role role=dev provider=claude_cli model="claude-3-5-sonnet-latest"
```
*Prerequisites*: run `claude login` (or equivalent token setup) beforehand and ensure the binary is on your `PATH`.
*Optional verbose mode*: set `debug: true` on the `claude_cli` provider in `config.yaml` to add `--verbose --debug` flags and persist CLI stderr under `artifacts/<role>/last_raw.txt`.

### Ollama (Local Models)
To run open-source models like Llama or Mistral on your own machine.
```bash
make set-role role=dev provider=ollama model="mistral:7b-instruct"
```

### Local-Only Example with Ollama
For an entirely local stack, point the core roles to Ollama models:
```bash
make set-role role=architect provider=ollama model="qwen2.5-coder:7b"
make set-role role=dev provider=ollama model="qwen2.5-coder:14b"
make set-role role=qa provider=ollama model="qwen2.5-coder:7b"
```
This keeps every agent on locally hosted models while the pipeline remains ready to switch back to hosted providers when needed.

---

## Quick Start

1. **Install dependencies**
   ```bash
   make setup
   ```
2. **Configure providers and models**
   ```bash
   # Example: Architect with OpenAI and Development with a local model
   make set-role role=architect provider=codex_cli model="gpt-4-turbo"
   make set-role role=dev provider=ollama model="mistral:7b-instruct"
   ```
3. **Run a full development cycle**
   ```bash
   make iteration CONCEPT="An inventory system for a coffee shop"
   ```
4. **Inspect the results**
   ```bash
   cat artifacts/iterations/<iteration>/summary.json
   tree artifacts/iterations/<iteration>/
   ```

---

## Modes: Legacy vs DSPy

The pipeline intentionally supports two execution styles:

1. **Legacy mode** – the original role scripts (`scripts/run_product_owner.py`, `scripts/run_architect.py`, etc.) call the selected models with static prompts. Use this mode to bootstrap or refresh datasets because it reflects the “factory baseline” and never depends on optimized instructions.
2. **DSPy + MiPROv2 mode** – each role also has a DSPy program (`dspy_baseline/modules/...`). When you want better quality you run:
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py --role <role> --trainset <train.jsonl> --valset <val.jsonl> --metric <metric> [...]
   ```
   MiPROv2 will discover improved instructions and few‑shot demos, write them under `artifacts/dspy/optimizer/<role>/`, and record the validation score.

### Recommended workflow

1. **Generate or clean data in legacy mode.**  
   - Run the role’s legacy script to produce JSONL outputs.  
   - Normalize them (helpers live under `scripts/` such as `normalize_ba_jsonl.py`).  
   - Split into `train/val` and store them in `dspy_baseline/data/production/` or `artifacts/synthetic/<role>/`.
2. **Run MiPROv2 on the DSPy program.**  
   - Launch `scripts/tune_dspy.py` with those JSONL files and the role metric (e.g., `dspy_baseline.metrics.architect_metrics:architect_metric_v2`).  
   - The optimizer prints the validation average and stores `program_components.json` plus `eval_summary.json`.
3. **Activate the optimized prompt.**  
   - Update `config.yaml` → `features.<role>.use_optimized_prompt: true` and point `prompt_override_file` to the generated `program_components.json`.  
   - From now on, running the role (either via `make <ROLE>` or `scripts/run_<role>.py`) automatically uses the tuned DSPy instructions.

When to switch back to legacy

- **New data** – if you need more examples or radically different concepts, return to legacy mode to generate/clean them, then run MiPRO again.  
- **New model/provider** – any time you swap the underlying LLM, re-run MiPRO because the old prompt was optimized for the previous model.  
- Otherwise keep executing in DSPy mode; legacy is only your “springboard” for data refreshes.

> **Architect note:** `features.architect.arch_only` controls whether the Architect role skips story generation and uses stubbed JSON just to produce architectures. Keep it `false` for the full BA→PO→Architect→Dev→QA pipeline (stories + architecture). Only set it to `true` when you are intentionally collecting architecture-only datasets, knowing that Dev/QA will not receive real stories in that mode.

---

## Docs & Articles

Project documentation lives under `docs/` inside this repository. For high‑level context and rationale, refer to the Medium series below.

Medium series (high‑level concepts and rationale)
- Part 1 — Why an Agentic, Model‑Agnostic Pipeline: replacing brittle scripts with a choreographed multi‑role loop that survives provider changes and scales with needs.  
  https://medium.com/@iotforce/why-an-agentic-model-agnostic-pipeline-beats-a-pile-of-scripts-b57661276505
- Part 2 — Inside the AI Development Team: how BA, Architect, Dev and QA hand off artifacts, enforce quality, and keep the cycle moving.  
  https://medium.com/@iotforce/inside-the-ai-development-team-ba-architect-developer-qa-e7631503f0d9
- Part 3 — Smart Routing for 89% Cost Reduction: choosing strong vs. local models per task to optimize spend without losing coverage.  
  https://medium.com/@iotforce/how-i-cut-ai-costs-by-89-using-smart-routing-and-local-models-d58258a14802
- Part 4 — Automatic Recovery from Model Failures: resilience patterns (fallbacks, retries, budgets) that keep releases on track.  
  https://iotforce.medium.com/how-my-ai-pipeline-automatically-recovered-from-8-model-failures-b39cb09c6ae0
- Part 5 — Scaling Agents with DSPy + MiPROv2: from manual prompts to automated program optimization with measurable metrics.  
  https://medium.com/@iotforce/scaling-ai-agents-with-dspy-and-miprov2-from-manual-prompts-to-automated-optimization-6a88f993f2b2

---

Additional reading
- GitHub Pages tour → Vision, fallback, multi‑role pipeline, cost controls.
- Medium article → Why an agentic, model‑agnostic pipeline (link above).

### Database Layer (optional)
Toggle an SQLite mirror of YAML artifacts in `config.yaml > database.enabled` (default on). Quick ops:
- Init/upgrade: `make db-migrate`
- Inspect: `make db-stats`, `make db-costs`, `make db-verify`
- Docs: schema + rollout → `docs/DATABASE_LAYER_PLAN.md`

### DSPy: Programs and Tuning (core idea)

DSPy define cada rol como un programa con I/O claros (ej., historias/epics JSON → arquitectura YAML), reemplazando prompts libres con salidas acotadas y validadas.

Qué aporta
- Módulos composables con validación de campos.
- Outputs acotados (capas de tokens, tamaños de listas).
- Métrica por rol (ej. `architect_metric_v2`) para puntuar.
- MiPROv2 busca instrucciones y few-shots mejores.

Cómo tunear (ejemplo rápido)
```bash
PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py \
  --role architect \
  --trainset artifacts/synthetic/architect/architect_train_gold_v2.jsonl \
  --valset   artifacts/synthetic/architect/architect_val_gold_v2.jsonl \
  --metric dspy_baseline.metrics.architect_metrics:architect_metric_v2
```
Artefactos: `artifacts/dspy/optimizer/<role>/{metadata.json,eval_summary.json,program_components.json}`

---

## Driver Layer

See the complete guide: docs/DRIVER_LAYER_GUIDE.md

Datasets & Tuning (detailed)
- Location: `dspy_baseline/data/production/` for curated sets; gold splits under `artifacts/synthetic/<role>/` (e.g., `.../architect_train_gold_v2.jsonl`).
- Schema (JSONL): each line has `{input:{...}, output:{...}, metadata:{score, provider, model}}`. Tuning only needs `input`/`output`; `metadata.score` helps filter gold.
- Build a gold split: generate ≥40 train / 10 val samples with min score ≥0.85 using the role’s metric (partial‑credit metrics recommended). Keep sets small but high quality.
- Generate datasets (legacy): use the role scripts (e.g., `scripts/run_architect.py dataset ... --metric-path <metric> --min-score 0.85 --max-records 50`) and normalizers (YAML sanitizers, dedupe) to stabilize outputs.
- Caps & pruning: bound lists (e.g., ≤6 stories, ≤3 epics/components) and raise token caps only when needed to avoid truncation.
- Larger searches: for deeper MiPRO runs, increase `--num-candidates` and `--num-trials` (e.g., 16×48). Expect long runs; always capture logs with `tee` and rely on `eval_summary.json` for the final score.
- Activation: once a tuned run is satisfactory, point `features.<role>.prompt_override_file` to the resulting `program_components.json` and set `use_optimized_prompt: true`.

Notes learned
- Prefer partial‑credit metrics (avoid all‑or‑nothing) so MiPRO can make incremental gains.
- Keep outputs bounded (caps, pruning) to reduce truncation; raise caps only if quality demands it.
- Build a small gold split (e.g., 40/10) with min score ≥ 0.85 before tuning; it stabilizes search.

Quick example
```bash
make ba CONCEPT="Smart radio with intelligent station selection"
make po && make plan
make dspy-qa && make dspy-qa-lint
# Inspect: planning/requirements.yaml, planning/stories.yaml,
# and artifacts/dspy/testcases/S001.md
```

CI/Sandbox Flags
- `DSPY_QA_SKIP_IF_MISSING=1 make qa` skips DSPy generation if no model is available and only lints when artifacts exist
- `DSPY_QA_STUB=1 make dspy-qa` generates deterministic cases from `dspy_baseline/data/qa_eval.yaml` (smoke when LLM is unavailable)

Key Files
- Modules: `dspy_baseline/modules/qa_testcases.py` (DSPy), `dspy_baseline/config/metrics.py` (heuristic), `dspy_baseline/data/qa_eval.yaml` (per‑story keywords)
- Scripts: `scripts/generate_dspy_testcases.py`, `scripts/lint_dspy_testcases.py`
- Artifacts: `planning/*.yaml`, `artifacts/dspy/testcases/*.md`

#### DSPy vs. legacy – how each role is configured
- **Single source of truth**: `config.yaml` controls provider/model/temperature per role for both legacy clients and DSPy modules. You no longer need to duplicate these values elsewhere.
- **Business Analyst**: toggle `features.use_dspy_ba` to switch between the DSPy baseline and the legacy `ba_legacy.py`. When DSPy is enabled, `scripts/run_ba.py` builds an LM with the `roles.ba` settings.
- **Product Owner**: toggle `features.use_dspy_product_owner`. When true, `scripts/run_product_owner.py` loads the frozen DSPy snapshot in `artifacts/dspy/po_optimized_full_snapshot_*` and uses the LM described under `roles.product_owner`. When false, the legacy LLM client runs with the same config defaults.
- **Architect**: toggle `features.use_dspy_architect`. In DSPy mode the role is broken into three modules (stories/epics, architecture, PRD/tasks) executed as a pipeline, each one picking the LM from `roles.architect` and writing its artifacts under `planning/`. When the flag is disabled the legacy prompt-based flow continues to work unchanged.
- **Concept source**: regardless of DSPy/legacy mode, the PO script pulls the concept from `planning/requirements.yaml` (`meta.original_request`) so it always matches the BA output. Setting `CONCEPT="..." make po` is only needed for local experiments when BA hasn’t run yet.
- **Dev/QA**: still run in legacy mode today. They will adopt the same DSPy + MiPRO flow once their datasets and metrics reach parity with Architect/PO.
- **Temporary overrides**: to experiment without editing `config.yaml`, export `DSPY_<ROLE>_LM`, `DSPY_<ROLE>_TEMPERATURE`, or `DSPY_<ROLE>_MAX_TOKENS` (for example `DSPY_PRODUCT_OWNER_LM=ollama/qwen2.5`). These environment variables override the LM spec only for that run. You can also force/disable PO DSPy with `USE_DSPY_PO=1` or `USE_DSPY_PO=0`.
If a provider is unavailable (e.g., Ollama is stopped) the scripts log the failure and, when applicable, fall back to the legacy path so the pipeline keeps moving.

### Google AI Gemini (optional)
- Install dependency once inside `.venv`: `pip install -U google-genai`.
- Add the provider block in `config.yaml`:
  ```yaml
  providers:
    google_ai_gemini:
      type: google_ai_gemini
      api_key: <tu_api_key>
  ```
- Point any role to it (e.g., `roles.product_owner.provider: google_ai_gemini`, `model: gemini-2.5-pro`).
- Export the key (or let the config supply it): `export GEMINI_API_KEY="<tu_api_key>"`.
The `google-genai` client se encarga del resto; desde los scripts basta con mantener `system`/`user` prompts como siempre.

 

BA (Requirements) with DSPy
- Module: `dspy_baseline/modules/ba_requirements.py` (signature + `Predict` module)
- CLI: `dspy_baseline/scripts/run_ba.py` (reads provider/model from `config.yaml`)
- Run: `make ba CONCEPT="..."` (or `make dspy-ba CONCEPT="..."`)
- Output: `planning/requirements.yaml` (title, description, FR/NFR/constraints)

Expanding the QA dataset
- Locate new story IDs in `planning/stories.yaml` and add entries to `dspy_baseline/data/qa_eval.yaml`:
  - `story_id`: the exact ID (e.g., `S011`)
  - `description`: short intent (why these checks exist)
  - `required_mentions`: 3–5 lowercase tokens you expect in Unhappy tests (e.g., `invalid`, `retry`, `timeout`, `unauthorized`, `no data`)
- Keep tokens short and failure‑oriented; avoid long sentences. Include at least one reliability or security keyword when applicable.
- Validate locally:
  - Real: `make dspy-qa && make dspy-qa-lint`
  - Stub (no model): `DSPY_QA_STUB=1 make dspy-qa && make dspy-qa-lint`
- CI tip: if the model isn’t available, commit a snapshot of `artifacts/dspy/testcases/` or run with `DSPY_QA_SKIP_IF_MISSING=1` so the lint checks only existing files.

### Architect Complexity Tiers

The Architect agent analyzes the requirements and adjusts the level of detail in the user stories.
- **Tiers**: `Simple`, `Medium`, `Corporate`.
- **Selection**: An LLM classifier determines the complexity level based on the requirements text, although it can be forced manually.

---

## Advanced Controls

| Flag | Purpose |
| ---- | ------- |
| `ALLOW_NO_TESTS` | TDD strictness level (0 = strict, 1 = relaxed) |
| `ARCHITECT_INTERVENTION` | Allows the architect to refine stories if QA fails |
| `STRICT_TDD` | Forces the architect to include additional TDD requirements |
| `LOOP_MODE=dev_only` | Skips the QA step for exploratory coding cycles |
| `SKIP_BA` / `SKIP_PO` / `SKIP_PLAN` | Reuses existing artifacts for incremental releases |

---

## Reference Commands

```bash
# Individual actions
make ba                          # Generate requirements
make po                          # Review product vision
make plan                        # Generate epics, stories, and tasks
make dev STORY=S1                # Implement a specific story
make qa QA_RUN_TESTS=1           # Run QA with tests

# Orchestration
make loop MAX_LOOPS=10           # Start a Dev↔QA loop
make iteration CONCEPT="..."     # Run a full release cycle

# Start services in A2A mode
python scripts/run_ba.py serve
python scripts/run_architect.py serve
python scripts/run_dev.py serve
# ... and so on for each role

# Utilities
make clean                       # Clean up artifacts
make show-config                 # Display the model configuration per role
```

---

## Proven Results

This pipeline has already generated:
- A complete e-commerce platform (authentication, catalog, cart, checkout).
- Over 200 automated tests validated by QA in strict mode.
- Zero manual coding once the initial concept is defined.

---

## Conclusion

Treat each `make iteration` cycle as a self-contained product increment. The workflow is **simple to operate**, **powerful in its coverage**, and **extensible to any tech stack**. The AGNOSTIC AI PIPELINE turns the release cycle into a repeatable process that scales while maintaining auditable artifacts. 🚀

---

## Public Pages (Guided Tour)

A friendly tour to understand the project before running anything. Each link opens a shareable HTML page.

- Start Here: Vision & End‑to‑End Flow (`docs/00-vision-ok/index.html`) — What the pipeline is, how an idea walks through BA → PO → Architect → Dev → QA, and why this loop keeps shipping consistently. Link: https://krukmat.github.io/agnostic-ai-pipeline/00-vision-ok/
- Resilience in Practice (`docs/01-fallback-system/index.html`) — How the system keeps working when models fail, from the decision logic that promotes backups to the guardrails that protect the budget. Link: https://krukmat.github.io/agnostic-ai-pipeline/01-fallback-system/
- Meet the Team of Agents (`docs/02-multi-role-pipeline/index.html`) — A story about each role’s deliverables, how artifacts move forward, and how you can run the same collaboration as Agent-to-Agent services. Link: https://krukmat.github.io/agnostic-ai-pipeline/02-multi-role-pipeline/
- Cost Engineering & Model Routing (`docs/03-cost-engineering/index.html`) — How the router (RoRF) balances speed vs. quality, with playbooks for keeping spend in check without giving up coverage. Link: https://krukmat.github.io/agnostic-ai-pipeline/03-cost-engineering/
- Configure Fallback Controls (`docs/04-fallback-system/index.html`) — Practical knobs in `config.yaml` to set recovery budgets, observability, and escalation paths so loops don’t stall. Link: https://krukmat.github.io/agnostic-ai-pipeline/04-fallback-system/
