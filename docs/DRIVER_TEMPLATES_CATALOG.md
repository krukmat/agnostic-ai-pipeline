# Driver Templates Catalog (P5.2)

A quick reference of files scaffolded by each driver. These templates are optional and only applied when enabled.

Enabling template expansion
- Set `drivers.enabled: true` in `config.yaml`.
- Ensure `drivers.templates.apply: true` (default is true when missing).
- Or run `make drivers-scaffold` to materialize templates without invoking Dev.

## Backend

- fastapi (project/backend-fastapi)
  - project/backend-fastapi/app/main.py ← drivers/backend/fastapi/templates/app/main.py

## Frontend

- next_js (project/web-frontend)
  - project/web-frontend/package.json ← drivers/frontend/next_js/templates/package.json
  - project/web-frontend/next.config.js ← drivers/frontend/next_js/templates/next.config.js
  - project/web-frontend/pages/index.js ← drivers/frontend/next_js/templates/pages/index.js

## Embedded

- esp32c3_riscv (project/embedded-esp32c3)
  - project/embedded-esp32c3/CMakeLists.txt ← drivers/embedded/esp32c3_riscv/templates/CMakeLists.txt
  - project/embedded-esp32c3/main/CMakeLists.txt ← drivers/embedded/esp32c3_riscv/templates/main/CMakeLists.txt
  - project/embedded-esp32c3/main/main.c ← drivers/embedded/esp32c3_riscv/templates/main/main.c

- zephyr_c (project/embedded-zephyr)
  - project/embedded-zephyr/CMakeLists.txt ← drivers/embedded/zephyr_c/templates/CMakeLists.txt
  - project/embedded-zephyr/prj.conf ← drivers/embedded/zephyr_c/templates/prj.conf
  - project/embedded-zephyr/src/main.c ← drivers/embedded/zephyr_c/templates/src/main.c

## GPU

- cuda_jetson
  - (no templates yet; P4.1 will add optional samples)

Notes
- Templates are idempotent: files are only written if missing.
- Embedded hooks (P3.4) never flash hardware; build/test are best‑effort and skipped when toolchains are absent.
