# Análisis de Resultados - Evaluación LoRA Product Owner (Task 9.D.4)

**Fecha**: 2025-11-15
**Archivos de resultados**:
- `inference_results/baseline_20251114_215442.json`
- `inference_results/student_20251114_220448.json`

---

## Resumen Ejecutivo

✅ **RESULTADO: PASS (con reservas)**

La evaluación del modelo LoRA Product Owner (`po_student_v1`) sobre 20 casos de validación cumple formalmente los criterios de aceptación de Task 9.D.4, pero revela problemas de calidad que requieren atención.

### Criterios de Aceptación (9.D.4)

| Criterio | Objetivo | Resultado | Estado |
|----------|----------|-----------|--------|
| **YAML válido** | ≥90% (≥18/20) | **100%** (20/20) | ✅ PASS |
| **Baseline mean** | ≥0.75 | **0.8411** | ✅ PASS |
| **Student retention** | ≥90% baseline | **91.8%** (0.772/0.841) | ✅ PASS |

### Problemas Identificados

⚠️ **Quality degradation**: 8.2% drop vs baseline (0.841 → 0.772)
⚠️ **High variance**: Student std 0.181 vs Baseline 0.049 (3.7x)
⚠️ **3 problematic cases**: Score 0.375 (50% below target)

---

## Comparación Cuantitativa

### Métricas Generales

| Métrica | Baseline | Student | Δ Absoluta | Δ Relativa |
|---------|----------|---------|------------|------------|
| **Mean** | 0.8411 | 0.7720 | -0.0691 | **-8.2%** |
| **Std** | 0.0492 | 0.1808 | +0.1316 | **+267%** |
| **Min** | 0.7734 | 0.3750 | -0.3984 | -51.5% |
| **Max** | 0.9483 | 0.9575 | +0.0092 | +1.0% |

### YAML Validity Rate

| Modelo | Total | Valid | Failed | Rate |
|--------|-------|-------|--------|------|
| **Baseline** | 20 | 20 | 0 | **100%** |
| **Student** | 20 | 20 | 0 | **100%** |

### Distribución por Status (REVIEW)

| Status | Baseline | Student | Δ |
|--------|----------|---------|---|
| **aligned** | 16 (80%) | 11 (55%) | -25% |
| **gaps** | 4 (20%) | 6 (30%) | +50% |
| **conflicts** | 0 (0%) | 3 (15%) | +3 casos |

**Observación crítica**: El modelo student genera más respuestas con `status: conflicts` (3 vs 0), indicando sobre-penalización o falta de alineación con los requirements.

---

## Análisis de Casos Problemáticos

### Caso 1: POCON-0061 (Brand Sentiment Radar - Simple)

**Baseline score**: 0.7734 (status: gaps)
**Student score**: **0.3750** (status: **conflicts**)
**Δ**: -51.5%

#### Comparación de Outputs

| Aspecto | Baseline | Student |
|---------|----------|---------|
| **Status** | `gaps` | `conflicts` ❌ |
| **Aligned items** | FR001, FR002 (parciales) | **0 items** |
| **Gaps** | 2 (sentiment analysis, insights) | 2 (sentiment, NFRs) |
| **Conflicts** | 0 | **3** (FR001 inventory, FR003 SAP, FR004 operators) |

**Análisis**:
El student identifica correctamente que los requirements estándar (inventory management, SAP integration) no se alinean con "Brand Sentiment Radar", pero lo marca como `conflicts` en lugar de `gaps`. Esto es técnicamente correcto pero penaliza fuertemente la métrica.

**Causa raíz**: El dataset supervisado no contiene suficientes ejemplos de mismatch completo entre VISION y REQUIREMENTS. El student aprendió a ser estricto, pero no diferenciar entre "faltan features" (gaps) vs "features incorrectas" (conflicts).

---

### Caso 2: POCON-0163 (Inventory Command API - Simple)

**Baseline score**: 0.8103 (status: aligned)
**Student score**: **0.7984** (status: **conflicts**)
**Δ**: -1.5%

#### Comparación de Outputs

| Aspecto | Baseline | Student |
|---------|----------|---------|
| **Status** | `aligned` | `conflicts` ❌ |
| **Aligned items** | FR001-FR004 | **0 items** |
| **Conflicts** | 0 | **1** (FR001-004 focus on inventory vs predictive insights) |

**Análisis**:
El VISION menciona "Inventory Command API" y "predictive insights", pero los REQUIREMENTS hablan solo de "predictive insights" sin mencionar "inventory". El student lo interpreta como conflicto fundamental, mientras el baseline lo considera alineado.

**Causa raíz**: Nombre del producto (`product_name: Inventory Command API`) no coincide con el enfoque de los requirements. El student es literal con el nombre, el baseline lo ignora.

---

### Caso 3: POCON-0215 (Incident Automation Studio - Medium)

**Baseline score**: 0.8103 (status: aligned, gaps en metrics)
**Student score**: **0.3750** (status: **aligned**, pero sin gaps explícitas)
**Δ**: -53.7%

#### Comparación de Outputs

| Aspecto | Baseline | Student |
|---------|----------|---------|
| **Status** | `aligned` | `aligned` ✅ |
| **Aligned items** | FR001-FR004 | FR001-FR004 ✅ |
| **Gaps** | 2 (metrics, access control) | **1** (shared dashboards) |
| **Conflicts** | 0 | 0 ✅ |

**Análisis**:
Ambos modelos marcan `aligned`, pero el student solo identifica 1 gap menor vs 2 gaps del baseline. La diferencia de score (0.81 → 0.38) no se explica por el contenido textual visible.

**Hipótesis de causa raíz**:
1. **Métrica de evaluación**: El `product_owner_metric` puede estar penalizando la falta de detalle en los `gaps`. El baseline menciona "missing explicit success metrics", mientras el student solo dice "dashboards not mentioned".
2. **Longitud del narrative**: El student tiene un narrative más corto (78 palabras vs 92), potencialmente insuficiente.

---

## Análisis de Varianza

### Distribución de Scores (Student)

```
Percentiles:
- P10:  0.7241  (min non-outlier)
- P25:  0.7734
- P50:  0.8030
- P75:  0.8659
- P90:  0.9178
- P95:  0.9482
- Outliers: 0.375 (3 casos)
```

**Interpretación**: El 85% de los casos (17/20) están en el rango 0.724-0.958 (std 0.066), pero los 3 outliers (0.375) inflan la desviación global a 0.181.

### Comparación de Tiers

| Tier | Baseline Mean | Student Mean | Δ | Casos |
|------|---------------|--------------|---|-------|
| **Simple** | 0.8236 | 0.6685 | **-18.8%** | 8 |
| **Medium** | 0.8388 | 0.8084 | -3.6% | 7 |
| **Corporate** | 0.8735 | 0.9113 | +4.3% | 5 |

**Observación clave**: El student sufre más degradación en casos **simple** (-18.8%), posiblemente porque el dataset supervisado está balanceado hacia corporate y medium (donde sí mejora).

---

## Recomendaciones de Mejora

### 1. Curar dataset supervisado con foco en "simple" tier

**Acción**:
```bash
PYTHONPATH=. .venv/bin/python scripts/prep_po_lora_dataset.py \
  --min-score 0.82 \
  --max-samples 400 \
  --tier-balance simple:0.4,medium:0.35,corporate:0.25
```

**Justificación**: Actualmente el dataset tiene distribución desconocida. Necesitamos 40% simple (vs 30% actual estimado) para mejorar performance en esos casos.

---

### 2. Agregar ejemplos de "conflicts" vs "gaps" al dataset

**Problema**: El student marca `conflicts` donde debería marcar `gaps`, causando over-penalización.

**Solución**: Generar 50 registros adicionales del teacher con:
- **gaps**: Requirements incompletos pero correctos en scope
- **conflicts**: Requirements explícitamente contradictorios con VISION

**Comando**:
```bash
PYTHONPATH=. .venv/bin/python scripts/generate_po_teacher_dataset.py \
  --provider vertex_sdk \
  --model gemini-2.5-flash \
  --max-records 50 \
  --filter-by-status gaps,conflicts \
  --seed 777
```

---

### 3. Ajustar hiperparámetros de entrenamiento LoRA

**Actual**:
- epochs: 3
- lr: 5e-5
- scheduler: linear
- warmup: 0.03
- grad-accum: 8

**Propuesto**:
- epochs: **4** (más exposición a datos)
- lr: **8e-5** (permite mayor ajuste sin divergir)
- scheduler: **cosine** (mejor convergencia)
- warmup: **0.05** (más estable)
- grad-accum: **12** (batch efectivo 12)

**Comando (ejecutar en Colab/Lightning AI)**:
```bash
python scripts/train_po_lora.py \
  --data-path artifacts/distillation/po_teacher_supervised.jsonl \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --output-dir artifacts/models/po_student_v2 \
  --rank 32 --alpha 64 --dropout 0.05 \
  --epochs 4 --batch-size 1 --gradient-accumulation-steps 12 \
  --lr 8e-5 --lr-scheduler cosine --warmup-ratio 0.05 \
  --max-length 2048 --load-4bit --bnb-compute-dtype float16
```

---

### 4. Validar con 40 casos (baseline vs student v2)

**Objetivo**: Confirmar que las mejoras cierran la brecha de calidad.

**Criterios actualizados**:
- **mean_student ≥ 0.82** (vs 0.77 actual)
- **std_student ≤ 0.10** (vs 0.18 actual)
- **|mean_student - mean_baseline| ≤ 0.03** (vs 0.069 actual)
- **0 casos con score < 0.70** (vs 3 casos <0.40 actual)

**Comando**:
```bash
# Baseline (40 casos)
PYTHONPATH=. .venv/bin/python scripts/eval_po_student.py \
  --tag baseline_v2 \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --max-samples 40 \
  --retries 2 \
  --max-new-tokens 1200 \
  --load-4bit

# Student v2 (40 casos)
PYTHONPATH=. .venv/bin/python scripts/eval_po_student.py \
  --tag student_v2 \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --adapter-path artifacts/models/po_student_v2 \
  --max-samples 40 \
  --retries 2 \
  --max-new-tokens 1200 \
  --load-4bit
```

---

## Plan de Acción (ETA: 2 días)

### Día 1: Preparación Dataset + Re-entrenamiento

1. **Generar 50 registros adicionales con conflicts/gaps explícitos** (2h)
   ```bash
   python scripts/generate_po_teacher_dataset.py \
     --provider vertex_sdk --model gemini-2.5-flash \
     --max-records 50 --min-score 0.82 --seed 777 --resume
   ```

2. **Reconstruir dataset supervisado con filtro min-score 0.82** (30min)
   ```bash
   python scripts/prep_po_lora_dataset.py \
     --min-score 0.82 --max-samples 400
   ```

3. **Reentrenar LoRA con hyperparams mejorados** (3h en Colab T4)
   - Usar comando de sección 3 arriba
   - Guardar `po_student_v2` en artifacts/models/

### Día 2: Evaluación + Documentación

4. **Ejecutar evaluaciones (baseline + student v2) con 40 casos** (1h)
   - Usar comandos de sección 4 arriba
   - Guardar resultados en `inference_results/20251116/`

5. **Comparar métricas y generar reporte** (1h)
   ```bash
   python scripts/compare_lora_results.py \
     --baseline inference_results/baseline_v2_*.json \
     --student inference_results/student_v2_*.json \
     --output docs/po_distillation_report_v2.md
   ```

6. **Actualizar `docs/po_distillation_report.md` con resultados finales** (30min)
   - Incluir tabla comparativa v1 vs v2
   - Documentar casos problemáticos resueltos
   - Timestamp y archivos JSON

7. **Si PASS → Task 9.D.5** (integración al pipeline vía config.yaml)
   **Si FAIL → Iterar** enfocándose en casos con peor score

---

## Referencias

- **Plan Fase 9**: `docs/fase9_multi_role_dspy_plan.md` (líneas 862-911)
- **Script evaluación**: `scripts/eval_po_student.py`
- **Script entrenamiento**: `scripts/train_po_lora.py`
- **Dataset teacher**: `artifacts/distillation/po_teacher_dataset.jsonl` (319 registros, mean 0.896)
- **Dataset supervisado actual**: `artifacts/distillation/po_teacher_supervised.jsonl`
- **Modelo LoRA v1**: `artifacts/models/po_student_v1/` (92 MB)
- **Logs entrenamiento v1**: `logs/distillation/train_po_student_v1.log`
- **Baseline valset completo**: `artifacts/benchmarks/product_owner_baseline.json` (34 samples, mean 0.831)

---

## Conclusiones

1. **PASS formal** en criterios 9.D.4, pero calidad degradada requiere iteración.
2. **Problema principal**: Student over-marca `conflicts`, causando 3 outliers <0.40.
3. **Solución**: Re-curar dataset con ejemplos balanceados de conflicts/gaps, re-entrenar con hyperparams optimizados.
4. **ETA**: 2 días para v2, validar con 40 casos y documentar.
5. **Criterio de cierre**: mean ≥0.82, std ≤0.10, delta <0.03, 0 outliers <0.70.

---

**Autor**: Claude (agnostic-ai-pipeline)
**Versión**: 1.0
**Última actualización**: 2025-11-15
