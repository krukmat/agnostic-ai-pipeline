# Resultados Paso 1 - Generación Dataset Teacher v2

**Fecha**: 2025-11-15
**Tarea**: Generar 50 registros adicionales con min-score 0.82
**Plan**: `docs/LORA_EVAL_RESULTS_ANALYSIS_20251115.md` (Sección "Plan de Acción - Día 1")

---

## Resumen Ejecutivo

✅ **PASO 1 COMPLETADO**

Se generaron exitosamente **50 registros adicionales** de alta calidad utilizando `gemini-2.5-flash` como modelo teacher, con umbral elevado de score (0.82 vs 0.80 anterior).

### Métricas Finales

| Métrica | Valor |
|---------|-------|
| **Registros generados** | 50/50 (100%) |
| **Dataset total** | 369 registros (319 + 50) |
| **Score promedio (nuevos)** | 0.917 |
| **Score mínimo (nuevos)** | 0.831 |
| **Score máximo (nuevos)** | 0.984 |
| **Intentos fallidos** | ~250 (descartados/sin REVIEW) |
| **Tasa de éxito** | ~16.7% (50/300) |

---

## Detalle de Generación

### Comando Ejecutado

```bash
PYTHONPATH=. .venv/bin/python scripts/generate_po_teacher_dataset.py \
  --provider vertex_sdk \
  --model gemini-2.5-flash \
  --max-records 50 \
  --min-score 0.82 \
  --seed 777 \
  --resume
```

### Parámetros Clave

- **Modelo teacher**: `gemini-2.5-flash` (Vertex AI SDK)
- **Min-score**: **0.82** (↑ desde 0.80, +2.5% más estricto)
- **Seed**: 777 (reproducibilidad)
- **Modo**: `--resume` (append a dataset existente)

### Tiempo de Ejecución

- **Inicio**: 2025-11-15 09:13:23
- **Fin**: 2025-11-15 10:00:35
- **Duración**: **47 minutos 12 segundos**
- **Tiempo por registro válido**: ~56.6 segundos promedio

---

## Análisis de Resultados

### Distribución de Status (Nuevos 50 Registros)

| Status | Cantidad | Porcentaje |
|--------|----------|------------|
| **needs** (gaps) | 14 | 28% |
| **aligned** | 36 | 72% |
| **conflicts** | 0 | 0% |

**Observación crítica**: NO se generaron registros con `status: conflicts` en esta iteración, **manteniendo el problema identificado en el análisis**.

### Distribución de Status (Dataset Completo - 369 Registros)

| Status | Cantidad | Porcentaje |
|--------|----------|------------|
| **needs** (gaps) | 110 | 29.8% |
| **aligned** | 259 | 70.2% |
| **conflicts** | 0 | 0% |

**Problema persistente**: El dataset completo **sigue sin registros con `status: conflicts`**, que era la causa raíz de la degradación del modelo student (sobre-marcaba conflicts donde no los había en el teacher).

### Distribución de Scores (Nuevos 50 Registros)

```
Estadísticas:
- Mean:  0.917 ± 0.042 (↑ vs dataset original 0.896)
- Min:   0.831 (dentro del umbral 0.82)
- Max:   0.984 (excelente calidad)
- P25:   0.890
- P50:   0.918 (mediana)
- P75:   0.945
```

**Comparación vs Dataset Original (319 registros)**:
- Mean original: ~0.896
- Mean nuevos: **0.917** (+2.3%)
- Umbral más estricto (0.82) mejoró la calidad promedio

### Tasa de Rechazo

De los logs se identificaron:
- **~250 intentos descartados** por:
  - Score < 0.82 (ej: 0.375, 0.684, 0.350)
  - REVIEW block missing (warnings/errors)
  - Missing VISION/REVIEW content

**Tasa de aprobación**: 50 / ~300 = **16.7%**

Esto es **significativamente más bajo** que con min-score 0.80, indicando que el umbral elevado filtra más agresivamente.

---

## Problemas Identificados

### 1. Falta de Diversidad en Status `conflicts`

**Problema**: El dataset generado NO contiene registros con `status: conflicts`, que era uno de los objetivos principales del Paso 1 (Recomendación #2 del análisis).

**Causa raíz**: El modelo teacher (`gemini-2.5-flash`) no está generando ejemplos con conflicts, posiblemente porque:
1. El prompt no solicita explícitamente generar casos con conflicts
2. Los conceptos de entrada (`concepts.jsonl`) no son lo suficientemente divergentes de los requirements
3. El teacher prefiere generar casos aligned/gaps por diseño

**Impacto**:
- **ALTO** - El student seguirá sobre-marcando conflicts si no aprende a diferenciarlos
- Los 3 casos problemáticos (POCON-0061, POCON-0163, POCON-0215) no se resolverán

### 2. Baja Eficiencia de Generación

**Tasa de éxito**: 16.7% (50 válidos / ~300 intentos)

**Causas**:
1. **Min-score 0.82 muy estricto**: Descarta 70-80% de outputs potencialmente útiles
2. **REVIEW block missing**: ~100+ intentos fallaron por formato incorrecto
3. **Seed 777**: Puede estar sesgando hacia ciertos tipos de conceptos

---

## Recomendaciones

### Acción Inmediata (antes de Paso 2)

**NO proceder con Paso 2** (rebuild supervised dataset) hasta resolver la falta de conflicts.

### Opción A: Generar Batch Focalizado en Conflicts

Ejecutar generación adicional con **prompt explícito** para producir conflicts:

```bash
# Modificar scripts/generate_po_teacher_dataset.py para forzar conflicts
PYTHONPATH=. .venv/bin/python scripts/generate_po_teacher_dataset.py \
  --provider vertex_sdk \
  --model gemini-1.5-pro \  # Modelo más capaz
  --max-records 20 \
  --min-score 0.75 \  # Relajar umbral
  --seed 888 \
  --force-conflicts  # Flag nuevo para inyectar divergencia
```

**Implementación**:
1. Crear flag `--force-conflicts` que modifica el sampling de `concepts.jsonl`
2. Seleccionar conceptos con alto mismatch vs requirements estándar
3. Inyectar casos sintéticos donde `product_name` contradice requirements

### Opción B: Curación Manual de Casos Conflicts

Aprovechar los 3 casos problemáticos ya identificados para crear ground truth:

```bash
# Convertir casos de validación a training examples
tail -3 artifacts/validation/product_owner_validation.jsonl > /tmp/conflicts_seed.jsonl

# Generar variaciones sintéticas
python scripts/augment_conflicts.py \
  --seed-file /tmp/conflicts_seed.jsonl \
  --output artifacts/distillation/conflicts_manual.jsonl \
  --variations 15
```

**Ventaja**: Control total sobre quality y diversidad
**Desventaja**: No escalable

### Opción C: Ajustar Umbral y Re-run

Bajar min-score a 0.78 para permitir más diversidad:

```bash
PYTHONPATH=. .venv/bin/python scripts/generate_po_teacher_dataset.py \
  --provider vertex_sdk \
  --model gemini-2.5-flash \
  --max-records 100 \
  --min-score 0.78 \  # Más permisivo
  --seed 999 \
  --resume
```

**Ventaja**: Más volumen, potencialmente más conflicts naturales
**Desventaja**: Puede degradar calidad promedio

---

## Decisión Recomendada

**Implementar Opción A** (Generación focalizada) + **Opción B** (Curación manual):

1. **Curar 5-10 casos conflicts** de los ejemplos problemáticos actuales (POCON-0061, etc.)
2. **Generar 15-20 casos adicionales** con gemini-1.5-pro forzando divergencia
3. **Validar distribución final**:
   - conflicts ≥ 10% (vs 0% actual)
   - gaps ≥ 25%
   - aligned ≤ 65%

4. **Entonces proceder a Paso 2** con dataset balanceado

---

## Archivos Generados

- **Dataset**: `artifacts/distillation/po_teacher_dataset.jsonl` (369 registros)
- **Log completo**: `/tmp/teacher_v2_generation.log` (47 min, 250+ warnings)
- **Comando**: Línea 263 de `docs/LORA_EVAL_RESULTS_ANALYSIS_20251115.md`

---

## Próximos Pasos

### Bloqueado: ⚠️ NO ejecutar Paso 2 aún

**Razón**: Dataset no contiene conflicts necesarios para resolver problema del student.

### Desbloqueado: Generar Conflicts Faltantes

1. **Tiempo estimado**: 2-3 horas
2. **Recursos**: gemini-1.5-pro (Vertex AI)
3. **Output esperado**: +25 registros con status conflicts

### Validación de Éxito

Antes de continuar a Paso 2, verificar:

```bash
# Debe retornar ≥ 25
grep -c 'status: conflicts' artifacts/distillation/po_teacher_dataset.jsonl
```

---

## Conclusiones

### Logros

✅ Generados 50 registros de alta calidad (mean 0.917)
✅ Dataset expandido a 369 registros (+15.7%)
✅ Min-score 0.82 garantiza calidad superior

### Problemas Críticos

❌ **0 registros con status conflicts** (objetivo principal no cumplido)
❌ Baja tasa de éxito (16.7% vs esperado 30-40%)
⚠️ **BLOQUEA** avance a Paso 2 del plan

### Acción Requerida

**Implementar generación focalizada de conflicts antes de re-entrenar LoRA**

---

**Autor**: Claude (agnostic-ai-pipeline)
**Versión**: 1.0
**Última actualización**: 2025-11-15 10:05 UTC
