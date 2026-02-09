# CC_TD — Cyclomatic Complexity + Technical Debt Prioritization

**Fecha**: 2026-02-08  
**Branch**: `feature/phase2-distilabel-finetuning-2a`  
**Base comparada**: `origin/main` (merge-base)

---

## 1) Objetivo

Documentar una priorización de deuda técnica que no dependa solo de complejidad ciclomática (CC), sino también del **impacto sistémico** de cada módulo mediante referencias externas:

- **Fan-in**: cuántos módulos dependen de ese módulo/función.
- **Fan-out**: cuántas dependencias arrastra.
- **Criticality**: si está en el camino crítico de ejecución runtime.

---

## 2) Metodología

### 2.1 Métricas base

1. **Cyclomatic Complexity (CC)** con `radon cc`.
2. **Severidad por bloque** (A-F):
   - A: 1–5
   - B: 6–10
   - C: 11–20
   - D: 21–30
   - E: 31–40
   - F: 41+

### 2.2 Métricas de impacto estructural

3. **Fan-in (externo)**: cantidad de referencias/imports/llamadas desde otros módulos del repo.
4. **Fan-out**: tamaño y diversidad de dependencias requeridas por el módulo.
5. **Criticality**: peso adicional para módulos del runtime core (`scripts/orchestrate.py`, `scripts/llm.py`).

### 2.3 Score de priorización (propuesto)

```text
PriorityScore =
  0.45 * CC_norm
  + 0.25 * FanIn_norm
  + 0.15 * Criticality
  + 0.10 * FanOut_norm
  + 0.05 * Churn_norm
```

> En esta iteración, el cálculo de CC es cuantitativo (medido) y Fan-in/Fan-out/Criticality se aplican con criterio técnico sobre arquitectura actual.

---

## 3) Resultado de complejidad (medido)

Scope: archivos `*.py` cambiados en el branch vs `origin/main`, excluyendo `tests/`.

- **Archivos analizados**: 29
- **Bloques analizados**: 199
- **Promedio global**: **A (4.50)**

### Hotspots (CC alta)

#### E
- `scripts/orchestrate.py::_process_story` → **E (37)**

#### D
- `scripts/orchestrate.py::analyze_qa_failure_severity` → **D (29)**
- `scripts/llm.py::Client._parse_cli_json_output` → **D (27)**

#### C (más relevantes)
- `scripts/llm.py::Client._cli_chat_async` → **C (20)**
- `scripts/llm.py::Client._cli_chat` → **C (19)**
- `scripts/orchestrate.py::_process_iteration` → **C (20)**
- `scripts/orchestrate.py::recover_yaml_automatic` → **C (19)**

---

## 4) Priorización teniendo en cuenta referencias externas

### P0 — Máxima prioridad

1. `scripts/orchestrate.py::_process_story` (E37)
   - **Por qué**: altísima CC + alto fan-in + camino crítico BA→PO→Arch→Dev→QA.
   - **Riesgo**: regresiones sistémicas y dificultad de testeo por branching complejo.

### P1 — Alta prioridad

2. `scripts/llm.py::_parse_cli_json_output` (D27)
   - **Por qué**: parser central para providers CLI (fan-in alto en flujos de llamada).
   - **Riesgo**: errores de parseo impactan múltiples proveedores.

3. `scripts/llm.py::_cli_chat_async` (C20) y `_cli_chat` (C19)
   - **Por qué**: núcleo de integración provider-agnostic (fan-in/fan-out altos).
   - **Riesgo**: duplicación de lógica de errores/reintentos/formato.

### P2 — Media prioridad

4. `scripts/orchestrate.py::_process_iteration` (C20) y funciones C adyacentes
   - **Por qué**: complejas, pero subordinadas a refactor de `_process_story`.

5. `conftest.py::_missing_optional_deps_for_test` (C14)
   - **Por qué**: fuera del runtime productivo; impacto contenido al entorno de test.

---

## 5) Estado del código nuevo (Fase 1 GraphRAG + Fase 2A Distilabel)

- `graph_rag/*`: predominantemente **A-B**.
- `training/*`: predominantemente **A**, con pico en `BaseSyntheticPipeline.run` **B (8)**.

Conclusión: la deuda de complejidad **no** se concentra en lo nuevo de Fase 1/2A, sino en módulos core preexistentes con alta centralidad.

---

## 6) Plan de remediación incremental

### PR1 (P0)
- Refactorizar `_process_story` en funciones puras por responsabilidad:
  - transición de estado
  - decisión de modelo
  - manejo de QA/reintentos
  - side effects (persistencia/logs)

### PR2 (P1)
- Extraer parser/normalizador CLI de `scripts/llm.py` a módulo dedicado.
- Unificar manejo de errores y shape de respuestas.

### PR3 (P1)
- Consolidar `_cli_chat` + `_cli_chat_async` compartiendo core y aislando transporte.

### PR4 (gobernanza)
- Agregar gate en CI:
  - prohibir nuevos bloques **E/F**
  - permitir **D** solo con justificación y ticket de remediación

---

## 7) Comandos reproducibles

### 7.1 Complejidad ciclomática (scope del branch)

```bash
BASE=$(git merge-base HEAD origin/main)
FILES=$(git diff --name-only $BASE..HEAD -- '*.py' | grep -v '^tests/')
./.venv/bin/python -m radon cc -s -a $(echo "$FILES" | tr '\n' ' ')
```

### 7.2 Referencias externas (aproximación rápida por módulo)

```bash
# fan-in aproximado por importación/uso textual
grep -R "scripts\.orchestrate\|from scripts import orchestrate\|import scripts.orchestrate" -n .
grep -R "scripts\.llm\|from scripts\.llm import\|import scripts.llm" -n .
```

---

## 8) Conclusión

Sí: para priorizar correctamente hay que combinar **CC + referencias externas**.  
Con esa óptica, el orden de trabajo recomendado se mantiene:

1. `scripts/orchestrate.py` (hotspot E, máxima centralidad)
2. `scripts/llm.py` (hotspots D/C, alta centralidad)
3. resto de módulos C/B

El código nuevo de GraphRAG y Distilabel 2A queda en buena posición (A/B) y no requiere intervención urgente por complejidad.
