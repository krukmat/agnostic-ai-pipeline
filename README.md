# AGNOSTIC AI PIPELINE 🏗️

Ship product increments through repeatable cycles: BA → PO → Architect → Dev → QA.

Learn more (Medium): Why an Agentic, Model‑Agnostic Pipeline beats a pile of scripts → https://medium.com/@iotforce/why-an-agentic-model-agnostic-pipeline-beats-a-pile-of-scripts-b57661276505

## Contents
- [Why this pipeline](#why-this-pipeline)
- [Quick Start](#quick-start)
- [Configure Providers](#configure-providers-examples)
- [Key Features](#key-features)
  - [Complexity-Based Routing](#complexity-based-routing-new)
  - [DSPy Programs & Optimization](#dspy-programs--tuning)
  - [Database Layer](#database-layer-optional)
  - [Driver Layer](#driver-layer)
- [Advanced Topics](#advanced-topics)
- [Docs & Articles](#docs--articles)

## Product Concept

The purpose of this project is to automate the entire software development lifecycle, from the conception of an idea to its validation by QA. The pipeline generates code, tests, and planning artifacts ready for delivery.

- **Involved Roles** – A Business Analyst, Product Owner, Architect, Developer, QA, and an Orchestrator collaborate to transform a concept into a functional product.
- **Generated Artifacts** – The system produces planning files (`requirements.yaml`, `stories.yaml`), source code and tests (in `project/`), and QA reports (`artifacts/qa/`).
- **Workflow** – Usa `make iteration` (orquestador agentic) o ejecuta cada rol de forma independiente para depurar o tener control granular.

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

- **Model‑agnostic by design**: swap providers without changing code
- **Practical economics**: mix local OSS models with cloud LLMs per role
- **Intelligent routing**: automatically select models based on task complexity (simple/medium/complex)
- **Built‑in resilience**: fallback routing keeps loops moving
- **Measurable quality**: DSPy + metrics enable prompt/program tuning

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

## Configure Providers (examples)

### Vertex AI (Gemini)
```bash
make set-role role=architect provider=vertex_cli model="gemini-1.0-pro"
```
*See `vertex_ai_gemini_provider_via_gcloud_implementation_guide_for_codex.md` for details.*

### OpenAI (GPT)
```bash
make set-role role=dev provider=codex_cli model="gpt-4-turbo"
```

### Claude Code CLI (Anthropic)
```bash
make set-role role=dev provider=claude_cli model="claude-3-5-sonnet-latest"
```
*Prerequisites*: run `claude login` and ensure the binary is on your `PATH`.

### Ollama (Local Models)
```bash
make set-role role=dev provider=ollama model="mistral:7b-instruct"
```

### Local-Only Stack Example
```bash
make set-role role=architect provider=ollama model="qwen2.5-coder:7b"
make set-role role=dev provider=ollama model="qwen2.5-coder:14b"
make set-role role=qa provider=ollama model="qwen2.5-coder:7b"
```

---

## Key Features

### Chain-of-Thought & Learning Layer

- The orchestrator logs every planner/policy/LLM decision via `scripts/orchestrator/cot_tracker.py` so you can audit CoT artifacts in `artifacts/cot_layer6/`.
- `scripts/orchestrator/cot_analytics.py` turns those logs into JSON/Markdown summaries while `scripts/orchestrator/learning_store.py` records per-story attempts for policy feedback.
- `scripts/orchestrator/policy_feedback.py` looks at the learning store, reprioritizes ready stories, and escalates repeat failures before developers begin work; deterministic `implements` tagging (`scripts/tools/generate_implements.py`) keeps the guard satisfied.
- See [Project Memory](docs/PROJECT_MEMORY.md) for the narrative, references, and artifacts related to CoT, analytics, guard reports, and policy feedback.

### Complexity-Based Routing (NEW)

**Automatically select different models based on story complexity** to optimize cost and quality.

#### How It Works

1. **Architect classifies stories** as `simple`, `medium`, or `complex`
2. **Routing matrix** in `config.yaml` maps each complexity level to specific provider/model
3. **Developer & QA** automatically use the appropriate model for each story

#### Example Configuration

```yaml
features:
  routing_by_complexity_enabled: true

routing_by_complexity:
  dev:
    simple: ollama/qwen2.5-coder:7b      # Cheap local model
    medium: vertex_sdk/gemini-2.5-flash  # Balanced cloud model
    complex: codex_cli/gpt-4-turbo       # Powerful model for hard tasks
  qa:
    simple: ollama/qwen2.5-coder:7b
    medium: vertex_cli/gemini-2.5-pro
    complex: claude_cli/claude-3-5-sonnet-latest
```

#### Benefits

✅ **Cost optimization**: Use cheap models for simple CRUD stories (40-60% cost reduction)
✅ **Quality assurance**: Complex architecture stories get powerful models
✅ **Automatic classification**: Heuristic analyzer intelligently classifies stories without LLM calls
✅ **Config-driven**: Change routing rules without touching code

#### Real-World Example

```
Story S1: "Create GET endpoint for listing users"
  → Complexity: simple
  → Model: ollama/qwen2.5-coder:7b (local, free)

Story S2: "Implement JWT authentication with refresh tokens"
  → Complexity: medium
  → Model: vertex/gemini-2.5-flash ($0.002/1K tokens)

Story S3: "Migrate to distributed multi-tenant architecture"
  → Complexity: complex
  → Model: gpt-4-turbo (powerful, worth the cost)
```

**Documentation**: See `docs/COMPLEXITY_ROUTING_PLAN.md` and `docs/COMPLEXITY_ANALYZER.md` for details.

---

### DSPy Programs & Tuning

DSPy replaces manual prompts with composable programs that can be automatically optimized using MiPROv2.

#### Quick Overview

- **Programs**: Each role (BA, PO, Architect) has a DSPy module with validated I/O
- **Metrics**: Role-specific scoring functions (e.g., `architect_metric_v2`)
- **Optimization**: MiPROv2 searches for better instructions and few-shot examples
- **Activation**: Point `config.yaml` to optimized components

#### Tune a Role

```bash
PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py \
  --role architect \
  --trainset dspy_baseline/data/production/architect_train.jsonl \
  --valset dspy_baseline/data/production/architect_val.jsonl \
  --metric dspy_baseline.metrics.architect_metrics:architect_metric_v2
```

Artifacts saved to: `artifacts/dspy/optimizer/<role>/`

#### Recommended Workflow

1. **Generate baseline data** in legacy mode
2. **Normalize and split** into train/val (40 train / 10 val minimum)
3. **Run MiPROv2** optimization
4. **Activate optimized prompt** in `config.yaml`:
   ```yaml
   features:
     architect:
       use_optimized_prompt: true
       prompt_override_file: artifacts/dspy/optimizer/architect/program_components.json
   ```

**When to re-tune**: New model/provider, new data domain, quality degradation.

**Documentation**: See Medium article Part 5 (link below) and `dspy_baseline/README.md`

---

### Database Layer (optional)

SQLite mirror of YAML artifacts for analytics and versioning.

```yaml
database:
  enabled: true  # Toggle in config.yaml
```

**Quick ops**:
```bash
make db-migrate  # Init/upgrade schema
make db-stats    # Show statistics
make db-costs    # Cost analysis
make db-verify   # Integrity check
```

**Docs**: `docs/DATABASE_LAYER_PLAN.md`

---

### Driver Layer

Abstraction layer for test execution (pytest, jest, etc.) with sandboxing and resource limits.

**Full guide**: `docs/DRIVER_LAYER_GUIDE.md`

**Quick example**:
```python
from drivers import get_test_driver

driver = get_test_driver("pytest")
result = driver.run(path="tests/", timeout=60)
print(result.exit_code, result.summary)
```

---

## Advanced Topics

<details>
<summary><b>Architect Complexity Tiers</b></summary>

The Architect classifies requirements into tiers (`Simple`, `Medium`, `Corporate`) to adjust story detail level. An LLM classifier auto-detects the tier, or force manually:

```bash
FORCE_ARCHITECT_TIER=simple make plan
```
</details>

<details>
<summary><b>Advanced Routing (RoRF)</b></summary>

Runtime model recommendation that overrides complexity routing for dynamic cost optimization. Analyzes prompt content to potentially downgrade/upgrade models.

**See**: Medium article Part 3 and `docs/03-cost-engineering/index.html`
</details>

<details>
<summary><b>Legacy vs DSPy Modes</b></summary>

**Legacy**: Static prompts, good for bootstrapping datasets
**DSPy**: Optimized programs with MiPROv2, better quality

Toggle per role in `config.yaml`:
```yaml
features:
  use_dspy_ba: false          # BA in legacy mode
  use_dspy_product_owner: true # PO in DSPy mode
  use_dspy_architect: true     # Architect in DSPy mode
```
</details>

<details>
<summary><b>Control Flags</b></summary>

| Flag | Purpose |
| ---- | ------- |
| `ALLOW_NO_TESTS=1` | Relaxed TDD mode |
| `ARCHITECT_INTERVENTION=1` | Architect refines stories on QA failure |
| `STRICT_TDD=1` | Enforce strict test requirements |
| `LOOP_MODE=dev_only` | Skip QA for exploratory cycles |
| `SKIP_BA` / `SKIP_PO` / `SKIP_PLAN` | Reuse existing artifacts |
</details>

<details>
<summary><b>Google AI Gemini Provider</b></summary>

```bash
pip install -U google-genai
```

Add to `config.yaml`:
```yaml
providers:
  google_ai_gemini:
    type: google_ai_gemini
    api_key: <your_key>

roles:
  product_owner:
    provider: google_ai_gemini
    model: gemini-2.5-pro
```

Export key: `export GEMINI_API_KEY="<your_key>"`
</details>

---

## Reference Commands

```bash
# Individual roles
make ba                          # Generate requirements
make po                          # Review product vision
make plan                        # Generate epics, stories, tasks
make dev STORY=S1                # Implement specific story
make qa QA_RUN_TESTS=1           # Run QA with tests

# Orchestration
make iteration CONCEPT="..."     # Full BA→PO→Architect→Dev→QA cycle
make agentic-iteration CONCEPT="..." MAX_STEPS=5 MAX_ACTIONS=2   # Iteración agentic completa

# Configuration
make show-config                 # Display current config
make set-role role=dev provider=ollama model="qwen2.5-coder:7b"

# Database
make db-migrate                  # Initialize database
make db-stats                    # Show statistics
make db-costs                    # Cost analysis

# DSPy
make dspy-ba CONCEPT="..."       # Run BA in DSPy mode
make dspy-qa                     # Generate QA test cases
make dspy-qa-lint                # Lint test cases

# Utilities
make clean                       # Clean artifacts
make clean FLUSH=1               # Clean artifacts + planning + project
make fix-stories                 # Normalize stories.yaml
```

---

## Docs & Articles

### Project Documentation

- **Complexity Routing**: `docs/COMPLEXITY_ROUTING_PLAN.md`, `docs/COMPLEXITY_ANALYZER.md`
- **Database Layer**: `docs/DATABASE_LAYER_PLAN.md`
- **Driver Layer**: `docs/DRIVER_LAYER_GUIDE.md`
- **DSPy Baseline**: `dspy_baseline/README.md`
- **Project Memory**: `docs/PROJECT_MEMORY.md` – consolidated view of CoT, learning store, policy feedback, guard artifacts, and key docs
- **GitHub Pages**: Vision, fallback, cost controls → https://krukmat.github.io/agnostic-ai-pipeline/

### Medium Series (Concepts & Rationale)

1. **Why an Agentic, Model‑Agnostic Pipeline**
   Replacing brittle scripts with a choreographed agentic loop
   https://medium.com/@iotforce/why-an-agentic-model-agnostic-pipeline-beats-a-pile-of-scripts-b57661276505

2. **Inside the AI Development Team**
   How BA, Architect, Dev and QA hand off artifacts and enforce quality
   https://medium.com/@iotforce/inside-the-ai-development-team-ba-architect-developer-qa-e7631503f0d9

3. **Smart Routing for 89% Cost Reduction**
   Choosing strong vs. local models per task to optimize spend
   https://medium.com/@iotforce/how-i-cut-ai-costs-by-89-using-smart-routing-and-local-models-d58258a14802

4. **Automatic Recovery from Model Failures**
   Resilience patterns (fallbacks, retries, budgets) that keep releases on track
   https://iotforce.medium.com/how-my-ai-pipeline-automatically-recovered-from-8-model-failures-b39cb09c6ae0

5. **Scaling Agents with DSPy + MiPROv2**
   From manual prompts to automated program optimization with measurable metrics
   https://medium.com/@iotforce/scaling-ai-agents-with-dspy-and-miprov2-from-manual-prompts-to-automated-optimization-6a88f993f2b2

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

[Your License Here]

---

**Built with ❤️ for AI-powered software development**
