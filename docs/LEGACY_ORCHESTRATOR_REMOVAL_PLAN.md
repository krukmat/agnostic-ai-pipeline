# Plan de Remoción del Orquestador Legacy (`scripts/orchestrate.py`)

Objetivo: retirar el orquestador legacy y el target `loop` del Makefile, migrando todo a la ruta agentic (`scripts/run_orchestrator_agent.py`) sin perder cobertura ni funcionalidades.

## Alcance
- En alcance: eliminar `scripts/orchestrate.py` y target `loop`, actualizar scripts que dependan de él (p.ej. `spike`), migrar tests `tests/scripts/test_orchestrate_*.py` a la ruta agentic o retirarlos si duplicados, ajustar docs/README.
- Fuera de alcance: reescritura profunda de roles BA/PO/Architect/Dev/QA o cambios en sus contratos; cambios en DB beyond wiring ya existente.

## Fases y tareas
1) **Inventario y redirección inicial**
   - Identificar todos los callsites de `scripts/orchestrate.py` y del target `loop` (incluye `spike` en Makefile y scripts auxiliares).
   - Decidir estrategia: stub temporal que delegue al agentic vs. eliminación directa. Preferible stub corto que llame a `run_orchestrator_agent` para mantener compatibilidad durante migración de tests.
2) **Migración de tests**
   - Reescribir o eliminar los `tests/scripts/test_orchestrate_*.py`:
     - Convertir casos de flujo/estado a usar `run_orchestrator_agent` (mockeando LLM y `execute_role`).
     - Retirar pruebas redundantes con el nuevo runtime.
   - Asegurar que nuevas pruebas cubran equivalentes: batch de historias, skips QA, modos local/remote (si aplica en agentic).
   - Listado de tests legacy a eliminar/migrar:
     - `test_orchestrate_analysis.py`, `test_orchestrate_deps.py`, `test_orchestrate_execute.py`, `test_orchestrate_flow_core.py`, `test_orchestrate_flow_stub.py`, `test_orchestrate_handlers.py`, `test_orchestrate_iteration_stub.py`, `test_orchestrate_more.py`, `test_orchestrate_process_story.py`, `test_orchestrate_process_story_branches.py`, `test_orchestrate_utils_light.py`, `test_orchestrate_wipe.py`.
   - Nuevos tests agentic a crear para mantener cobertura:
     - Cobertura de `execute_role`/drivers (mover a un módulo utilitario o mantener stub reducido) para reemplazar `test_orchestrate_execute.py`.
     - Cobertura de flujo básico de historias y estados en `run_orchestrator_agent` (batch, skip QA/dev errors) para reemplazar `test_orchestrate_flow_*` y `process_story*`.
     - Cobertura de manejo de dependencias/artifacts (equivalente a `wipe`/`analysis`) bajo el nuevo runtime o utilidades compartidas.
3) **Makefile y CLI**
   - Quitar target `loop` y referencias (`spike`); añadir mensaje de deprecación o redirección a `agentic-iteration`.
   - Asegurar que `run_iteration.py` siga siendo el entrypoint único (ya agentic).
4) **Depuración final**
   - Eliminar `scripts/orchestrate.py` o dejar stub con aviso que llama a `run_orchestrator_agent` (si se requiere periodo de gracia).
   - Limpiar helpers/fixtures específicos del legacy no usados por agentic.
   - Actualizar README/AGENTS con el nuevo flujo único agentic.

## Validación
- `./.venv/bin/pytest -q` pasando con las pruebas migradas (sin suites legacy).
- Smoke manual: `make agentic-iteration CONCEPT="demo" MAX_STEPS=1 MAX_ACTIONS=1` y verificación de `artifacts/iterations/latest_orchestrator_summary.json`.
 - Comparar cobertura antes/después: asegurar que las nuevas pruebas agentic cubren funciones equivalentes (manejo de drivers, estado de historias, reparación de JSON, persistencia de artefactos).

## Riesgos y mitigaciones
- **Ruptura de CI por eliminación de tests legacy**: migrar gradualmente con stub de compatibilidad para evitar caída total; coordinar actualización de pipelines que invoquen `loop`.
- **Dependencias ocultas del target `loop`**: buscar referencias en scripts/CI antes de eliminar y proveer mensaje de redirección.
- **Pérdida de cobertura**: crear equivalentes agentic para los comportamientos críticos que validaban los tests legacy (estado de historias, skip QA, modos).
