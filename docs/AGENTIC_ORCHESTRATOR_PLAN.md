# Agentic Orchestrator Integration Plan

Plan para incorporar un orquestador agentic como rol que coordine BA→PO→Architect→Dev↔QA, enmascarando incoherencias de estado del pipeline y preservando los flujos actuales (`make iteration`, `make loop`, roles individuales).

## Objetivo
- Habilitar un orquestador LLM que decida la siguiente acción por iteración y por historia, con bucles acotados, usando `execute_role` y sin romper las entradas existentes.
- Reducir incoherencias de pipeline: sincronizar estado de historias, artefactos (`planning/`, `artifacts/`), y resultados QA/Dev para evitar desalineaciones entre pasos.

## Éxito medible
- Nuevo comando `python -m scripts.run_orchestrator_agent --concept "...")` y objetivo Make (`agentic-iteration`) funcionando sin alterar `iteration/loop`.
- Generación de resumen final `artifacts/iterations/latest_orchestrator_summary.json` con concepto, historias y estado QA/Dev.
- Orquestador detiene en `should_stop` o `max_steps`, con manejo robusto de JSON inválido y acciones desconocidas.

## Alcance
- En alcance: runtime agentic (`scripts/run_orchestrator_agent.py`), prompt placeholder (`prompts/orchestrator.md`), mapeo de herramientas→roles, estado en memoria, límites (`max_steps`, `max_actions_per_step`), logging/metrics (`a2a.metrics.save_metrics`), Make target.
- Fuera de alcance: rediseño de prompts de roles, cambio de contratos en `execute_role`, migración total de `make iteration` (se mantiene legacy por defecto).

## Entregables
- `scripts/run_orchestrator_agent.py` con CLI (Typer/argparse), carga de config (`load_config`), `ensure_dirs`, envoltura `DualWriteContext` si DB activo, cliente `llm.Client(role="orchestrator")`.
- `prompts/orchestrator.md` (placeholder inicial).
- Lazo agentic asíncrono que arma contexto compacto, llama LLM, valida JSON, aplica `state_update`, despacha `next_actions` vía `execute_role`, persiste resumen final.
- Tabla de mapeo de herramientas a roles (`RUN_BA/PO/ARCHITECT/DEV_STORY/QA_STORY/QA_FULL`) con normalización de estatus.
- Objetivo `agentic-iteration` en `Makefile`.

## Enfoque por fases
1) **Fundación runtime**: crear módulo, CLI (`--concept`, `--max-steps`, `--max-actions-per-step`), carga config, `ensure_dirs`, `DualWriteContext` opcional, `llm.Client` con prompt.
2) **Modelo de estado**: mantener `concept`, presencia/timestamps de `planning/requirements.yaml` y `planning/stories.yaml`, historias (id, status todo/in_progress/done/failed, error), últimos QA/Dev, acciones recientes.
3) **Bucle agentic**: construir contexto resumido (no archivos completos), invocar LLM, validar/reparar JSON (reintentos), aplicar `state_update`, ejecutar hasta `max_actions_per_step`, acumular resultados y errores, romper en `should_stop` o `max_steps`.
4) **Despacho de herramientas**: mapear acciones a `execute_role` con payloads requeridos, logging envolvente, normalizar `status` (`ok/error/failed/tests_failed/exception`) y propagar a estado de historias.
5) **Artefactos y observabilidad**: escribir `artifacts/iterations/latest_orchestrator_summary.json` (concept, historias, QA/Dev, riesgos, límites alcanzados), llamar `a2a.metrics.save_metrics()` al final, conservar logs.
6) **Integración CLI/Make**: añadir target `agentic-iteration` que usa `.venv/bin/python -m scripts.run_orchestrator_agent --concept "$${CONCEPT}"`; mantener `iteration/loop` intactos, opción futura `ORCHESTRATOR_MODE=agentic` sin cambiar default.
7) **QA rápida**: prueba manual con concepto corto y `--max-steps 2`, verificar artefactos y que roles se disparan; opcional smoke `make loop MAX_LOOPS=1` para asegurar que no se rompen flujos legacy.

## Mapeo herramientas → roles
- `RUN_BA` → `execute_role("business_analyst", {"concept": concept, ...})`.
- `RUN_PO` → `execute_role("product_owner", payload opcional)`.
- `RUN_ARCHITECT` → `execute_role("architect", {"concept": concept?, "architect_mode":?, "story_id":?, "detail_level":?})`.
- `RUN_DEV_STORY` → `execute_role("developer", {"story_id": "...", "retries":?})`.
- `RUN_QA_STORY` → `execute_role("qa", {"story_id": "...", "allow_no_tests": true/false})`.
- `RUN_QA_FULL` → `execute_role("qa", {"allow_no_tests": true/false, "story_id": ""})`.

## Coherencia y guardrails
- Validar JSON del orquestador; si inválido, log y reintento con mensaje de reparación; abortar con resumen claro tras agotar reintentos.
- Ignorar acciones desconocidas con warning; evitar loops infinitos con límites configurables.
- Propagar fallos de roles al estado (errores Dev/QA) para que el orquestador pueda reintentar o escalar a Architect.
- No romper rutas existentes: conservar `scripts/orchestrate.py` y `execute_role` como única capa de ejecución; cambios son aditivos.

## Pruebas mínimas
- Ejecución manual: `python -m scripts.run_orchestrator_agent --concept "demo" --max-steps 2 --max-actions-per-step 2`.
- Verificar creación y contenido básico de `artifacts/iterations/latest_orchestrator_summary.json`.
- Smoke de `make iteration` / `make loop MAX_LOOPS=1` para confirmar que la vía legacy sigue operativa.
- ✅ **Smoke test automatizado**: `tests/smoke/test_agentic_orchestrator.py` con 5 tests incrementales:
  1. **Trivial** (max_steps=1, max_actions=1, timeout=5min): Validación básica de inicialización
  2. **Simple** (max_steps=2, max_actions=2, timeout=5min): BA → PO con validación de requirements.yaml
  3. **Moderado** (max_steps=3, max_actions=3, timeout=5min): BA → PO → Architect con validación de stories.yaml
  4. **Pipeline completo** (max_steps=6, max_actions=2, timeout=15min): BA → PO → Architect → Dev → QA con validación de todos los artifacts y ejecución de código. NOTA: Puede tardar 10-15 minutos.
  5. **Cleanup**: Verificación de limpieza y regeneración

## Riesgos y mitigaciones
- **Salida JSON inválida del LLM**: reintentos + mensaje de reparación; abortar limpio.
- **Estado inconsistente de historias**: normalizar `status` y forzar lectura de `planning/stories.yaml` al inicio de cada paso; actualizar estado interno tras cada Dev/QA.
- **Consumo excesivo de tokens**: contexto resumido (no archivos completos) y límites de acciones.
- **DB no disponible**: `DualWriteContext` opcional; degradar a no-op.

## Próximo paso (desacople legacy)
- Planificar eliminación o apagado gradual del orquestador legacy (`scripts/orchestrate.py` / `make iteration/loop`) una vez el agentic esté estable: definir flag de conmutación, ventana de deprecación y migración de tests a la ruta agentic.

### Plan de deprecación del orquestador legacy
- Fase 0 (ahora): mantener `iteration/loop` legacy como default; agentic via `make agentic-iteration`. Publicar nota de deprecación en README/AGENTS indicando nuevo camino.
- Fase 1 (opt-in): agregar flag `ORCHESTRATOR_MODE=agentic` en `scripts/run_iteration.py`/`make iteration` que seleccione `run_orchestrator_agent` sin romper default. Añadir pruebas de modo agentic en CI.
- Fase 2 (opt-out): cambiar default a agentic, manteniendo legacy detrás de `ORCHESTRATOR_MODE=legacy`. Marcar legacy como deprecated en help/README; mover tests principales al modo agentic, dejar smoke minimal del legacy.
- Fase 3 (remoción): retirar `scripts/orchestrate.py` y targets `loop/iteration` legacy; limpiar referencias en docs/tests; consolidar un único flujo (agentic) y migrar métricas/DB hooks si falta algo.
- Validaciones: asegurar paridad funcional (BA→PO→Architect→Dev↔QA), preservar métricas `a2a`, DualWrite, y artefactos (`planning/`, `artifacts/iterations/`). Mantener rollback fácil (tag/branch) durante la ventana de opt-out.
