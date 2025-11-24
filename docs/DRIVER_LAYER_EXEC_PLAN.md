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

Status: Partial (P2.1 Complete, P2.2 Incomplete)
Notes:
- **P2.1 ✅ Complete**: `scripts/run_dev.py` (lines 384-413) aplica plantillas al inicio y (lines 485-547) ejecuta `build/test/lint` del driver (best‑effort, con logs en `artifacts/dev/<story>/run-<ts>/`).
  - Template expansion: copies driver templates if they don't exist (lines 398-408)
  - Command execution: runs driver build/test/lint commands for backend/frontend (lines 519-544)
  - Best-effort: warnings logged, RC captured, never blocks development
  - Behind feature flag: only when `drivers.enabled: true`
- **P2.2 ❌ Not Implemented**: QA role (`scripts/run_qa.py`) does NOT yet use driver test runners. No driver integration found in QA script.

---

### Phase 3 – Embedded (ESP32‑C3 RISC‑V, Zephyr C) – gated
Deliverables
- P3.1: `embedded/esp32c3_riscv.yaml` (ESP‑IDF) – idf.py build/flash/monitor; templates for FreeRTOS app.
- P3.2: `embedded/zephyr_c.yaml` – west build/flash; `twister` tests; templates.

Acceptance Criteria
- Host validation without device: detect toolchain presence; run host unit tests or skip with notice.

Status: Planned (gated by toolchains)

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
| P2.2  | QA role driver test runner integration | Pending     | `scripts/run_qa.py` does NOT yet use driver test runners |

We will update this table as tasks move to In Progress / Completed, adding incidents and adjustments as needed.

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

### P2.2 – QA role driver runner (Completed)

**What changed**:
- `scripts/run_qa.py` ahora detecta `drivers.enabled` y resuelve `project.targets`. Si hay driver para backend/frontend, ejecuta `build/test/lint` declarados por el driver (best‑effort) y guarda los logs bajo `artifacts/qa/<story>/` (ej. `backend_fastapi_test.log`, `frontend_next_js_build.log`). Si el driver no está configurado o el flag está apagado, mantiene el comportamiento legacy (pytest/npm sobre rutas por defecto).

**Status**: Completed

---

## Approvals Requested
- Phase 0 (Scaffolding & Spec): approve to create schema, placeholders, registry skeleton, and feature flag.
- Phase 1 (Backend/Frontend MVP): approve to implement fastapi/next_js drivers and safe wiring under feature flag.
