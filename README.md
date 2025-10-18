Agnostic AI Pipeline — Usage Guide (EN)

Automate an agnostic pipeline with three coordinated roles: Architect → Dev → QA.
Runs on open-source models via Ollama, and lets you optionally use paid models (e.g., only for review/QA).

Quick Start (copy/paste)
# 1) Setup
make setup

# 2) Make sure Ollama is running and you have these models
# (pull only what you need / what your machine can handle)
ollama pull mistral:7b-instruct
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5:7b

# 3) Set roles (models/providers)
make set-role role=architect provider=ollama model="mistral:7b-instruct"
make set-role role=dev       provider=ollama model="qwen2.5-coder:7b"
make set-role role=qa        provider=ollama model="qwen2.5:7b"

# 4) Optional: set quality preset (low|normal|high)
make set-quality profile=high

# 5) Generate planning with a solid concept (use heredoc to avoid quoting issues)
read -r -d '' CONCEPT <<'TXT'
Product: shopping cart MVP (web Express.js, backend FastAPI, React Native Android 9+).

Phase 1 scope (no real payments): signup/login, catalog, cart (add/remove/update),
simulated checkout, order creation, order status tracking.

Output requirements (strict):
1) stories.yaml → flat YAML list (top-level sequence). Each item: id (S1..S12),
   epic (E1..E5), description, acceptance (list), priority (P1..P3), status: "todo".
   Distribute across web/backend/mobile; atomic, prioritized stories.

2) epics.yaml → 3–5 epics (id, name, goal).

3) prd.yaml → goals, personas, scope, constraints, KPIs, assumptions.

4) architecture.yaml → modules, entities, endpoints (method/path/req/res), ADRs,
   and web–backend–mobile interactions. YAML only, no comments or fences.

5) tasks.csv → columns: epic,story,priority,title,detail.

Rules:
- No comments (#) and no fences (```).
- Spanish output is fine or English—your choice, but be consistent.
- Consistent IDs across files.
TXT

make plan

# 6) Normalize stories (removes comments/fences; fixes acceptance as list)
./.venv/bin/python scripts/fix_stories.py

# (Optional) Reopen blocked/failed stories to "todo"
./.venv/bin/python scripts/reopen_stories.py

# 7) Implement first 'todo' story (or pick a specific one via STORY=Sx)
make dev
# STORY=S3 DEV_RETRIES=4 make dev

# 8) Run QA gates (static checks by default; real tests if configured)
make qa
# QA_RUN_TESTS=1 make qa    # run real tests if you have suites

# 9) Full loop: Architect plan already done → Dev → QA (N iterations)
ALLOW_NO_TESTS=1 MAX_LOOPS=5 DEV_RETRIES=4 make loop

1) Requirements

macOS / Linux with:

Python 3.9+ (3.11+ recommended)

curl and jq (optional but handy)

Ollama
 running (ollama serve)

Suggested local models:

Architect: mistral:7b-instruct or qwen2.5:7b

Dev (code): qwen2.5-coder:7b (or 14b if your machine can handle it)

QA: qwen2.5:7b

(Optional) External provider (OpenAI/Claude via your gateway) just for QA.

2) Install
# Create venv and install deps
make setup

# Show current configuration
make show-config

# Check Ollama models
curl -s http://localhost:11434/api/tags | jq .
# If missing:
# ollama pull qwen2.5-coder:7b

3) Core Flow
3.1 Planning (Architect)

Use a heredoc to avoid shell quoting problems:

read -r -d '' CONCEPT <<'TXT'
[Put your concept + output rules here, same as in Quick Start.]
TXT

make plan


Artifacts go to planning/: stories.yaml, epics.yaml, prd.yaml, architecture.yaml, tasks.csv.

3.2 Normalize Stories (if LLM was “creative”)
# Cleans comments/fences and ensures acceptance is a YAML list
./.venv/bin/python scripts/fix_stories.py

# (Optional) Re-open blocked stories to "todo"
./.venv/bin/python scripts/reopen_stories.py
# Or selective:
# ./.venv/bin/python scripts/reopen_stories.py --only blocked fail failed

3.3 Development (Dev)
# Picks the first story with status "todo"
make dev

# Or target a specific one
STORY=S5 DEV_RETRIES=4 make dev


The Dev writes/updates files under project/ and logs to artifacts/dev/....

3.4 QA (Gates)
# Lightweight QA (static validations/structure)
make qa

# QA with real tests (if you have suites and deps in project/)
QA_RUN_TESTS=1 make qa


Reports in artifacts/qa/last_report.json.

3.5 Full Orchestration
# Iterates: take a 'todo' story → Dev → QA → update story status
MAX_LOOPS=5 make loop


For bootstrap without tests, allow progression:
ALLOW_NO_TESTS=1 MAX_LOOPS=5 make loop

4) Available Commands
make setup         # install deps into .venv
make plan          # run Architect with $CONCEPT → planning/
make dev           # run Dev on first 'todo' (or STORY=Sx)
make qa            # run QA (QA_RUN_TESTS=1 to run real tests)
make loop          # orchestrate Dev→QA for N iterations (MAX_LOOPS=N)
make show-config   # print config.yaml
make set-role role=<architect|dev|qa> provider=<ollama|openai> model="<id>"
make set-quality profile=<low|normal|high>   # global quality presets

5) Models & Quality
Change model per role
# Architect with Mistral
make set-role role=architect provider=ollama model="mistral:7b-instruct"

# Dev with Qwen coder
make set-role role=dev       provider=ollama model="qwen2.5-coder:7b"

# QA with Qwen general (or your paid provider if you have a gateway)
make set-role role=qa        provider=ollama model="qwen2.5:7b"
# External example:
# make set-role role=qa provider=openai model="gpt-4o-mini"

Quality presets
make set-quality profile=low
make set-quality profile=normal
make set-quality profile=high


Presets adjust temperature, top_p, and max_tokens for the roles in config.yaml.

6) Environment Variables

CONCEPT — Architect’s planning prompt.

STORY — Story to implement (e.g., S1).

DEV_RETRIES — Dev retries if LLM doesn’t return a valid FILES JSON block (e.g., DEV_RETRIES=4).

MAX_LOOPS — Orchestrator iterations in make loop.

ALLOW_NO_TESTS — 1: QA won’t block if no tests; 0: strict.

QA_RUN_TESTS — 1: run real tests; 0: static/structural QA.

7) Use Cases
A) Fast bootstrap (no tests yet)
make plan
./.venv/bin/python scripts/fix_stories.py
./.venv/bin/python scripts/reopen_stories.py
ALLOW_NO_TESTS=1 MAX_LOOPS=10 DEV_RETRIES=4 make loop

B) Strict QA with tests

Prepare test suites in project/ (e.g., pytest/Jest + deps).

Run:

QA_RUN_TESTS=1 MAX_LOOPS=5 make loop

C) Backlog “stalled”
# Reopen blocked/failed
./.venv/bin/python scripts/reopen_stories.py --only blocked fail failed

# Increase iterations and retries
MAX_LOOPS=20 DEV_RETRIES=5 make loop

D) “Premium” QA (paid provider only for QA)
make set-role role=qa provider=openai model="gpt-4o-mini"
MAX_LOOPS=5 make loop

8) Repository Layout
project/            # Dev-generated code (web/backend/mobile)
planning/
  stories.yaml      # stories (top-level YAML list)
  epics.yaml
  prd.yaml
  architecture.yaml
  tasks.csv
artifacts/
  dev/...           # Dev logs
  qa/...            # QA reports (last_report.json, etc.)
scripts/
  run_architect.py  # runs Architect
  run_dev.py        # runs Dev
  run_qa.py         # runs QA
  orchestrate.py    # loops Dev→QA per story
  fix_stories.py    # normalizes stories.yaml
  reopen_stories.py # reopens stories (status: todo)
config.yaml         # roles, providers, quality, QA gates

9) Troubleshooting

stories.yaml empty/invalid
Run ./.venv/bin/python scripts/fix_stories.py.
Ensure top-level YAML list and acceptance is a list:

acceptance:
  - criterion 1
  - criterion 2


No comments #, no fences.

Dev didn’t write files
Increase DEV_RETRIES. Check artifacts/dev/ for “missing FILES JSON block” or bad paths.

QA blocks due to missing tests
In bootstrap use ALLOW_NO_TESTS=1.
For real QA, set QA_RUN_TESTS=1 and add suites + deps.

Ollama 404 on /api/chat
The client auto-fallbacks to /api/generate. Make sure model exists:

curl -s http://localhost:11434/api/tags | jq .


Pull if missing: ollama pull qwen2.5-coder:7b (or whichever you set).

No more todo stories
They might be blocked/failed.
./.venv/bin/python scripts/reopen_stories.py

10) Handy Snippets
Solid planning prompt (copy/paste)
read -r -d '' CONCEPT <<'TXT'
Product: shopping cart MVP (web Express.js, backend FastAPI, React Native Android 9+).

Phase 1 scope (no real payments): signup/login, catalog, cart (add/remove/update),
simulated checkout, order creation, order status tracking.

Output requirements (strict):
1) stories.yaml → flat YAML list (top-level). Each item: id (S1..S12), epic (E1..E5),
   description, acceptance (list), priority (P1..P3), status: "todo".
   Distribute across web/backend/mobile; atomic and prioritized stories.

2) epics.yaml → 3–5 epics (id, name, goal).

3) prd.yaml → goals, personas, scope, constraints, KPIs, assumptions.

4) architecture.yaml → modules, entities, endpoints (method/path/req/res), ADRs,
   and web–backend–mobile interactions. YAML only, no comments/fences.

5) tasks.csv → columns: epic,story,priority,title,detail.

Rules:
- No comments (#) and no fences (```).
- Consistent IDs.
TXT

make plan
./.venv/bin/python scripts/fix_stories.py

Dev across all todo stories
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

Permissive loop (no tests yet)
ALLOW_NO_TESTS=1 MAX_LOOPS=10 DEV_RETRIES=4 make loop

Switch models & quality
make set-role role=architect provider=ollama model="mistral:7b-instruct"
make set-role role=dev       provider=ollama model="qwen2.5-coder:7b"
make set-role role=qa        provider=ollama model="qwen2.5:7b"

make set-quality profile=high
