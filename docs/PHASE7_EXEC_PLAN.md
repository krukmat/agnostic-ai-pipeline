# Phase 7 — Architecture & Code Quality (Execution Plan)

Status: In progress
Scope: Raise architecture and code quality (SRP/SoC/SOLID, KISS/YAGNI, testability, DRY, defensive/security) for the code touched in this branch (drivers, Dev/QA, CLI).

## Tasks (7.x)

- 7.1 — Principles + ADRs
  - Deliver: ARCHITECTURE_PRINCIPLES.md, ADR-0001 (logging + status schema)
  - Status: Completed

- 7.2 — Drivers SRP/SoC (split)
  - Deliver: drivers/validator.py, drivers/loader.py, drivers/cli.py, drivers/registry.py (wrapper + reexports)
  - Status: Completed
  - Notes: CLI/backward-compat preserved; `python -m drivers.registry` works; load_driver/VALID_CATEGORIES reexported

- 7.3 — Runner util + integration
  - Deliver: scripts/utils/runner.py; adapt run_dev.py/run_qa.py
  - Status: Completed
  - Tests: tests/utils/test_runner.py (5 passed)

- 7.4 — Shell/Env hardening
  - Deliver: validator blocks chaining/redirections; runner prefers argv (shell=False) with fallback
  - Status: Completed
  - Notes: build/test/lint validated; unsafe operators (&&, ||, ;, |, >, <) rejected; single-line only

- 7.5 — DRY cleanup (dead code removal)
  - Deliver: remove legacy rc==10 paths and unused branches/comments
  - Status: Planned

- 7.6 — Lint/Typing (new modules)
  - Deliver: basic ruff/mypy for new files (optional warnings allowed)
  - Status: Planned

- 7.7 — Minimal unit tests (drivers)
  - Deliver: validator/loader unit tests (IDs/commands/log paths)
  - Status: Planned

## Tracking (live)

| ID  | Task                                 | Status     | Notes |
|-----|--------------------------------------|------------|-------|
| 7.1 | Principles + ADR-0001                | Completed  | Docs added (principles + logging/status schema) |
| 7.2 | Drivers split (validator/loader/cli) | Completed  | CLI + compat verified; reexports in registry |
| 7.3 | Runner util + integration            | Completed  | Dev/QA use run_driver_cmd; tests added |
| 7.4 | Shell/env hardening                  | Completed  | Validator blocks chaining; runner uses argv |
| 7.5 | DRY cleanup                          | Completed  | Removed rc==10 branches; simplified QA strict mode and normalization |
| 7.6 | Lint/Typing                           | Completed  | make lint-new (ruff) / typecheck-new (mypy) with safe fallbacks |
| 7.7 | Drivers unit tests                    | Completed  | validator/loader tests added (7 passed incl. CLI) |

## References
- docs/ARCHITECTURE_PRINCIPLES.md — Principles, checklist, and 7.4 implementation notes
- docs/adr/0001-logging-and-status-schema.md — ADR for logging/status schema
