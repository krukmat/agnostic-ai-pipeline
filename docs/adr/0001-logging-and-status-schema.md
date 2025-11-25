# ADR 0001 — Logging Standard and QA/Dev Status Schema

- Status: Accepted
- Date: 2025-11-24
- Context: QA needed a single, reliable summary of execution and consistent logging across Dev/QA. Prior behavior mixed ad‑hoc messages and special RCs (e.g., 10 for “no tests”).

## Decision

1) Standardize log prefixes
- Format: `[ROLE][area] RUN|SKIP|ERROR|DONE: message`
- Examples:
  - `[DEV][backend] RUN: .venv/bin/pytest -q …`
  - `[DEV][web] DONE (see artifacts/…)`
  - `[QA][web] SKIP: package.json missing in web-express`

2) Adopt a shared status schema for summaries
- Fields per area: `area, executed, rc, status, reason, tools_present, logs[]`
- Status enum: `run_pass, run_fail, skip_no_tests, skip_tool_missing, skip_not_configured, error_collection, error_other`
- RC mapping:
  - `0` success (including skips)
  - `1` generic failure
  - `4` collection error (schema/collection)
  - `127` tool missing (binary not found)

3) Summaries and relative paths
- Dev writes: `artifacts/dev/<story>/run-<ts>/dev_summary.json`
- QA  writes: `artifacts/qa/<story>/qa_summary.json`
- All `logs[]` entries are relative to the repo root (portable between machines/CI).

4) Strict mode behavior
- Skips are treated as success (rc=0). Only real failures (rc>0) or collection errors produce a failing status.
- Removes legacy reliance on rc=10 as “no tests”.

5) Tooling
- Make target `qa-summary` prints the latest (or STORY‑scoped) summary using `jq` or `python -m json.tool` fallback.

## Consequences
- Pros
  - QA validation reduces a multi‑log hunt to a single json file.
  - Logs become greppable and consistent across roles/areas.
  - Relative paths enable artifact portability and simpler diffs.
- Cons
  - Any third‑party tooling expecting rc=10 for “no tests” must be updated.

## Notes
- This ADR consolidates the outcomes from S4.1–S4.5 (Smoke Reliability) and sets a baseline for future refactors (Phase 7).
- Summaries are additive; they do not replace detailed logs.
