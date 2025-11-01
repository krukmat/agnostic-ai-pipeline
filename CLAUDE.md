# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AGNOSTIC AI PIPELINE** - An AI-powered software development lifecycle automation system that transforms business concepts into production-ready code through a multi-role agent pipeline (Business Analyst → Product Owner → Architect → Developer → QA).

The project is **provider-agnostic**: each role can use different AI models (OpenAI GPT, Claude, Gemini via Vertex AI, Ollama local models, etc.) configured dynamically in `config.yaml`.

## Essential Commands

### Setup and Configuration
```bash
make setup                    # Install dependencies in .venv
make show-config              # Display current model configuration per role
make set-role role=<ba|architect|dev|qa> provider=<ollama|openai|codex_cli|claude_cli|vertex_cli|vertex_sdk> model="model-name"
```

### Testing
```bash
# Run tests from repository root
.venv/bin/pytest                                    # Run all tests
.venv/bin/pytest tests/test_model_recommender.py   # Run specific test file
.venv/bin/pytest -v -s                              # Verbose output with print statements
.venv/bin/pytest tests/smoke/                      # Run smoke tests only
```

**IMPORTANT**: Always run tests before committing. Use `.venv/bin/pytest` from the repository root.

### Individual Role Execution
```bash
make ba CONCEPT="Your business idea"                # Generate requirements.yaml
make po                                             # Validate product vision
make plan                                           # Generate epics/stories from architect
make dev STORY=S1                                   # Implement specific story
make qa QA_RUN_TESTS=1                             # Run QA with test execution
```

### Orchestration Workflows
```bash
make iteration CONCEPT="Your idea" LOOPS=1          # Full BA→PO→Architect→Dev→QA cycle
make loop MAX_LOOPS=10 LOOP_MODE=full              # Dev↔QA loop until all stories done
make loop-dev                                       # Development-only loop (no QA)
```

### A2A (Agent-to-Agent) Service Mode
```bash
# Start individual role services (runs on ports defined in config.yaml a2a section)
python scripts/run_ba.py serve                      # Start BA service on :8001
python scripts/run_architect.py serve               # Start Architect service on :8003
python scripts/run_dev.py serve                     # Start Developer service on :8004
python scripts/run_qa.py serve                      # Start QA service on :8005

make warmup                                         # Pre-initialize A2A services
```

### Utilities
```bash
make clean                                          # Clean artifacts/ directory
make clean FLUSH=1                                  # Also delete planning/ and project/
make fix-stories                                    # Normalize planning/stories.yaml format
```

## Architecture

### Core Components

1. **LLM Client (`scripts/llm.py`)**
   - Unified interface for multiple AI providers (Ollama, OpenAI, Claude CLI, Vertex AI)
   - Configured via `config.yaml` with per-role provider/model settings
   - Supports model recommendation (RoRF) for dynamic cost/quality tradeoffs
   - CLI providers use subprocess execution with JSON/text input/output
   - Async-compatible with `httpx` for HTTP-based providers

2. **Role Scripts (`scripts/run_*.py`)**
   - Each role (BA, PO, Architect, Dev, QA) has a standalone script
   - Can run as CLI command or HTTP service (A2A mode)
   - Reads prompts from `prompts/*.md` templates
   - Outputs artifacts to `planning/` or `artifacts/`

3. **A2A Framework (`a2a/`)**
   - Agent-to-Agent protocol implementation for distributed execution
   - `runtime.py`: Service lifecycle management
   - `executors.py`: Local vs. remote execution strategies
   - `server.py`: FastAPI-based agent HTTP endpoints
   - `client.py`: HTTP client for invoking remote agents
   - `config.py`: A2A configuration loader from `config.yaml`

4. **Orchestrator (`scripts/orchestrate.py`)**
   - Coordinates multi-role workflows (iteration, loop modes)
   - Manages story dependencies and state transitions
   - Handles retries, approval cycles, and QA feedback loops
   - Supports both local (direct function calls) and A2A (HTTP) execution

5. **Model Recommender (`src/recommend/`)**
   - Optional RoRF (Routing or Ranking Framework) integration
   - Dynamically selects weak vs. strong models based on prompt complexity
   - Controlled via `MODEL_RECO_ENABLED` environment variable

### Directory Structure

- **`planning/`**: Generated artifacts (requirements, stories, epics, architecture)
  - `requirements.yaml`: BA output
  - `product_owner_review.yaml`: PO validation
  - `stories.yaml`: Architect-generated user stories
  - `architecture.yaml`, `epics.yaml`, `prd.yaml`

- **`project/`**: Generated code output (e.g., `backend-fastapi/`)
  - Developer role writes implementation here
  - Follows project template from `project-defaults/`

- **`artifacts/`**: Execution logs, QA reports, iteration snapshots
  - `artifacts/iterations/<name>/`: Full cycle results with summary.json
  - `artifacts/qa/`: QA test results and reports

- **`prompts/`**: LLM prompt templates for each role
  - `ba.md`, `product_owner.md`, `architect.md`, `developer.md`, `qa.md`

- **`scripts/`**: Executable role implementations
  - `run_ba.py`, `run_product_owner.py`, `run_architect.py`, `run_dev.py`, `run_qa.py`
  - `orchestrate.py`: Main orchestration loop
  - `llm.py`: LLM client abstraction

- **`config.yaml`**: Centralized configuration
  - `providers`: Define provider types and connection settings
  - `roles`: Map roles to provider/model/temperature/max_tokens
  - `a2a`: Agent service URLs and authentication

### Workflow State Management

- **Story Status**: `todo` → `doing` → `done` (in `planning/stories.yaml`)
- **Architect Tiers**: `Simple`, `Medium`, `Corporate` (auto-classified by complexity)
- **QA Feedback Loop**: QA failures can trigger architect intervention to refine stories
- **Approval Cycles**: Architect validates story implementation before marking done

### Key Design Patterns

1. **Provider Abstraction**: `Client(role="dev")` automatically resolves provider from config
2. **CLI Bridging**: External CLIs (like Claude Code CLI) wrapped via subprocess with JSON I/O
3. **Async Throughout**: All LLM calls are async-compatible for concurrency
4. **TDD Enforcement**: Stories can require tests; QA validates test coverage
5. **Artifact Snapshots**: Each iteration creates timestamped snapshot for reproducibility

## Configuration Notes

- **Provider Types**: `ollama`, `openai`, `codex_cli`, `claude_cli`, `vertex_cli`, `vertex_sdk`
- **Environment Variables**:
  - `OLLAMA_BASE_URL`: Override Ollama endpoint
  - `OPENAI_API_KEY`, `OPENAI_API_BASE`: OpenAI configuration
  - `GCP_PROJECT`, `VERTEX_LOCATION`, `VERTEX_MODEL`: Vertex AI settings
  - `MODEL_RECO_ENABLED`: Enable/disable model recommender
  - `ROLE`: Override role detection in LLM client

## Provider-Specific Setup

### Claude Code CLI (claude_cli)
- Requires `claude` CLI on PATH
- Must authenticate first: `claude login`
- Config example:
  ```yaml
  roles:
    dev:
      provider: claude_cli
      model: claude-3-5-sonnet-latest
  ```

### Vertex AI (vertex_cli / vertex_sdk)
- Requires GCP authentication: `gcloud auth application-default login`
- Enable APIs: `gcloud services enable aiplatform.googleapis.com`
- Set `GCP_PROJECT` environment variable
- Use `make vertex-ping` to test connectivity

### Ollama (Local Models)
- Requires Ollama running: `ollama serve`
- Pull models first: `ollama pull mistral:7b-instruct`
- Default endpoint: `http://localhost:11434`

## Development Workflow

1. **New Feature Cycle**:
   ```bash
   make iteration CONCEPT="Your feature description"
   # Produces: requirements → stories → code → tests → QA report
   ```

2. **Incremental Development**:
   ```bash
   make ba CONCEPT="New feature"
   make po
   make plan
   make loop MAX_LOOPS=5  # Auto-implement all stories with QA validation
   ```

3. **Manual Story Implementation**:
   ```bash
   make dev STORY=S1      # Implement story S1
   make qa QA_RUN_TESTS=1 # Validate with tests
   ```

4. **Debugging Single Role**:
   ```bash
   .venv/bin/python scripts/run_dev.py  # Direct script execution
   ```

## Important Constraints

- **TDD by Default**: Developer role enforces test-first approach (configurable via `ALLOW_NO_TESTS`, `STRICT_TDD`)
- **Story Dependencies**: Architect can specify story order; orchestrator respects `depends_on`
- **Retry Logic**: Dev role retries up to `DEV_RETRIES` times on failure (default 3)
- **Model Context Limits**: Stories should be granular to fit within model token limits
- **Artifact Immutability**: Past iteration snapshots are preserved; never modify them directly

## Testing Strategy

- **Unit Tests**: `tests/test_*.py` - Test individual components
- **Smoke Tests**: `tests/smoke/` - Validate provider connectivity
- **Integration Tests**: `tests/test_orchestrator_modes.py` - Full workflow validation
- **Project Tests**: `project/backend-fastapi/tests/` - Generated code tests (run by QA role)

## Common Issues

1. **Provider Not Found**: Check `claude`, `codex`, or `gcloud` CLI is on PATH
2. **Model Not Available**: Verify model name matches provider's catalog (e.g., `ollama list`)
3. **Empty Response**: Check provider logs in `artifacts/<role>/last_raw.txt`
4. **Story Status Mismatch**: Run `make fix-stories` to normalize `planning/stories.yaml`
5. **Tests Failing**: Ensure test dependencies installed: `pip install -r requirements.txt`
