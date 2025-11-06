# Loop Release Workflow – AGNOSTIC AI PIPELINE 🏗️

**Deliver finished products through repeatable development cycles: BA → Product Owner → Architect → Dev → QA.**

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

## The Advantage of an Agnostic Pipeline

The main strength of this pipeline is its **AI model agnosticism**. This eliminates dependencies on a single provider and allows business priorities to drive technical decisions. The roles remain perfectly choreographed even when swapping model providers on the fly.

- **Frictionless Speed** – Adapt the AI power for each role. Use lightweight open-source models for ideation and delegate critical QA tasks to more powerful premium models.
- **Cost and Compliance Control** – Keep sensitive data on-premise using local models and only turn to cloud providers when strictly necessary.
- **Operational Resilience** – If an external provider fails, the pipeline can switch to an alternative model without stopping the development cycle.
- **Continuous Innovation** – Test new LLMs without rewriting scripts or prompts. Simply point to a new model and compare the results.

## Supported Providers

The pipeline is compatible with multiple AI model providers. You can configure which model each role uses with a simple command.

Here are some examples:

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

## Quick Start Guide

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

## Additional Features

### Deployable Pipeline as Services (A2A)

This repository adopts the **Agent-to-Agent (A2A)** protocol, allowing each role in the pipeline to run as an independent HTTP service. This enables distributed orchestration, where agents can be deployed, scaled, and replaced independently.

- **Classic Mode**: Run `make iteration`. The entire process occurs sequentially on a single machine. Ideal for quick iterations.
- **A2A Mode (Service Mesh)**: Start each role with `python scripts/run_<role>.py serve`. Agents expose HTTP endpoints and can be orchestrated remotely. Ideal for distributed systems and team collaboration.

### Model Recommender (RoRF)

The system can dynamically select the most suitable model (cost-efficient vs. high-quality) for a given task.
- **Activation**: Controlled from `config/model_recommender.yaml`.
- **How it works**: It uses a pre-trained router to analyze the prompt and choose between a `weak` model (fast and cheap) or a `strong` model (powerful and expensive).

### Developer Fallback Models

If the primary model fails, the developer role can automatically requeue the story using a fallback provider.
- **Configuration**: define a `backup_models` list under `roles.dev` in `config.yaml`, for example:
  ```yaml
  backup_models:
    - provider: claude_cli
      model: claude-3-5-sonnet-20241022
    - provider: ollama
      model: qwen2.5-coder:32b
  ```
- **How it works**: when `run_dev` exhausts its retries, the orchestrator logs the failure and writes `metadata.model_override` back to `planning/stories.yaml`. The next `make loop` run picks that override and launches the alternate provider with the correct settings.
- **Observability**: check `planning/stories.yaml` for `recovery_attempts`, `last_failure_reason`, `model_history`, and any active overrides.
- **Limits**: cap the number of recovery attempts via `pipeline.max_recovery_attempts` in `config.yaml` (default: `2`). Stories exceeding the budget move to `status: blocked_recovery_budget`.

### DSPy-Driven Planning & QA (New Feature)

Purpose
- Generate consistent requirements and per‑story QA test cases with DSPy.

Why DSPy? (Concept & Fit)
- Composable and testable: replace brittle prompts with clear I/O signatures and small modules (`Predict`, `ChainOfThought`).
- Measurable quality: heuristics + `qa_eval.yaml` make negative‑path coverage auditable.
- Consistency across roles: the same provider/model policy feeds BA → PO → Architect → QA. Dev tests (pytest/Jest) stay as the execution ground truth.

Scope
- Adds declarative generation and linting. It does not drive browsers or run end‑to‑end UI automation.

Flow & Artifacts
```
CONCEPT ── make ba (DSPy) ──> planning/requirements.yaml
  └── make po ──────────────> planning/product_vision.yaml, product_owner_review.yaml
      └── make plan ────────> planning/epics.yaml, stories.yaml, architecture.yaml, tasks.csv
          └── make dspy-qa ─> artifacts/dspy/testcases/Sxxx.md (numbered Happy/Unhappy)
               └── dspy-qa-lint ─> validates headings, numbering, and per‑story keywords
```

Simple Usage
- `make ba CONCEPT="..."` → generates `planning/requirements.yaml` (DSPy-backed)
- `make po && make plan` → vision/epics/stories from YAML
- `make dspy-qa` → Markdown per story under `artifacts/dspy/testcases/`
- `make dspy-qa-lint` → validates format and minimal negative coverage; also runs within `make qa`

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

Datasets & Tuning
- Curated datasets viven en `dspy_baseline/data/production/` (JSONL + `manifest.json` con hashes).
- Optimización opcional vía `dspy_baseline/optimizers/mipro.py` y el CLI `scripts/tune_dspy.py` (`--role`, `--trainset`, `--metric`, `--num-candidates`, `--max-iters`, `--seed`).
- Los programas compilados y metadatos se guardan bajo `artifacts/dspy/optimizer/<role>/`.

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
