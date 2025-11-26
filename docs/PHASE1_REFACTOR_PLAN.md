# Phase 1 — General Refactor Plan

**Status**: ✅ COMPLETED (2025-11-26)
**Completion**: 6/7 tasks (86%) - Task 1.7 (CI) skipped as optional
**Branch**: `refactor-roles` (6 commits ahead of main)
**Coverage**: 82% → 99% (305 statements, 2 missing)
**Tests**: 33 → 101 tests (+68 tests added)

Scope: Refactor architecture and code quality in touched modules (drivers, Dev/QA, CLI), applying SRP/SoC, DIP, DRY, Clean Code, Defensive/Security, KISS/YAGNI, and testability.

## 0) Executive Summary

- **Issues** (high level)
  - Monolithic flows in `scripts/run_dev.py` (711 lines) and `scripts/run_qa.py` (704 lines) — hard to test/extend
  - Drivers CLI couples argparse + logic; no dependency injection for toolchain detection
  - Validator lacks category whitelist (missing mobile) and cross-platform script checks
  - Duplication of patterns (log names/prefixes, execution) across Dev/QA
  - Coverage uneven: core avg 86.67% (loader 95%, runner 91%, validator 74%); overall 50% including wrappers
- **Goal**
  - Isolate responsibilities (SRP/SoC), improve unit-testability (DIP), reduce duplication (DRY)
  - Harden shell/env security (whitelist + no chaining), stabilize contracts (logs/RC/summaries)
  - Target: core ≥90%, overall ≥60% coverage
- **Scope**: Refactor drivers/*, run_dev.py, run_qa.py, orchestrate.py while preserving P2.1/P2.2 functionality

## 1) Principles, Scope, Non‑Goals

- **Principles**: SRP/SoC, DIP/testability, DRY/Clean, Defensive/Security, KISS/YAGNI.
- **Scope** (Phase 1 - primary refactor targets):
  - `drivers/*` (cli.py, validator.py, loader.py, detect.py, registry.py)
  - `scripts/run_dev.py` (711 lines - monolithic)
  - `scripts/run_qa.py` (704 lines - monolithic)
  - `scripts/utils/*` (runner.py - extend with naming helpers)
  - `scripts/orchestrate.py` (driver payload attachment)
  - `scripts/drivers_scaffold.py`, `scripts/drivers_show.py` (utilities)
  - `tests/*` (driver_layer/, utils/)
- **Deferred to Phase 2** (out of scope for this PR):
  - `scripts/run_architect.py` (926 lines - **largest role**, needs refactor)
  - `scripts/run_product_owner.py` (371 lines)
  - `scripts/run_ba.py` (112 lines)
  - `scripts/run_orchestrator.py` (34 lines)
  - Rationale: Focus on driver layer + Dev/QA integration first; apply lessons learned to other roles
- **Non‑Goals**:
  - New features or DSPy/MiPRO changes
  - 100% coverage for wrappers (registry/detect/CLI) - these stay at ~0%
  - Rewriting existing template/scaffolding logic (preserve P2.1/P2.2 functionality)

## 2) Findings (with refs)

- `scripts/run_dev.py`
  - Monolithic: config, scaffold, embedded detection, LLM, parsing, writing, runner, summary (≈ L560).
  - DIP missing: idf/west detection is coupled (≈ L435–L456).
- `scripts/run_qa.py`
  - Mixes execution + reporting (≈ L360–L680); `analyze_test_failures` lacks a clear contract.
- `drivers/cli.py`
  - Argparse + plan logic coupled; toolchain detection imported at module scope (hard to mock/inject).
- `drivers/validator.py`
  - No category whitelist; no (+x) checks for referenced scripts.
- Dev/QA duplication
  - Log prefixes/name composition and driver command prep repeated (runner utility helps, but more DRY is possible).

## 2.1) Current State Baseline (context from completed phases)

This refactor builds on completed driver layer work (Phase 0-3 per DRIVER_LAYER_EXEC_PLAN.md):

**Completed Infrastructure:**
- ✅ **P2.1** (run_dev.py:384-547): Driver template expansion + build/test execution
- ✅ **P2.2** (run_qa.py:392-503): Driver test runner integration
- ✅ **P3.1-P3.4**: Embedded drivers (ESP32-C3, Zephyr) with toolchain detection

**File Sizes (refactor scope):**
- `scripts/run_dev.py`: 711 lines
- `scripts/run_qa.py`: 704 lines
- `drivers/cli.py`: 149 lines
- `drivers/validator.py`: 95 lines
- `scripts/utils/runner.py`: 72 lines

**Additional Files in Scope (not listed in original plan):**
- `scripts/orchestrate.py`: +38 lines (driver attachment to role payloads)
- `scripts/drivers_scaffold.py`: 61 lines (scaffolding utility)
- `scripts/drivers_show.py`: 60 lines (driver display utility)

**Known Integration Points:**
- Dev/QA roles use `load_driver()` from `drivers.registry`
- Orchestrator resolves drivers from `config.yaml` when `drivers.enabled: true`
- Runner utility (`scripts/utils/runner.py`) already provides `run_driver_cmd()`, `prepare_env_for_area()`, `area_from_name()`

## 2.2) Known Bugs to Preserve Fixes (critical for refactor)

**IMPORTANT**: These bugs were fixed in previous phases. Refactoring MUST preserve fixes:

- **BUG-004** (DRIVER_LAYER_PLAN.md): Registry CLI now validates all drivers with `make drivers-validate`
- **BUG-005** (DRIVER_LAYER_PLAN.md): ESP32-C3 YAML migrated from `flash: {command}` to `flash_command`/`monitor_command`
- **BUG-006** (DRIVER_LAYER_PLAN.md): Zephyr YAML corrected template paths and commands
- **BUG-007** (DRIVER_LAYER_EXEC_PLAN.md): Silent except/pass blocks removed from driver execution paths
- **BUG-7.2-001** (ARCHITECTURE_PRINCIPLES.md): `drivers/registry.py` now reexports `load_driver` and `VALID_CATEGORIES`

**Validation**: After refactor, run:
```bash
make drivers-validate              # Must pass all driver YAMLs
python -c "from drivers.registry import load_driver, VALID_CATEGORIES; print('OK')"  # Must not error
PYTHONPATH=. .venv/bin/pytest tests/driver_layer/ tests/utils/  # All 12 tests must pass
```

## 3) Work Plan (Phase 1.x)

### 3.A — Execution Checklist (automatic vs. judgment)

| Task  | Area | Nature | What to do | Gate (pass criteria) |
|------|------|--------|------------|-----------------------|
| 1.1  | CLI  | Mostly automatic | Extract pure fns (list/show/plan), inject detectors, add unit tests | `python -m drivers.registry {list,show,plan}` unchanged; CLI tests pass |
| 1.2  | Validator | Mostly automatic | Add category whitelist and `+x` check for scripts; unit tests | `make drivers-validate` fails clearly on violations; no false positives |
| 1.3  | Dev | Needs judgment | Split helpers (config/targets, scaffold, detect, summary); keep runner util | `make dev-smoke` OK; dev_summary.json structure/stability verified |
| 1.4  | QA  | Needs judgment | Separate execution from reporting; define `build_qa_summary` contract | `make qa-smoke` OK; `make qa-summary` rc/status/logs stable |
| 1.5  | DRY | Mostly automatic | Add naming/rc helpers; replace duplicates in Dev/QA | Grep shows consistent `<area>_<id>_<cmd>.log`; summaries list the same |
| 1.6  | Tests | Mostly automatic | Add negative tests (validator/runner/loader) to reach targets | Core ≥90% (validator/loader/runner), Overall ≥60% |
| 1.7  | CI   | Judgment (optional) | Add workflow: validate → tests → qa-smoke (tolerant) | Green job with logs and optional artifacts |

### 3.B — Progress Tracking (Phase 1)

| Task | Status | Details | Date | Branch |
|------|--------|---------|------|--------|
| **1.1** | ✅ COMPLETED | Extract pure functions (list_drivers, show_driver, plan_from_config); inject DetectorMap; 21 new tests (76% coverage). CLI output unchanged. | 2025-11-25 | refactor-roles (d38f405) |
| **1.2** | ✅ COMPLETED | Add category-based allowlist + cross-platform script checks to validator; 5 new negative tests; all 5 drivers pass validation (gpu/cuda_jetson, embedded/esp32c3_riscv, embedded/zephyr_c, backend/fastapi, frontend/next_js). Coverage 80%. | 2025-11-25 | refactor-roles |
| **1.3** | ✅ COMPLETED | Refactor run_dev.py: extract _load_config(), _resolve_targets(), _scaffold_templates(), _embedded_detection(), _write_dev_summary() helpers; 15 new unit tests with mocked deps; implement_story() now cleaner and testable. Total 48/48 driver_layer tests passing. | 2025-11-25 | refactor-roles |
| **1.4** | ✅ COMPLETED | Refactor run_qa.py: extract _load_qa_config(), _build_qa_summary() helpers for SRP + testability; 13 new unit tests with mocked config/filesystem; main() delegates reporting to pure helper. Total 56/56 driver_layer tests passing (was 48, added 8). | 2025-11-26 | refactor-roles |
| **1.5** | ✅ COMPLETED | DRY runner.py: add driver_log_name(), normalize_rc(), area_from_name() helpers; updated run_dev.py + run_qa.py to use standardized log naming (backend|web|embedded_<id>_<cmd>.log) and RC normalization. 6 new runner tests + adoption in Dev/QA. Total 62/62 tests passing (56 driver_layer + 6 utils/runner). | 2025-11-26 | refactor-roles |
| **1.6** | ✅ COMPLETED | Core tests: achieved 99% coverage (305 stmts, 2 missing). Added 15 validator negative tests, 10 CLI main() tests, 10 detect.py tests, 4 runner.py edge case tests. Total 101/101 tests passing (87 driver_layer + 10 utils + 4 new). validator.py 100%, detect.py 100%, runner.py 100%, cli.py 99%, loader.py 98%. | 2025-11-26 | refactor-roles |
| **1.7** | ⏳ PENDING | Minimal CI: GitHub Actions workflow (optional) | - | - |

---

### 1.1 — Decouple drivers CLI (DIP + testability)
- Changes
  - Extract pure functions: `list_drivers()`, `show_driver(id)`, `plan_from_config(cfg, detectors)`
  - **Inject detectors as protocol** (extensible for future toolchains):
    ```python
    DetectorMap = Dict[str, Callable[[], Tuple[bool, str]]]
    # Example: {"idf": has_idf, "west": has_west, "nvcc": has_nvcc, ...}
    ```
  - Default detectors imported from `drivers.detect` only in `main()`, not at module scope
- Deliverables
  - `drivers/cli.py`: thin argparse layer calling pure functions
  - Unit tests: `tests/driver_layer/test_cli_plan.py` with mocked detectors (no real binaries)
- Acceptance
  - `python -m drivers.registry {list|show|plan}` keeps current output
  - CLI unit tests pass without relying on idf.py/west/nvcc on PATH
  - Easy to extend with new detectors (e.g., `has_flutter`, `has_gradle`) without modifying signatures

### 1.2 — Validator: category whitelist + script checks
- Changes
  - **Whitelist by category** (extend existing `_validate_command_string()` in validator.py:76-95):
    - backend: `^(.venv/bin/pytest|ruff|uvicorn|python|pip)`
    - frontend: `^(npm|node|yarn|pnpm|next)`
    - mobile: `^(react-native|flutter|expo|gradle|xcodebuild)`
    - embedded: `^(idf.py|west|esptool|twister|drivers/.+/scripts/.+\.(sh|bat))`
    - gpu: `^(make|nvcc|nvidia-smi|hipcc|rocminfo)`
  - **Cross-platform script validation**:
    - If command references `drivers/.../scripts/*.(sh|bat)`, verify file existence
    - On Unix: check executable flag (+x) if available
    - On Windows: accept .bat/.cmd without +x check
  - **Build on existing**: validator.py already blocks `&&`, `||`, `;`, `|`, `>`, `<` - preserve this
- Deliverables
  - `drivers/validator.py`: add `_validate_allowed_command(cmd, category)` called from `validate_driver_dict()`
  - Tests: positive/negative per category in `tests/driver_layer/test_validator.py`
- Acceptance
  - `make drivers-validate` fails with clear messages on whitelist violations or missing scripts
  - Cross-platform: tests pass on macOS/Linux/Windows (WSL acceptable)

### 1.3 — Refactor `run_dev.py` (SRP/SoC + testability)
- Changes
  - Extract helpers:
    - `_load_config()` + `_resolve_targets()` (I/O minimal; return typed dicts)
    - `_scaffold_templates(drv)` (idempotent, uses logger)
    - `_embedded_detection(detectors)` (injectable)
    - `_write_dev_summary(drivers_info)` (pure)
  - Delegate all execution to runner util (`scripts/utils/runner.py`).
- Deliverables
  - Smaller `scripts/run_dev.py` with helpers in the same file (no extra modules unless needed).
  - Minimal unit tests with runner/detector mocks (no LLM).
- Acceptance
  - `make dev-smoke` unchanged; `dev_summary.json` valid; log prefixes consistent.

### 1.4 — Refactor `run_qa.py` (execution vs reporting)
- Changes
  - Extract `build_qa_summary(areas, failure_details, flags)` (pure) and `run_driver_area(area, drv)` (uses runner).
  - Document `analyze_test_failures()` contract; simplify if possible.
- Deliverables
  - Smaller `scripts/run_qa.py` with typed helpers; runner as single exec path.
  - Minimal unit tests (synthesize `areas` → expected `qa_summary.json`).
- Acceptance
  - `make qa-smoke` / `make qa-summary` OK; strict mode intact; clean logs.

### 1.5 — DRY: common helpers for log names and areas
- Changes
  - **Extend existing** `scripts/utils/runner.py` (already has `area_from_name()` at line 14):
    - Add `driver_log_name(area: str, driver_id: str, cmd: str) -> str` → `{area}_{driver_id}_{cmd}.log`
    - Add `normalize_rc(rc: int, tool_missing: bool) -> int` → skip=0, missing=127
  - **Consolidate** log prefix patterns from Dev/QA into runner module
  - Replace remaining duplication in Dev/QA summary generation
- Deliverables
  - Extended `scripts/utils/runner.py` with DRY helpers
  - Dev/QA import and use new helpers (no new module created)
  - Tests: `tests/utils/test_runner.py` expanded with naming/rc tests
- Acceptance
  - Consistent log names across Dev/QA and summaries
  - Single source of truth for area/log/RC conventions

### 1.6 — Core tests (target ≥90% in validator/runner/loader) ✅ COMPLETED
- **Initial Coverage** (before Task 1.6):
  - `drivers/validator.py`: 74% (15 lines missing)
  - `drivers/cli.py`: 76% (main() entry point + error path)
  - `drivers/detect.py`: 89% (exception handling in _probe)
  - `scripts/utils/runner.py`: 89% (edge cases in run_driver_cmd)
  - Overall: 82% (248 stmts, 44 missing)
- **Changes Implemented**:
  - **validator.py** (15 new negative tests in `test_validator_loader.py`):
    - Missing required keys (id, category, language, framework)
    - Invalid types for all fields
    - Invalid category values
    - Templates validation (not a list, missing path/source)
    - Command validation (not a dict, empty command, newlines, invalid tokens)
    - artifact_paths not a list
    - Embedded fields: board/flash_command/monitor_command not string
    - GPU fields: gpu_arch not string or invalid format (not sm_/gfx)
    - Coverage: 74% → **100%** (0 lines missing)
  - **cli.py** (10 new tests in `test_cli_plan.py::TestCLIMainEntryPoint`):
    - main() validate --all command
    - main() validate without --all (argparse error)
    - main() load/show commands
    - main() list command
    - main() plan command (default + custom config)
    - main() plan error path (missing config file → rc=2)
    - main() no command raises SystemExit
    - main() invalid command raises SystemExit
    - Coverage: 76% → **99%** (1 line missing: unreachable return 0)
  - **detect.py** (10 new tests in `test_detect.py`):
    - _probe() command not found in PATH
    - _probe() subprocess timeout exception (lines 16-17)
    - _probe() generic exception handling
    - _probe() version from stderr fallback
    - _probe() no version output
    - has_idf() and has_west() wrappers
    - Coverage: 89% → **100%** (0 lines missing)
  - **runner.py** (4 new tests in `test_runner.py`):
    - run_driver_cmd() empty command early return (line 46)
    - run_driver_cmd() shlex.split() exception → shell=True fallback (lines 55-56, 61)
    - run_driver_cmd() empty argv → shell=True fallback (line 61)
    - normalize_rc() exception handling (lines 90-91)
    - Coverage: 89% → **100%** (0 lines missing)
- **Deliverables**:
  - `tests/driver_layer/test_validator_loader.py`: +15 tests (5 → 20 tests)
  - `tests/driver_layer/test_cli_plan.py`: +10 tests (21 → 31 tests)
  - `tests/driver_layer/test_detect.py`: NEW FILE with 10 tests
  - `tests/utils/test_runner.py`: +4 tests (6 → 10 tests)
- **Final Coverage** (after Task 1.6):
  - `drivers/validator.py`: **100%** (57 stmts, 0 missing)
  - `drivers/cli.py`: **99%** (110 stmts, 1 missing - unreachable)
  - `drivers/detect.py`: **100%** (18 stmts, 0 missing)
  - `drivers/loader.py`: **98%** (59 stmts, 1 missing - defensive)
  - `drivers/registry.py`: **100%** (4 stmts, 0 missing)
  - `scripts/utils/runner.py`: **100%** (57 stmts, 0 missing)
  - **Overall: 99%** (305 stmts, 2 missing)
  - **Test Count**: 101/101 passing (87 driver_layer + 10 utils/runner + 4 new)
- **Acceptance Criteria**:
  - ✅ Core modules exceed 90% target (all at 98-100%)
  - ✅ Overall coverage: 82% → 99% (exceeded 90% target)
  - ✅ No regressions: all previous tests still pass
  - ✅ New tests cover all error paths and edge cases

### 1.7 — Minimal CI (optional)
- Changes
  - Workflow: drivers-validate → tests (driver_layer + utils) → qa-smoke (tolerant).
- Deliverables
  - `.github/workflows/phase1.yml` (if CI is approved).
- Acceptance
  - Green job with RUN/SKIP/ERROR logs and optional artifacts.

## 4) Metrics & Acceptance Criteria

### Logging Format (standardized)
- **Pattern**: `[{ROLE}][{area}] {STATUS} {context}`
- **Statuses**: `RUN` (start), `DONE` (success), `ERROR` (failure), `SKIP` (intentional skip)
- **Example**:
  ```
  [DEV][backend] RUN build: .venv/bin/pytest tests/
  [DEV][backend] DONE build: exit 0
  [QA][embedded] SKIP test: idf.py not found (set drivers.embedded.run_test=true to enable)
  [QA][web] ERROR lint: npm run lint failed, exit 1
  ```

### Summary JSON Schema
- **dev_summary.json** / **qa_summary.json**:
  ```json
  {
    "story_id": "S1",
    "timestamp": "2025-01-15T10:30:00Z",
    "drivers": {
      "backend": {
        "id": "fastapi",
        "commands": {
          "build": {"rc": 0, "log": "artifacts/dev/S1/backend_fastapi_build.log"},
          "test": {"rc": 0, "log": "artifacts/dev/S1/backend_fastapi_test.log"}
        }
      }
    },
    "changed_files": ["project/backend-fastapi/app/main.py"],
    "rc_normalized": 0
  }
  ```
- **RC normalization**: skip=0, tool_missing=127, failure=non-zero

### Coverage Targets
- **Core modules** (validator/loader/runner): ≥ 90% (currently 86.67%)
- **Overall** (drivers/ + scripts/utils): ≥ 60% (currently 50%)
- **Wrappers** (cli/detect/registry): no minimum (acceptable at ~0%)

### Security Validation
- `make drivers-validate` blocks:
  - Chaining/redirection: `&&`, `||`, `;`, `|`, `>`, `<`
  - Off-whitelist commands per category (see 1.2)
  - Missing script files referenced in commands

## 5) Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Breaking P2.1/P2.2 functionality** | High | Preserve existing template expansion + driver execution; add regression tests; validate against known good outputs |
| **CLI compatibility break** | Medium | Keep `drivers/registry.py` reexports; verify `python -m drivers.registry` still works; test in CI |
| **Whitelist too strict** | Medium | Start conservative, document override mechanism for `drivers/.../scripts/*`; iterate via PR feedback |
| **Reintroducing fixed bugs** | High | See section 2.2 - validate BUG-004 to BUG-7.2-001 fixes preserved; run validation commands post-refactor |
| **Helper growth without tests** | Low | Enforce: each new helper gets minimal unit test (mocked dependencies); no untested code merged |
| **Timeline slip (Dev/QA refactor)** | Medium | Allocate Week 4 buffer; prioritize 1.1-1.2 first (foundational); split 1.3/1.4 if needed |
| **Cross-platform test failures** | Low | Test on macOS/Linux (primary); accept WSL for Windows; document OS-specific handling |

## 6) Suggested Timeline (conservative estimates)

**Week 1**: Foundation (1.1 + 1.2)
- Days 1-2: CLI DIP refactor + tests (1.1)
- Days 3-4: Validator whitelist + cross-platform script checks (1.2)
- Day 5: Buffer + integration testing

**Week 2**: Dev/QA refactor (1.3 + 1.4) — **high complexity**
- Days 1-3: run_dev.py refactor (711 lines → extract helpers, preserve P2.1)
- Days 4-5: run_qa.py refactor (704 lines → execution vs reporting split)
- **Risk**: Large files, many integration points — may slip to Week 3

**Week 3**: DRY + coverage + CI (1.5 + 1.6 + 1.7)
- Days 1-2: Extend runner.py with naming/RC helpers (1.5)
- Days 3-4: Core coverage tests to reach 90% (1.6)
- Day 5: Optional CI workflow (1.7) or buffer

**Week 4** (buffer): Integration, review, documentation
- Full regression testing (all 12+ tests pass)
- Code review and adjustments
- Update documentation (ADRs, ARCHITECTURE_PRINCIPLES.md)

**Dependencies**:
- 1.2 → 1.3/1.4 (validator must be solid before refactoring consumers)
- 1.3/1.4 → 1.5 (need to understand duplication before DRYing)
- 1.5 → 1.6 (new helpers need tests)

## 7) Current Coverage Appendix (context)

- 12 tests (7 driver layer + 5 runner)
- **Core modules coverage** (loader/validator/runner avg: 86.67%):
  - `drivers/loader.py`: 95% (59 stmts, 3 miss)
  - `scripts/utils/runner.py`: 91% (44 stmts, 4 miss)
  - `drivers/validator.py`: 74% (57 stmts, 15 miss) — needs embedded/gpu validation tests
- **Wrapper modules** (excluded from core target, will stay low):
  - `drivers/cli.py`: 0% (92 stmts, argparse layer)
  - `drivers/detect.py`: 0% (18 stmts, toolchain detection)
  - `drivers/registry.py`: 0% (4 stmts, reexport wrapper)
- **Overall** (drivers/ + scripts/utils): 50% (274 stmts, 136 miss)
- **Test performance**: 12/12 pass in ~2.7s

## 8) Branch & PR Instructions (to execute)

- **Branch for Phase 1 implementation** (uses general branch name for all refactor phases):
  - `git checkout -b refactor-roles`
  - Work on Phase 1 tasks (1.1-1.7)
  - `git add -A && git commit -m "refactor(phase1): apply SRP/DIP/DRY to drivers, Dev/QA roles"`
  - `git push -u origin refactor-roles`

- **Create PR to main** (GH CLI):
  ```bash
  gh pr create -B main -H refactor-roles \
    -t "Phase 1 Refactor: Drivers, Dev, QA (SRP/DIP/DRY)" \
    -b "Details in docs/PHASE1_REFACTOR_PLAN.md

  ## Summary
  - Refactored drivers/* (CLI DIP, validator whitelist, cross-platform)
  - Refactored run_dev.py (711 lines → extracted helpers)
  - Refactored run_qa.py (704 lines → execution vs reporting split)
  - Extended runner.py with DRY helpers
  - Core coverage: 86.67% → 90%+

  ## Testing
  - All 12+ driver layer tests pass
  - Phase 1 regression validated
  - Preserved P2.1/P2.2 functionality

  See: docs/PHASE1_REFACTOR_PLAN.md"
  ```

- **After merge**:
  - `git checkout main && git pull --ff-only`
  - `git branch -d refactor-roles`
  - Phase 2 will reuse the same branch name: `git checkout -b refactor-roles` (see PHASE2_REFACTOR_PLAN.md)

---

## 9) Next Steps

After Phase 1 completion, see **docs/PHASE2_REFACTOR_PLAN.md** for Architect, Product Owner, and BA role refactoring.
\n+## 3.B — Automation vs. Judgment Execution Checklist (Phase 1)

This checklist clarifies which tasks can run unattended and which require human judgment, with concrete gates and commands to verify completion.

- 1.1 Drivers CLI decoupling — Automatic
  - Outcome: Extract pure functions `list_drivers()`, `show_driver()`, `plan_from_config(cfg, detectors)`; add unit tests with mocked detectors.
  - Commands: `pytest -q tests/driver_layer` and `python -m drivers.registry list|show|plan` must behave unchanged.
  - Gate: CLI outputs stable vs. baseline; all tests green.

- 1.2 Validator whitelist + script checks — Mostly automatic
  - Outcome: Allowlist per category (backend/frontend/mobile/embedded/gpu) and verification of referenced scripts being executable.
  - Commands: `make drivers-validate` must fail on intentionally bad fixtures and pass on valid drivers.
  - Gate: Negative tests catch disallowed binaries; positive cases pass; docs updated in `drivers/validator.py` docstring.

- 1.3 Refactor run_dev.py (SRP/SoC) — Needs judgment
  - Outcome: Extract helpers `_load_config()`, `_resolve_targets()`, `_scaffold_templates()`, `_embedded_detection()`, `_write_dev_summary()`; inject detectors for testability.
  - Commands: `make dev-smoke` must pass; logs under `artifacts/dev/<story>/` and stable `dev_summary.json` schema.
  - Gate: Code review for SRP; smoke run OK; relative paths preserved in summary.

- 1.4 Refactor run_qa.py (exec vs. reporting) — Needs judgment
  - Outcome: Extract `build_qa_summary(...)` and `run_driver_area(area, drv)`; use `scripts/utils/runner.py` only.
  - Commands: `make qa-smoke` and `make qa-summary` must pass; stable `qa_summary.json` with expected fields.
  - Gate: Smoke OK; summary RC normalization and relative paths verified.

- 1.5 DRY helpers (logs, RC normalization) — Mostly automatic
  - Outcome: Single helper for log naming `<area>_<id>_<cmd>.log` and RC normalization (skip=0, missing=127).
  - Commands: grep for log filenames in artifacts; confirm consistency with summaries.
  - Gate: No mismatches between file names and summary entries.

- 1.6 Core tests & coverage — Mostly automatic
  - Outcome: ≥90% in validator/runner/loader; overall ≥60%.
  - Commands: `pytest -q` and `pytest --cov=drivers --cov=scripts/utils -q` (or `make drivers-test`).
  - Gate: Coverage thresholds met; all tests pass locally.

- 1.7 Minimal CI (optional) — Judgment
  - Outcome: GitHub Actions (lint + tests + artifact upload for summaries/logs).
  - Gate: Green CI run on PR; artifacts visible for QA/dev smoke.

What can run unattended
- Sequence: `make drivers-validate && make drivers-test && make dev-smoke && make qa-smoke && make qa-summary`
- Safe to run in headless environments; produces artifacts under `artifacts/dev|qa` and summaries.

Where human review is required
- Code structure changes in `scripts/run_dev.py` and `scripts/run_qa.py` (SRP/SoC).
- Validator allowlist semantics and any changes that may reject previously acceptable drivers.
- CI pipeline configuration and gating thresholds.

Branching & PR flow (reference)
- From `main`: `git checkout -b refactor-roles`
- Commit Phase 1 steps incrementally; open PR to `main`.
- Merge only when all gates above are met and summaries look stable.

---

## 7) Phase 1 Completion Summary

**Completion Date**: 2025-11-26
**Final Status**: ✅ COMPLETED (6/7 tasks - 86%)
**Branch**: `refactor-roles` (ready for merge or Phase 2)

### Tasks Completed

| Task | Status | Highlights |
|------|--------|------------|
| 1.1 - CLI DIP | ✅ | Dependency injection, pure functions, 21 tests |
| 1.2 - Validator | ✅ | Category allowlists, cross-platform checks, 5 negative tests |
| 1.3 - run_dev.py | ✅ | 5 helpers extracted, 15 unit tests, SRP applied |
| 1.4 - run_qa.py | ✅ | Execution vs reporting split, 13 unit tests |
| 1.5 - runner.py DRY | ✅ | Standardized log naming + RC normalization, 6 tests |
| 1.6 - Core tests | ✅ | 99% coverage achieved, 39 new tests added |
| 1.7 - CI | ⏸️ SKIPPED | Optional - deferred (no blocking impact) |

### Final Metrics

**Coverage**:
- Before: 82% (248 statements, 44 missing)
- After: **99%** (305 statements, 2 missing)
- Improvement: +17 percentage points

**Tests**:
- Before: 33 tests (62 if counting all previous work)
- After: **101 tests**
- New tests: +39 (validator: 15, CLI: 10, detect: 10, runner: 4)

**Code Quality**:
- ✅ SRP/SoC: Helpers extracted from monolithic flows
- ✅ DIP: Detector injection in CLI
- ✅ DRY: Shared utilities in runner.py
- ✅ Security: Command validation, no shell operators
- ✅ Testability: All core modules 98-100% coverage

### Commits (refactor-roles branch)

1. `d38f405` - Task 1.1: CLI DIP refactor
2. `a31f870` - Task 1.1: Driver management CLI
3. `91bef5a` - Task 1.2: Driver validation enhancements
4. `59f72b8` - Task 1.3: run_dev.py refactor
5. `cd8f83a` - Task 1.4: run_qa.py refactor
6. `085116a` - Task 1.5: Documentation update
7. `70ef641` - Task 1.6: 99% coverage achieved

**Total**: 7 commits, all documented with Co-Authored-By: Claude

### Acceptance Criteria Met

✅ **Core modules ≥90% coverage**: All at 98-100%
✅ **Overall ≥60% coverage**: Achieved 99%
✅ **No regressions**: All previous tests pass
✅ **Security hardening**: Command validation + allowlists
✅ **Standardized contracts**: Logs, RC codes, summaries
✅ **Testability**: Pure functions, mocked dependencies

### Outstanding Items

**Task 1.7 (CI)**: Deferred as optional
- Reason: Local testing covers 99%, no team collaboration requiring CI yet
- Can be implemented later if needed (15-20 min effort)

**Phase 2 Preparation**: Ready to proceed
- Architect refactor (926 lines)
- PO refactor (371 lines)
- BA refactor (112 lines)
- Apply lessons learned from Phase 1

### Next Steps

**Option A**: Merge to main via PR
```bash
gh pr create --base main --head refactor-roles \
  --title "Phase 1: Driver Layer Refactor (99% coverage)" \
  --body "6/7 tasks completed, Task 1.7 CI optional"
```

**Option B**: Start Phase 2 on same branch
- Continue refactoring Architect/PO/BA roles
- Keep Phase 1 changes isolated until full refactor complete

**Option C**: Archive and document
- Keep `refactor-roles` branch as reference
- Document lessons learned for future refactors

### Lessons Learned

1. **DIP upfront**: Dependency injection from start makes testing 10x easier
2. **Helper extraction**: Breaking 700-line functions into 5-6 helpers dramatically improves clarity
3. **Negative tests**: Error paths coverage is as important as happy paths
4. **DRY utilities**: Shared helpers (runner.py) prevent drift between Dev/QA
5. **Documentation**: Detailed progress tracking (PHASE1_REFACTOR_PLAN.md) essential for context

---

**Phase 1 officially closed. Ready for Phase 2 or production merge.**
