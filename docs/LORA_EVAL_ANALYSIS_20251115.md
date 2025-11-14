# Análisis de Resultados LoRA - Product Owner (2025-11-15)

## Contexto

**Modelo Student**: LoRA sobre `Qwen/Qwen2.5-7B-Instruct` (rank 32, alpha 64, dropout 0.05)
**Entrenamiento**: 3 epochs, loss 1.46 → 0.59, 319 registros teacher (gemini-2.5-flash/pro, score medio 0.896)
**Ubicación**: `artifacts/models/po_student_v1/` (92 MB sin checkpoints)

## Problema de la Ejecución Anterior (2025-11-14)

### Resultados en inference_results/

| Archivo | Modelo | Dataset | Problema |
|---------|--------|---------|----------|
| `baseline_20251114_143731.json` | Qwen2.5-7B-Instruct (sin LoRA) | 3 casos hardcodeados | ❌ Sin YAML válido |
| `finetuned_20251114_143731.json` | Qwen2.5-7B-Instruct + LoRA | 3 casos hardcodeados | ❌ Sin YAML válido |
| `comparison_20251114_143731.json` | Comparación | 3 casos | Diferencia longitud: -2.9% (irrelevante) |

**Diagnóstico**:
- Los modelos generaron texto explicativo en vez de bloques YAML fenceados
- No se pudo calcular `product_owner_metric` en ningún caso
- Dataset de prueba inadecuado (3 casos sintéticos, no del valset real)

## Solución Implementada

### Estado del Script eval_po_student.py

El script `scripts/eval_po_student.py` **YA está correctamente implementado**:

1. ✅ **Prompt con ejemplo completo**: Usa `build_po_prompt(concept, requirements, include_example=True)`
   - Incluye `PO_SAMPLE_OUTPUT` con VISION y REVIEW completos
   - Instrucciones claras sobre formato requerido

2. ✅ **Retry automático**: Si falta YAML, reintenta con REMINDER adicional
   - Parámetro `--retries` controla intentos adicionales
   - Mensaje reforzado: "REMINDER: Respond ONLY with the two fenced YAML blocks..."

3. ✅ **Validación y métricas**:
   - Extrae bloques con `extract_vision_review()`
   - Calcula `product_owner_metric` solo si YAML válido
   - Marca casos como `format_error` si fallan

4. ✅ **Dataset real**: Lee de `product_owner_val.jsonl` (34 registros, balanceados por tier)

### Parámetros Optimizados

**Cambios necesarios** (vs ejecución anterior):

| Parámetro | Anterior | Nuevo | Razón |
|-----------|----------|-------|-------|
| `--retries` | 1 (default) | 2 | 3 intentos totales para generar YAML |
| `--max-new-tokens` | 900 (default) | 1200 | Output completo necesita ~800-1000 tokens |
| `--max-samples` | 3 (hardcoded) | 20 | Dataset real del valset, representativo |

## Plan de Ejecución - Task 9.D.4

### 1. Evaluación Baseline (sin LoRA)

```bash
PYTHONPATH=. .venv/bin/python scripts/eval_po_student.py \
  --tag baseline \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --max-samples 20 \
  --retries 2 \
  --max-new-tokens 1200 \
  --load-4bit --bnb-compute-dtype float16
```

**Output esperado**: `inference_results/baseline_<timestamp>.json`

### 2. Evaluación Student (con LoRA)

```bash
PYTHONPATH=. .venv/bin/python scripts/eval_po_student.py \
  --tag student \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --adapter-path artifacts/models/po_student_v1 \
  --max-samples 20 \
  --retries 2 \
  --max-new-tokens 1200 \
  --load-4bit --bnb-compute-dtype float16
```

**Output esperado**: `inference_results/student_<timestamp>.json`

### 3. Criterios de Aceptación

**Gate para completar 9.D.4 y avanzar a 9.D.5**:

1. **YAML válido**: ≥90% de los casos (≥18/20) generan bloques VISION + REVIEW válidos
   - Máximo 2 casos con `format_error` aceptable

2. **Métrica baseline**: `mean_baseline >= 0.75`
   - Esperado ~0.83 según `product_owner_baseline.json` (valset completo)
   - Variación aceptable por shuffle/sampling

3. **Métrica student**: `mean_student >= 0.9 * mean_baseline`
   - Si baseline = 0.83 → student ≥ 0.75
   - Degradación <10% aceptable (distillación conserva 90%+ calidad)

4. **Documentación**: Actualizar `docs/po_distillation_report.md` con:
   - Tabla comparativa (mean/std/min/max)
   - Casos `format_error` (IDs, tier, raw output)
   - Velocidad estimada (si disponible del log)
   - Timestamp y ruta de archivos JSON

## Próximos Pasos (Post 9.D.4)

**Si pasa el gate**:
1. Actualizar `docs/po_distillation_report.md` sección 3 con resultados finales
2. Commit de resultados en `inference_results/`
3. Avanzar a **9.D.5 - Integración al pipeline**:
   - Actualizar `config.yaml` para usar `po-student` en rol PO
   - Ejecutar `make po` con concepto real y validar end-to-end

**Si NO pasa el gate** (<90% YAML válido):
1. Analizar casos `format_error` (¿patrón común?)
2. Opciones:
   - Aumentar `--retries 3`
   - Post-procesado con regex agresivo
   - Re-entrenar con más ejemplos teacher o más epochs
   - Usar constrained decoding (futuro)

## Referencias

- **Plan Fase 9**: `docs/fase9_multi_role_dspy_plan.md` líneas 862-909 (sección 9.D.4)
- **Reporte Distillation**: `docs/po_distillation_report.md`
- **Baseline valset completo**: `artifacts/benchmarks/product_owner_baseline.json` (mean 0.831, 34 samples)
- **Dataset teacher**: `artifacts/distillation/po_teacher_dataset.jsonl` (319 registros)
- **Modelo LoRA**: `artifacts/models/po_student_v1/` (tokenizer + adapter)
- **Log entrenamiento**: `logs/distillation/train_po_student_v1.log`

---

**Fecha análisis**: 2025-11-15
**Estado**: Listo para ejecutar comandos 9.D.4
**Owner**: Dev team
