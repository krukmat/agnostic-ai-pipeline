# Driver Layer – Embedded Examples (P3.6)

This document provides two minimal, didactic examples for embedded targets. They illustrate structure, commands, expected logs, and common checks. No flashing is performed.

## Prerequisites
- Enable drivers in `config.yaml`:
  ```yaml
  drivers:
    enabled: true
    embedded:
      run_build: true
      run_test: true
  project:
    targets:
      embedded: esp32c3_riscv   # or: zephyr_c
  ```
- Ensure toolchains are on PATH:
  - ESP‑IDF: `idf.py`
  - Zephyr: `west`

## Example A — ESP32‑C3 (FreeRTOS, ESP‑IDF)

- Target: `embedded: esp32c3_riscv`
- Templates expanded under: `project/embedded-esp32c3/`

Directory skeleton after Dev runs with drivers enabled:
```
project/
  embedded-esp32c3/
    CMakeLists.txt
    main/
      CMakeLists.txt
      main.c
```

Typical commands (executed automatically by Dev/QA when flags are true and tooling is present):
- Build: `idf.py set-target esp32c3 && idf.py build`
- Test:  `idf.py unit-test-app`

Expected logs:
- Dev: `artifacts/dev/<story>/embedded_build.log`, `embedded_test.log`
  - Markers: `[DEV][embedded] Running 'build'...`, `[DEV][embedded] Running 'test'...`
- QA: `artifacts/qa/<story>/embedded_test.log`
  - Markers: `[QA][embedded] Running 'test'...`

Skip reasons (safe):
- Toolchain missing → `skip (reason: idf.py not found in PATH)`
- Flags disabled → `skip (reason: run_build=false)` or `run_test=false`

## Example B — Zephyr C

- Target: `embedded: zephyr_c`
- Templates expanded under: `project/embedded-zephyr/`

Directory skeleton after Dev runs with drivers enabled:
```
project/
  embedded-zephyr/
    CMakeLists.txt
    prj.conf
    src/
      main.c
```

Typical commands (executed automatically by Dev/QA when flags are true and tooling is present):
- Build: `west build -b <board>` (board read from driver YAML; default `nrf52840dk_nrf52840`)
- Test:  `west twister -v`

Expected logs:
- Dev: `artifacts/dev/<story>/embedded_build.log`, `embedded_test.log`
- QA:  `artifacts/qa/<story>/embedded_test.log`

Skip reasons (safe):
- Toolchain missing → `skip (reason: west not found in PATH)`
- Flags disabled → `skip (reason: run_build=false)` or `run_test=false`

## Quick Checklist
- PATH contains the toolchain executable (`idf.py` or `west`).
- `drivers.enabled: true` and `project.targets.embedded` set.
- `drivers.embedded.run_build|run_test` set appropriately.
- Inspect logs under `artifacts/dev|qa/<story>/` for run/skip markers.

## Notes
- These examples are minimal and intended for structure and verification. They complement, not replace, the templates referenced by the driver YAMLs.
- CI integration (P3.5) is deferred; examples are local/CI-safe because they never flash hardware.
