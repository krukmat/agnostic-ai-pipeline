# QA/Dev Smoke Reliability — Execution Plan

Status: Proposed (awaiting approval to implement)
Scope: Add minimal, provider/toolchain‑agnostic smoke checks for backend (FastAPI) and web (Express) to stabilize iteration/loop runs.

## Goals
- Catch obvious breakages early (imports, basic routes, scaffolds) without requiring models, GPUs, or embedded toolchains.
- Provide clear run/skip messaging and consistent artifacts under `artifacts/qa/` and `artifacts/dev/` when applicable.
- Keep the pipeline fast and non‑intrusive; no changes to providers/models.

## Non‑Goals
- No DSPy/MiPRO tuning or dataset generation.
- No embedded/GPU actions (remain opt‑in via drivers and safe‑skip as today).
- No exhaustive test coverage — smokes only.

## Tasks (Phase Outline)
1) Backend smoke (pytest)
   - Add `project/backend-fastapi/tests/test_smoke.py` with:
     - `test_smoke_imports`: import `app` and construct a TestClient.
     - `test_smoke_health`: GET `/` or `/health` returns 200 if route exists; otherwise mark as informative failure (message suggests scaffolding the route).

2) Web smoke (Jest)
   - Add `project/web-express/tests/smoke.test.js` with:
     - Import of main router/app (e.g., `src/index.js` or router module) guarded with try/catch.
     - If project not scaffolded, mark the test as skipped with a clear reason (Jest `test.skip(...)`).

3) Make targets
   - `qa-smoke`: run only the minimal smokes.
     - Backend: `pytest -q project/backend-fastapi` (filters to smoke file if needed).
     - Web: `npm test -- --passWithNoTests` inside `project/web-express` when present.
   - `dev-smoke` (optional): quick import/lint where applicable without running full suites.

4) QA/Dev runner messaging
   - Ensure QA reports explicit skip reasons when:
     - No backend/web project found.
     - No tests discovered.
     - Tooling missing (npm/pytest) — already logged as warning.
   - Keep current safe‑skip behavior; do not fail the pipeline for missing smokes.

5) Documentation
   - Brief “Smoke tests” subsection in Driver/QA guide areas with commands and expectations.
   - Do not add noise to README; link to the guide if necessary.

6) Verification
   - Run `make qa-smoke` on a clean repo to confirm:
     - Backend: import test passes; health route returns 200 if exists, or gives a clear hint.
     - Web: test suite runs and is skipped if project not scaffolded, with explicit message.
   - Artifacts appear under `artifacts/qa/<story>/` when executed via QA runner; for direct Make, ensure logs are printed to console and/or simple files under `artifacts/qa/smoke/`.

## Deliverables
- Files
  - `project/backend-fastapi/tests/test_smoke.py`
  - `project/web-express/tests/smoke.test.js`
- Make targets
  - `qa-smoke` (and optionally `dev-smoke`)
- Docs
  - Add a short “Smoke tests” section to the QA/Driver guide with run commands and expected outcomes.

## Acceptance Criteria
- `make qa-smoke` runs without fatal errors on a clean repo.
- When a project/test set is missing, output is explicit (skip with reason) and not a hard failure.
- When present, backend import + minimal route are validated; web import smoke executes or is skipped clearly.
- Artifacts and/or console output are sufficient to diagnose basic issues quickly.

## Risks & Mitigations
- Tooling not installed (pytest/npm): already handled with safe‑skip and explicit warnings.
- Route names differ by scaffold: test clarifies acceptable endpoints and failure messages recommend next steps.
- CI variability: keep smokes deterministic and minimal; prefer markers over heavy assertions.

## Tracking (to be updated during execution)
| ID   | Task                         | Status     | Notes |
|------|------------------------------|------------|-------|
| S1   | Backend smoke (pytest)       | Completed  | test_smoke_imports, test_smoke_health. BUG-S1-001 Fixed |
| S2   | Web smoke (Jest)             | Completed  | smoke.test.js with safe skip. BUG-S2-001 Fixed |
| S3   | Make targets (qa-smoke/dev)  | Completed  | minimal wiring only. BUG-S3-001 Fixed |
| S4.1 | Status schema + RC mapping   | Completed  | Defined enum + rc mapping (doc-only) |
| S4.2 | Dev dev_summary.json         | Completed  | Emits per-run summary under artifacts/dev/<story>/run-<ts>/. BUG-S4.2-001 Fixed |
| S4.3 | QA qa_summary.json + target  | Completed  | Emits consolidated summary; add make qa-summary |
| S4.4 | Log prefixes consistency     | Completed  | Standardized RUN/SKIP/ERROR prefixes (QA/DEV) |
| S4.5 | RC normalization + area naming | Completed  | Skips use rc=0; area naming aligned to 'web' |
| S5   | Documentation                | Planned    | brief guide subsection |
| S6   | Verification                 | Planned    | run on clean repo |

## Notes
- This phase is independent from the Driver Layer phases (P3.x–P6). It focuses solely on reliability for QA/Dev.

---

## Bugs

---

## S4 — Standardized QA/Dev summary (Subtasks)

Purpose: simplify validation by producing a single, structured summary for QA and a lightweight pre-summary from Dev, plus consistent messaging/logs.

- Status schema (shared)
  - Fields: `area`, `executed` (bool), `rc` (int), `status` (enum), `reason` (str|null), `tools_present` (bool|map), `logs` (list[str])
  - Status enum: `run_pass`, `run_fail`, `skip_no_tests`, `skip_tool_missing`, `skip_not_configured`, `error_collection`, `error_other`
  - RC mapping: `0` pass, `10` skip/no-tests, `127` tool-missing, `4` collection-error, `1` generic-fail

- Artifacts
  - Dev → `artifacts/dev/<story>/run-<ts>/preqa_summary.json` (attempted commands, RCs, tool detections)
  - QA  → `artifacts/qa/<story>/qa_summary.json` (final per-area status with reasons and log paths)

- Make target
  - `qa-summary`: pretty-print `qa_summary.json` (uses `jq` if available; fallback raw)

- Log prefixes
  - QA: `[QA][backend|web|embedded] RUN/SKIP/ERROR: reason`
  - Dev: `[DEV][backend|frontend|embedded] RUN/SKIP/ERROR: reason`

Subtasks
- S4.1 — Status schema + RC mapping (doc-only)
- S4.2 — Dev dev_summary.json emission (rename from preqa_)
- S4.3 — QA qa_summary.json emission + `make qa-summary`
- S4.4 — Prefixes audit and alignment across messages
- S4.5 — RC normalization in code (treat skips as rc=0) and area naming alignment (use "web")

### Implementation Notes (S4 review findings)

The following gaps and clarifications should be addressed before/during S4 implementation:

**S4.1 - Schema clarifications applied**:
- RC mapping simplified: skips are rc=`0` (success), not `10`. Reserve `127` for tool-missing, `4` for collection error, `1` generic failure. Note: existing code may still emit `10`; migrate in S4.5.
- Status meanings documented:
  - `skip_no_tests`: project present but test suite absent (treated as success).
  - `skip_not_configured`: drivers/targets not set or feature disabled (treated as success).
  - `skip_tool_missing`: tooling missing but optional path (treated as success with explicit reason).
- `tools_present` is a map per tool, e.g.:
  ```json
  "tools_present": {"pytest": true, "jest": false, "idf.py": false}
  ```

S4.1 — Status schema (final)

Shared status item (per area):
```json
{
  "area": "backend|web|embedded",
  "executed": true,
  "rc": 0,
  "status": "run_pass|run_fail|skip_no_tests|skip_tool_missing|skip_not_configured|error_collection|error_other",
  "reason": "string or null",
  "tools_present": {"pytest": true, "jest": false, "idf.py": false},
  "logs": ["artifacts/.../backend_fastapi_test.log"]
}
```

Dev summary (dev_summary.json):
```json
{
  "version": 1,
  "timestamp": "2025-11-24T12:00:00Z",
  "drivers": [
    {
      "area": "backend",
      "id": "fastapi",
      "tools_present": {"pytest": true},
      "commands": {
        "test": {"attempted": true, "rc": 0, "log": "artifacts/dev/S1/run-.../backend_fastapi_test.log"},
        "lint": {"attempted": true, "rc": 0, "log": "artifacts/dev/S1/run-.../backend_fastapi_lint.log"}
      }
    },
    {
      "area": "web",
      "id": "next_js",
      "tools_present": {"npm": true, "jest": false},
      "commands": {
        "build": {"attempted": true, "rc": 0, "log": ".../frontend_next_js_build.log"},
        "test": {"attempted": false, "rc": 0, "log": null}
      }
    }
  ]
}
```

QA summary (qa_summary.json):
```json
{
  "version": 1,
  "timestamp": "2025-11-24T12:05:00Z",
  "areas": {
    "backend": {"area": "backend", "executed": true,  "rc": 0,   "status": "run_pass",          "reason": null, "tools_present": {"pytest": true}, "logs": ["artifacts/qa/S1/backend_fastapi_test.log"]},
    "web":     {"area": "web",     "executed": false, "rc": 0,   "status": "skip_tool_missing", "reason": "Jest not installed", "tools_present": {"jest": false}, "logs": []},
    "embedded":{"area": "embedded","executed": false, "rc": 0,   "status": "skip_not_configured","reason": "No embedded target", "tools_present": {"idf.py": false, "west": false}, "logs": []}
  }
}
```

RC mapping (final): `0` success (including skip_*), `1` generic failure, `4` collection-error, `127` tool-missing.

**S4.2 - Naming**:
- Adopt `dev_summary.json` (replace previous preqa_ naming) for Dev-only summary.

**S4.3 - Make target**:
- `make qa-summary` must work without jq; add fallback to python json.tool:
  ```makefile
  @if command -v jq >/dev/null 2>&1; then jq . ...; else python -m json.tool ...; fi
  ```
- Multiple stories: define behavior when `artifacts/qa/` contains multiple story directories.
  - Behavior: if STORY env var is set, show that story; else pick the most recent `artifacts/qa/*/qa_summary.json` by mtime.

**S4.4 - Current state audit**:
- `[DEV]` and `[QA]` prefixes existen pero no siguen el patrón propuesto; se estandariza solo para nuevos mensajes y summaries.
- Área: usar `backend|web|embedded` de forma consistente en summaries. En logs existentes, mantener backward‑compat por ahora; alinear mensajes en S4.4 cuando sea seguro.

**S4.5 - Code alignment**:
- Cambiar retornos `10` por `0` para estados de skip en Dev/QA donde no representen error real.
- Alinear nomenclatura de área a `web` (no `frontend`) en nuevos mensajes y summaries.

---

### BUG-S1-001: test_smoke_health_route falla cuando fastapi no está instalado

**Severity**: Low (test debería skip, no fail)

**Reproduction**:
```bash
PYTHONPATH=project/backend-fastapi .venv/bin/pytest -v project/backend-fastapi/tests/test_smoke.py
# test_smoke_imports: SKIPPED (correcto)
# test_smoke_health_route: FAILED - ModuleNotFoundError: No module named 'fastapi.testclient'
```

**Cause**: `test_smoke_health_route` hace `from fastapi.testclient import TestClient` en línea 43 sin guard try/except. Cuando fastapi no está instalado, el test falla en vez de skip.

**Affected file**: `project/backend-fastapi/tests/test_smoke.py:43`
```python
def test_smoke_health_route():
    from fastapi.testclient import TestClient  # Sin guard - falla si fastapi no está
```

**Expected behavior**: El test debería hacer `pytest.skip()` con mensaje claro cuando fastapi no está disponible, igual que `test_smoke_imports`.

**Fix required**: Llamar a `_load_app()` primero (que ya tiene el guard), o agregar try/except al import:
```python
def test_smoke_health_route():
    app = _load_app()  # Esto hace skip si fastapi no está disponible
    from fastapi.testclient import TestClient
    # ...
```

**Status**: Fixed
**Resolution**: Ajustado el test para llamar primero a `_load_app()` (que salta con skip si falta FastAPI). Se mueve el import de `TestClient` después de `_load_app()`. Validado: `2 skipped` cuando FastAPI no está instalado.

---

### BUG-S2-001: Web smoke test no verificable - falta package.json con Jest

**Severity**: Medium (S2 no puede ser verificado funcionalmente)

**Reproduction**:
```bash
cd project/web-express && npm test -- --passWithNoTests
# Error: ENOENT: no such file or directory, open '.../project/web-express/package.json'
```

**Cause**: `project/web-express/` no tiene `package.json` con Jest configurado. Sin esto, no se puede ejecutar `npm test` para verificar que `smoke.test.js` hace skip correctamente cuando no hay entry points.

**Current state**:
- `project/web-express/tests/smoke.test.js` existe (39 líneas, lógica correcta)
- `project/web-express/src/` solo tiene `.gitkeep` (sin entry points)
- `project/web-express/package.json` no existe

**Expected**: Un `package.json` mínimo con Jest para poder ejecutar y verificar el comportamiento de skip.

**Fix required**: Agregar `project/web-express/package.json` con configuración mínima de Jest:
```json
{
  "name": "web-express",
  "version": "0.0.1",
  "scripts": {
    "test": "jest"
  },
  "devDependencies": {
    "jest": "^29.0.0"
  }
}
```

**Status**: Fixed
**Resolution**:
- Se agregó `project/web-express/package.json` con script `test: jest` y devDependency `jest`.
- QA runner detecta si `node_modules/.bin/jest` no existe y hace skip con razón clara (evita falsos negativos cuando no se instaló Jest). Cuando Jest esté instalado, `npm test -- --passWithNoTests` se ejecutará normalmente.

---

### BUG-S3-001: Make targets qa-smoke/dev-smoke muestran error confuso cuando Jest no está instalado

**Severity**: Low (funciona pero mensaje no es claro)

**Reproduction**:
```bash
make qa-smoke
# ==> QA Smoke: web-express
# > web-express@0.0.1 test
# > jest --passWithNoTests
# sh: jest: command not found
```

**Cause**: Los Make targets `qa-smoke` y `dev-smoke` ejecutan `npm test` directamente sin verificar si Jest está instalado. El `|| true` hace que el target no falle, pero el mensaje `jest: command not found` es confuso comparado con el skip limpio que hace `run_qa.py`.

**Current behavior**: Error críptico `sh: jest: command not found` seguido de continuación silenciosa.

**Expected behavior**: Mensaje claro como `(skip) Jest not installed in web-express` similar al backend.

**Fix required**: Agregar guard en Makefile similar al de `run_qa.py`:
```makefile
qa-smoke:
	# ...
	@if [ -f project/web-express/package.json ]; then \
		if [ -x project/web-express/node_modules/.bin/jest ]; then \
			cd project/web-express && npm test -- --passWithNoTests || true; \
		else \
			echo "(skip) Jest not installed in web-express"; \
		fi \
	else \
		echo "(skip) web-express package.json not present"; \
	fi
```

**Status**: Fixed
**Resolution**: Añadido guard en Makefile para comprobar `project/web-express/node_modules/.bin/jest` antes de ejecutar `npm test`. Si no existe, muestra `(skip) Jest not installed in web-express)` y no imprime `sh: jest: command not found`.

---

### BUG-S4.2-001: dev_summary.json usa paths absolutos en lugar de relativos

**Severity**: Low (funciona pero menos portable)

**Location**: `scripts/run_dev.py:606,610,632,637,641`

**Current behavior**:
```python
"log": str((run_dir / f"{name}.log"))
# Produces: "/Users/.../agnostic-ai-pipeline/artifacts/dev/S1/run-20251124.../backend_fastapi_test.log"
```

**Expected behavior** (per schema):
```json
"log": "artifacts/dev/S1/run-.../backend_fastapi_test.log"
```

**Cause**: La implementación usa `str(run_dir / f"{name}.log")` que genera path absoluto. El schema documentado muestra paths relativos al repo root.

**Impact**:
- Los paths absolutos funcionan pero son menos portables entre máquinas.
- Si el summary se comparte o se usa en CI, los paths no serán válidos en otro entorno.

**Fix required**: Usar paths relativos al ROOT del proyecto:
```python
"log": str((run_dir / f"{name}.log").relative_to(ROOT))
```

**Status**: Open
