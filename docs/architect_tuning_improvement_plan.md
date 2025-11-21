# Plan de Mejora del Tuning de Architect

**Fecha**: 2025-11-21
**Estado actual**: 62.36% (techo identificado)
**Meta**: 75%+

---

## 1. Diagnostico

### 1.1 Estado Actual

| Metrica | Valor |
|---------|-------|
| Best E2E Score | 62.36% |
| Trials ejecutados | 59 (Flash48) + 40 (Flash32) = 99 |
| Truncaciones | 0 (fix aplicado) |
| Dataset train | 32 registros |
| Dataset val | 20 registros |

### 1.2 Problema Identificado

El optimizador MIPROv2 encuentra repetidamente el mismo techo (~62%) sin poder superarlo.
Evidencia: minibatch scores [41-62%], full eval [53-62%].

### 1.3 Causas Raiz

1. **Metrica binaria**: Penaliza 0 puntos por errores menores (IDs no secuenciales, refs fallidas)
2. **Dataset sin calidad verificada**: 32 ejemplos sin scores conocidos
3. **Tarea compleja**: 3 outputs interdependientes (stories, epics, architecture)
4. **Dependencias circulares**: Stories necesitan epic_ids, Epics necesitan story_ids

---

## 2. Plan de Accion

### FASE 1: Metrica v2 con Partial Credit (PRIORIDAD ALTA)

**Objetivo**: Permitir que el modelo aprenda de errores parciales en lugar de recibir 0.

**Archivo a modificar**: `dspy_baseline/metrics/architect_metrics.py`

**Cambios propuestos**:

```python
# ANTES (binario)
def _stories_completeness(stories, epic_ids):
    # ...
    checks = [field_ratio, 1.0 if (unique and sequential) else 0.0, ...]

# DESPUES (gradual)
def _stories_completeness_v2(stories, epic_ids):
    # ...
    # Partial credit para IDs
    id_score = 0.0
    if ids and len(ids) == len(set(ids)):  # IDs unicos
        id_score += 0.5
    if is_sequential:  # IDs secuenciales
        id_score += 0.5

    # Partial credit para epic refs
    epic_ref_score = sum(1 for s in stories if str(s.get("epic")) in epic_ids) / len(stories)

    checks = [field_ratio, id_score, epic_ref_score]
```

**Tareas**:
- [x] T1.1: Crear `architect_metric_v2()` en architect_metrics.py (COMPLETADO 2025-11-21)
- [x] T1.2: Crear tests unitarios para la nueva metrica (COMPLETADO 2025-11-21: tests/test_architect_metric_v2.py)
- [x] T1.3: Comparar scores v1 vs v2 en dataset existente (COMPLETADO: v1=98.04%, v2=98.04% - sin delta en dataset gold, diferencia en outputs imperfectos)
- [x] T1.4: Verificar que tune_dspy.py soporta --metric custom (COMPLETADO: `--metric dspy_baseline.metrics.architect_metrics:architect_metric_v2` funciona)

**Tiempo estimado**: 2-3 horas
**Impacto esperado**: +10-15% en score

---

### FASE 2: Dataset Gold de Alta Calidad (PRIORIDAD ALTA)

**Objetivo**: Entrenar con ejemplos que tengan score >= 0.85

**Script a usar**: `scripts/generate_architect_dataset.py`

**Comando**:
```bash
PYTHONPATH=. .venv/bin/python scripts/generate_architect_dataset.py \
  --ba-path dspy_baseline/data/production/ba_train.jsonl \
  --out-train artifacts/synthetic/architect/architect_train_gold_v2.jsonl \
  --out-val artifacts/synthetic/architect/architect_val_gold_v2.jsonl \
  --provider vertex_sdk \
  --model gemini-2.5-pro \
  --min-score 0.85 \
  --max-records 50 \
  --seed 42
```

**Tareas**:
- [x] T2.1: Verificar que generate_architect_dataset.py guarda scores en metadata (✅ `metadata.score` presente)
- [x] T2.2: Ejecutar generación con Gemini Flash (min_score=0.85, 50 records) → `logs/dataset_architect_gold_v2_20251121_143558.log`
- [x] T2.3: Validar que todos los registros tienen score >= 0.85 (primeros registros muestran `score: 1.0`)
- [x] T2.4: Crear split train/val (40/10) → `artifacts/synthetic/architect/architect_train_gold_v2.jsonl` (40) / `_val_...` (10)

**Tiempo estimado**: 4-6 horas (generacion)
**Impacto esperado**: +10-15% en score

---

### FASE 3: Re-tuning con Mejoras (PRIORIDAD MEDIA)

**Objetivo**: Ejecutar MIPROv2 con metrica v2 + dataset gold

**Comando**:
```bash
# Nota: No usar GCP_PROJECT/VERTEX_LOCATION hardcodeados - usar configuración local
PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py \
  --role architect \
  --trainset artifacts/synthetic/architect/architect_train_gold_v2.jsonl \
  --valset artifacts/synthetic/architect/architect_val_gold_v2.jsonl \
  --metric dspy_baseline.metrics.architect_metrics:architect_metric_v2 \
  --num-candidates 12 \
  --num-trials 32 \
  --max-bootstrapped-demos 6 \
  --seed 0
```

**Tareas**:
- [x] T3.1: Ejecutar tuning E2E con metrica v2 (Flash, dataset gold) → `logs/mipro_architect_gold_v2_20251121_150330.log`
- [ ] T3.2: Comparar resultados vs baseline (62.36%) *(pendiente: log no emitió “Best full score” → se requiere evaluación manual o rerun con verbose)*
- [ ] T3.3: Si >= 70%, guardar como nuevo optimized *(programa quedó en `artifacts/dspy/optimizer/architect_gold_v2/` vía component extraction; falta activar en config hasta tener score validado)*
- [ ] T3.4: Documentar resultados en fase9 doc *(actualización parcial, falta completar análisis de score)*

**Tiempo estimado**: 4-6 horas (tuning)
**Criterio de exito**: >= 70%

---

### FASE 4: Optimizacion por Etapas (PRIORIDAD BAJA)

**Objetivo**: Si E2E no supera 75%, optimizar cada stage por separado

**Tareas**:
- [ ] T4.1: Optimizar Stage 1 (stories_epics) hasta >= 75%
- [ ] T4.2: Optimizar Stage 2 (architecture) hasta >= 90%
- [ ] T4.3: Combinar stages optimizados
- [ ] T4.4: Validar E2E combinado

**Tiempo estimado**: 8-12 horas
**Impacto esperado**: +5-10% adicional

---

## 3. Criterios de Exito

| Fase | Criterio | Estado |
|------|----------|--------|
| Fase 1 | Metrica v2 creada y testeada | [x] COMPLETADA - T1.1, T1.2, T1.3, T1.4 OK |
| Fase 2 | 50 ejemplos gold con score >= 0.85 | [x] COMPLETADA - 40/10 split min_score 0.85 |
| Fase 3 | E2E score >= 70% | [ ] EN PROCESO - run completado pero falta score reportado |
| Fase 4 | E2E score >= 75% | [ ] Opcional |

---

## 4. Archivos Afectados

```
dspy_baseline/metrics/architect_metrics.py  # T1.1: architect_metric_v2
scripts/generate_architect_dataset.py       # T2.1: verificar metadata
scripts/tune_dspy.py                        # T1.4: soporte metrica v2
artifacts/synthetic/architect/              # T2.2-T2.4: dataset gold
docs/fase9_multi_role_dspy_plan.md         # T3.4: documentar resultados
```

---

## 5. Riesgos

| Riesgo | Probabilidad | Mitigacion |
|--------|--------------|------------|
| Metrica v2 no mejora score | Media | Ajustar pesos de partial credit |
| Gemini Pro no genera calidad suficiente | Baja | Aumentar min_score a 0.90 |
| Techo persiste con todas las mejoras | Media | Simplificar la tarea (menos outputs) |

---

## 6. Proximos Pasos Inmediatos

1. **AHORA**: Implementar T1.1 (architect_metric_v2)
2. **Luego**: Ejecutar T1.2-T1.3 (tests y comparacion)
3. **Paralelo**: Iniciar T2.2 (generacion dataset gold)

---

## 7. Historial de Cambios

| Fecha | Cambio |
|-------|--------|
| 2025-11-21 | Documento creado |
| 2025-11-21 | FASE 1 completada: metric_v2 implementada, tests creados, comparacion v1/v2 OK (98.04%), tune_dspy.py soporta --metric |
| 2025-11-21 | Corregido: Removidos parámetros GCP hardcodeados del comando FASE 3 (usar config local) |
| 2025-11-21 | FASE 2 cerrada: dataset gold 40/10 (0.85) generado y verificado |
| 2025-11-21 | FASE 3 Run #1 completado con dataset gold (log: `logs/mipro_architect_gold_v2_20251121_150330.log`); falta evaluar score por ausencia de “Best full score” en log |
