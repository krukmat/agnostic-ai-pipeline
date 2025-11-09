# Fase 9: Multi-Role DSPy MIPROv2 Optimization - Plan Detallado

**Fecha Inicio**: 2025-11-09
**Branch**: `dspy-multi-role`
**Objetivo**: Extender optimización DSPy MIPROv2 a roles Architect, Developer y QA
**Precedente**: Fase 8 - BA optimizado con 85.35% score (+13.35% vs baseline 72%)

---

## 📋 Resumen Ejecutivo

### Contexto

Fase 8 demostró que DSPy MIPROv2 es **extremadamente efectivo** para optimización de roles:
- **Tiempo**: 3 horas vs 200+ horas de fine-tuning
- **Score**: 85.35% (mejora de +13.35% vs baseline)
- **Costo**: $0 (100% local con Ollama)
- **Iterabilidad**: Alta (cambios en segundos)

**Decisión**: Extender este enfoque exitoso a los 3 roles restantes del pipeline.

### Objetivos Fase 9

1. **Architect**: Optimizar generación de historias técnicas (epics → stories)
2. **Developer**: Optimizar generación de código + tests
3. **QA**: Optimizar generación de reportes de calidad

**Meta Global**: Pipeline completo con 4/4 roles optimizados, manteniendo 100% local + $0 costo.

---

## 🎯 Objetivos por Rol

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
**Total Fase 9**: ~9-12 días (secuencial) o ~5-6 días (paralelo)

---

## 📁 Estructura de Artefactos

### Datasets (por rol)

```
artifacts/synthetic/
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
   - Architect: genera stories.yaml + architecture.yaml
   - Developer: genera código + tests
   - QA: genera qa_report.yaml

3. **`scripts/filter_synthetic_data.py`** ⚠️
   - Requiere métricas específicas por rol
   - Architect: metric `architect_stories_metric`
   - Developer: metric `developer_code_metric`
   - QA: metric `qa_report_metric`

4. **`scripts/split_dataset.py`** ✅
   - Genérico, funciona para todos los roles

### Scripts Nuevos a Crear

1. **`scripts/generate_architect_concepts.py`**
   - Similar a `generate_business_concepts.py`
   - Genera requirements sintéticos como input para Architect

2. **`scripts/generate_developer_stories.py`**
   - Genera stories sintéticas como input para Developer
   - Incluye architecture context

3. **`scripts/generate_qa_implementations.py`**
   - Genera código + tests sintéticos como input para QA
   - Incluye story context

4. **`dspy_baseline/metrics.py`** (extender)
   - `architect_stories_metric(gold, pred, trace=None)`
   - `developer_code_metric(gold, pred, trace=None)`
   - `qa_report_metric(gold, pred, trace=None)`

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
| Architect optimizado | ≥80% | `architect_stories_metric` en validation set |
| Developer optimizado | ≥75% | `developer_code_metric` en validation set |
| QA optimizado | ≥85% | `qa_report_metric` en validation set |
| Mejora promedio | ≥+20% | (optimized - baseline) / baseline |
| Costo total | $0 | 100% local con Ollama |
| Tiempo total | ≤15 días | Desde inicio hasta integración completa |
| Pipeline completo optimizado | 4/4 roles | BA, Architect, Dev, QA con DSPy MIPROv2 |

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

- `scripts/generate_architect_concepts.py`
- `scripts/generate_developer_stories.py`
- `scripts/generate_qa_implementations.py`
- Extensiones en `scripts/generate_synthetic_dataset.py`
- Extensiones en `scripts/filter_synthetic_data.py`

### Métricas

- `dspy_baseline/metrics.py`:
  - `architect_stories_metric()`
  - `developer_code_metric()`
  - `qa_report_metric()`

### Datasets

- `artifacts/synthetic/architect/` (6 archivos)
- `artifacts/synthetic/developer/` (6 archivos)
- `artifacts/synthetic/qa/` (6 archivos)

### Modelos Optimizados

- `artifacts/dspy/architect_optimized/program.pkl`
- `artifacts/dspy/developer_optimized/program.pkl`
- `artifacts/dspy/qa_optimized/program.pkl`

### Documentación

- `docs/fase9_multi_role_dspy_plan.md` (este documento)
- `docs/fase9_architect_optimization.md`
- `docs/fase9_developer_optimization.md`
- `docs/fase9_qa_optimization.md`
- `docs/fase9_final_report.md`

---

## 🏁 Criterios de Completitud Fase 9

### Mínimo Viable (MVP)

1. ✅ Al menos 2/3 roles optimizados (Architect + Developer)
2. ✅ Mejora ≥+15% en cada rol optimizado
3. ✅ Pipeline funcional end-to-end
4. ✅ Documentación completa
5. ✅ $0 costo (100% local)

### Objetivo Ideal

1. ✅ 3/3 roles optimizados (Architect + Developer + QA)
2. ✅ Mejora ≥+20% en cada rol
3. ✅ Pipeline optimizado completo (4/4 roles con BA)
4. ✅ Benchmarks reproducibles
5. ✅ Tiempo total ≤15 días

---

## 🚀 Próximos Pasos Inmediatos

### Paso 1: Setup Inicial

```bash
# Crear estructura de directorios
mkdir -p artifacts/synthetic/{architect,developer,qa}
mkdir -p artifacts/dspy/{architect_optimized,developer_optimized,qa_optimized}

# Verificar dependencias
.venv/bin/python -c "import dspy; print('DSPy OK')"

# Confirmar Ollama disponible
ollama list | grep mistral
```

### Paso 2: Comenzar con Architect (Fase 9.1)

```bash
# Leer plan específico
cat docs/fase9_architect_optimization.md

# Comenzar con tarea 9.1.1
# (Análisis de output Architect actual)
```

### Paso 3: Crear Plan de Trabajo Diario

Ver sección "Orden de Ejecución Recomendado" abajo.

---

## 📅 Orden de Ejecución Recomendado

### Semana 1 (Días 1-5): Architect

- **Día 1**: Tareas 9.1.1 - 9.1.3 (análisis, métrica, conceptos)
- **Día 2**: Tareas 9.1.4 - 9.1.6 (generación dataset, filtrado, split)
- **Día 3**: Tareas 9.1.7 - 9.1.8 (baseline evaluation, optimization)
- **Día 4**: Tarea 9.1.9 (evaluation & comparison)
- **Día 5**: Tarea 9.1.10 (integration & testing) + buffer

### Semana 2 (Días 6-10): Developer

- **Día 6**: Tareas 9.2.1 - 9.2.2 (análisis, métrica)
- **Día 7**: Tareas 9.2.3 - 9.2.4 (generación stories, dataset)
- **Día 8**: Tareas 9.2.5 - 9.2.7 (filtrado, split, baseline)
- **Día 9**: Tarea 9.2.8 (optimization)
- **Día 10**: Tareas 9.2.9 - 9.2.10 (evaluation, integration) + buffer

### Semana 3 (Días 11-13): QA

- **Día 11**: Tareas 9.3.1 - 9.3.4 (análisis, métrica, generación)
- **Día 12**: Tareas 9.3.5 - 9.3.8 (filtrado, split, baseline, optimization)
- **Día 13**: Tareas 9.3.9 - 9.3.10 (evaluation, integration)

### Semana 3 (Días 14-15): Cierre

- **Día 14**: Reporte final, benchmarks comparativos
- **Día 15**: Documentación, limpieza, commit final

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
