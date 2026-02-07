# Auditoría Externa — Fase 1 Graph RAG (LightRAG)

**Fecha**: 2026-02-06  
**Rol auditor**: Arquitecto externo / evaluador de calidad  
**Alcance**: Validación de implementación real vs plan F1 en `PLAN_implementation_distilabel_finetuning_rag.md` y contraste con `AUDIT_PHASE1_GRAPH_RAG.md`.

---

## 1) Resumen ejecutivo

La implementación de Fase 1 es **funcional a nivel base** (módulos creados, integración con `scripts/llm.py`, targets de Makefile, dependencias separadas). Sin embargo, la evidencia técnica no soporta varias afirmaciones de “production-ready” del informe interno.

**Veredicto externo**: **APROBACIÓN CONDICIONAL** (no “aprobado para producción” todavía).  
Hay brechas relevantes en: cumplimiento exacto del plan, testabilidad E2E real, control de costos/tokens, y robustez operativa.

---

## 2) Hallazgos priorizados

## H-01 (ALTO) — Política `top_k` por rol no se aplica realmente

**Evidencia**
- `graph_rag/retrieval.py` define `ROLE_POLICIES` con `top_k` por rol.
- `AgentRetriever.retrieve_for_role()` solo pasa `mode` a engine.
- `graph_rag/engine.py` usa `top_k` global desde config (`self.config.get("top_k", 60)`).

**Impacto**
- La personalización por rol queda incompleta.
- Riesgo de sobre-contexto (más tokens, más latencia/costo) o infra-contexto (peor calidad).

**Recomendación**
1. Extender API de engine para aceptar `top_k` por query.
2. Pasar `policy["top_k"]` desde `AgentRetriever`.
3. Añadir test unitario que valide variación real de `top_k` por rol.

---

## H-02 (ALTO) — `make rag-query MODE=...` no respeta `MODE`

**Evidencia**
- En `Makefile`, target `rag-query` define `MODE=$${MODE:-mix}`.
- Pero el comando ejecuta `retriever.retrieve_for_role('architect', '$$QUERY')` sin override de modo.

**Impacto**
- La CLI induce a error: parece configurable, pero ignora `MODE`.
- Dificulta pruebas y diagnósticos de retrieval mode.

**Recomendación**
1. Pasar override explícito de policy/mode en `rag-query`.
2. Incluir test smoke CLI para validar que `MODE=hybrid`/`MODE=local` cambia comportamiento.

---

## H-03 (ALTO) — Cobertura E2E insuficiente; criterios de aceptación “simulados”

**Evidencia**
- `tests/test_graph_rag_e2e.py` tiene test principal E2E `skipped`.
- `test_acceptance_criteria_f1t7` y `test_graph_rag_advantages` hacen `assert True` (validación documental, no técnica).
- En `tests/test_graph_rag_engine.py` hay pruebas clave de retrieval también `skipped`.

**Impacto**
- No hay evidencia automatizada robusta para sustentar readiness productivo.
- Riesgo de regresiones ocultas.

**Recomendación**
1. Separar explícitamente tests “contractuales” (deben correr en CI) y tests “manuales”.
2. Reemplazar asserts triviales por verificaciones reales (ingest→query→relación esperada).
3. Definir perfil de CI para tests Graph RAG con marker y entorno reproducible.

---

## H-04 (MEDIO-ALTO) — Graph RAG habilitado por defecto (`enabled: true`) sin budget guard

**Evidencia**
- `config.yaml` activa `graph_rag.enabled: true`.
- `scripts/llm.py` inyecta contexto en **todas** las llamadas `chat()` cuando está habilitado.
- No existe límite explícito de longitud de contexto previo a inyección.

**Impacto**
- Riesgo de aumento de latencia/costo/tokens en todo el pipeline.
- Potencial degradación por prompts excesivos.

**Recomendación**
1. Cambiar estrategia operativa a “opt-in controlado” por entorno/rol.
2. Introducir presupuesto de contexto (char/token cap + truncado jerárquico).
3. Añadir telemetría mínima: tamaño de contexto inyectado, latencia extra por rol.

---

## H-05 (MEDIO) — `auto_ingest` declarado pero no orquestado

**Evidencia**
- `config.yaml` declara `graph_rag.auto_ingest: true`.
- No se observa hook real de auto-ingest tras cada step del pipeline (solo `make rag-index` y métodos disponibles).

**Impacto**
- Riesgo de KG desactualizado respecto a artefactos recientes.
- Promesa funcional incompleta frente al plan F1-T5.

**Recomendación**
1. Definir contractualmente dónde ocurre el auto-ingest (post-step hooks).
2. Si no está implementado, marcar feature como “manual indexing” para no sobreprometer.
3. Añadir test de actualización incremental post artefacto nuevo.

---

## H-06 (MEDIO) — `GraphRAGConfig` infrautilizado y riesgo de drift de configuración

**Evidencia**
- Existe `graph_rag/config.py`, pero `scripts/llm.py` consume `load_config()` directo y diccionarios crudos.
- Hay defaults duplicados/dispersos entre engine/config.yaml/config module.

**Impacto**
- Mayor riesgo de inconsistencias de runtime.
- Mantenimiento más costoso.

**Recomendación**
1. Consolidar fuente de verdad de configuración.
2. Validar esquema de config al inicio (campos, tipos, rangos).
3. Eliminar defaults redundantes o documentar precedencia exacta.

---

## H-07 (MEDIO) — Deduplicación por hash de contenido puede perder trazabilidad de fuente

**Evidencia**
- `PipelineIngestion` deduplica por hash de contenido global (`md5(content)`).
- Dos archivos distintos con mismo contenido se consideran duplicados.

**Impacto**
- Puede perderse contexto de procedencia múltiple (source diversity).
- Menor riqueza de relaciones en KG en casos límite.

**Recomendación**
1. Usar clave de dedup compuesta (path + hash) o política configurable.
2. Mantener mapa de “múltiples fuentes” para mismo contenido.

---

## H-08 (MEDIO) — Inconsistencias de naming de modelo Ollama

**Evidencia**
- Se mezclan variantes `qwen2.5-coder:7b` y `qwen2.5:7b-instruct` entre módulos/documentación.

**Impacto**
- Errores operativos evitables en setup y runbooks.

**Recomendación**
1. Normalizar naming por entorno y documentar alias válidos.
2. Agregar validación temprana y mensaje de remediación consistente.

---

## 3) Cumplimiento vs Fase 1 del plan (visión externa)

| Tarea F1 | Estado externo | Observación |
|---|---|---|
| F1-T1 Setup LightRAG | Parcialmente OK | Setup existe, pero evidencia automatizada no totalmente robusta en CI |
| F1-T2 Engine wrapper | OK con reservas | Funcional, pero faltan controles finos y coherencia config |
| F1-T3 Ingestion incremental | OK con reservas | Incremental existe; dedup/trazabilidad mejorable |
| F1-T4 Retrieval adapter | Parcial | Falta aplicar `top_k` por rol realmente |
| F1-T5 Integración LLM | Parcial | Integrado, pero sin budget guard y con enable global agresivo |
| F1-T6 Make targets | Parcial | `rag-query MODE` no efectivo |
| F1-T7 E2E + aceptación | No suficiente | Tests clave skipeados / asserts triviales |

---

## 4) Riesgo operativo actual

**Nivel global**: **MEDIO**  
Motivo: el feature funciona, pero la evidencia de calidad/robustez está por debajo de lo exigible para “production-ready”.

---

## 5) Plan de remediación sugerido (sin implementar)

### Sprint R1 (rápido, alto impacto)
1. Corregir paso efectivo de `top_k` por rol.
2. Corregir `Makefile rag-query` para respetar `MODE`.
3. Incorporar límite de contexto inyectado en `chat()` (budget guard).

### Sprint R2 (calidad y confiabilidad)
1. Reescribir tests E2E para validación técnica real (sin `assert True`).
2. Activar pipeline CI de pruebas Graph RAG con markers.
3. Formalizar comportamiento de `auto_ingest` (o desactivar claim/documentarlo como manual).

### Sprint R3 (hardening)
1. Unificar capa de configuración con validación de esquema.
2. Mejorar estrategia de deduplicación para preservar trazabilidad.
3. Normalizar naming de modelos y runbook de setup.

---

## 6) Recomendación final del auditor externo

No bloquearía el avance a Fase 2, **pero sí condicionaría** el uso extendido de Fase 1 a cerrar al menos H-01, H-02 y H-03 antes de considerar “listo para producción”.

---

## 7) Nota metodológica

Esta auditoría se realizó sobre evidencia estática (código, tests, Makefile, config y reporte interno) sin modificar implementación, cumpliendo la restricción solicitada.

---

## 8) Análisis adicional solicitado: complejidad ciclomática y grado de mocks

### 8.1 Métricas objetivas de complejidad ciclomática (CC)

Se calculó CC por función sobre los módulos implementados en Fase 1 y sus tests.

#### Código Fase 1 (Graph RAG)

| Archivo | Función más compleja | CC máx | Evaluación |
|---|---:|---:|---|
| `graph_rag/engine.py` | `query`, `get_context_only`, `finalize`, `get_instance` | 5 | Aceptable |
| `graph_rag/ingestion.py` | `_ingest_directory` | 8 | Moderada (hotspot) |
| `graph_rag/retrieval.py` | `retrieve_for_role` | 6 | Moderada |

**Lectura técnica**:
- El núcleo Graph RAG está en rango **aceptable a moderado**.
- El principal punto de deuda es `_ingest_directory` (CC=8), candidato a particionar.

#### Integración en cliente LLM

| Archivo | Función | CC | Observación |
|---|---:|---:|---|
| `scripts/llm.py` | `__init__` | 61 | Deuda estructural alta (preexistente) |
| `scripts/llm.py` | `_cli_chat_async` | 55 | Deuda estructural alta (preexistente) |
| `scripts/llm.py` | `_cli_chat` | 53 | Deuda estructural alta (preexistente) |
| `scripts/llm.py` | `_augment_with_graph_rag` | 7 | Moderada, no crítica |

**Lectura técnica**:
- La complejidad alta está concentrada en `scripts/llm.py` y no invalida Fase 1, pero sí incrementa riesgo de regresión en integración.

#### Tests Fase 1

Las pruebas de Fase 1 presentan CC baja (1-3) en general, lo cual es correcto para tests legibles.

---

### 8.2 Grado de mocking observado (criterio: mock sólo para externos/complejos)

#### Conteo por archivo

| Archivo de test | #tests | refs a mocks | fixtures mock | skipped |
|---|---:|---:|---:|---:|
| `tests/test_graph_rag_engine.py` | 6 | 0 | 0 | 2 |
| `tests/test_graph_rag_ingestion.py` | 3 | 3 | 1 | 0 |
| `tests/test_graph_rag_retrieval.py` | 6 | 4 | 1 | 0 |
| `tests/test_graph_rag_e2e.py` | 3 | 0 | 0 | 1 |

#### Juicio de auditoría sobre mocks

1. **Mock aceptable (externo/complejo)**
   - Mock de engine/Ollama/LightRAG en tests unitarios rápidos para evitar dependencia de servicio externo y asincronía costosa.

2. **Mock discutible (lógica del sistema)**
   - En `test_graph_rag_retrieval.py`, el mock del engine impide verificar completamente el contrato real `policy -> llamada efectiva -> parámetros reales`.
   - En `test_graph_rag_ingestion.py`, el mock de `engine.ingest` simplifica exceso y reduce validación del flujo de negocio de ingestión.

3. **Cobertura real insuficiente complementaria**
   - Hay tests E2E relevantes en `skip`, por lo que la dependencia en mocks queda menos compensada por pruebas reales de integración.

**Conclusión de cumplimiento del criterio solicitado**:
- **Parcialmente cumple**: se mockean bien servicios externos, pero también hay mock de lógica/proceso interno en más medida de la deseable.

---

### 8.3 Matriz de cumplimiento (mock policy)

| Test / bloque | Clasificación |
|---|---|
| `test_graph_rag_engine.py` (sin mocks) | ✅ Adecuado |
| `test_graph_rag_ingestion.py::test_ingest_artifact_tags_metadata` (mock engine) | ⚠️ Discutible |
| `test_graph_rag_retrieval.py` (mock engine generalizado) | ⚠️ Discutible |
| `test_graph_rag_e2e.py` (sin mocks pero skip parcial) | ⚠️ Incompleto |

---

### 8.4 Recomendaciones concretas (sin implementar)

1. Mantener mocks **solo** en frontera externa (Ollama/LightRAG/red).  
2. Reemplazar al menos 2 tests de `retrieval` y 1 de `ingestion` por integración local real.  
3. Reducir `skip` de E2E críticos con marker de integración y entorno reproducible.  
4. Objetivo de complejidad para nuevo código: ideal `CC <= 5`, warning `6-10`, justificar >10.  
5. Plan de refactor acotado para `_ingest_directory` y `retrieve_for_role` para simplificar ramificación.
