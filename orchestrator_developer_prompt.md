# Orchestrator Agent – Developer Implementation Prompt

You are a **Senior Python Developer** working on the repository `agnostic-ai-pipeline`.

## High-Level Goal

Refactor and extend the existing orchestration logic so that the pipeline can be driven by a **true Orchestrator LLM agent**, instead of only by hard-coded Python control flow.

The Orchestrator agent will:

- Think at the **iteration level** (concept → BA → PO → Architect → Dev ↔ QA → snapshot).
- Decide **which role to call next**, with what payload, and when to loop or stop.
- Interact with the existing role runners (BA, PO, Architect, Dev, QA) via the already implemented abstractions (`execute_role`, A2A executors, etc.).
- Produce a structured JSON response on each step, describing:
  - The current state summary.
  - The next actions (which role/tool to call).
  - Whether the iteration should terminate.

Your task is to adjust the code so this Orchestrator LLM can sit on top of the current pipeline without breaking existing CLI flows (`make iteration`, `make loop`, `make ba`, `make dev`, etc.).

---

## Current Architecture (what you must respect)

1. **Roles & runners**
   - BA → `scripts/run_ba.py` (DSPy or legacy, writes `planning/requirements.yaml`).
   - PO → `scripts/run_product_owner.py`.
   - Architect → `scripts/run_architect.py` (writes `planning/stories.yaml` and related artifacts).
   - Dev → `scripts/run_dev.py` (implements stories in `project/` and writes dev artifacts under `artifacts/dev/`).
   - QA → `scripts/run_qa.py` (runs tests, writes QA reports under `artifacts/qa/`).

2. **Existing orchestrator script**
   - `scripts/orchestrate.py`:
     - Defines local handlers: `_local_business_analyst_handler`, `_local_product_owner_handler`, `_local_architect_handler`, `_local_developer_handler`, `_local_qa_handler`.
     - Uses `a2a.executors.get_executor(role, handler, skill_id=ROLE_SKILLS[role])` to obtain a `RoleExecutor` object for each role, with **local vs remote** execution depending on `a2a` config.
     - Exposes `async def execute_role(role: str, payload: Dict[str, Any]) -> Dict[str, Any]` that:
       - Optionally injects driver information (`drivers.registry.load_driver`).
       - Invokes the underlying role executor.
       - Is already instrumented via `@instrumented(role)` and `a2a.metrics.save_metrics`.

3. **A2A layer**
   - `a2a/executors.py` implements `LocalExecutor` and `RemoteExecutor` and decides per role whether to call:
     - A local Python handler (current default).
     - Or a remote A2A agent (via HTTP) when configured.

4. **Config & tools**
   - `config.yaml` controls providers, models, and pipeline parameters (complexity routing, DB layer thresholds, etc.).
   - `AGENTS.md` describes:
     - Where artifacts are persisted: `planning/`, `artifacts/`.
     - How to run: `make ba`, `make po`, `make plan`, `make dev STORY=S#`, `make qa QA_RUN_TESTS=1`, `make iteration`, `make loop`.
   - The Orchestrator must respect existing design: **do not break** these entry points.

---

## Target Design for the Orchestrator Agent

You are NOT designing the Orchestrator’s *prompt* here. Assume there will be a system prompt like:

> “You are the Orchestrator agent for this pipeline. You coordinate BA, PO, Architect, Developer, QA and return a JSON { state_update, next_actions, termination } describing what to do next…”

Your job is to:

1. Provide the **runtime glue** that:
   - Calls the Orchestrator LLM.
   - Interprets its JSON response.
   - Dispatches the requested actions to the existing roles using `execute_role(...)`.
   - Loops until the Orchestrator signals `termination.should_stop = true`.

2. Keep the design **config-driven** and **non-breaking**:
   - Existing flows (`make iteration`, `make loop`) must keep working as today.
   - The agentic Orchestrator should be enabled via:
     - a new CLI entry, and/or
     - a configuration flag (e.g. `pipeline.agentic_orchestrator: true`).

---

## Concrete Tasks

### 1. Introduce an Orchestrator runtime module

Create a new module under `scripts/`, for example:

- `scripts/run_orchestrator_agent.py`

Responsibilities:

- Provide a **CLI entrypoint** (Typer or argparse) that accepts:
  - `--concept` (or reads `CONCEPT` from env),
  - optional options like `--max-steps`, `--max-actions-per-step`, etc.
- Initialize environment:
  - Load `config.yaml` using existing helpers (`load_config`).
  - Prepare directories (`ensure_dirs()`).
  - If the DB layer is enabled, wrap the orchestration in a `DualWriteContext` (same pattern used elsewhere).
- Create a **LLM client for the Orchestrator** using the existing LLM abstraction:
  - Use `llm.Client` (or equivalent) with a dedicated role name, e.g. `"orchestrator"`.
  - Load its prompt template from a file like `prompts/orchestrator.md` (you can create it and leave a placeholder for the actual prompt content).
- Implement an **async orchestration loop**:
  - Maintain an internal Python `state` object that tracks:
    - `concept` (original user brief).
    - High-level information extracted from artifacts:
      - presence/absence of `planning/requirements.yaml`, `planning/stories.yaml`.
      - list of stories with IDs and status (`todo/in_progress/done/failed`).
      - QA summary if available.
      - any known risks or errors captured in recent role calls.
  - On each iteration:
    1. Build a **compact context** for the Orchestrator LLM:
       - Summaries of current state (not raw big files).
       - Recent actions and outcomes (role, payload summary, status, key fields from the result dict).
    2. Call the Orchestrator LLM and expect a JSON response like:

       ```json
       {
         "state_update": {
           "summary": "...",
           "risks": ["...", "..."]
         },
         "next_actions": [
           { "tool": "RUN_DEV_STORY", "arguments": { "story_id": "S3", "strategy": "fix_after_qa" }, "reason": "..." }
         ],
         "termination": {
           "should_stop": false,
           "reason": ""
         }
       }
       ```

    3. Apply `state_update` locally (update your Python `state`).
    4. For each `next_actions[i]`, dispatch to the correct role via the existing `execute_role` or wrappers (see below).
    5. Aggregate the results of these role calls, augment the `state` with them (e.g. list of last actions with status, errors).
    6. If `termination.should_stop` is `true`, exit the loop and write a final iteration summary artifact (e.g. `artifacts/iterations/latest_orchestrator_summary.json`).

- Make sure the loop is **bounded**:
  - Support a `max_steps` limit and a `max_actions_per_step` limit to avoid infinite loops.
  - If the limit is hit, stop gracefully and surface this in the summary.

### 2. Map Orchestrator "tools" to role executors

Define a clear mapping inside `run_orchestrator_agent.py`, reusing `execute_role` from `scripts/orchestrate.py`:

- `RUN_BA` → `await execute_role("business_analyst", payload)`
  - Required payload: `{ "concept": concept }` (plus any extra flags you deem useful).
- `RUN_PO` → `await execute_role("product_owner", payload)`
  - Usually no mandatory payload; it works on existing `requirements.yaml`.
- `RUN_ARCHITECT` → `await execute_role("architect", payload)`
  - Payload may include:
    - `"concept"` (optional, for re-planning),
    - `"architect_mode"`, `"story_id"`, `"detail_level"`, etc.
- `RUN_DEV_STORY` → `await execute_role("developer", payload)`
  - Require `"story_id"` and optionally `"retries"`.
- `RUN_QA_STORY` → `await execute_role("qa", payload)`
  - Require `"story_id"` and `"allow_no_tests"` (default True).
- `RUN_QA_FULL` → `await execute_role("qa", { "allow_no_tests": ..., "story_id": "" })`

Implementation notes:

- Wrap each call with logging via `logger` for traceability.
- Normalize statuses:
  - Ensure that each role result has a `"status"` field (`ok/error/exception/failed/tests_failed/etc.`).
  - For Dev and QA, update the in-memory `state` for the relevant story (status, last error message).

### 3. Expose a Makefile target

Add a new target to `Makefile`, for example:

```makefile
agentic-iteration:
	.venv/bin/python -m scripts.run_orchestrator_agent --concept "$${CONCEPT}"
```

Requirements:

- Reuse the same `CONCEPT="..."` environment pattern as `make iteration`.
- Do **not** change existing `iteration`/`loop` targets; this is an additive feature.

Optionally, expose a flag like `ORCHESTRATOR_MODE=agentic` and make `iteration` smart enough to choose between:
- the legacy scripted orchestrator, and
- the new agentic orchestrator.

But this must not break existing usage.

### 4. Keep DB and metrics integration consistent

- Use `a2a.metrics.save_metrics()` at the end of the Orchestrator run to flush any collected metrics.
- If there is an existing DB context pattern (e.g. `DualWriteContext` from `src.db`), reuse it so that:
  - Stories statuses updated by Dev/QA are persisted.
  - Iteration metadata is recorded as today (or better).

If in doubt, search for how existing scripts wrap their main logic in DB contexts and copy that pattern.

### 5. Guardrails & Error Handling

Implement robust error handling:

- If the Orchestrator LLM returns invalid JSON:
  - Log it.
  - Retry once or twice with a simpler prompt or a “repair” message.
  - If still invalid, abort gracefully with a clear error summary.
- If an action tool name is unknown:
  - Log a warning and skip that action.
- If a role execution returns `"status": "exception"` or `"error"`:
  - Attach that info to the Orchestrator `state` so it can decide whether to:
    - retry Dev,
    - escalate to Architect,
    - or abort the iteration.

---

## Output Expectations

By the end of your changes, we should have:

1. A new module `scripts/run_orchestrator_agent.py` (or equivalent) that:
   - Can be run as `python -m scripts.run_orchestrator_agent --concept "some concept"`.
   - Drives the BA→PO→Architect→Dev↔QA loop by talking to the Orchestrator LLM.
   - Writes at least one final JSON summary under `artifacts/iterations/` or similar, including:
     - concept,
     - list of stories and their final status,
     - any QA failures or accepted tech debt,
     - whether the iteration is considered “done”.

2. A new Make target (e.g. `agentic-iteration`) that wires this into the normal workflow.

3. No regressions:
   - `make ba`, `make po`, `make plan`, `make dev`, `make qa`, `make iteration`, `make loop` still work.
   - All existing unit tests still pass.

---

## Style & Constraints

- Follow existing **coding style**:
  - 4-space indentation, snake_case for Python, short docstrings.
  - Use the existing `logger` instead of `print`.
- Reuse helpers wherever possible:
  - `common.load_config`, `ensure_dirs`, `execute_role`, DB context utilities, etc.
- Keep the Orchestrator runtime logic clearly separated from:
  - role-specific logic,
  - low-level A2A client/server implementation.

Focus on making the Orchestrator agent a thin, robust **controller** that delegates everything to the already existing primitives.
