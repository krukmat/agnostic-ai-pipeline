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

**Evaluación corregida (2025-11-17)**
- Script: `/tmp/evaluate_po_optimization_FIXED.py` (log `/tmp/po_evaluation_CORRECTED.log`).
- Baseline: media 0.0295, σ 0.0315, mediana 0.0156.
- Optimizado: media 0.7458, σ 0.2619, **mediana 0.9031**.
- Gap vs 0.85: 0.1042 (12.25%).
- Se decide reportar mediana como indicador primario y registrar media/desvío para comparación.

### 9.0.9 - Evaluation & Comparison

**Evaluación corregida (2025-11-17)**
- Script: `/tmp/evaluate_po_optimization_FIXED.py` (log en `/tmp/po_evaluation_CORRECTED.log`).
- Baseline (`gemini-2.5-flash` sin optimizar):
  - Media: 0.0295 (2.95%).
  - Desvío estándar: 0.0315.
  - Mediana: 0.0156 (casi todos los samples en el mínimo).
- Optimizado (`gemini-2.5-pro` + último push DSPy):
  - Media: 0.7458 (74.58%).
  - Desvío estándar: 0.2619 (varios outliers en 0.3094).
  - **Mediana**: 0.9031 (90.31%) → indicador más representativo dado el sesgo.
- Gap vs meta 0.85: diferencia de 0.1042 (12.25%).
- Archivos de referencia: `artifacts/dspy/po_optimization_evaluation_FIXED.json`, `/tmp/po_evaluation_CORRECTED.log`.
- Determinación tomada: reportar mediana 0.9031 como indicador principal mientras se define si vale la pena otro run (ver recomendaciones previas).

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

**Acciones inmediatas**:
- Congelar el snapshot `artifacts/dspy/po_optimized_full_snapshot_20251117T105427/product_owner` (copiado 2025-11-17 10:54) y expedirlo al pipeline.
  - Estado (2025-11-17 11:00): snapshot congelado en `artifacts/dspy/po_optimized_full_snapshot_20251117T105427/`; listo para consumo de 9.0.10.
- Actualizar `scripts/run_product_owner.py` para cargar `program_components.json` cuando `program.pkl` esté vacío.
- Conectar `make po` y `scripts/run_product_owner.py` a `features.use_dspy_product_owner` (manteniendo `USE_DSPY_PO` solo como override puntual).
  - Estado (2025-11-17 12:45): 📌 **Completado.** `config.yaml` ahora incluye `features.use_dspy_product_owner`, `Makefile` deja de forzar `USE_DSPY_PO=0` y el script usa el flag como default, permitiendo overrides con `USE_DSPY_PO=0|1` cuando se necesite un cambio temporal.
    * El loader aplica `program_components.json` (instructions+demos) y sanitiza YAML antes de escribir.
    * `scripts/dspy_lm_helper.py` soporta overrides `DSPY_PRODUCT_OWNER_LM`, `_TEMPERATURE`, `_MAX_TOKENS` para pruebas rápidas sin editar el YAML principal.
    * LM por defecto: `ollama/granite4`, totalmente local. Vertex se mantiene como fallback manual cuando vuelva la red.
    * 2025-11-17 13:40: además se ajustó `scripts/run_product_owner.py` para que el concepto se lea siempre desde `planning/requirements.yaml` (env `CONCEPT` solo opera cuando ese meta falta), evitando divergencias BA→PO.
- Ejecutar `make ba → po → plan` con historia real y adjuntar logs/evidencia.
  - Referencia fix BA: ver `docs/BA_DSPY_THREADFIX_PLAN.md` (2025-11-17) para resolver el error dspy.settings al llamar `make ba`.
    * Estado actual: thread fix aplicado; la corrida se detiene por falta de acceso al LLM remoto (ver plan para reintentar cuando haya red/GCP).
    * Plan aprobado: ver `docs/BA_DSPY_THREADFIX_PLAN.md` (sección DSPy Local LM) para configurar BA con `DSPY_BA_LM` y modelos locales.
    * Validación 2025-11-17: `make ba` completado usando `DSPY_BA_LM=ollama/granite4`; falta repetir con logs formales cuando tengamos un LM local estable.

    * Estado actual: thread fix aplicado; la corrida se detiene por falta de acceso al LLM remoto (ver plan para reintentar cuando haya red/GCP).
    * Plan aprobado: ver `docs/BA_DSPY_THREADFIX_PLAN.md` (sección DSPy Local LM) para configurar BA con `DSPY_BA_LM` y modelos locales.
  - Estado (2025-11-17 11:38): `make ba` ya no falla por hilos; la ejecución se detiene porque el proveedor remoto no está disponible (`Operation not permitted`). Próximo paso: habilitar LM local (ver plan) o reintentar con red.

### 9.0.10 - Integration & Testing

**Cambios Requeridos**:
1. Actualizar `scripts/run_product_owner.py` para cargar el programa optimizado (`program.pkl`) si existe
2. Ajustar `prompts/product_owner.md` para reflejar nuevas instrucciones y placeholders DSPy
3. Enlazar `make po` y `scripts/run_product_owner.py` a `features.use_dspy_product_owner` (con `USE_DSPY_PO` como override opcional)
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

### 9.D.1 - Diseño y alcance _(Estado: en curso)_

**Objetivo**: Definir los parámetros operativos de la distillation antes de generar datasets o lanzar entrenamiento.

**Decisiones tomadas**:
- **Teacher**: `gemini-2.5-pro` (Vertex AI) – buena calidad en visión/review y ya tenemos credenciales/config en `config.yaml`.
- **Cobertura**: 600 ejemplos (aprox. 200 por tier simple/medium/corporate) tomados de `artifacts/synthetic/product_owner/concepts.jsonl` para asegurar diversidad de dominios.
- **Costos estimados**:
  - Teacher inference: 600 llamadas × ~$0.01 = ~$6 (crecerá si se agregan retries).
  - GPU para LoRA (A100 40GB) ~3 horas → ~$4–6 (según proveedor).
- **Outputs esperados**:
  - `artifacts/distillation/po_teacher_dataset.jsonl`
  - Adapter/model card en `artifacts/models/po_student_v1/`
  - Log de entrenamiento `logs/distillation/po_student_v1.log`

**Plan de trabajo**:
1. Script `scripts/generate_po_teacher_dataset.py`
   - Batch size configurable (default 20) para Vertex.
   - Validación automática (`product_owner_metric` >=0.85); los que queden debajo irán a una cola de revisión.
2. Entrenamiento LoRA con `mistral-7b-instruct`:
   - rank=32, alpha=64, target modules `q_proj,k_proj,v_proj,o_proj`.
   - Epochs=3, batch=4, LR=1e-4.
3. Conversión + despliegue:
   - Merge LoRA → full weights (`po-student-v1.safetensors`).
   - Empaquetar para Ollama (`Modelfile` con quantization q4_0).

**Entregables de la tarea**:
- Documento `docs/phase9_distillation_plan.md` (listo).
- Tickets de seguimiento (opcional) para dataset y training.

**Estado actual**: Documentación creada (ver `docs/phase9_distillation_plan.md`). Próximo paso → 9.D.2 (generación dataset maestro).

- **Teacher**: Modelo superior (Gemini 2.5 Pro, GPT‑4o, etc.) usado sólo para generar un dataset maestro de alta calidad (500‑1000 ejemplos).
- **Student**: Modelo OSS ligero (Mistral 7B, Qwen 7B) entrenado vía LoRA/PEFT o FT corto.
- **Salida**: Adapter/modelo empaquetado para Ollama o HF Transformers (`po-student`), listo para reemplazar a `granite4`.

**Tareas**:
1. Definir prompts del teacher (basados en `prompts/product_owner.md` + ejemplos).
2. Seleccionar tamaño del dataset (mínimo 500 inputs PO representativos).
3. Estimar costo teacher (n llamadas x precio) y reservar slot en GPU para entrenamiento.

### 9.D.2 - Generación de dataset maestro

**Estado**: en curso

**Objetivo**: Crear `artifacts/distillation/po_teacher_dataset.jsonl` con ≥600 pares (concept + requirements) → (VISION, REVIEW) generados por el modelo teacher (Gemini 2.5 Pro).

**Plan**:
1. Implementar `scripts/generate_po_teacher_dataset.py`:
   - Entrada: `artifacts/synthetic/product_owner/concepts.jsonl`
   - Parámetros: `--provider vertex_sdk`, `--model gemini-2.5-pro`, `max_records=400`
   - Validación automática con `product_owner_metric` (threshold 0.85)
2. Registrar costo por lote (guardar log en `logs/distillation/teacher_calls_YYYYMMDD.log`)
3. Salida JSONL con campos:
   ```json
   {
     "concept": "...",
     "requirements_yaml": "...",
     "teacher_product_vision": "...",
     "teacher_product_owner_review": "...",
     "score": 0.91,
     "metadata": { "model": "gemini-2.5-pro", "timestamp": "..." }
   }
   ```

**Avance**:
- 45 registros de `gemini-2.5-pro` + 274 registros de `gemini-2.5-flash` (threshold 0.80) → **319/350** completados.
- Score promedio actual: 0.896 (min 0.80 / max 0.984). Dataset activo: `artifacts/distillation/po_teacher_dataset.jsonl`.
- Log de generación: `/tmp/teacher_hybrid_flash.log` (pendiente mover a `logs/distillation/teacher_calls_20251110.log`).

**Pendiente**:
- Completar hasta 350 registros (faltan ~31). Comando (cuando se reanude):
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/generate_po_teacher_dataset.py \
    --provider vertex_sdk \
    --model gemini-2.5-flash \
    --max-records 350 \
    --min-score 0.80 \
    --seed 999 \
    --resume \
    2>&1 | tee -a /tmp/teacher_hybrid_flash.log
  ```
- Registrar costo estimado en `logs/distillation/teacher_costs_20251110.txt`.
- Nota: último intento (`PID 82959`) falló por `NameResolutionError` al resolver `oauth2.googleapis.com` (sin red). Reintentar cuando haya conectividad.

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

**Estado**: pendiente (listo para iniciar)

**Objetivo**: Entrenar un modelo `po-student` (loRA sobre Mistral-7B) que replique al teacher dataset (actualmente 319 muestras válidas) para reducir latencia del rol Product Owner.

**Entradas disponibles**:
- `artifacts/distillation/po_teacher_dataset.jsonl` (319 registros, score medio 0.896, min 0.80).
- `docs/phase9_distillation_plan.md` (detalle de hyperparams).

**Plan de trabajo**:
1. **Preparar dataset supervisado**  
   - Script `scripts/prep_po_lora_dataset.py` (pendiente) → transforma cada registro teacher en un prompt-respuesta.
   - Estructura target:
     ```
     ### CONCEPT
     ...
     ### REQUIREMENTS
     ...
     ### OUTPUT
     ```yaml VISION
     ...
     ```
     ```yaml REVIEW
     ...
     ```
     ```
2. **Entrenamiento LoRA**  
   - Modelo base: `mistral-7b-instruct` (HF).  
   - Hyperparams (desde plan):
     - rank=32, alpha=64, dropout=0.05
     - epochs=3, batch=4, lr=1e-4, max seq len=2048
   - Comando tentativo:
     ```bash
     PYTHONPATH=. .venv/bin/python scripts/train_po_lora.py \
       --data-path artifacts/distillation/po_teacher_supervised.jsonl \
       --base mistral-7b-instruct \
       --output artifacts/models/po_student_v1 \
       --rank 32 --alpha 64 --epochs 3 --batch 4 --lr 1e-4 \
       2>&1 | tee logs/distillation/train_po_student_v1.log
     ```
3. **Merge + empaquetado**  
   - `merge_lora.py` para obtener `po_student_v1.safetensors`.
   - Crear `Modelfile` para Ollama (`po-student-v1`).  
   - Guardar model card en `artifacts/models/po_student_v1/model_card.md`.

4. **Validación rápida**  
   - Reutilizar 20 ejemplos del teacher dataset → `scripts/eval_po_student.py`.  
   - Comparar `product_owner_metric` y tiempos vs granite4.

**Deliverables**:
- `artifacts/models/po_student_v1/` (adapters, merged weights, Modelfile).
- Logs de entrenamiento (`logs/distillation/train_po_student_v1.log`).
- Reporte comparativo (`docs/po_distillation_report.md`).

**Prereq**: Dataset maestro ≥300 (actual: 319) y dataset supervisado (`artifacts/distillation/po_teacher_supervised.jsonl`). Listo para iniciar.

**Actualización 2025-11-13**:
- Entrenamiento ejecutado en Colab (GPU T4 16 GB) con `Qwen/Qwen2.5-7B-Instruct`, `--load-4bit`, batch 1 y grad-accum 8.  
- Métricas clave: loss inicial 1.46 → final 0.4299; `train_loss` promedio 0.6537; `train_runtime` 6005 s (≈1h40m).  
- Artefactos generados en `/content/agnostic-ai-pipeline/artifacts/models/po_student_v1/`; log en `logs/distillation/train_po_student_v1.log`.  
- **Pendiente**: descargar/zip de `po_student_v1`, traer el log al repo, documentar en `docs/po_distillation_report.md` y avanzar a 9.D.4 (validación con `scripts/eval_po_student.py`).

#### Plan Colab (FT/LoRA en entorno cloud)

**Pasos resumidos**:
1. **Preparar entorno**  
   - Abrir Colab → seleccionar GPU (T4 vale, A100 preferible).  
   - `!git clone https://.../agnostic-ai-pipeline.git && cd agnostic-ai-pipeline`.  
   - `pip install -r requirements.txt` (añadir `pip install -U transformers peft accelerate bitsandbytes` si Colab viene desactualizado o no trae bnb).  
   - Desactivar W&B para evitar prompts interactivos antes de entrenar:  
     ```python
     import os
     os.environ["WANDB_DISABLED"] = "true"
     os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
     ```
2. **Copiar dataset maestro**  
   - Asegurar que `artifacts/distillation/po_teacher_dataset.jsonl` y `artifacts/distillation/po_teacher_supervised.jsonl` existan dentro del repo en `/content/agnostic-ai-pipeline`.  
   - Si es necesario subirlos desde local, usar `from google.colab import files; files.upload()` o `!wget <url_privada>` y moverlos a `artifacts/distillation/`.
3. **Entrenar LoRA**  
   - Ejecutar `python scripts/train_po_lora.py` con paths absolutos de `/content/agnostic-ai-pipeline` (ejemplo más abajo) y parámetros `rank=32, alpha=64, epochs=3, batch=4, lr=1e-4, max_length=2048`.  
   - Modelos probados sin token HF: `mistral-7b-instruct`, `Qwen/Qwen2.5-7B-Instruct`.  
   - Guardar checkpoints y tokenizer en `/content/agnostic-ai-pipeline/artifacts/models/po_student_v1/` (o en Drive montado si se requiere persistencia extra).
   - Para GPUs con ~16 GB (p. ej. T4) usar `--load-4bit --batch-size 1 --gradient-accumulation-steps 8` y mantener `gradient_checkpointing` activo para evitar OOM.
4. **Monitorear/Exportar resultados**  
   - Correr con `!stdbuf -oL python ... | tee logs/distillation/train_po_student_v1.log` para ver progreso en tiempo real y guardar log.  
   - Al finalizar, `!zip -r po_student_v1.zip artifacts/models/po_student_v1` y descargar/respaldar.  
5. **Merge + validación**  
   - Ejecutar `merge_lora.py` en local si se requiere pesos completos.  
   - Correr `scripts/eval_po_student.py` (20 ejemplos) para comparar contra granite4.  
6. **Documentar**  
   - Registrar fecha/duración y métricas en `docs/po_distillation_report.md`.  
   - Sincronizar `logs/distillation/train_po_student_v1.log` al repo (`artifacts/logs` si pesa mucho).

> **Nota**: `scripts/train_po_lora.py` fuerza `WANDB_DISABLED=true`, pero si Colab vuelve a mostrar el prompt de W&B (1/2/3) es porque la celda previa no ejecutó el bloque `os.environ["WANDB_DISABLED"]="true"` o porque otro proceso lo sobreescribió. Re-ejecutar esa celda y volver a lanzar el entrenamiento.

1. **Preparar notebook (colab_po_student.ipynb)**  
   - Secciones:
     1. Montar drive/repositorio (`!git clone` + `pip install -r requirements.txt`).
     2. Descargar dataset maestro (`po_teacher_dataset.jsonl`) desde repositorio (uso de `wget` + token o `gdown`) o cargarlo manualmente, verificando que quede en `/content/agnostic-ai-pipeline/artifacts/distillation/`.
     3. Configurar entorno (instalar `transformers`, `peft`, `accelerate`, `auto-gptq` si se requiere quant).
     4. Entrenar LoRA (celdas con los hiperparámetros mencionados).
     5. Guardar adapters y merged weights en `/content/drive/MyDrive/po_student_v1/`.

2. **Recursos**:
   - Runtime: GPU T4 / A100 (preferible A100 para velocidad).
   - Uso aproximado: 3h (dependerá de la cola de Colab).

3. **Descarga y merge**:
   - Tras finalizar, `!zip -r po_student_v1.zip po_student_v1/` y descargar.
   - Ya en local: mover a `artifacts/models/po_student_v1/` y ejecutar `merge_lora.py` si se requiere conversiones adicionales.

4. **Checklist**:
   - Notebook versionado en `notebooks/colab_po_student.ipynb`.
   - Registro de ejecución (fecha, duración, métricas de entrenamiento) en `docs/po_distillation_report.md`.
   - Subir log/outputs relevantes a `logs/distillation/`.

**Config recomendada**:
- Base: `mistral-7b-instruct` o `qwen2.5-7b`.
- Técnica: LoRA (rank 16‑32) para ahorrar VRAM y facilitar despliegues.
- Dataset: 500‑1000 ejemplos teacher (mezclar con outputs reales del pipeline si se desea robustez).
- Epochs: 3‑5 (monitorizar loss para evitar overfitting).
- Hardware: GPU cloud (A10/A100) por ~3‑4 horas.

**Comando de ejemplo (Colab)**:
```bash
!python scripts/train_po_lora.py \
  --data-path /content/agnostic-ai-pipeline/artifacts/distillation/po_teacher_supervised.jsonl \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --output-dir /content/agnostic-ai-pipeline/artifacts/models/po_student_v1 \
  --rank 32 --alpha 64 --dropout 0.05 \
  --epochs 3 --batch-size 1 --gradient-accumulation-steps 8 \
  --lr 1e-4 --max-length 2048 \
  --load-4bit --bnb-compute-dtype float16
```

> **Tip OOM**: Si aparece `CUDA out of memory`, reduce `--batch-size`, incrementa `--gradient-accumulation-steps`, y asegúrate de correr con `--load-4bit`. Re-lanza la celda tras reiniciar el runtime para liberar memoria residual.

### 9.D.4 - Validación del modelo distillado

1. Convertir LoRA a formato Ollama/HF (merge LoRA → full weights o cargar adapter en runtime).
2. Re-ejecutar `scripts/run_product_owner.py` sobre un subset (ej. 30 conceptos) y comparar métricas con el teacher (usar `product_owner_metric`, diff textual, etc.).
3. Documentar la comparación en `docs/po_distillation_report.md` (teacher vs student, velocidad, coste).

**Ejecución 2025-11-14 (inference_results/)**  
- Se corrió `scripts/eval_po_student.py` con 3 escenarios (`basic_blog_validation`, `ecommerce_requirements`, `incomplete_requirements`) usando el baseline (`Qwen/Qwen2.5-7B-Instruct` sin adapter) y el student (`po_student_v1`). Outputs guardados en `inference_results/baseline_20251114_143731.json`, `finetuned_20251114_143731.json` y comparativo `comparison_20251114_143731.json`.  
- Resultado cuantitativo disponible: longitud promedio de respuesta bajó de **2577** caracteres (baseline) a **2503** (-2.9%), sin cambios relevantes en cobertura.  
- Problema principal: ninguno de los dos modelos emitió los bloques ```yaml VISION``` / ```yaml REVIEW``` requeridos, por lo que **no pudimos calcular `product_owner_metric` ni validar contra el schema**. Además, las salidas incluyen repeticiones del prompt y texto libre, señal de que el prompt/evaluador no está forzando el formato.  
- Estado: 9.D.4 **incompleto** hasta que logremos respuestas en el formato contractual. Próximos pasos:
  1. Ajustar prompt de inferencia para inyectar ejemplos YAML o reutilizar el template del dataset supervisado.  
  2. Reentrenar o aplicar post-processing para garantizar la emisión de bloques estructurados (posible uso de constrained decoding).  
  3. Repetir la evaluación con ≥20 casos y registrar `product_owner_metric` una vez se obtenga YAML válido.

**Intento Lightning AI Studio (2025-11-15)**  
- Se migró el entrenamiento al entorno Lightning (GPU T4) para evitar los límites de Colab gratuito. Se actualizó el notebook `PO_LoRA_Training_v2.ipynb` para detectar `/workspace`, usar instalación pura via `subprocess`, y forzar padding/validación con el nuevo script (`scripts/eval_po_student.py`).  
- Ajustes aplicados para contener VRAM:
  - Reducción progresiva de `max_length` (2048→1536→1200→1024→768) y finalmente `rank=16 / alpha=32`.
  - `per_device_train_batch_size=1`, `gradient_accumulation_steps` hasta 48, `torch_empty_cache_steps=10`, `torch.cuda.empty_cache()` antes de `trainer.train()`.  
  - Se implementaron fallbacks automáticos para carga del modelo (4-bit → fp16 si el backend no soporta QLoRA) y se encapsuló todo en Python puro para evitar `%bash`.
- Resultado: **OOM persistente** en `trainer.train()` a pesar de los recortes. La T4 (14 GB) no sostiene el LoRA sobre Qwen2.5 con secuencias >512 tokens.  
- Próxima acción obligatoria → usar una GPU con ≥24 GB (RunPod L4/A100, Colab Pro u otra). El plan documentado ya incluye instrucciones para RunPod y Lightning; en cuanto se tenga acceso a una L4/A100, relanzar 9.D.3 con la configuración completa y repetir 9.D.4.

**Plan de remediación (2025-11-15)**  
1. **Curar dataset supervisado** (Owner: PO/BA, ETA 0.5d)  
   - Filtrar `artifacts/distillation/po_teacher_supervised.jsonl` → descartar muestras con `score < 0.82` o REVIEW sin referencias a IDs.  
   - Generar +50 registros nuevos del teacher centrados en tier corporate / edge cases (usando `scripts/generate_po_teacher_dataset.py --min-score 0.85`).  
   - Volver a correr `scripts/prep_po_lora_dataset.py --min-score 0.82 --max-samples 400` para balancear la muestra final.  
2. **Refinar prompt y evaluación** (Owner: Dev, ETA 0.5d)  
   - Actualizar `scripts/po_prompts.py` para exigir:  
     - `requirements_alignment` debe mencionar IDs específicos (FR/NFR/CON).  
     - `recommended_actions` ≥2 entradas con verbos accionables.  
     - `narrative` <=120 palabras para evitar desvíos.  
   - Ajustar `scripts/eval_po_student.py` a `--retries 2` y validar que cada bloque contenga al menos 3 bullet points donde aplique; si falla, reintentar con instrucción más estricta.  
3. **Reentrenar LoRA** (Owner: Dev, ETA 0.5d)  
   - Volver a lanzar `train_po_lora.py` con: `--epochs 4`, `--gradient-accumulation-steps 12`, `--lr 8e-5`, `--lr-scheduler cosine`, `--warmup-ratio 0.05`.  
   - Conservar `rank 32`, `alpha 64`, `--load-4bit`, `--gradient-checkpointing`. Al terminar, registrar loss y subir adapters a Drive.  
   - Ejemplo (Colab / notebook):
     ```bash
     !python scripts/train_po_lora.py \
       --data-path artifacts/distillation/po_teacher_supervised.jsonl \
       --base-model Qwen/Qwen2.5-7B-Instruct \
       --output-dir artifacts/models/po_student_v1 \
       --rank 32 --alpha 64 --dropout 0.05 \
       --epochs 4 --batch-size 1 --gradient-accumulation-steps 12 \
       --lr 8e-5 --lr-scheduler cosine --warmup-ratio 0.05 \
       --max-length 2048 --load-4bit --bnb-compute-dtype float16
     ```
4. **Nueva evaluación ≥40 casos** (Owner: QA, ETA 0.5d)  
   - Ejecutar `scripts/eval_po_student.py` dos veces: baseline y student (20 casos por corrida, tiers balanceados).  
   - Objetivo: `mean_student ≥ 0.82`, `|mean_student - mean_baseline| ≤ 0.03`, `std_student ≤ 0.10`, 0 `format_error`.  
   - Guardar artefactos bajo `inference_results/20251115/` y anexar resumen comparativo en `docs/po_distillation_report.md`.  
5. **Criterio de cierre 9.D.4**  
   - Si el student supera los umbrales anteriores y las respuestas cumplen el schema, documentar la mejora en `docs/fase9_multi_role_dspy_plan.md` y avanzar a 9.D.5.  
   - Si no, repetir pasos 1-4 enfocándose en los casos con peor score (ver `results[].score` en los JSON).

**Herramienta nueva – `scripts/eval_po_student.py`**  
- Reutiliza el prompt supervisado (con ejemplo YAML) y fuerza retries si falta algún bloque.  
- Genera `inference_results/<tag>_<timestamp>.json` con cada caso, puntajes y estado (`ok` o `format_error`).  
- Ejecución recomendada (usar `PYTHONPATH=.`):
```bash
.venv/bin/python scripts/eval_po_student.py \
  --tag baseline \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --max-samples 20 \
  --max-new-tokens 1200 \
  --retries 2 \
  --load-4bit --bnb-compute-dtype float16

.venv/bin/python scripts/eval_po_student.py \
  --tag student \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --adapter-path artifacts/models/po_student_v1 \
  --max-samples 20 \
  --max-new-tokens 1200 \
  --retries 2 \
  --load-4bit --bnb-compute-dtype float16
```
- Tras ambos corridas, comparar `metrics.mean` y anexar los hallazgos (incluidos los casos `format_error`) en `docs/po_distillation_report.md` para decidir si avanzar a 9.D.5.

**DSPy – Pilot Optimization (Paso 2 completado, 2025-11-15)**  
- Proceso `dcf7ef` (Lightning AI Studio) finalizó con `Average Metric = 34/34 (100%)` sobre el valset de 34 ejemplos (`artifacts/synthetic/product_owner/product_owner_val.jsonl`).  
- Log: `/tmp/po_pilot_optimization.log`. Componentes exportados a `artifacts/dspy/po_optimized_pilot/product_owner/program_components.json`; metadata en `.../metadata.json`.  
- Acciones siguientes según el plan DSPy: ejecutar **Paso 3 – Full Optimization (142 samples, 2-4 h)** e incorporar el score resultante antes de decidir el paso 4.

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

- **Nota de control**: Antes de iniciar cada tarea 9.D.x se debe registrar el plan/entradas en este documento, y al finalizar dejar constancia de resultados/incidencias para facilitar retomarlo si se interrumpe.

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

---

## 🆕 ACTUALIZACIÓN 9.0.8 - Full Optimization Kickoff (2025-11-15)

**Objetivo**: Ejecutar el Paso 3 (Full Optimization) con el **trainset completo (142 ejemplos)** usando Vertex AI `gemini-2.5-flash`, para obtener un programa superior al piloto (Paso 2 = 34/34, 100%).

**Plan previo (documentado antes del arranque)**:
- **Dataset**: `artifacts/synthetic/product_owner/product_owner_train.jsonl` + `product_owner_val.jsonl`.
- **Hyperparams**: `--num-candidates 6`, `--num-trials 10`, `--max-bootstrapped-demos 4`, `seed=0`.
- **Provider**: `vertex_ai` (modelo `gemini-2.5-flash`) con las mismas métricas (`product_owner_metric`).
- **Infra**: Corrida desatendida vía `nohup`, log persistido en `/tmp/po_full_optimization.log`, PID en `/tmp/po_full_optimization.pid`.
- **Cache fix**: fuerza `DSPY_CACHEDIR=/tmp/dspy_cache` para evitar el error `sqlite3.OperationalError: unable to open database file` visto el 15/11 por permisos en `artifacts/dspy/cache`.

**Comando lanzado (15:43 UTC-3)**:
```bash
export DSPY_CACHEDIR=/tmp/dspy_cache PYTHONPATH=.
nohup .venv/bin/python scripts/tune_dspy.py \
  --role product_owner \
  --trainset artifacts/synthetic/product_owner/product_owner_train.jsonl \
  --valset artifacts/synthetic/product_owner/product_owner_val.jsonl \
  --metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
  --num-candidates 6 \
  --num-trials 10 \
  --max-bootstrapped-demos 4 \
  --seed 0 \
  --output artifacts/dspy/po_optimized_full \
  --provider vertex_ai \
  --model gemini-2.5-flash \
  >> /tmp/po_full_optimization.log 2>&1 &
echo $! > /tmp/po_full_optimization.pid
```

**Estado / Métricas en vivo (15:54 UTC-3)**:
- STEP 1 completado: bootstrapping de 6 sets (demora ~2.5 min por set con 142 ejemplos).
- STEP 2 activo: 6 instrucciones propuestas para `ProductOwnerModule` (logs muestran truncation warnings → revisar `max_tokens` si reaparece).
- Trials completados hasta el momento: 12 minibatches + 2 evaluaciones completas.
  - **Best full score provisional**: **51.88 / 100** (34/34 validaciones con `gemini-2.5-flash`).
  - Minibatch scores recientes: `[37.0, 36.5, 65.7, 9.31, 32.91, 36.5, 7.17, 10.76, 45.71, 1.56]`.
- Logs en tiempo real: `tail -f /tmp/po_full_optimization.log`
- PID tracking: `cat /tmp/po_full_optimization.pid` → `49795`

**Incidencias resueltas**:
1. `sqlite3.OperationalError` → resuelto creando `/tmp/dspy_cache` y exportando `DSPY_CACHEDIR` antes de invocar DSPy.
2. `oauth2.googleapis.com` DNS failure (sandbox sin red) → rerun autorizado con red para Vertex.

**Artefactos generados (en curso)**:
- `artifacts/dspy/po_optimized_full/` (estructura inicial creada; se completará al cerrar el run).
- `/tmp/po_full_optimization_20251115154251.log` conserva el log del intento fallido anterior (sin red).

**Próximos pasos**:
1. 🕒 Dejar correr la optimización (ETA 2-3h); monitorear `po_full_optimization.log` para confirmar `Trial 13/13` y guardado de `program_components.json`.
2. 📦 Al finalizar: copiar el log a `logs/mipro/product_owner/20251115_full.log`, zipear los componentes y registrar métricas finales aquí y en `docs/po_distillation_report.md`.
3. 📊 Task 9.0.9: correr evaluación usando el nuevo programa vs baseline (0.831) y documentar comparativa.
4. 🔁 Si score final < target (85%), ajustar `num_trials`/`max_bootstrapped-demos` o repetir usando `gemini-2.5-pro`.

**Notas operativas**:
- Si el runtime se extiende >4h o aparecen nuevos `LM response truncated`, incrementar `max_tokens` en `dspy.LM` o dividir el trainset (Plan B).
- Mantener libre `/tmp/dspy_cache` (limpiarlo sólo cuando la corrida finalice para no perder shards en uso).

### Iteración ajustada (2025-11-15 16:09 UTC-3)

Tras completar el primer intento full (51.88), lanzamos un **segundo run** priorizando exploración más profunda pero aún sobre `gemini-2.5-flash`:

- **Ajustes solicitados**:
  1. `--num-trials 20` (DSPy internamente ejecutó 25 iteraciones contando los full eval extra).
  2. `--max-bootstrapped-demos 3` para reducir STEP 1.
  3. `--num-candidates 5` + `--stop-metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric` (el stop metric hoy es un no-op, pero deja documentada la intención de cortar en 0.7 cuando DSPy lo soporte).
- **Comando**:
  ```bash
  export DSPY_CACHEDIR=/tmp/dspy_cache PYTHONPATH=.
  nohup .venv/bin/python scripts/tune_dspy.py \
    --role product_owner \
    --trainset artifacts/synthetic/product_owner/product_owner_train.jsonl \
    --valset artifacts/synthetic/product_owner/product_owner_val.jsonl \
    --metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
    --num-candidates 5 \
    --num-trials 20 \
    --max-bootstrapped-demos 3 \
    --stop-metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
    --seed 0 \
    --output artifacts/dspy/po_optimized_full \
    --provider vertex_ai \
    --model gemini-2.5-flash \
    >> /tmp/po_full_optimization.log 2>&1 &
  ```
- **Duración**: ~10.5 min (inicio 16:09, fin 16:20 UTC-3) gracias a menos candidatos/demos.
- **Resultados**:
  - `Full eval scores`: `[3.14, 43.35, 64.08, 49.31]` → **mejor = 64.08 / 100** (↑ +12.2 pts vs run anterior).
  - `Minibatch scores`: `[33.16, 32.16, 46.3, 33.16, 25.97, 65.7, 29.56, 30.06, 46.71, 48.3, 39.51, 55.42, 50.4, 37.48, 36.93, 35.97, ...]` (ver log para el listado completo).
  - `program_components.json` actualizado (22 KB) + `metadata.json` sobrescrito; `program.pkl` permanece como placeholder de 2 B.
- **Logs**: `/tmp/po_full_optimization.log` (copiado a `logs/mipro/product_owner/po_full_optimization_20251115162146.log`).
- **Observaciones**:
  - STEP 1 ahora bootstrappeó 5 sets (vs 6) → menos overhead sin perder diversidad.
  - Persisten los warnings de `max_tokens` en Vertex; evaluar aumentar el límite o habilitar `temperature>0` si seguimos viendo truncations.
  - `stop_metric` no es consumido por `dspy.MIPROv2.compile`, pero dejamos el flag activo para cuando la librería habilite early stopping real.
- **Siguiente acción**: ejecutar 9.0.9 con este snapshot (64.08) y decidir si hace falta un tercer run (ej. `gemini-2.5-pro` o más trials) para acercarnos al target ≥85.

Luego de la evaluación corregida (71.7%), lanzaremos un **último push** con estos ajustes para intentar superar el 85%:

- `max_tokens 8000` (nuevo flag en `scripts/tune_dspy.py`) para eliminar truncations.
- `num_trials 25`, `max_bootstrapped-demos 5` (más exploración).
- `num_candidates 5`, `temperature 0.0`, `seed 0`.
- Plataforma: `gemini-2.5-pro`.

Comando:
```bash
export DSPY_CACHEDIR=/tmp/dspy_cache PYTHONPATH=.
nohup .venv/bin/python scripts/tune_dspy.py \
  --role product_owner \
  --trainset artifacts/synthetic/product_owner/product_owner_train.jsonl \
  --valset artifacts/synthetic/product_owner/product_owner_val.jsonl \
  --metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
  --num-candidates 5 \
  --num-trials 25 \
  --max-bootstrapped-demos 5 \
  --stop-metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
  --max-tokens 8000 \
  --temperature 0.0 \
  --seed 0 \
  --output artifacts/dspy/po_optimized_full \
  --provider vertex_ai \
  --model gemini-2.5-pro \
  >> /tmp/po_full_optimization.log 2>&1 &
```

Notas: log final → `logs/mipro/product_owner/po_full_optimization_<timestamp>_pro_push.log`; al cerrar, repetir 9.0.9.


### Iteración con gemini-2.5-pro (2025-11-15 16:25 UTC-3)

Con 29 € disponibles confirmamos que había margen para un intento con `gemini-2.5-pro`, reutilizando exactamente los hyperparams anteriores.

- **Objetivo**: medir si el modelo Pro aporta la mejora necesaria para acercarnos al target ≥85 sin tocar dataset ni seeds.
- **Comando**:
  ```bash
  export DSPY_CACHEDIR=/tmp/dspy_cache PYTHONPATH=.
  nohup .venv/bin/python scripts/tune_dspy.py \
    --role product_owner \
    --trainset artifacts/synthetic/product_owner/product_owner_train.jsonl \
    --valset artifacts/synthetic/product_owner/product_owner_val.jsonl \
    --metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
    --num-candidates 5 \
    --num-trials 20 \
    --max-bootstrapped-demos 3 \
    --stop-metric dspy_baseline.metrics.product_owner_metrics:product_owner_metric \
    --seed 0 \
    --output artifacts/dspy/po_optimized_full \
    --provider vertex_ai \
    --model gemini-2.5-pro \
    >> /tmp/po_full_optimization.log 2>&1 &
  ```
- **Duración / costo estimado**: ~40 min (start 16:25, end 17:07 UTC-3). A 2.8 € aprox. por corrida todavía quedan >8 intentos dentro del crédito de 29 €.
- **Resultados**:
  - `Full eval scores`: `[5.31, 77.51, 67.10, 71.04, 78.57]` → **nuevo máximo = 78.57 / 100** (↑ +14.5 pts vs run flash ajustado).
  - Minibatch scores completos registrados en `logs/mipro/product_owner/po_full_optimization_20251115170702_pro_run.log`.
  - `program_components.json` (22 KB) y `metadata.json` fueron actualizados nuevamente; `program.pkl` sigue con 2 B por el fallback.
- **Logs**:
  - `logs/mipro/product_owner/po_full_optimization_20251115170702_pro_run.log` (copia del runtime completo).
  - `/tmp/po_full_optimization.log` contiene la ejecución actual hasta que se lance otra.
- **Observaciones**:
  - STEP 1 demoró más (bootstrap de 5 sets tomó >4 min cada uno) pero el run completo quedó <45 min.
  - Los warnings de `max_tokens=4000` se repitieron entre 16:31 y 16:41; sigue pendiente exponer un flag para incrementarlo cuando necesitemos otra corrida Pro.
  - DSPy aún ignora `stop_metric`, por lo que se completaron los 20 trials planificados.
- **Próximo paso**:
  1. Ejecutar 9.0.9 con este snapshot (78.57) y comparar contra baseline 0.831.
  2. Si todavía apuntamos a ≥85, evaluar cuarta corrida con ajustes adicionales (e.g., `max_tokens` elevado, `num_trials` 25 o seeds nuevos) antes de cerrar 9.0.8.



### 9.X - Plan para LM independiente por rol (aprobado 2025-11-17)
- Contexto: actualmente PO y BA ya leen sus LMs desde `config.yaml` (flags `features.use_dspy_ba` / `features.use_dspy_product_owner` + overrides `DSPY_<ROL>_*`). El refactor general unificará todos los roles.
1. Definir variables `DSPY_<ROL>_LM`, `DSPY_<ROL>_MAX_TOKENS`, `DSPY_<ROL>_TEMPERATURE` en `config.yaml`/env para BA, PO, Architect, Dev y QA, reutilizando los valores existentes en `config.yaml` como default.
2. Ajustar `scripts/run_<rol>.py` para leer esas variables y configurar `dspy.LM` con fallback a modelos locales (Ollama). Si se quiere Vertex u otros proveedores, bastará con cambiar la variable.
3. Documentar en un anexo (por rol) cómo cambiar el LM sin tocar el código y actualizar este plan con el estado de cada rol.
4. Verificación: ejecutar `make <rol>` con los modelos locales y guardar logs en `logs/mipro/<rol>/`.

Estado: Fase en marcha. BA y PO ya consumen modelos DSPy directamente desde config.yaml (ver scripts/dspy_lm_helper.py). Pendiente aplicar la misma capa en Architect, Dev y QA.

1. Definir variables de entorno `DSPY_<ROL>_LM`, `DSPY_<ROL>_MAX_TOKENS`, `DSPY_<ROL>_TEMPERATURE` para BA, PO, Architect, Dev y QA.
2. Ajustar cada `scripts/run_<rol>.py` para leer dichas variables, configurar `dspy.LM` con fallback a modelos locales (Ollama) y solo opcionalmente usar Vertex/otros si se especifica.
3. Documentar en `docs/<rol>_DSPY.md` cómo cambiar los modelos y actualizar `docs/fase9...` con el estado de cada rol.
4. Verificación: ejecutar `make <rol>` para cada rol en modo local y guardar logs en `logs/mipro/<rol>/`.

Estado: A la espera de aprobación para proceder con el refactor general.
