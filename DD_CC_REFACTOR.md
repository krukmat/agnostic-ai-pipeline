# DD — Refactor Prioritario por Complejidad y Centralidad

**Fecha**: 2026-02-08  
**Base**: `CC_TD.md`  
**Autoría**: enfoque conjunto de arquitectura + desarrollo senior

---

## 1) Contexto

El análisis en `CC_TD.md` muestra:

- Complejidad promedio saludable del branch (**A=4.50**).
- Hotspots críticos concentrados en módulos core con alta centralidad:
  - `scripts/orchestrate.py::_process_story` (**E37**)
  - `scripts/orchestrate.py::analyze_qa_failure_severity` (**D29**)
  - `scripts/llm.py::Client._parse_cli_json_output` (**D27**)

Conclusión: el riesgo principal no está en `graph_rag/*` ni `training/*`, sino en piezas legacy del runtime.

---

## 2) Decisión arquitectónica

Se aprueba una estrategia de refactor **incremental y gobernada por riesgo**:

1. Atacar primero hotspots con mayor combinación de:
   - complejidad ciclomática,
   - fan-in/fan-out,
   - criticidad en path BA→PO→Architect→Dev→QA.
2. Evitar big-bang refactor.
3. Mantener compatibilidad funcional por iteraciones (PRs pequeños + tests de regresión).

---

## 3) Alcance

### Incluye
- `scripts/orchestrate.py` (flujo de story processing)
- `scripts/llm.py` (parsing y flujo CLI)
- Gates de calidad en CI para complejidad

### Excluye (por ahora)
- Refactor de `graph_rag/*`
- Refactor de `training/*`
- Rediseño funcional de negocio (solo calidad estructural)

---

## 4) Plan por fases (PR-driven)

## Fase 1 (P0): `scripts/orchestrate.py::_process_story`

**Objetivo**: bajar de **E(37)** a **C/B**.

### Diseño
- Extraer en unidades puras:
  - `resolve_story_state_transition(...)`
  - `resolve_model_strategy(...)`
  - `handle_qa_feedback(...)`
  - `persist_story_outcomes(...)`

### Criterios de aceptación
- No cambia comportamiento observable del pipeline.
- Cobertura de tests igual o mejor.
- CC de `_process_story` <= 20 (ideal <=10 en iteraciones posteriores).

---

## Fase 2 (P1): parser y normalización CLI en `scripts/llm.py`

**Objetivo**: reducir riesgo sistémico de parseo multi-provider.

### Diseño
- Extraer parser a módulo dedicado (ej. `scripts/llm_cli_parser.py`).
- Estandarizar contract de salida intermedia (`normalized_cli_response`).
- Centralizar mapeo de errores estructurados.

### Criterios de aceptación
- `_parse_cli_json_output` baja de D a C/B.
- Sin regresión en providers CLI actuales.

---

## Fase 3 (P1): consolidación `_cli_chat` y `_cli_chat_async`

**Objetivo**: reducir duplicación y ramas de error.

### Diseño
- Core común de construcción de request y post-proceso.
- Wrappers sync/async livianos.

### Criterios de aceptación
- Reducción de CC en ambos métodos.
- Menor duplicación, igual semántica de fallback/retry.

---

## Fase 4 (Governance): gate de complejidad en CI

### Regla mínima
- Bloquear nuevos bloques **E/F**.
- Permitir **D** solo con justificación + issue de remediación.

### Regla objetivo (mediano plazo)
- Tender a C/B en módulos core.

---

## 5) Riesgos y mitigación

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Regresión funcional en orquestación | Alto | Refactor por extracción + tests de snapshot/flujo |
| Incompatibilidad entre providers CLI | Alto | Contract tests por provider + golden fixtures |
| Refactor incompleto deja deuda dispersa | Medio | PRs acotados por objetivo de CC + checklist de salida |

---

## 6) KPIs de éxito

- `scripts/orchestrate.py::_process_story`: E→C/B
- `scripts/llm.py::_parse_cli_json_output`: D→C/B
- Sin caída en test suite existente
- 0 nuevos bloques E/F en archivos tocados

---

## 7) Estado de decisión

**Estado**: Aprobada para ejecución incremental.  
**Siguiente paso recomendado**: ejecutar Fase 1 (PR1) y medir CC post-refactor en pipeline CI.
