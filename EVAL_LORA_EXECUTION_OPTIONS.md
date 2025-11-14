# Opciones de Ejecución - Evaluación LoRA Product Owner

**Objetivo**: Evaluar el modelo LoRA Product Owner (Task 9.D.4) comparando baseline vs student con 20 casos cada uno.

**Estado**: Análisis completo, listo para ejecutar en plataforma cloud con GPU gratuita.

---

## Resumen de Opciones Disponibles

| Plataforma | GPU Gratuita | Cuota | Complejidad | Archivo/Instrucción |
|------------|--------------|-------|-------------|---------------------|
| **Google Colab** | T4 (15 GB) | Ilimitada con interrupciones | Baja | `colab_eval_po_lora.ipynb` |
| **Kaggle** | T4 x2 | 30h/semana | Baja | `kaggle_eval_po_lora.ipynb` |
| **Lightning AI Studio** | T4 (16 GB) | 10h/mes | Media | `lightning_eval_po_lora.ipynb` o `LIGHTNING_AI_INSTRUCTIONS.md` |
| **Local** | Propia | N/A | Alta (OOM) | ❌ Falla con Exit 137 |

**Recomendación**:
1. **Preferir Google Colab** si tienes acceso (guarda automáticamente en Drive)
2. **Usar Lightning AI Studio** si Colab no está disponible (10h/mes gratis)
3. **Evitar Kaggle** si no tienes verificación de cuenta o cuota GPU

---

## Opción 1: Google Colab (RECOMENDADO)

### Requisitos
- Cuenta Google
- Acceso a Google Colab (https://colab.research.google.com)

### Pasos
1. Subir `colab_eval_po_lora.ipynb` a Google Colab
2. Runtime → Change runtime type → **GPU T4**
3. Ejecutar las 7 celdas en orden
4. Los resultados se guardan automáticamente en **Google Drive** (`MyDrive/lora_eval_results/`)
5. También puedes descargarlos manualmente desde `/content/`

### Tiempo estimado
- **Setup**: 5 minutos
- **Baseline**: 15-20 minutos
- **Student**: 15-20 minutos
- **Total**: ~40-45 minutos

### Ventajas
- Guardado automático en Google Drive
- Cuota ilimitada (con interrupciones ocasionales)
- Fácil importación y ejecución

### Archivo
- `colab_eval_po_lora.ipynb`

---

## Opción 2: Lightning AI Studio

### Requisitos
- Cuenta gratuita en https://lightning.ai
- 10 horas GPU/mes (cuota gratuita)

### Pasos

#### Método A: Import Notebook (si funciona)
1. Ir a https://lightning.ai
2. New Studio → Python
3. Upload notebook: `lightning_eval_po_lora.ipynb`
4. Settings → Machine → GPU T4 → Apply
5. Ejecutar celdas

#### Método B: Manual (RECOMENDADO si import falla)
Seguir las instrucciones detalladas en `LIGHTNING_AI_INSTRUCTIONS.md`:

1. Crear cuenta en https://lightning.ai
2. New Studio → Python
3. Settings → Machine → GPU T4 → Apply
4. Crear 7 celdas copiando el código de `LIGHTNING_AI_INSTRUCTIONS.md`:
   - Celda 1: Verificar GPU
   - Celda 2: Instalar dependencias
   - Celda 3: Clonar repositorio
   - Celda 4: Evaluación baseline
   - Celda 5: Evaluación student
   - Celda 6: Comparar resultados
   - Celda 7: Guardar resultados
5. Ejecutar en orden
6. Descargar resultados desde sidebar (File Browser)

### Tiempo estimado
- **Setup manual**: 10-15 minutos
- **Baseline**: 15-20 minutos
- **Student**: 15-20 minutos
- **Total**: ~45-55 minutos

### Ventajas
- 10h GPU gratuitas/mes
- Persistencia de datos (puedes pausar y reanudar)
- Sin dependencia de Google

### Desventajas
- Import de notebook puede fallar (usar método manual)
- Cuota limitada a 10h/mes

### Archivos
- `lightning_eval_po_lora.ipynb` (automático)
- `LIGHTNING_AI_INSTRUCTIONS.md` (manual paso a paso)

---

## Opción 3: Kaggle

### Requisitos
- Cuenta Kaggle verificada
- Cuota GPU disponible (30h/semana)

### Pasos
1. Ir a https://www.kaggle.com/code
2. New Notebook → Upload: `kaggle_eval_po_lora.ipynb`
3. Settings → Accelerator → **GPU T4 x2**
4. Run All
5. Resultados en la pestaña **Output**

### Tiempo estimado
- **Setup**: 5 minutos
- **Baseline**: 15-20 minutos
- **Student**: 15-20 minutos
- **Total**: ~40-45 minutos

### Ventajas
- 30h GPU/semana
- Resultados automáticos en Output tab

### Desventajas
- Requiere verificación de cuenta
- Puede bloquear acceso a GPU/TPU

### Archivo
- `kaggle_eval_po_lora.ipynb`

---

## Estructura de los Notebooks

Todos los notebooks siguen la misma estructura de 7 celdas:

1. **Verificar GPU**: `!nvidia-smi`
2. **Instalar dependencias**: transformers, peft, bitsandbytes, accelerate, torch, typer, pyyaml
3. **Clonar repositorio y verificar modelo**:
   - Repo: `https://github.com/krukmat/agnostic-ai-pipeline.git`
   - Branch: `dspy-multi-role`
   - Modelo: `artifacts/models/po_student_v1/`
   - Dataset: `artifacts/synthetic/product_owner/product_owner_val.jsonl`
4. **Evaluación baseline**: Qwen2.5-7B-Instruct sin LoRA
5. **Evaluación student**: Qwen2.5-7B-Instruct + LoRA adapter
6. **Comparar resultados**: Cálculo automático de métricas y criterios PASS/FAIL
7. **Guardar resultados**: ZIP + JSONs individuales

---

## Parámetros de Evaluación

```bash
--tag baseline                  # Identificador del run
--base-model Qwen/Qwen2.5-7B-Instruct
--max-samples 20                # Casos del valset
--retries 2                     # 3 intentos totales (inicial + 2 retries)
--max-new-tokens 1200           # Suficiente para YAML completo
--load-4bit                     # Cuantización 4-bit (ahorra memoria)
--bnb-compute-dtype float16     # Precisión mixta
```

Para student, se agrega:
```bash
--adapter-path artifacts/models/po_student_v1
```

---

## Criterios de Aceptación (9.D.4)

Los notebooks calculan automáticamente:

1. **YAML válido**: ≥90% de los casos (≥18/20) generan bloques VISION + REVIEW válidos
   - Máximo 2 casos con `format_error` aceptable

2. **Métrica baseline**: `mean_baseline >= 0.75`
   - Esperado ~0.83 según `artifacts/benchmarks/product_owner_baseline.json`

3. **Métrica student**: `mean_student >= 0.9 * mean_baseline`
   - Si baseline = 0.83 → student ≥ 0.75
   - Degradación <10% aceptable

**Resultado**: ✅ PASS → Avanzar a Task 9.D.5 | ❌ FAIL → Analizar casos `format_error`

---

## Archivos de Resultados

Después de la ejecución, descargarás:

- `baseline_<timestamp>.json`: Resultados del modelo base sin LoRA
- `student_<timestamp>.json`: Resultados del modelo con LoRA
- `eval_results_20251115.zip`: Todos los resultados comprimidos

**Estructura de cada JSON**:
```json
{
  "config": {...},
  "total_samples": 20,
  "valid_samples": 18,
  "failed_samples": 2,
  "metrics": {
    "mean": 0.831,
    "std": 0.142,
    "min": 0.567,
    "max": 1.0
  },
  "results": [
    {
      "concept_id": "simple-01",
      "tier": "Simple",
      "status": "success",
      "score": 0.89,
      ...
    }
  ]
}
```

---

## Próximos Pasos Después de la Ejecución

1. **Subir resultados al repositorio**:
   ```bash
   # Copiar JSONs descargados a inference_results/
   cp baseline_*.json inference_results/
   cp student_*.json inference_results/
   ```

2. **Actualizar documentación**:
   - Editar `docs/po_distillation_report.md` sección 3 con:
     - Tabla comparativa (mean/std/min/max)
     - Casos `format_error` (IDs, tier, raw output)
     - Timestamp y archivos JSON
     - Resultado PASS/FAIL

3. **Si PASS → Task 9.D.5 (Integración)**:
   - Actualizar `config.yaml` para usar modelo student
   - Ejecutar `make po` con concepto real
   - Validar end-to-end

4. **Si FAIL → Ajustes**:
   - Analizar casos `format_error` (¿patrón común?)
   - Opciones:
     - Aumentar `--retries 3`
     - Post-procesado con regex
     - Re-entrenar con más epochs

---

## Referencias

- **Análisis completo**: `docs/LORA_EVAL_ANALYSIS_20251115.md`
- **Plan Fase 9**: `docs/fase9_multi_role_dspy_plan.md` (sección 9.D.4, líneas 862-909)
- **Reporte Distillation**: `docs/po_distillation_report.md`
- **Baseline valset completo**: `artifacts/benchmarks/product_owner_baseline.json` (mean 0.831, 34 samples)
- **Dataset teacher**: `artifacts/distillation/po_teacher_dataset.jsonl` (319 registros)
- **Modelo LoRA**: `artifacts/models/po_student_v1/` (92 MB, tokenizer + adapter)
- **Log entrenamiento**: `logs/distillation/train_po_student_v1.log`

---

**Fecha**: 2025-11-15
**Estado**: LISTO PARA EJECUTAR
**Acción requerida**: Elegir plataforma (Colab preferido, Lightning AI como alternativa) y ejecutar evaluación
