# Agnostic AI Pipeline

Automate an agnostic multi-agent pipeline with four coordinated roles: BA → Architect → Dev → QA.
Runs on open-source models via Ollama, with the option to use paid models only for review/QA.

## Features

- **Four-stage pipeline**: BA (Business Analyst) → Architect → Dev → QA
- Role-based prompts and settings (ba, architect, dev, qa).
- Planning artifacts: requirements.yaml, stories.yaml, epics.yaml, prd.yaml, architecture.yaml, tasks.csv.
- Business Analyst generates detailed functional requirements from concept.
- Architect creates technical architecture and development plan from requirements.
- Developer agent that writes/updates code under project/.
- QA gates with lightweight checks and optional real test execution.
- Orchestrator loop to run Dev → QA across the backlog.
- Easy model switching and quality presets.

## Prerequisites

- macOS/Linux
- Python 3.9+ (3.11+ recommended)
- Ollama running locally (ollama serve)
- Optional: external provider (e.g., OpenAI/Claude via your gateway) for QA only

Suggested local models (pull only what you need):
```
ollama pull granite:7b               # ba (business analyst)
ollama pull mistral:7b-instruct      # architect
ollama pull qwen2.5-coder:7b         # dev (code)
ollama pull qwen2.5:7b               # qa (general)
```

## Install
```
make setup                 # creates .venv and installs requirements
make show-config           # prints current config.yaml
```

## Quick Start

1) **Configure roles (models/providers)**
```
make set-role role=ba        provider=ollama model="granite:7b"
make set-role role=architect provider=ollama model="mistral:7b-instruct"
make set-role role=dev       provider=ollama model="qwen2.5-coder:7b"
make set-role role=qa        provider=ollama model="qwen2.5:7b"
```

Optional quality presets:
```
make set-quality profile=low|normal|high
```

2) **Generate requirements (Business Analyst)**

```
read -r -d '' CONCEPT <<'TXT'
Product: shopping cart MVP (web Express.js, backend FastAPI, React Native Android 9+).

Phase 1 scope (no real payments): signup/login, catalog, cart (add/remove/update),
simulated checkout, order creation, order status tracking.

Business context: e-commerce platform for retail with mobile-first approach.
TXT

make ba
```

Generates `planning/requirements.yaml` with detailed functional requirements.

3) **Generate planning (Architect)**

```
make plan
```

Uses both CONCEPT and requirements.yaml to generate technical architecture and development plan.

Artifacts are written into planning/.

3) **Normalize stories (if needed)**
```
# Cleans comments/fences and ensures acceptance is a YAML list
./.venv/bin/python scripts/fix_stories.py

# (Optional) Reopen blocked/failed stories to "todo"
./.venv/bin/python scripts/reopen_stories.py
# Or selective:
# ./.venv/bin/python scripts/reopen_stories.py --only blocked fail failed
```

4) **Implement (Dev)**
```
make dev                     # picks the first 'todo' story
# or target a specific one
STORY=S3 DEV_RETRIES=4 make dev
```

Generated/updated code goes under project/. Dev logs land in artifacts/dev/....

5) **QA gates**
```
make qa                      # static checks / structure
QA_RUN_TESTS=1 make qa       # run real tests if suites exist in project/
```

QA reports go to artifacts/qa/last_report.json.

6) **Full loop (Dev → QA across backlog)**
```
# Permissive loop for bootstrap (no tests yet)
ALLOW_NO_TESTS=1 MAX_LOOPS=5 DEV_RETRIES=4 make loop

# Strict loop (requires tests to pass)
QA_RUN_TESTS=1 MAX_LOOPS=5 DEV_RETRIES=4 make loop
```

## Commands
```
make setup                # install deps into .venv
make ba                   # run Business Analyst with $CONCEPT → requirements.yaml
make plan                 # run Architect with $CONCEPT + requirements.yaml → planning/
make dev                  # run Dev on first 'todo' (or STORY=Sx)
make qa                   # run QA (QA_RUN_TESTS=1 to run real tests)
make loop                 # orchestrate Dev→QA for N iterations (MAX_LOOPS=N)
make show-config          # print config.yaml
make set-role role=<ba|architect|dev|qa> provider=<ollama|openai> model="<id>"
make set-quality profile=<low|normal|high>
```

## Advanced Features

### Architect Intervention
When stories are in review status, the Architect can intervene to adjust acceptance criteria for better developer implementation:

```bash
# Enable architect intervention in loops
ARCHITECT_INTERVENTION=1 make loop

# Disable architect intervention (default behavior)
ARCHITECT_INTERVENTION=0 make loop
```

The Architect will:
- Review stories in "in_review" status
- Adjust acceptance criteria for clarity
- Provide more specific technical requirements
- Analyze QA failure details to provide targeted corrections
- Escalate detail level with each rejection attempt

### Quality Assurance Intelligence
QA provides detailed failure analysis to improve iteration:

- **Advanced Failure Analysis**: Extracts specific test failures, assertion errors, and exception details
- **Pytest & Jest Intelligence**: Captures failed test info, error contexts, and error types
- **Architect Context**: QA details are passed to architect for targeted criterion adjustments
- **Smart Severity Classification**: Critical errors, test-only failures, and persistent issues
- **Progressive Escalation**: More detail required with each rejection iteration

### Resource Management
Automatic cleanup prevents accumulation and maintains performance:

- **Artifact Cleanup**: Removes old dev/qa logs, .pyc files, and __pycache__ directories
- **Configurable Retention**: Controlled via ARTIFACT_RETENTION_DAYS (default: 7 days)
- **Smart Recovery**: Automatic YAML repair, backup creation, and fallback handling
- **Proactive Maintenance**: Pre-iteration cleanup prevents performance degradation

### Advanced State Management
Multiple intermediate states provide granular control:

- **qa_pass_no_tests**: QA approved without tests (tests marked as pending)
- **quality_gate_waiting**: Waiting for test validation
- **in_review_critical**: Urgent critical error review
- **code_done_tests_pending**: Code functional, tests separated
- **in_review_retry**: Standard retry mechanism
- **done_force_architect**: Force-approved by architect (high priority)
- **blocked_quality_issues**: Permanently blocked (quality issues)

Environment variables:

- CONCEPT — Architect prompt (use heredoc).
- STORY — Story id (e.g., S1).
- DEV_RETRIES — Dev retries for valid FILES JSON (default 3).
- MAX_LOOPS — Iterations for make loop.
- ALLOW_NO_TESTS — 1 allows QA to pass without tests; 0 blocks.
- QA_RUN_TESTS — 1 runs real tests; 0 only static gates.

### Optional: Paid model for QA only

You can keep Architect/Dev on Ollama and switch QA to a paid provider (via your gateway):
```
make set-role role=qa provider=openai model="gpt-4o-mini"
MAX_LOOPS=5 make loop
```

## Repository Layout
```
project/              # Dev-generated code (web/backend/mobile)
planning/
  requirements.yaml   # BA-generated functional requirements
  stories.yaml        # User stories from architect
  epics.yaml          # Epic definitions
  prd.yaml           # Product requirements document
  architecture.yaml   # Technical architecture
  tasks.csv          # Development tasks
artifacts/
  dev/...             # Dev logs
  qa/last_report.json # QA result
scripts/
  run_ba.py           # Business Analyst runner
  run_architect.py    # Architect runner
  run_dev.py          # Dev runner
  run_qa.py           # QA runner
  orchestrate.py      # Dev→QA loop
  fix_stories.py      # Normalize stories.yaml
  reopen_stories.py   # Reopen stories to 'todo'
config.yaml           # roles, providers, quality, QA gates
requirements.txt
Makefile
```

## Troubleshooting

### stories.yaml empty/invalid
Run ./.venv/bin/python scripts/fix_stories.py.
Ensure top-level YAML list and acceptance is a list:

```yaml
- id: S1
  epic: E1
  description: ...
  acceptance:
    - criterion 1
    - criterion 2
  priority: P1
  status: todo
```

No comments #, no markdown fences.

### Dev didn’t write files
Increase DEV_RETRIES. Check artifacts/dev/ for errors like "missing FILES JSON block".

### QA blocks due to missing tests
For bootstrap, run with ALLOW_NO_TESTS=1.
For strict QA, set QA_RUN_TESTS=1 and add proper test suites + deps in project/.

### Ollama 404 (chat endpoint)
The client auto-fallbacks to /api/generate. Verify model is present:

```
curl -s http://localhost:11434/api/tags | jq .
```

Pull missing models (see Prerequisites).

### No 'todo' stories
Use ./.venv/bin/python scripts/reopen_stories.py to reopen blocked/failed.

## Handy Snippets

Run Dev across all todo stories:

```python
./.venv/bin/python - <<'PY'
import yaml, os, subprocess, pathlib
p=pathlib.Path("planning/stories.yaml")
data=yaml.safe_load(p.read_text(encoding="utf-8"))
if isinstance(data, dict) and "stories" in data: data=data["stories"]
for s in data:
    if s.get("status")=="todo":
        env=os.environ.copy()
        env["STORY"]=s["id"]
        env["DEV_RETRIES"]=env.get("DEV_RETRIES","3")
        print("==> Dev on", s["id"])
        subprocess.run(["make","dev"], env=env)
PY
```

Permissive loop (bootstrap without tests):
```
ALLOW_NO_TESTS=1 MAX_LOOPS=10 DEV_RETRIES=4 make loop
```

Switch models quickly:
```
make set-role role=ba        provider=ollama model="granite:7b"
make set-role role=architect provider=ollama model="mistral:7b-instruct"
make set-role role=dev       provider=ollama model="qwen2.5-coder:7b"
make set-role role=qa        provider=ollama model="qwen2.5:7b"
make set-quality profile=high
```

## License
