# Driver Layer – Execution Plan (Phased)

Status: Draft for approval
Branch: feature/driver-layer
Scope: Introduce a driver registry and per‑target driver YAMLs (backend, frontend, mobile, embedded, gpu) without breaking the current pipeline.

## Goals
- Standardize how stacks (FastAPI, Next.js, ESP32‑C3, CUDA Jetson, etc.) are described and consumed by roles.
- Keep legacy behavior as default; add a feature flag to enable drivers.
- Deliver incrementally: start with backend/frontend drivers, then expand to embedded and gpu.

## Non‑Goals (this phase)
- No breaking changes to `make iteration`/`make loop`.
- No mandatory installation of embedded/gpu toolchains.

---

## Architecture Summary
- Registry: `drivers/registry.py` loads YAML for a given category/id and exposes typed traits (templates, build/test/lint commands, artifact paths, metadata).
- Drivers: `drivers/<category>/<driver>.yaml` (schema aligned with `docs/DRIVER_LAYER_PLAN.md`).
- Config: extend `config.yaml` with `project.targets` and a feature flag `drivers.enabled`.
- Orchestrator: passes resolved drivers to roles; drivers are only honored when `drivers.enabled: true`.
- Roles impact:
  - BA/PO: minimal; only surface targets in requirements/vision (optional).
  - Architect: references targets to tailor architecture (e.g., framework, device constraints).
  - Dev: scaffolds templates, runs build/test commands from drivers.
  - QA: uses the driver’s test runner/commands.

---

## Phases & Tasks

### Phase 0 – Scaffolding & Spec (approval required)
Deliverables
- D0.1: Driver YAML schema (keys: id, category, language, framework, templates[], build/test/lint, artifact_paths[], metadata) – documented.
- D0.2: Directory layout with placeholders: `drivers/backend/fastapi.yaml`, `drivers/frontend/next_js.yaml`, `drivers/embedded/esp32c3_riscv.yaml`, `drivers/gpu/cuda_jetson.yaml` – placeholders only.
- D0.3: Registry skeleton `drivers/registry.py` – loads YAML, validates required keys, no side‑effects.
- D0.4: Feature flag proposal – `drivers.enabled: false` (default) in `config.yaml`.

Acceptance Criteria
- Spec aligned with `docs/DRIVER_LAYER_PLAN.md` and extended to cover ESP32‑C3 (RISC‑V) and CUDA Jetson.
- Running `python -c "import drivers.registry as r"` does not fail when placeholders exist.
- No changes to current pipeline behavior when the flag is off.

Status: Completed

Risks/Mitigations
- Divergence between plan and implementation → lock schema in this phase; version driver schema as `v1`.
- Over‑scope → keep embedded/gpu as placeholders until Phase 3–4.

---

### Phase 1 – Backend/Frontend MVP (approval required)
Deliverables
- P1.1: Minimal drivers: `backend/fastapi.yaml`, `frontend/next_js.yaml` with working templates and commands.
- P1.2: Registry CLI + Makefile target: `python -m drivers.registry validate --all` and `make drivers-validate` for quick checks.
- P1.3: Orchestrator wiring behind flag: when `drivers.enabled: true`, resolve targets from `config.yaml > project.targets` and attach to role context.

Acceptance Criteria
- With `drivers.enabled: false`, pipeline runs unchanged.
- With `drivers.enabled: true` and targets set (`backend: fastapi`, `frontend: next_js`), Dev can scaffold and run `build/test` commands defined by drivers without breaking the loop.

Status: In Progress
Notes:
- Added `drivers.enabled` feature flag to `config.yaml` (default false).
- Added `project.targets` scaffold in `config.yaml` with null defaults.
- Orchestrator (`scripts/orchestrate.py`) now attaches resolved drivers to role payloads when the flag is on; legacy behavior preserved otherwise.
- Makefile: `drivers-validate` target calls the registry CLI to validate all YAMLs.

Risks/Mitigations
- Tooling mismatch on host → detect missing commands and fall back to legacy behavior, logging a warning.

---

### Phase 2 – Dev/QA integration (after Phase 1)
Deliverables
- P2.1: Dev role: template expansion (copy driver templates to `project/`), then execute driver build/test.
- P2.2: QA role: run the driver's test runner; persist reports under driver‑aware paths.

Acceptance Criteria
- Sample project with FastAPI + Next.js builds and tests via driver commands inside `make iteration`/`make loop`.

Status: Complete (P2.1 and P2.2)
Notes:
- **P2.1 ✅ Complete**: `scripts/run_dev.py` applies driver templates and executes build/test/lint commands.
  - Template expansion (lines 384-413): copies driver templates if they don't exist (lines 398-408)
  - Command execution (lines 485-547): runs driver build/test/lint commands for backend/frontend (lines 519-544)
  - Best-effort: warnings logged, RC captured, never blocks development
  - Behind feature flag: only when `drivers.enabled: true`
  - **Tested**: Templates applied, commands executed with logs in `artifacts/dev/S1/run-20251124-110012/`
- **P2.2 ✅ Complete**: QA role (`scripts/run_qa.py`) runs driver test runners.
  - Backend (lines 392-404): runs driver test and lint commands if available
  - Frontend (lines 437-451): runs driver build, test, and lint commands if available
  - Fixed missing import: added `from drivers.registry import load_driver` (line 9)
  - Logs persisted under `artifacts/qa/<story>/` as `<category>_<id>_<command>.log`
  - **Tested**: Backend test/lint executed, logs captured in `artifacts/qa/S1/`

---

### Phase 3 – Embedded (ESP32‑C3 RISC‑V, Zephyr C) – gated
Deliverables
- P3.1: `embedded/esp32c3_riscv.yaml` (ESP‑IDF) – idf.py build/flash/monitor; templates for FreeRTOS app.
- P3.2: `embedded/zephyr_c.yaml` – west build/flash; `twister` tests; templates.
- P3.3: Dev role embedded toolchain detection + optional build/test execution.
- P3.4: QA role embedded toolchain detection + optional test execution.

Acceptance Criteria
- Host validation without device: detect toolchain presence; run host unit tests or skip with notice.

Status: Completed
Notes:
- **P3.1**: Templates added (ESP‑IDF FreeRTOS): `CMakeLists.txt`, `main/CMakeLists.txt`, `main/main.c`. YAML valida (`make drivers-validate` ✅).
- **P3.2**: Templates added (Zephyr): `CMakeLists.txt`, `prj.conf`, `src/main.c`. YAML valida (`make drivers-validate` ✅).
- **P3.3**: Dev role (`run_dev.py:413-456`) detects ESP-IDF (`has_idf()`) and Zephyr (`has_west()`) toolchains. Optional build/test execution controlled by `drivers.embedded.run_build` and `drivers.embedded.run_test` flags. Logs in `artifacts/dev/<story>/run-<ts>/embedded_<id>_<cmd>.log`.
- **P3.4**: QA role (`run_qa.py:469-503`) detects toolchains and optionally runs test when `drivers.embedded.run_test: true`. Logs in `artifacts/qa/<story>/embedded_<id>_test.log`.

---

### Phase 4 – GPU (CUDA Jetson, ROCm Edge) – gated
Deliverables
- P4.1: `gpu/cuda_jetson.yaml` – nvcc build, TensorRT deployment hooks, profiling commands.
- P4.2: `gpu/rocm_edge.yaml` – hipcc build, `rocminfo` validation.

Acceptance Criteria
- No hard dependency on GPU; host‑side checks + skip behavior when not available.

Status: Planned (gated by hardware)

---

## Tracking (live)

| ID    | Task                                   | Status      | Notes |
|-------|----------------------------------------|-------------|-------|
| D0.1  | Driver YAML schema                     | Completed   | Schema v1 keys locked |
| D0.2  | Placeholders for initial drivers       | Completed   | fastapi/next_js/esp32c3/cuda_jetson added |
| D0.3  | Registry skeleton                      | Completed   | `drivers/registry.py` with CLI validate |
| D0.4  | Feature flag in config.yaml            | Completed   | `drivers.enabled` default false |
| P1.0  | Orchestrator payload wiring            | Completed   | Attaches `drivers` map behind flag |
| P1.1  | fastapi/next_js drivers (MVP)          | Completed   | Templates + commands added |
| P1.2  | Registry CLI validate                  | Completed   | `drivers.registry validate --all` + `make drivers-validate`. BUG-004 Fixed |
| P1.3  | Orchestrator wiring (behind flag)      | Completed   | Attach driver objects to context; `make drivers-show` prints resolved targets |
| P2.1  | Dev role template expansion + build/test | Completed   | `scripts/run_dev.py` (lines 384-547): templates + driver commands (best-effort) |
| P2.2  | QA role driver test runner integration | Completed   | `scripts/run_qa.py` (lines 392-404, 437-451): runs driver test/lint commands. Fixed missing import |
| P3.1  | embedded/esp32c3_riscv.yaml (ESP-IDF)  | Completed   | YAML + templates (CMakeLists, main.c). BUG-005 Fixed |
| P3.2  | embedded/zephyr_c.yaml (Zephyr)        | Completed   | YAML + templates (CMakeLists, prj.conf, main.c). BUG-006 Fixed |
| P3.3  | Dev embedded toolchain detection       | Completed   | `run_dev.py:413-456`, `drivers/detect.py`. Flags: `run_build`, `run_test` |
| P3.4  | QA embedded toolchain detection        | Completed   | `run_qa.py:469-503`. Flag: `run_test`. Logs in `artifacts/qa/<story>/` |
| P3.5  | Embedded CI stubs (safe, no flashing)  | Deferred    | Moved to end of roadmap per decision; implement after P6 |
| P4.1  | GPU driver refinement (cuda_jetson)     | Planned     | Add nvcc/nvidia-smi detection, safe build/test hooks |
| P4.2  | Cross-driver conventions + lint         | Completed   | ID regex, non-empty commands, unified log names; docs updated |
| P5.1  | Registry/CLI enhancements               | Completed   | list/show/plan subcommands in drivers.registry; guide updated |
| P5.2  | Templates catalog + scaffold flag       | Completed   | docs/DRIVER_TEMPLATES_CATALOG.md, make drivers-scaffold, drivers.templates.apply flag |
| P6    | Docs + Test coverage                    | Completed   | Troubleshooting + tests/driver_layer; make drivers-test. BUG-009 Fixed |
| P3.6  | Driver Docs + Examples                 | Completed   | `docs/DRIVER_EXAMPLES.md`, enriched YAML comments, `DRIVER_LAYER_GUIDE.md` links |

We will update this table as tasks move to In Progress / Completed, adding incidents and adjustments as needed.

---

## Roadmap Update (Ordering Change)

Decision: Move P3.5 (Embedded CI Stubs) to the end of the roadmap. This defers CI wiring for embedded until after higher‑value items are complete.

Updated execution order (next milestones):
- P3.6 — Driver Docs + Examples (hello‑world ESP32‑C3 FreeRTOS; hello‑world Zephyr; enrich YAML comments)
- P4.1 — GPU Driver Refinement (cuda_jetson build/test hooks; detection via nvcc/nvidia‑smi; safe skips)
- P4.2 — Cross‑Driver Conventions (unify command names and artifact paths; schema lint rules)
- P5.1 — Registry/CLI Enhancements (list/show, dry‑run execution plan, explain decisions)
- P5.2 — Templates Catalog (optional scaffold packs per driver; guarded application during Dev)
- P6   — Documentation + Test Coverage (integration tests with mocked toolchains; troubleshooting matrix)
- P3.5 — Embedded CI Stubs (last) (GitHub Actions examples guarded by detection; no flashing)

Rationale:
- Prioritize developer experience, parity across drivers, and documentation before CI wiring.
- Reduce CI churn while embedded hooks stabilize locally (P3.3/P3.4 done).
- Maintain safety: no flashing/USB interactions until the very end.

---

## Bugs

### BUG-004: CLI `load` command fails with dataclasses

**Severity**: Low (CLI only, does not affect pipeline)

**Reproduction**:
```bash
python -m drivers.registry load backend fastapi
# Error: yaml.representer.RepresenterError: cannot represent an object Template(...)
```

**Cause**: `yaml.safe_dump(drv.__dict__)` cannot serialize `Template` and `Command` dataclass instances.

**Fix required**:
```python
import dataclasses

# In main(), replace:
#   print(yaml.safe_dump(drv.__dict__, sort_keys=False, allow_unicode=True))
# With:
print(yaml.safe_dump(dataclasses.asdict(drv), sort_keys=False, allow_unicode=True))
```

**Status**: Fixed (registry v1.1)
**Change**: CLI now serializes drivers with `dataclasses.asdict(drv)` to ensure nested dataclasses are YAML‑safe.

---

### BUG-005: P3.1 esp32c3_riscv.yaml missing templates

**Severity**: Medium (deliverable incomplete)

**Issue**: Deliverable P3.1 specifies "templates for FreeRTOS app" but `drivers/embedded/esp32c3_riscv.yaml` has `templates: []` (empty).

**Expected**: Templates for a basic FreeRTOS application scaffold (e.g., main.c, CMakeLists.txt, sdkconfig.defaults).

**Status**: Fixed
**Resolution**: Templates added in `drivers/embedded/esp32c3_riscv/templates/` (CMakeLists.txt, main/CMakeLists.txt, main/main.c). YAML updated with template references.

---

### BUG-006: P3.2 zephyr_c.yaml missing templates

**Severity**: Medium (deliverable incomplete)

**Issue**: Deliverable P3.2 specifies "templates" but `drivers/embedded/zephyr_c.yaml` has `templates: []` (empty).

**Expected**: Templates for a basic Zephyr application scaffold (e.g., main.c, CMakeLists.txt, prj.conf).

**Status**: Fixed
**Resolution**: Templates added in `drivers/embedded/zephyr_c/templates/` (CMakeLists.txt, prj.conf, src/main.c). YAML updated with template references.

---

### BUG-007: Silent `except Exception: pass` blocks hide driver errors

**Severity**: High (errors silently ignored, debugging difficult)

**Issue**: Multiple locations use `except Exception: pass` without any logging, completely hiding errors from the driver layer.

**Affected locations**:

1. **`scripts/orchestrate.py:176-178`**
   ```python
   except Exception:
       # Never block role execution due to driver layer
       pass
   ```
   Context: Driver resolution in `execute_role()`. Config errors, import failures, typos silenced.

2. **`scripts/run_dev.py:430-432`**
   ```python
   except Exception:
       # Never block development due to driver layer
       pass
   ```
   Context: Template expansion block. Template load failures, config errors silenced.

3. **`scripts/run_dev.py:564-566`**
   ```python
   except Exception:
       # Never block development due to driver layer
       pass
   ```
   Context: Driver command execution block. Build/test/lint execution errors silenced.

4. **`scripts/run_qa.py:363-364`**
   ```python
   except Exception:
       cfg = {}
   ```
   Context: Loading `config.yaml`. YAML syntax errors cause QA to run with empty config without warning.

**Risk**: Configuration errors, missing imports, typos, and other issues pass silently. Users get unexpected behavior with no indication of what went wrong.

**Fix required**: Replace `pass` with at minimum `logger.debug()` or `logger.warning()` to capture errors:
```python
except Exception as e:
    logger.warning(f"[CONTEXT] Driver layer error (non-fatal): {e}")
    # Continue with fallback behavior
```

**Status**: Fixed
**Change**:
- `scripts/orchestrate.py`: ahora registra `logger.warning` ante errores de wiring.
- `scripts/run_dev.py`: registra `logger.warning` ante fallos de scaffold o ejecución de comandos del driver.
- `scripts/run_qa.py`: si falla la carga de `config.yaml`, registra `logger.warning` y continúa con config vacío.

---

### BUG-008: Backend tests fail to import `app` (PYTHONPATH in subprocess)

**Severity**: Medium (backend tests can fail under Dev/QA subprocesses)

**Issue**: When backend tests run via subprocess from repo root, Python cannot find the `app` package under `project/backend-fastapi` → `ModuleNotFoundError: app`.

**Resolution**:
- Add `project/backend-fastapi` to `PYTHONPATH` for backend driver commands in Dev/QA.
- Files changed:
  - `scripts/run_dev.py`: injects backend path into `PYTHONPATH` when running `backend_*` commands.
  - `scripts/run_qa.py`: same injection inside `run_shell()` for backend driver commands.

**Status**: Fixed

---

### P2.2 – QA role driver runner (Completed)

**What changed**:
- `scripts/run_qa.py` ahora detecta `drivers.enabled` y resuelve `project.targets`. Si hay driver para backend/frontend, ejecuta `build/test/lint` declarados por el driver (best‑effort) y guarda los logs bajo `artifacts/qa/<story>/` (ej. `backend_fastapi_test.log`, `frontend_next_js_build.log`). Si el driver no está configurado o el flag está apagado, mantiene el comportamiento legacy (pytest/npm sobre rutas por defecto).

**Status**: Completed

**Testing Results** (2025-11-24):
- Test config: `drivers.enabled: true`, `project.targets.backend: fastapi`, `project.targets.frontend: next_js`
- Dev execution:
  - ✅ Templates scaffolded (main.py, package.json, next.config.js, pages/index.js)
  - ✅ Commands executed: `backend_fastapi_test`, `backend_fastapi_lint`, `frontend_next_js_build`, `frontend_next_js_test`, `frontend_next_js_lint`
  - ✅ Logs persisted: `artifacts/dev/S1/run-20251124-110012/<cmd>.log`
- QA execution:
  - ✅ Backend driver test/lint executed: `artifacts/qa/S1/backend_fastapi_test.log`, `backend_fastapi_lint.log`
  - ✅ Commands properly detected and invoked
- Conclusion: Phase 2 fully functional when `drivers.enabled: true`

---

### BUG-009: test_registry_cli.py falla por ROOT incorrecto en subprocess

**Severity**: Medium (tests fallan, CI afectado)

**Reproduction**:
```bash
make drivers-test
# Error: ModuleNotFoundError: No module named 'drivers'
# 2 failed tests
```

**Cause**: `tests/driver_layer/test_registry_cli.py` usa `ROOT = Path(__file__).resolve().parents[1]` que apunta a `tests/` en lugar del root del proyecto. Además, no pasa `PYTHONPATH` al subprocess.

**Affected file**: `tests/driver_layer/test_registry_cli.py:12,17`
```python
ROOT = Path(__file__).resolve().parents[1]  # Apunta a tests/, no al repo root

def _run_cli(args: list[str], env: dict | None = None) -> str:
    cmd = [sys.executable, "-m", "drivers.registry", *args]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)  # env puede ser None
```

**Fix required**:
```python
ROOT = Path(__file__).resolve().parents[2]  # Repo root

def _run_cli(args: list[str], env: dict | None = None) -> str:
    cmd = [sys.executable, "-m", "drivers.registry", *args]
    run_env = env.copy() if env else os.environ.copy()
    run_env["PYTHONPATH"] = str(ROOT)
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=run_env)
```

**Status**: Fixed
**Resolution**:
- tests/driver_layer/test_registry_cli.py: usa `parents[2]` para resolver ROOT al repo y exporta `PYTHONPATH=ROOT` al env del subprocess. `pytest -q tests/driver_layer` pasa (2 tests).

---

## Approvals Requested
- Phase 0 (Scaffolding & Spec): approve to create schema, placeholders, registry skeleton, and feature flag.
- Phase 1 (Backend/Frontend MVP): approve to implement fastapi/next_js drivers and safe wiring under feature flag.
