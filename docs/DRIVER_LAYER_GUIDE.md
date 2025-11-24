# Driver Layer Guide

A concise, self‑contained guide for using the Driver Layer across backend, frontend, embedded, and GPU targets. The Driver Layer is optional and fully feature‑flagged to preserve legacy behavior.

## Overview
- Purpose: Standardize how stacks (FastAPI, Next.js, ESP32‑C3, CUDA Jetson, etc.) are selected and executed by Dev/QA.
- Safety: If tools are missing, steps are skipped with explicit reasons. No destructive actions by default.
- Opt‑in: Enabled via `drivers.enabled: true` in `config.yaml`.
 - Sample configs: see `config_gpu.yaml` for a safe GPU target example (no hooks run on non‑GPU machines).

## Configuration
Edit `config.yaml`:
- Feature flag: `drivers.enabled: true|false` (default: false)
- Targets: `project.targets` with optional categories:
  - `backend: fastapi`
  - `frontend: next_js`
  - `embedded: esp32c3_riscv` or `zephyr_c`
  - `gpu: cuda_jetson` (planned refinement)
- Embedded execution flags:
  - `drivers.embedded.run_build: true|false` (Dev only)
  - `drivers.embedded.run_test: true|false` (Dev and QA)

## Conventions + Lint (P4.2)
- Driver id: lowercase letters, digits, and underscore only (`^[a-z0-9_]+$`).
- Commands: keys are `build`, `test`, `lint`; each has a non‑empty `command` string.
- Log names: `<category>_<id>_<cmd>.log` (e.g., `backend_fastapi_test.log`, `embedded_esp32c3_riscv_build.log`).
- Artifacts:
  - Dev: `artifacts/dev/<story>/run-<timestamp>/...`
  - QA:  `artifacts/qa/<story>/...`
`make drivers-validate` fails if ids or command sections violate the convention.

## Dev/QA Usage
- Dev: `make dev STORY=S#`
  - Applies driver templates (when missing), runs build/test/lint if declared by the driver.
  - Logs under `artifacts/dev/<story>/` (e.g., `backend_fastapi_test.log`, `frontend_next_js_build.log`).
- QA: `make qa QA_RUN_TESTS=1`
  - Executes driver test/lint where available.
  - Logs under `artifacts/qa/<story>/`.
- Behavior on missing tools/flags: emits a clear skip reason and continues.

## Embedded Drivers (P3.4)
Optional build/test hooks for embedded targets executed by Dev/QA when toolchains are present. No flashing by design.

- Prerequisites
  - `drivers.enabled: true`
  - `project.targets.embedded: esp32c3_riscv` (ESP‑IDF) or `zephyr_c` (Zephyr)
  - Toolchains on PATH:
    - ESP‑IDF: `idf.py`
    - Zephyr: `west`

- Flags
  - `drivers.embedded.run_build` (Dev)
  - `drivers.embedded.run_test` (Dev/QA)

- Outputs
  - Dev logs: `artifacts/dev/<story>/embedded_build.log`, `embedded_test.log`
  - QA logs: `artifacts/qa/<story>/embedded_test.log`
  - Typical markers: `[DEV][embedded] Running 'build'...`, `skip (reason: ...)`, `[QA][embedded] Running 'test'...`

- Safety
  - No flashing/serial operations in P3.4.
  - Missing toolchains or disabled flags never break the pipeline.
  - Commands are sourced from driver YAMLs:
    - `drivers/embedded/esp32c3_riscv.yaml`
    - `drivers/embedded/zephyr_c.yaml`
  - Examples: see docs/DRIVER_EXAMPLES.md for minimal ESP‑IDF and Zephyr walkthroughs.

## GPU Drivers (Planned Refinement)
- `gpu/cuda_jetson.yaml` scaffolding exists; refinement will add detection (nvcc, nvidia‑smi) and safe build/test hooks.
- Goal: safe‑skip on non‑GPU machines; optional micro‑bench for verification.

## CLI Helpers
- Validate all drivers: `make drivers-validate`
- Show resolved targets (friendly): `make drivers-show`
- List available drivers: `make drivers-list` (or `python -m drivers.registry list`)
- Dry-run plan (what would run and why): `make drivers-plan` (or `python -m drivers.registry plan [--config ...]`)
- Show one driver (YAML dump): `python -m drivers.registry show <category> <id>`
- Scaffold templates only (no run): `make drivers-scaffold`

## Templates Catalog (P5.2)
- Optional template packs per driver; Dev will expand them when `drivers.templates.apply: true`.
- To scaffold ahead of time (without running Dev), use `make drivers-scaffold`.
- Catalog: see `docs/DRIVER_TEMPLATES_CATALOG.md` for a per-driver file list.
  - Backend: fastapi → project/backend-fastapi/app/main.py
  - Frontend: next_js → project/web-frontend/* (package.json, next.config.js, pages/index.js)
  - Embedded: esp32c3_riscv, zephyr_c → project/embedded-*/ skeletons

## Roadmap Notes
- Ordering update: P3.5 (Embedded CI Stubs) is deferred to the end of the roadmap to focus first on docs/examples, GPU refinement, cross‑driver conventions, and CLI enhancements. See `docs/DRIVER_LAYER_EXEC_PLAN.md` for live tracking.

## Troubleshooting
- “Skip (reason: toolchain not found)” → install ESP‑IDF (`idf.py`) or Zephyr (`west`) and ensure they’re on PATH.
- Commands not running with drivers.enabled=true → confirm `project.targets` entries match existing driver YAML IDs.
- Logs not appearing → check for warnings in role output and ensure STORY param is set in Dev/QA runs.

## Tests (P6)
- Smoke tests for the driver layer live under `tests/driver_layer/`.
- Run them with: `make drivers-test`
- What they cover:
  - Registry CLI `list` basic output.
  - `plan` dry-run with a mocked Zephyr `west` on PATH, verifying detection and `would_run.test` resolution.
