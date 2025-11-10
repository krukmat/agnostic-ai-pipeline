# Fase 9: Multi-Role DSPy MIPROv2 Optimization - Plan Detallado

**Fecha Inicio**: 2025-11-09
**Branch**: `dspy-multi-role`
**Objetivo**: Extender optimización DSPy MIPROv2 al resto de los roles críticos (Product Owner, Architect, Developer y QA) para cerrar el loop BA→PO→Architect→Dev→QA optimizado end-to-end.
**Precedente**: Fase 8 - BA optimizado con 85.35% score (+13.35% vs baseline 72%)

---

## 📋 Resumen Ejecutivo

### Contexto

Fase 8 demostró que DSPy MIPROv2 es **extremadamente efectivo** para optimización de roles:
- **Tiempo**: 3 horas vs 200+ horas de fine-tuning
- **Score**: 85.35% (mejora de +13.35% vs baseline)
- **Costo**: $0 (100% local con Ollama)
- **Iterabilidad**: Alta (cambios en segundos)

**Decisión**: Extender este enfoque exitoso a los 4 roles restantes del pipeline (Product Owner, Architect, Developer, QA).

### Objetivos Fase 9

1. **Product Owner**: Optimizar consistencia entre requirements DSPy y `product_vision.yaml` + `product_owner_review.yaml`
2. **Architect**: Optimizar generación de historias técnicas (epics → stories)
3. **Developer**: Optimizar generación de código + tests
4. **QA**: Optimizar generación de reportes de calidad

**Meta Global**: Pipeline completo con 5/5 roles optimizados, manteniendo 100% local + $0 costo.

---

## 🎯 Objetivos por Rol

### 9.0 - Product Owner Role Optimization

**Input**: `planning/requirements.yaml` generado por BA DSPy + concepto original (`meta.original_request`)
**Output**: `product_vision.yaml`, `product_owner_review.yaml`

**Complejidad**: ⭐⭐⭐ (Media - requiere juicio de negocio y consistencia narrativa)

**Baseline Esperado**: ~68-72%
**Target Optimizado**: ~85-88%
**Mejora Esperada**: +15-18%

**Métricas Clave**:
- Vision completeness (secciones overview, objetivos, KPIs, riesgos)
- Alignment con requirements (cada requisito clave cubierto en vision o review)
- Review accuracy (aprobación/rechazo justificado, action items)
- YAML validity + consistencia entre vision y review

**Desafíos**:
- Necesidad de inferir stakeholders/personas aunque BA no los provea
- Balance entre creatividad y trazabilidad al concepto
- Mantener formato y tono esperados por `scripts/run_product_owner.py`

---

### 9.1 - Architect Role Optimization

**Input**: Requirements YAML (desde BA)
**Output**: `stories.yaml`, `architecture.yaml`, `epics.yaml`

**Complejidad**: ⭐⭐⭐⭐ (Alta - decisiones arquitectónicas complejas)

**Baseline Esperado**: ~60-65%
**Target Optimizado**: ~80-85%
**Mejora Esperada**: +20-25%

**Métricas Clave**:
- Story completeness (fields: id, title, description, acceptance_criteria, dependencies)
- Story granularity (no demasiado grandes ni pequeñas)
- Architecture validity (componentes, tech stack, patrones)
- Epic coherence (agrupación lógica de stories)

**Desafíos**:
- Output multi-archivo (stories.yaml, architecture.yaml, epics.yaml)
- Dependencias entre stories (orden de implementación)
- Trade-offs arquitectónicos (simplicidad vs escalabilidad)

---

### 9.2 - Developer Role Optimization

**Input**: Single story (YAML) + architecture context
**Output**: Código fuente + tests

**Complejidad**: ⭐⭐⭐⭐⭐ (Muy Alta - código ejecutable + tests)

**Baseline Esperado**: ~55-60%
**Target Optimizado**: ~75-80%
**Mejora Esperada**: +20-25%

**Métricas Clave**:
- Code syntax correctness (parseable, lintable)
- Test coverage (≥80% líneas cubiertas)
- Story alignment (implementa acceptance criteria)
- Code quality (no duplicación, patrones adecuados)
- Test execution (tests pasan en CI)

**Desafíos**:
- Output complejo (múltiples archivos de código + tests)
- Sintaxis correcta en múltiples lenguajes
- Tests que realmente validan funcionalidad
- Integración con código existente

---

### 9.3 - QA Role Optimization

**Input**: Código implementado + tests + story
**Output**: `qa_report.yaml` (defects, test_summary, recommendations)

**Complejidad**: ⭐⭐⭐ (Media-Alta - análisis de calidad)

**Baseline Esperado**: ~65-70%
**Target Optimizado**: ~85-90%
**Mejora Esperada**: +20-25%

**Métricas Clave**:
- Defect detection rate (encuentra bugs reales)
- False positive rate (no reporta no-bugs como bugs)
- Test execution summary accuracy
- Recommendation quality (accionables)
- Report completeness (fields requeridos)

**Desafíos**:
- Requiere ejecutar tests reales (no solo análisis estático)
- Balance entre exhaustividad y practicidad
- Variedad de tipos de defectos (funcionales, performance, seguridad)

---

## 📊 Estructura General del Plan

### Fases por Rol (Secuencial)

Cada rol sigue el mismo pipeline probado en Fase 8:

```
1. Dataset Preparation (1-2 días)
   ├── 1.1. Generate synthetic concepts
   ├── 1.2. Generate outputs from baseline model
   ├── 1.3. Filter by quality (score ≥ baseline threshold)
   └── 1.4. Train/val split (80/20)

2. Baseline Evaluation (0.5 días)
   ├── 2.1. Run baseline model on validation set
   ├── 2.2. Calculate metrics
   └── 2.3. Document baseline score

3. MIPROv2 Optimization (0.5-1 día)
   ├── 3.1. Configure optimization parameters
   ├── 3.2. Run MIPROv2 (bootstrapping + instruction optimization)
   ├── 3.3. Monitor progress
   └── 3.4. Save optimized program

4. Evaluation & Analysis (0.5 días)
   ├── 4.1. Run optimized model on validation set
   ├── 4.2. Compare vs baseline
   ├── 4.3. Analyze improvements
   └── 4.4. Document results

5. Integration (0.5 días)
   ├── 5.1. Update pipeline to use optimized model
   ├── 5.2. Run end-to-end test
   └── 5.3. Commit changes
```

**Total por rol**: ~3-4 días
**Total Fase 9**: ~12-15 días (secuencial) o ~6-7 días (paralelo, compartiendo datasets)

---

## 📁 Estructura de Artefactos

### Datasets (por rol)

```
artifacts/synthetic/
├── product_owner/
│   ├── concepts.jsonl                   # Concepto + requirements para PO
│   ├── product_owner_synthetic_raw.jsonl
│   ├── product_owner_synthetic_filtered.jsonl
│   ├── product_owner_train.jsonl
│   └── product_owner_val.jsonl
├── architect/
│   ├── concepts.jsonl                    # Input concepts para arquitecturas
│   ├── architect_synthetic_raw.jsonl     # 200+ ejemplos sin filtrar
│   ├── architect_synthetic_filtered.jsonl # 100-120 ejemplos filtrados
│   ├── architect_train.jsonl             # 80-96 ejemplos (80%)
│   └── architect_val.jsonl               # 20-24 ejemplos (20%)
├── developer/
│   ├── stories.jsonl                     # Stories para implementar
│   ├── developer_synthetic_raw.jsonl
│   ├── developer_synthetic_filtered.jsonl
│   ├── developer_train.jsonl
│   └── developer_val.jsonl
└── qa/
    ├── implementations.jsonl             # Código + tests para evaluar
    ├── qa_synthetic_raw.jsonl
    ├── qa_synthetic_filtered.jsonl
    ├── qa_train.jsonl
    └── qa_val.jsonl
```

### Modelos Optimizados

```
artifacts/dspy/
├── product_owner_optimized/
│   ├── program.pkl
│   ├── config.json
│   └── evaluation_report.json
├── architect_optimized/
│   ├── program.pkl                       # Programa DSPy compilado
│   ├── config.json                       # Configuración usada
│   └── evaluation_report.json           # Resultados vs baseline
├── developer_optimized/
│   ├── program.pkl
│   ├── config.json
│   └── evaluation_report.json
└── qa_optimized/
    ├── program.pkl
    ├── config.json
    └── evaluation_report.json
```

### Documentación

```
docs/
├── fase9_multi_role_dspy_plan.md         # Este documento (plan maestro)
├── fase9_product_owner_optimization.md   # Detalles específicos Product Owner
├── fase9_product_owner_schema.md         # Contrato vision/review
├── fase9_architect_optimization.md       # Detalles específicos Architect
├── fase9_developer_optimization.md       # Detalles específicos Developer
├── fase9_qa_optimization.md              # Detalles específicos QA
└── fase9_final_report.md                 # Resultados finales y comparación
```

---

## 🔧 Scripts y Herramientas

### Scripts Existentes (reutilizables de Fase 8)

1. **`scripts/tune_dspy.py`** ✅
   - Ya soporta múltiples roles (parámetro `--role`)
   - MIPROv2 optimization
   - Métricas customizables

2. **`scripts/generate_synthetic_dataset.py`** ⚠️
   - Requiere adaptación por rol (diferentes outputs)
   - Product Owner: genera product_vision.yaml + product_owner_review.yaml
   - Architect: genera stories.yaml + architecture.yaml
   - Developer: genera código + tests
   - QA: genera qa_report.yaml

3. **`scripts/filter_synthetic_data.py`** ⚠️
   - Requiere métricas específicas por rol
   - Product Owner: metric `product_owner_metric`
   - Architect: metric `architect_stories_metric`
   - Developer: metric `developer_code_metric`
   - QA: metric `qa_report_metric`

4. **`scripts/split_dataset.py`** ✅
   - Genérico, funciona para todos los roles

### Scripts Nuevos a Crear

1. **`scripts/generate_po_payloads.py`**
   - Normaliza conceptos BA + requirements para Product Owner
   - Genera metadata (`concept_id`, `tier`, `persona_focus`)
   - Produce `artifacts/synthetic/product_owner/concepts.jsonl`

2. **`scripts/generate_architect_concepts.py`**
   - Similar a `generate_business_concepts.py`
   - Genera requirements sintéticos como input para Architect

3. **`scripts/generate_developer_stories.py`**
   - Genera stories sintéticas como input para Developer
   - Incluye architecture context

4. **`scripts/generate_qa_implementations.py`**
   - Genera código + tests sintéticos como input para QA
   - Incluye story context

5. **`dspy_baseline/metrics.py`** (extender)
   - `product_owner_metric(gold, pred, trace=None)`
   - `architect_stories_metric(gold, pred, trace=None)`
   - `developer_code_metric(gold, pred, trace=None)`
   - `qa_report_metric(gold, pred, trace=None)`

---

## 🔁 Consideraciones Transversales para aplicar DSPy MIPROv2

1. **Registro unificado de experimentos** – Crear `artifacts/dspy/experiments.csv` con columnas `role`, `dataset_version`, `metric`, `baseline`, `optimized`, `date`, `notes` para auditar mejoras sin revisar carpetas manualmente.
2. **Versionado de Schemas** – Incluir `schema_version` en cada JSONL y referenciar documentos (`docs/fase9_product_owner_schema.md`, `docs/fase9_architect_schema.md`, etc.) desde los scripts. **Implementar migración automática** antes de abortar: si el schema no coincide, intentar migrar datos a la versión esperada; solo abortar si la migración falla. Esto evita perder progreso por cambios menores de schema.
3. **Bandera de activación por rol** – Añadir toggles en `config.yaml` para activar modelos optimizados de forma incremental.
   ```yaml
   # config.yaml (source of truth)
   dspy_optimization:
     enabled_roles:
       - ba              # ✅ Fase 8 completada
       # - product_owner  # Habilitar después de 9.0.10
       # - architect
       # - developer
       # - qa
     fallback_on_error: true  # Si programa optimizado falla, usar baseline
   ```
   Los scripts (e.g., `scripts/run_product_owner.py`) deben verificar esta configuración antes de cargar el programa optimizado.
4. **Validación cruzada de outputs** – Inyectar validadores ligeros en `scripts/run_iteration.py` para asegurar que cada rol cumple su contract antes de pasar al siguiente (ej.: Product Owner debe definir KPIs que Architect referenciará).
5. **Observabilidad y logs** – Centralizar logs MIPRO en `logs/mipro/<role>/YYYYMMDD.log` y publicar métricas resumidas en `artifacts/qa/last_report.json` aunque el rol no sea QA, facilitando monitoreo dentro de `make loop`.
6. **Reutilización de prompts y módulos** – Crear `dspy_baseline/modules/product_owner.py` y documentar prompts compartidos en `dspy_prompts/README.md` para evitar drift entre implementaciones manuales y DSPy.

Estas brechas deben cerrarse antes de escalar las optimizaciones en paralelo para garantizar reproducibilidad y trazabilidad.

---

## 📝 Tareas Detalladas - Fase 9.0: Product Owner

### 9.0.1 - Análisis de Output Product Owner Actual ✅ COMPLETADO

**Objetivo**: Mapear la estructura vigente de `product_vision.yaml` y `product_owner_review.yaml` y detectar campos críticos para la métrica.

**Tareas**:
1. ✅ Revisar muestras en `planning/product_vision.yaml` y `planning/product_owner_review.yaml`
2. ✅ Identificar secciones obligatorias (overview, objetivos, stakeholders, KPIs, riesgos, decisiones)
3. ✅ Marcar dependencias con `meta.original_request` y `planning/requirements.yaml`
4. ✅ Documentar schema en `docs/fase9_product_owner_schema.md`

**Criterios de Aceptación**:
- ✅ Schema validado con ≥3 ejemplos reales (Blog legacy + API REST + Inventory API)
- ✅ Lista de campos obligatorios vs opcionales documentada en `docs/fase9_product_owner_schema.md`

**Tiempo Estimado**: 0.3 días

**Artefactos Generados**:
- `docs/fase9_product_owner_schema.md` actualizado (sección 8 documenta 3 ejemplos reales con scoring ≥92%)
- Muestras persistidas en `artifacts/examples/product_owner/`:
  - `blog_product_vision.yaml`, `blog_product_owner_review.yaml`
  - `product_rest_api_vision.yaml`, `product_rest_api_review.yaml`
  - `inventory_api_vision.yaml`, `inventory_api_review.yaml`
- `scripts/run_product_owner.py` ajustado (regex para capturar bloques ```yaml ... ```) para evitar pérdida de REVIEW

**Resultados de Validación**:
- **Ejemplo 1 (Blog legacy)**: 113/120 pts (94.2%)
- **Ejemplo 2 (Product REST API)**: 113/120 pts (94.2%)
- **Ejemplo 3 (Inventory API)**: 111/120 pts (92.5%)
- Todas las listas críticas (`gaps`, `conflicts`, `recommended_actions`) ahora usan `[]` en vez de `null`, manteniendo compatibilidad con los parsers.

---

### 9.0.2 - Diseño de Métrica Product Owner ✅ COMPLETADO

**Componentes Implementados (`product_owner_metric` en `dspy_baseline/metrics/product_owner_metrics.py`)**:
1. **Schema Compliance** (30 pts) – valida campos obligatorios y tipos en visión/review.
2. **Requirements Alignment** (30 pts) – usa IDs (`FR/NFR/C`) cuando existen y fallback semántico (token overlap ≥30%) sobre `aligned/gaps/recommended_actions`.
3. **Vision Completeness** (30 pts) – evalúa riqueza de listas clave y longitud del summary.
4. **Review Specificity** (30 pts) – mide cantidad/calidad de summary, acciones, gaps/conflicts y narrativa.

**Artefactos**:
- Métrica implementada + registrada en `dspy_baseline/metrics/__init__.py`.
- Pruebas en `dspy_baseline/tests/test_product_owner_metric.py` (3 escenarios: completo, semántico sin IDs, output incompleto).
- Corrección en `scripts/run_product_owner.py` (regex para bloques ```yaml ... ```), evitando pérdidas del bloque REVIEW.
- Ejemplos congelados en `artifacts/examples/product_owner/*.yaml` (blog, product API, inventory API) usados como fixtures contextuales.

**Resultados (pytest)**:
- `pytest dspy_baseline/tests/test_product_owner_metric.py` → 3 tests verdes (≤0.1s).
- Scores esperados:
  - Blog legacy ≥0.85
  - Product/Inventory APIs ≥0.70 incluso sin IDs explícitos (semántica).
  - Outputs incompletos <0.30.

**Próximos pasos**:
- Integrar la métrica al pipeline de tuning (`scripts/tune_dspy.py`) y usarla en `scripts/filter_synthetic_data.py`.
- Documentar cómo mapear el score (0-1) a porcentajes en los reportes de experimentos.

---

### 9.0.3 - Generación de Inputs Sintéticos (Conceptos + Requirements) ✅ COMPLETADO

**Objetivo**: Obtener ≥220 pares concepto + requirements para estimular variedad en dominios.

**Implementado**:
1. **Nuevo script** `scripts/generate_po_payloads.py` (Typer CLI)
   - Reutiliza hasta `--existing-limit` ejemplos del BA dataset (`artifacts/synthetic/ba_train_v2_fixed.jsonl`) normalizando `meta.original_request` y serializando requisitos a YAML.
   - Sintetiza conceptos adicionales via plantillas deterministas (dominio/plataforma/foco/región) para garantizar ejecución offline y reproducible (`--synthetic-count`, `--seed`).
   - Añade `tier`, `metadata.origin`, `metadata.score/region/focus`, y asigna IDs `POCON-XXXX`.
2. **Dataset generado**: `artifacts/synthetic/product_owner/concepts.jsonl`
   - **Total**: 228 registros (98 existentes + 130 sintéticos).
   - **Distribución tier**: `{'corporate': 59, 'simple': 71, 'medium': 98}`.
   - Cada registro incluye campos obligatorios: `concept_id`, `tier`, `concept`, `requirements_yaml`, `metadata`.

**Comando ejecutado**:
```bash
.venv/bin/python scripts/generate_po_payloads.py \
  --existing-path artifacts/synthetic/ba_train_v2_fixed.jsonl \
  --existing-limit 120 \
  --synthetic-count 130 \
  --output artifacts/synthetic/product_owner/concepts.jsonl \
  --seed 42
```

**Resultado**: Se superó la meta (≥220 payloads). El archivo sirve como input directo para 9.0.4 (generación de outputs PO) y para `scripts/filter_synthetic_data.py` una vez que 9.0.5 esté en marcha.

---

### 9.0.4 - Generación de Dataset Sintético Product Owner ✅ COMPLETADO

**Objetivo**: Ejecutar Product Owner baseline sobre los 228 conceptos y capturar `product_vision` + `product_owner_review`.

**Implementación**:
- Nuevo script `scripts/generate_po_outputs.py`:
  - Lee `artifacts/synthetic/product_owner/concepts.jsonl`.
  - Para cada registro: escribe `planning/requirements.yaml`, invoca `run_product_owner.py` (granite4 vía Ollama) y captura VISION/REVIEW.
  - Persiste en `artifacts/synthetic/product_owner/product_owner_synthetic_raw.jsonl` con huella temporal y `exit_code`.
- Ejecución en 2 etapas (por límite de tiempo del proceso):
  ```bash
  .venv/bin/python scripts/generate_po_outputs.py --overwrite
  .venv/bin/python scripts/generate_po_outputs.py --offset 4 --append
  .venv/bin/python scripts/generate_po_outputs.py --offset 160 --append
  ```

**Resultados**:
- `product_owner_synthetic_raw.jsonl`: 228 líneas (∼5.9 MB).
- Tiempo promedio por concepto ≈ 22 s (granite4 + retry cuando falta REVIEW).
- 223 registros completos, 5 con `metadata.error = "run_product_owner failed (code=1)"` (concepts POCON-0004, 0009, 0012, 0115, 0191). Quedan marcados para reintento manual antes del filtrado.
- Ejemplo de estructura:
  ```json
  {
    "input": {
      "concept_id": "POCON-0101",
      "concept": "...",
      "requirements_yaml": "...",
      "tier": "medium"
    },
    "output": {
      "product_vision": "product_name: ...",
      "product_owner_review": "status: aligned ..."
    },
    "metadata": {
      "generated_at": "2025-11-09T22:15:33.48Z",
      "duration_seconds": 23.4,
      "exit_code": 0
    }
  }
  ```

**Pendientes antes de 9.0.5**:
1. (Opcional) Reintentar los 5 registros fallidos (usar `--offset` apuntando a sus IDs) antes de futuras ampliaciones del dataset.
2. Correr un script de sanity check (`yaml.safe_load`) sobre todos los campos `output.*` para confirmar parseo (actualmente los fallidos están marcados y se excluirán del filtrado hasta reintento).

---

### 9.0.5 - Filtrado de Dataset por Score ✅ COMPLETADO

**Objetivo**: Conservar únicamente los outputs con score ≥0.70 usando `product_owner_metric`.

**Implementación**:
1. Nuevo script `scripts/filter_po_dataset.py`
   - Lee `product_owner_synthetic_raw.jsonl`.
   - Para cada registro crea wrappers (`ExampleWrapper`, `PredictionWrapper`) y calcula el score.
   - Escribe:
     - `product_owner_synthetic_filtered.jsonl` (solo entradas ≥ threshold, incluye campo `score`).
     - `product_owner_scores.json` (reporte consolidado con totales, promedio, fallidos).
2. Comando ejecutado:
   ```bash
   .venv/bin/python scripts/filter_po_dataset.py --threshold 0.70
   ```

**Resultados**:
- `product_owner_synthetic_raw.jsonl`: 228 registros totales, 5 marcados con `error` (fallos previos en `run_product_owner`).
- 223 registros evaluados → **176** superan el umbral (min 0.7058, max 0.9844, promedio 0.8432).
- 52 registros filtrados por score bajo.
- `product_owner_scores.json` incluye estadísticas (media general 0.7622, listado de fallidos).

**Próximos pasos**:
- (Opcional) Reintentar los 5 conceptos con `error` para completar el dataset pleno en iteraciones siguientes.
- Añadir visualizaciones (histograma / boxplot) reutilizando el JSON si el equipo lo requiere.

---

### 9.0.6 - Train/Val Split ✅ COMPLETADO

**Implementación**:
- Nuevo script `scripts/split_po_dataset.py` (stratificado por `tier`, seed 42).
- Entrada: `product_owner_synthetic_filtered.jsonl` (176 ejemplos ≥0.70).
- Salidas:
  - `artifacts/synthetic/product_owner/product_owner_train.jsonl` → **142** ejemplos.
  - `.../product_owner_val.jsonl` → **34** ejemplos.

**Comando**:
```bash
.venv/bin/python scripts/split_po_dataset.py --val-ratio 0.2 --seed 42
```

**Notas**:
- Stratificación mantiene proporción simple/medium/corporate entre train y val.
- `val_ratio=0.2` produce 80/20 exacto dado el tamaño (176 → 34 val).

**Siguiente**: utilizar estos archivos en 9.0.7 (baseline evaluation).

---

### 9.0.7 - Baseline Evaluation ✅ COMPLETADO

**Objetivo**: Obtener el score base del PO (sin MIPRO) sobre el conjunto de validación.

**Implementación**:
- Nuevo script `scripts/evaluate_po_baseline.py` que:
  - Lee `product_owner_val.jsonl` (34 registros).
  - Recalcula `product_owner_metric` para cada ejemplo.
  - Guarda resultados en `artifacts/benchmarks/product_owner_baseline.json`.
- Comando:
  ```bash
  .venv/bin/python scripts/evaluate_po_baseline.py \
    --input artifacts/synthetic/product_owner/product_owner_val.jsonl \
    --report artifacts/benchmarks/product_owner_baseline.json
  ```

**Resultados**:
- Registros evaluados: 34.
- Media: **0.831** (≈83.1%).
- Desviación estándar: 0.067.
- Min/Max: 0.708 / 0.959.
- Reporte incluye listado de scores por `concept_id` para comparar contra futuros modelos optimizados.

**Notas**:
- Este baseline ya supera el target de 68-72% gracias al filtrado previo; la meta de MIPRO será empujar hacia ≥0.88 para justificar la optimización.

---

### 9.0.8 - MIPROv2 Optimization 🟡 EN CURSO

**Avance actual**:
1. **Infra previa**:
   - Nuevo módulo DSPy `ProductOwnerModule` (`dspy_baseline/modules/product_owner.py`).
   - `scripts/tune_dspy.py` actualizado para soportar `--role product_owner` + selección de provider (`ollama`, `vertex_ai`, etc.).
2. **Contrainset reducido**:
   - Para evitar ejecuciones de >3h con granite4, se generaron subconjuntos:
     - `product_owner_train_small.jsonl` (60 ejemplos).
     - `product_owner_train_small20.jsonl` (20 ejemplos, para pruebas rápidas).
3. **Primer tuning completo (60 ejemplos, 4 trials)**:
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py \
     --role product_owner \
     --trainset artifacts/synthetic/product_owner/product_owner_train_small.jsonl \
     --valset artifacts/synthetic/product_owner/product_owner_val.jsonl \
     --metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
     --num-candidates 4 \
     --num-trials 4 \
     --max-bootstrapped-demos 3 \
     --seed 0 \
     --output artifacts/dspy/product_owner_optimized \
     --provider ollama \
     --model mistral:7b-instruct \
     2>&1 | tee /tmp/mipro_product_owner.log
   ```
   - Duración ≈ 4h (cada ejemplo tarda 90‑110 s en granite4).
   - Log: `/tmp/mipro_product_owner.log` (copiar a `logs/mipro/product_owner/20251110.log` antes de sobrescribir).
   - Artefactos generados:
     - `artifacts/dspy/product_owner_optimized/product_owner/program.pkl`
     - Metadata con parámetros e hyperparams reales (num_trials=4, num_candidates=4, etc.).
   - Score MIPRO reportado: **1.56** (dentro de la escala dspy=0‑2). Promedio en valset durante la compilación: 0.53.
4. **Intento adicional (20 ejemplos, 2 trials)**:
   - Buscando acelerar, se lanzó un run con `product_owner_train_small20.jsonl`, pero se abortó manualmente antes de completar (no sobrescribió el programa anterior).

**Trabajo pendiente**:
- Repetir la optimización con el trainset completo (142 ejemplos) o con ≥100 ejemplos para asegurar generalización.
- Automatizar el guardado del log en `logs/mipro/product_owner/*.log`.
- Documentar comparativa (task 9.0.9) una vez consolidado el modelo final.

**Notas operativas**:
- Granite4 en Ollama tarda ~1.8 min por ejemplo; para runs largos, considerar `qwen2.5-coder:32b` o Vertex AI si se dispone de cuota.
- El comando actual soporta `--provider vertex_ai` + `--model gemini-2.5-pro` si se desea migrar.

---

### 9.0.9 - Evaluation & Comparison

**Objetivo**: Comparar baseline vs modelo optimizado en `product_owner_val.jsonl`.

**Métricas**:
- Score promedio, desviación estándar
- Cobertura de requirements (porcentaje cubierto)
- Calidad de review (match con decisiones esperadas)

**Criterios de Aceptación**:
- Mejora ≥ +12 puntos absolutos
- Reporte en `artifacts/dspy/product_owner_optimized/evaluation_report.json`

**Tiempo Estimado**: 0.4 días

---

### 9.0.10 - Integration & Testing

**Cambios Requeridos**:
1. Actualizar `scripts/run_product_owner.py` para cargar el programa optimizado (`program.pkl`) si existe
2. Ajustar `prompts/product_owner.md` para reflejar nuevas instrucciones y placeholders DSPy
3. Añadir bandera `USE_DSPY_PO=1` en `make po` para habilitar el modelo optimizado
4. Ejecutar `make ba → po → plan` con conceptos reales y validar artefactos

**Criterios de Aceptación**:
- `planning/product_vision.yaml` y `planning/product_owner_review.yaml` se generan a partir del programa optimizado
- Backwards compatibility: si el programa no existe, fallback a comportamiento anterior
- QA puntual documentado en `docs/fase9_product_owner_optimization.md`

**Tiempo Estimado**: 0.4 días

---

## 🔄 Sub-fase 9.D: Distillation / Fine-tune ligero (PO acceleration)

### Objetivo
Reducir drásticamente el tiempo de inferencia del rol Product Owner (y futuros roles) reemplazando `granite4` por un modelo local distillado que genere `product_vision` + `product_owner_review` en segundos. Esto habilita MIPROv2 repetible, reduce costos y evita cuellos de >3 horas por corrida.

### 9.D.1 - Diseño y alcance

- **Teacher**: Modelo superior (Gemini 2.5 Pro, GPT‑4o, etc.) usado sólo para generar un dataset maestro de alta calidad (500‑1000 ejemplos).
- **Student**: Modelo OSS ligero (Mistral 7B, Qwen 7B) entrenado vía LoRA/PEFT o FT corto.
- **Salida**: Adapter/modelo empaquetado para Ollama o HF Transformers (`po-student`), listo para reemplazar a `granite4`.

**Tareas**:
1. Definir prompts del teacher (basados en `prompts/product_owner.md` + ejemplos).
2. Seleccionar tamaño del dataset (mínimo 500 inputs PO representativos).
3. Estimar costo teacher (n llamadas x precio) y reservar slot en GPU para entrenamiento.

### 9.D.2 - Generación de dataset maestro

**Pipeline**:
1. Tomar `artifacts/synthetic/product_owner/concepts.jsonl` (o subset balanceado por tier/industry).
2. Para cada entrada, llamar al teacher y capturar `product_vision` + `product_owner_review`.
3. Validar cada salida contra el schema (usar `product_owner_metric` o validaciones directas).

**Artefactos**:
- `artifacts/distillation/po_teacher_dataset.jsonl` con campos:
  ```json
  {
    "concept": "...",
    "requirements_yaml": "...",
    "teacher_product_vision": "...",
    "teacher_product_owner_review": "...",
    "metadata": { "model": "gemini-2.5-pro", "cost": "$0.02" }
  }
  ```

### 9.D.3 - Entrenamiento LoRA/FT del student

**Config recomendada**:
- Base: `mistral-7b-instruct` o `qwen2.5-7b`.
- Técnica: LoRA (rank 16‑32) para ahorrar VRAM y facilitar despliegues.
- Dataset: 500‑1000 ejemplos teacher (mezclar con outputs reales del pipeline si se desea robustez).
- Epochs: 3‑5 (monitorizar loss para evitar overfitting).
- Hardware: GPU cloud (A10/A100) por ~3‑4 horas.

**Comando de ejemplo (pseudo-code)**:
```bash
python finetune_po_lora.py \
  --base mistral-7b-instruct \
  --dataset artifacts/distillation/po_teacher_dataset.jsonl \
  --output adapters/po_student_lora \
  --epochs 3 \
  --batch-size 4 \
  --lr 1e-4
```

### 9.D.4 - Validación del modelo distillado

1. Convertir LoRA a formato Ollama/HF (merge LoRA → full weights o cargar adapter en runtime).
2. Re-ejecutar `scripts/run_product_owner.py` sobre un subset (ej. 30 conceptos) y comparar métricas con el teacher (usar `product_owner_metric`, diff textual, etc.).
3. Documentar la comparación en `docs/po_distillation_report.md` (teacher vs student, velocidad, coste).

### 9.D.5 - Integración al pipeline

1. Actualizar `config.yaml`:
   ```yaml
   roles:
     product_owner:
       provider: ollama
       model: po-student
       temperature: 0.4
   ```
2. Ajustar `scripts/run_product_owner.py` si se requiere prompt específico para el student (normalmente no).
3. Ejecutar `make po` para validar end-to-end con el modelo nuevo.
4. Registrar en `docs/fase9_multi_role_dspy_plan.md` la transición (fecha, versión del modelo student, métricas).

### 9.D.6 - Beneficios esperados

- Inferencia PO: 2‑10s en vez de 90‑120s (granite4).
- MIPROv2 loops: de 4h → <30m por run (especialmente con dataset completo).
- Reutilizable para Architect/Dev si luego distillamos roles adicionales.
- Teacher cost acotado: 500 ejemplos × ($0.01‑0.05) ≈ $5‑25 + GPU cloud (unas horas).

### 9.D.7 - Próximos pasos tras distillation

1. Repetir 9.0.8 con el modelo student (trainset completo de 142 ejemplos) para obtener un programa optimizado sin esperas.
2. Continuar con Architect/Dev/QA usando la misma estrategia (teacher dataset → student LoRA) si PO resulta exitoso.
3. Mantener versionado de adapters/modelos en `artifacts/models/po_student_v1/` con metadata (`model_card.md`).

---

## 📝 Tareas Detalladas - Fase 9.1: Architect

### 9.1.1 - Análisis de Output Architect Actual

**Objetivo**: Entender formato actual y definir estructura del dataset.

**Tareas**:
1. Revisar `planning/stories.yaml` generados por Architect actual
2. Revisar `planning/architecture.yaml` generados
3. Identificar campos clave para métricas
4. Documentar schema esperado

**Criterios de Aceptación**:
- Schema documentado en `docs/fase9_architect_schema.md`
- Ejemplos de outputs "gold standard" identificados

**Tiempo Estimado**: 0.5 días

---

### 9.1.2 - Diseño de Métrica Architect

**Objetivo**: Definir métrica `architect_stories_metric` para evaluar calidad.

**Componentes de Métrica**:
1. **Story Completeness** (30 pts)
   - Todos los campos requeridos presentes
   - IDs únicos y secuenciales
   - Descriptions no vacías

2. **Story Quality** (25 pts)
   - Acceptance criteria específicos y verificables
   - Titles descriptivos y concisos
   - Estimates razonables

3. **Architecture Validity** (25 pts)
   - Componentes definidos correctamente
   - Tech stack coherente
   - Patrones apropiados al problema

4. **Dependency Correctness** (20 pts)
   - Dependencies apuntan a stories existentes
   - No ciclos en grafo de dependencias
   - Orden de implementación viable

**Score Total**: 100 pts (normalizar a 0-1)

**Tareas**:
1. Implementar `architect_stories_metric()` en `dspy_baseline/metrics.py`
2. Crear tests unitarios para la métrica
3. Validar con ejemplos reales

**Criterios de Aceptación**:
- Métrica implementada y testeada
- Score coherente con juicio humano (muestreo 10 ejemplos)

**Tiempo Estimado**: 1 día

---

### 9.1.3 - Generación de Conceptos Sintéticos (Architect Input)

**Objetivo**: Generar 200+ requirements sintéticos como input para Architect.

**Estrategia**:
- Reutilizar `artifacts/synthetic/ba_train_v2_fixed.jsonl` (98 ejemplos)
- Generar 102 ejemplos adicionales con `mistral:7b-instruct`
- Total: 200 examples

**Tareas**:
1. Crear `scripts/generate_architect_concepts.py`
2. Usar BA outputs existentes como seed
3. Generar variaciones sintéticas (diferentes dominios)
4. Guardar en `artifacts/synthetic/architect/concepts.jsonl`

**Criterios de Aceptación**:
- 200 requirements YAML sintéticos generados
- Diversidad de dominios (web, mobile, data, ML, etc.)

**Tiempo Estimado**: 0.5 días

---

### 9.1.4 - Generación de Dataset Sintético Architect

**Objetivo**: Generar outputs de Architect (stories.yaml) para 200 inputs.

**Proceso**:
1. Ejecutar Architect baseline sobre 200 concepts
2. Generar `stories.yaml` + `architecture.yaml` para cada uno
3. Guardar en `artifacts/synthetic/architect/architect_synthetic_raw.jsonl`

**Formato JSONL**:
```json
{
  "input": {
    "requirements": "..."  // YAML string
  },
  "output": {
    "stories": "...",      // YAML string
    "architecture": "...", // YAML string
    "epics": "..."         // YAML string (opcional)
  },
  "metadata": {
    "concept_id": "architect_001",
    "generated_at": "2025-11-09T...",
    "model": "mistral:7b-instruct"
  }
}
```

**Tareas**:
1. Adaptar `scripts/generate_synthetic_dataset.py` para Architect
2. Ejecutar generación (ETA: ~1-2 horas con Ollama)
3. Validar outputs (YAML válido, campos presentes)

**Criterios de Aceptación**:
- 200 ejemplos generados
- 100% con YAML válido
- Guardado en `architect_synthetic_raw.jsonl`

**Tiempo Estimado**: 0.5 días

---

### 9.1.5 - Filtrado de Dataset por Score

**Objetivo**: Filtrar ejemplos con score ≥ 0.60 (baseline threshold).

**Proceso**:
1. Calcular `architect_stories_metric` para cada ejemplo
2. Filtrar ejemplos con score ≥ 0.60
3. Guardar en `architect_synthetic_filtered.jsonl`
4. Objetivo: 100-120 ejemplos de calidad

**Tareas**:
1. Adaptar `scripts/filter_synthetic_data.py` para Architect
2. Ejecutar filtrado
3. Generar reporte de distribución de scores

**Criterios de Aceptación**:
- 100-120 ejemplos con score ≥ 0.60
- Reporte JSON con estadísticas

**Tiempo Estimado**: 0.25 días

---

### 9.1.6 - Train/Val Split

**Objetivo**: Dividir dataset en 80% train / 20% val.

**Resultado**:
- `architect_train.jsonl`: 80-96 ejemplos
- `architect_val.jsonl`: 20-24 ejemplos

**Tareas**:
1. Ejecutar `scripts/split_dataset.py` con seed fijo
2. Verificar distribución balanceada

**Criterios de Aceptación**:
- Split 80/20 exacto
- Ambos sets tienen diversidad de dominios

**Tiempo Estimado**: 0.1 días

---

### 9.1.7 - Baseline Evaluation

**Objetivo**: Establecer baseline score de Architect sin optimización.

**Proceso**:
1. Ejecutar Architect baseline sobre validation set
2. Calcular `architect_stories_metric` promedio
3. Documentar baseline score

**Expected Baseline**: ~60-65%

**Tareas**:
1. Ejecutar benchmark con `mistral:7b-instruct`
2. Calcular métricas
3. Guardar resultados en `artifacts/benchmarks/architect_baseline.json`

**Criterios de Aceptación**:
- Baseline score documentado
- Benchmark repetible (script + seed)

**Tiempo Estimado**: 0.25 días

---

### 9.1.8 - MIPROv2 Optimization

**Objetivo**: Optimizar Architect con DSPy MIPROv2.

**Configuración**:
- Provider: `ollama`
- Model: `mistral:7b-instruct`
- Num candidates: 4-8
- Num trials: 4-10
- Max bootstrapped demos: 4-6
- Seed: 0 (reproducibilidad)

**Comando**:
```bash
PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py \
  --role architect \
  --trainset artifacts/synthetic/architect/architect_train.jsonl \
  --metric dspy_baseline.metrics:architect_stories_metric \
  --num-candidates 8 \
  --num-trials 10 \
  --max-bootstrapped-demos 6 \
  --seed 0 \
  --output artifacts/dspy/architect_optimized \
  --provider ollama \
  --model mistral:7b-instruct \
  2>&1 | tee /tmp/mipro_architect.log
```

**Tiempo Esperado**: 1-2 horas (similar a BA)

**Tareas**:
1. Configurar DSPy program para Architect
2. Ejecutar MIPROv2 optimization
3. Monitorear progreso (`tail -f /tmp/mipro_architect.log`)
4. Guardar programa optimizado

**Criterios de Aceptación**:
- Optimización completa sin errores
- Programa optimizado guardado en `artifacts/dspy/architect_optimized/program.pkl`
- Log completo en `/tmp/mipro_architect.log`

**Tiempo Estimado**: 0.5 días (incluyendo setup y monitoreo)

---

### 9.1.9 - Evaluation & Comparison

**Objetivo**: Comparar modelo optimizado vs baseline.

**Métricas a Comparar**:
- Score promedio (validation set)
- Desviación estándar
- Mejora absoluta y relativa
- Por componente (completeness, quality, architecture, dependencies)

**Expected Results**:
- Baseline: 60-65%
- Optimized: 80-85%
- Mejora: +20-25%

**Tareas**:
1. Ejecutar modelo optimizado sobre validation set
2. Calcular métricas
3. Generar reporte comparativo
4. Crear visualizaciones (gráficos)

**Criterios de Aceptación**:
- Reporte JSON completo
- Markdown summary
- Mejora ≥ +15% (mínimo aceptable)

**Tiempo Estimado**: 0.5 días

---

### 9.1.10 - Integration & Testing

**Objetivo**: Integrar modelo optimizado en pipeline.

**Cambios Requeridos**:
1. Actualizar `scripts/run_architect.py`:
   - Cargar programa DSPy optimizado si existe
   - Fallback a modelo base si no

2. Actualizar `config.yaml`:
   - Agregar flag `use_dspy_optimized: true` para Architect

3. Testing end-to-end:
   - Ejecutar `make ba CONCEPT="Test"` → `make plan`
   - Verificar que stories generados tienen alta calidad

**Tareas**:
1. Modificar `scripts/run_architect.py`
2. Crear tests de integración
3. Ejecutar full pipeline test
4. Documentar cambios

**Criterios de Aceptación**:
- Pipeline funciona end-to-end
- Architect usa modelo optimizado
- Calidad de outputs mejorada visiblemente

**Tiempo Estimado**: 0.5 días

---

## 📝 Tareas Detalladas - Fase 9.2: Developer

### 9.2.1 - Análisis de Output Developer Actual

**Objetivo**: Entender formato actual de código generado.

**Tareas**:
1. Revisar archivos generados en `project/backend-fastapi/`
2. Analizar estructura de tests
3. Identificar patrones de código
4. Documentar schema esperado

**Criterios de Aceptación**:
- Schema documentado en `docs/fase9_developer_schema.md`
- Ejemplos de código "gold standard" identificados

**Tiempo Estimado**: 0.5 días

---

### 9.2.2 - Diseño de Métrica Developer

**Objetivo**: Definir métrica `developer_code_metric` para evaluar código generado.

**Componentes de Métrica**:
1. **Syntax Correctness** (25 pts)
   - Código parseable (AST válido)
   - Sin errores de sintaxis
   - Imports resueltos

2. **Test Completeness** (25 pts)
   - Tests presentes (≥1 test por función)
   - Coverage ≥80%
   - Assertions significativas

3. **Story Alignment** (25 pts)
   - Implementa acceptance criteria
   - Nombres de funciones/clases alineados con story
   - Lógica coherente con descripción

4. **Code Quality** (25 pts)
   - No duplicación excesiva
   - Funciones con single responsibility
   - Documentación (docstrings)
   - Linting (PEP8, etc.)

**Score Total**: 100 pts (normalizar a 0-1)

**Tareas**:
1. Implementar `developer_code_metric()` en `dspy_baseline/metrics.py`
2. Integrar con tools (ast, coverage.py, pylint)
3. Crear tests unitarios

**Criterios de Aceptación**:
- Métrica implementada y testeada
- Validación con ejemplos reales

**Tiempo Estimado**: 1.5 días (más compleja que otras métricas)

---

### 9.2.3 - Generación de Stories Sintéticas (Developer Input)

**Objetivo**: Generar 200+ stories sintéticas como input para Developer.

**Estrategia**:
- Usar outputs de Architect (stories.yaml) como seed
- Generar variaciones sintéticas
- Incluir architecture context

**Tareas**:
1. Crear `scripts/generate_developer_stories.py`
2. Generar 200 stories diversas
3. Guardar en `artifacts/synthetic/developer/stories.jsonl`

**Criterios de Aceptación**:
- 200 stories con acceptance criteria claros
- Diversidad de tipos (CRUD, business logic, API, UI, etc.)

**Tiempo Estimado**: 0.5 días

---

### 9.2.4 - Generación de Dataset Sintético Developer

**Objetivo**: Generar código + tests para 200 stories.

**Proceso**:
1. Ejecutar Developer baseline sobre 200 stories
2. Generar código fuente + tests para cada uno
3. Guardar en `developer_synthetic_raw.jsonl`

**Formato JSONL**:
```json
{
  "input": {
    "story": "...",        // YAML string
    "architecture": "..."  // Context
  },
  "output": {
    "code_files": [
      {"path": "main.py", "content": "..."},
      {"path": "test_main.py", "content": "..."}
    ]
  },
  "metadata": {
    "story_id": "dev_001",
    "generated_at": "...",
    "model": "mistral:7b-instruct"
  }
}
```

**Tareas**:
1. Adaptar `scripts/generate_synthetic_dataset.py` para Developer
2. Ejecutar generación (ETA: ~2-3 horas)
3. Validar outputs (código parseable)

**Criterios de Aceptación**:
- 200 ejemplos generados
- ≥80% con código sintácticamente correcto
- Tests presentes en cada ejemplo

**Tiempo Estimado**: 1 día

---

### 9.2.5 - Filtrado de Dataset por Score

**Objetivo**: Filtrar ejemplos con score ≥ 0.55.

**Tareas**:
1. Calcular `developer_code_metric` para cada ejemplo
2. Filtrar ejemplos con score ≥ 0.55
3. Guardar en `developer_synthetic_filtered.jsonl`
4. Objetivo: 100-120 ejemplos

**Criterios de Aceptación**:
- 100-120 ejemplos de calidad
- Reporte de distribución de scores

**Tiempo Estimado**: 0.5 días

---

### 9.2.6 - Train/Val Split

**Resultado**:
- `developer_train.jsonl`: 80-96 ejemplos
- `developer_val.jsonl`: 20-24 ejemplos

**Tiempo Estimado**: 0.1 días

---

### 9.2.7 - Baseline Evaluation

**Expected Baseline**: ~55-60%

**Tiempo Estimado**: 0.25 días

---

### 9.2.8 - MIPROv2 Optimization

**Configuración similar a Architect**

**Tiempo Esperado**: 1-2 horas

**Tiempo Estimado**: 0.5 días

---

### 9.2.9 - Evaluation & Comparison

**Expected Results**:
- Baseline: 55-60%
- Optimized: 75-80%
- Mejora: +20-25%

**Tiempo Estimado**: 0.5 días

---

### 9.2.10 - Integration & Testing

**Cambios en**: `scripts/run_dev.py`

**Tiempo Estimado**: 0.5 días

---

## 📝 Tareas Detalladas - Fase 9.3: QA

### 9.3.1 - Análisis de Output QA Actual

**Objetivo**: Entender formato actual de `qa_report.yaml`.

**Tiempo Estimado**: 0.5 días

---

### 9.3.2 - Diseño de Métrica QA

**Componentes de Métrica**:
1. **Defect Detection Accuracy** (30 pts)
2. **Test Summary Correctness** (25 pts)
3. **Recommendation Quality** (25 pts)
4. **Report Completeness** (20 pts)

**Tiempo Estimado**: 1 día

---

### 9.3.3 - Generación de Implementations Sintéticas (QA Input)

**Estrategia**:
- Usar outputs de Developer (código + tests) como seed
- Generar variaciones (con y sin bugs)

**Tiempo Estimado**: 0.5 días

---

### 9.3.4 - Generación de Dataset Sintético QA

**Tiempo Estimado**: 0.5 días

---

### 9.3.5 - Filtrado de Dataset por Score

**Threshold**: ≥ 0.65

**Tiempo Estimado**: 0.25 días

---

### 9.3.6 - Train/Val Split

**Tiempo Estimado**: 0.1 días

---

### 9.3.7 - Baseline Evaluation

**Expected Baseline**: ~65-70%

**Tiempo Estimado**: 0.25 días

---

### 9.3.8 - MIPROv2 Optimization

**Tiempo Estimado**: 0.5 días

---

### 9.3.9 - Evaluation & Comparison

**Expected Results**:
- Baseline: 65-70%
- Optimized: 85-90%
- Mejora: +20-25%

**Tiempo Estimado**: 0.5 días

---

### 9.3.10 - Integration & Testing

**Cambios en**: `scripts/run_qa.py`

**Tiempo Estimado**: 0.5 días

---

## 📊 Resumen de Timeline

### Por Rol (Secuencial)

| Rol | Tareas | Tiempo Estimado | Baseline Esperado | Target Optimizado |
|-----|--------|-----------------|-------------------|-------------------|
| **Product Owner** | 9.0.1 - 9.0.10 | 3.5 días | 68-72% | 85-88% |
| **Architect** | 9.1.1 - 9.1.10 | 4 días | 60-65% | 80-85% |
| **Developer** | 9.2.1 - 9.2.10 | 5 días | 55-60% | 75-80% |
| **QA** | 9.3.1 - 9.3.10 | 3.5 días | 65-70% | 85-90% |

**Total Secuencial**: 12.5 días (~2.5 semanas)

### Optimización Paralela (Si es posible)

Si se ejecutan roles en paralelo (con ayuda adicional o múltiples sesiones):
- **Total Paralelo**: 5 días (~1 semana)

---

## 🎯 Métricas de Éxito Fase 9

| Métrica | Target | Medición |
|---------|--------|----------|
| Product Owner optimizado | ≥85% | `product_owner_metric` en validation set |
| Architect optimizado | ≥80% | `architect_stories_metric` en validation set |
| Developer optimizado | ≥75% | `developer_code_metric` en validation set |
| QA optimizado | ≥85% | `qa_report_metric` en validation set |
| Mejora promedio | ≥+20% | (optimized - baseline) / baseline |
| Costo total | $0 | 100% local con Ollama |
| Tiempo total | ≤15 días | Desde inicio hasta integración completa |
| Pipeline completo optimizado | 5/5 roles | BA, PO, Architect, Dev, QA con DSPy MIPROv2 |

---

## 🚨 Riesgos y Mitigaciones

### Riesgo 1: Métricas complejas (Developer)

**Probabilidad**: Media
**Impacto**: Alto

**Mitigación**:
- Comenzar con métricas simples (syntax correctness)
- Iterar hacia métricas más sofisticadas
- Validar cada componente de métrica independientemente

---

### Riesgo 2: Dataset sintético de baja calidad

**Probabilidad**: Media
**Impacto**: Alto

**Mitigación**:
- Filtrado agresivo (thresholds altos)
- Revisión manual de muestra (10-20 ejemplos)
- Generación iterativa con prompts mejorados

---

### Riesgo 3: Optimización no mejora suficiente (<15%)

**Probabilidad**: Baja (basado en éxito de Fase 8)
**Impacto**: Medio

**Mitigación**:
- Ajustar hiperparámetros MIPROv2 (más candidates, más trials)
- Aumentar dataset (200 → 300 ejemplos)
- Refinar métricas (pueden estar penalizando incorrectamente)

---

### Riesgo 4: Tiempo excede estimación

**Probabilidad**: Media
**Impacto**: Bajo

**Mitigación**:
- Priorizar roles (Architect > Developer > QA)
- Fases paralelas si es posible
- Reducir scope (2 roles en Fase 9, 1 rol en Fase 10)

---

## 📦 Entregables Fase 9

### Scripts

- `scripts/generate_po_payloads.py`
- `scripts/generate_architect_concepts.py`
- `scripts/generate_developer_stories.py`
- `scripts/generate_qa_implementations.py`
- Extensiones en `scripts/generate_synthetic_dataset.py`
- Extensiones en `scripts/filter_synthetic_data.py`
- Nuevo módulo `dspy_baseline/modules/product_owner.py`

### Métricas

- `dspy_baseline/metrics.py`:
  - `product_owner_metric()`
  - `architect_stories_metric()`
  - `developer_code_metric()`
  - `qa_report_metric()`

### Datasets

- `artifacts/synthetic/product_owner/` (6 archivos)
- `artifacts/synthetic/architect/` (6 archivos)
- `artifacts/synthetic/developer/` (6 archivos)
- `artifacts/synthetic/qa/` (6 archivos)

### Modelos Optimizados

- `artifacts/dspy/product_owner_optimized/program.pkl`
- `artifacts/dspy/architect_optimized/program.pkl`
- `artifacts/dspy/developer_optimized/program.pkl`
- `artifacts/dspy/qa_optimized/program.pkl`

### Documentación

- `docs/fase9_multi_role_dspy_plan.md` (este documento)
- `docs/fase9_product_owner_schema.md`
- `docs/fase9_product_owner_optimization.md`
- `docs/fase9_architect_optimization.md`
- `docs/fase9_developer_optimization.md`
- `docs/fase9_qa_optimization.md`
- `docs/fase9_final_report.md`

---

## 🏁 Criterios de Completitud Fase 9

### Mínimo Viable (MVP)

1. ✅ Product Owner + Architect optimizados (≥+12 pts) y activos en `make ba → po → plan`
2. ✅ Dataset + métricas documentadas para Developer y QA (aunque sigan en baseline)
3. ✅ Pipeline funcional end-to-end con DSPy en BA/PO/Architect
4. ✅ Documentación y experiment logs completos
5. ✅ $0 costo (100% local)

### Objetivo Ideal

1. ✅ 4/4 roles nuevos optimizados (Product Owner + Architect + Developer + QA)
2. ✅ Mejora ≥+20% en cada rol
3. ✅ Pipeline optimizado completo (5/5 roles contando BA)
4. ✅ Benchmarks reproducibles
5. ✅ Tiempo total ≤15 días

---

## 🚀 Próximos Pasos Inmediatos

### Paso 1: Setup Inicial

```bash
# Crear estructura de directorios
mkdir -p artifacts/synthetic/{product_owner,architect,developer,qa}
mkdir -p artifacts/dspy/{product_owner_optimized,architect_optimized,developer_optimized,qa_optimized}

# Verificar dependencias
.venv/bin/python -c "import dspy; print('DSPy OK')"

# Confirmar Ollama disponible
ollama list | grep mistral
```

### Paso 2: Comenzar con Product Owner (Fase 9.0)

```bash
# Leer plan específico
cat docs/fase9_product_owner_optimization.md

# Ejecutar pipeline BA + PO con un concepto pequeño para recolectar ejemplos
make ba CONCEPT="Portal de reservas SaaS"
make po
```

### Paso 3: Preparar Architect (Fase 9.1) y alinear datasets

```bash
cat docs/fase9_architect_optimization.md
python scripts/generate_architect_concepts.py --help
```

### Paso 4: Crear Plan de Trabajo Diario

Ver sección "Orden de Ejecución Recomendado" abajo.

---

## 📅 Orden de Ejecución Recomendado

### Semana 1 (Días 1-4): Product Owner

- **Día 1**: Tareas 9.0.1 - 9.0.2 (análisis + métrica) - **1.0 días** ✅ (completado)
- **Día 2**: Tareas 9.0.3 - 9.0.4 (payloads + dataset raw) - **0.9 días** ⏳
- **Día 3**: Tareas 9.0.5 - 9.0.7 + inicio 9.0.8 (filtrado, split, baseline, setup MIPROv2) - **0.9 días** ⏳
- **Día 4**: Tareas 9.0.8-9.0.10 (completar optimization, evaluation, integración) - **1.0 días** ⏳

**Nota sobre rebalanceo**: Las tareas 9.0.5-9.0.7 (0.6 días) se complementan con el setup de 9.0.8 (0.3 días) para equilibrar Día 3 y evitar sobrecarga en Día 4.

### Semana 2 (Días 5-8): Architect

- **Día 5**: Tareas 9.1.1 - 9.1.3 (análisis, métrica, conceptos)
- **Día 6**: Tareas 9.1.4 - 9.1.6 (dataset, filtrado, split)
- **Día 7**: Tareas 9.1.7 - 9.1.8 (baseline, optimization)
- **Día 8**: Tareas 9.1.9 - 9.1.10 (evaluation, integration)

### Semana 3 (Días 9-12): Developer

- **Día 9**: Tareas 9.2.1 - 9.2.2 (análisis, métrica)
- **Día 10**: Tareas 9.2.3 - 9.2.4 (stories, dataset)
- **Día 11**: Tareas 9.2.5 - 9.2.7 (filtrado, split, baseline)
- **Día 12**: Tareas 9.2.8 - 9.2.10 (optimization, evaluation, integration)

### Semana 4 (Días 13-15): QA + Cierre

- **Día 13**: Tareas 9.3.1 - 9.3.4 (análisis, métrica, generación)
- **Día 14**: Tareas 9.3.5 - 9.3.9 (filtrado, split, baseline, optimization, evaluation)
- **Día 15**: Tarea 9.3.10 (integration) + reporte final y benchmarks comparativos

---

## 📖 Referencias

- **Fase 8 Success Case**: `docs/fase8_progress.md`
- **DSPy Documentation**: https://dspy-docs.vercel.app/
- **MIPROv2 Paper**: https://arxiv.org/abs/2406.11695
- **Pipeline Architecture**: `docs/architecture.md`

---

**Última Actualización**: 2025-11-09 20:30
**Branch**: `dspy-multi-role`
**Status**: ⏳ PENDING - Ready to start with 9.1.1

---

## 📝 ACTUALIZACIÓN 9.0.8 - Fix de Serialización (2025-11-10)

### Problema Descubierto
El run de optimización MIPROv2 (60 ejemplos, 4 trials, ~4h) completó exitosamente PERO falló al serializar:
- Error: `Can't pickle StringSignature... has recursive self-references`
- `program.pkl` solo 2 bytes (vacío)
- Causa: MIPROv2 genera instrucciones muy largas que crean referencias circulares

### Solución Implementada (`scripts/tune_dspy.py`)
**Líneas modificadas**: 87-146, 230-260

1. **Nueva función** `_extract_program_components()`:
   - Extrae manualmente: instructions, demos, fields
   - Retorna JSON serializable

2. **Estrategia dual de serialización**:
   - Strategy 1: Intentar dill (estándar)
   - Strategy 2 (Fallback): Extracción a `program_components.json`

### Test de Validación Exitoso (20 ejemplos)
```bash
# Ejecutado 2025-11-10 08:06-08:45 (39 min)
PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py \
  --role product_owner --trainset /tmp/po_test_tiny.jsonl \
  --metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
  --num-candidates 2 --num-trials 2 --max-bootstrapped-demos 2 --seed 0 \
  --output /tmp/po_test_optimized --provider ollama --model mistral:7b-instruct
```

**Resultados**:
- ✅ 4 trials completados, score 1.56 (consistente)
- ❌ dill falló (esperado) - `program.pkl` = 2 bytes  
- ✅ **Fallback JSON exitoso** - `program_components.json` = 954 bytes
- Componentes extraídos: role, type, module con instructions y 5 fields

### Próximos Pasos
1. ⏳ Ejecutar optimización completa (60 ejemplos) con fix validado
2. Evaluar vs baseline (0.831) - task 9.0.9
3. Integrar en pipeline - task 9.0.10

### Archivos Modificados
- `scripts/tune_dspy.py:87-146` - `_extract_program_components()`
- `scripts/tune_dspy.py:230-260` - Dual serialization strategy
- `docs/PO_SERIALIZATION_FIX_20251110.md` - Documentación detallada

### Performance por Modelo
| Modelo | Tiempo/Ejemplo | 60 ejemplos |
|--------|----------------|-------------|
| mistral:7b | ~30-45s | ~30-45min |
| qwen2.5-coder:32b | ~20s | ~20-30min |
| gemini-2.5-flash | ~10s | ~10-15min |

**Status**: Fix implementado y validado ✅. Listo para optimización completa.
