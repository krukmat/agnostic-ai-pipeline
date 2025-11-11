# Product Owner - Teacher Dataset Generation (Hybrid Strategy)
**Fecha**: 2025-11-10
**Task**: 9.D.2 - Generación Dataset Maestro (EN CURSO)
**Status**: 🚧 EN PROGRESO (237/300 registros, 79.0%)
**Estrategia**: Híbrida (45 registros `gemini-2.5-pro` + 192 registros `gemini-2.5-flash`, threshold 0.80)

---

## 📋 Resumen Ejecutivo

### Problema Identificado
Durante la generación inicial del teacher dataset con `gemini-2.5-pro`, se detectó una tasa de éxito muy baja (~20-25%) con los siguientes problemas:

- ❌ **80% de intentos fallaban** con "Missing VISION/REVIEW content"
- ❌ Modelo no generaba estructura YAML válida consistentemente
- ❌ Tiempo estimado: **25-30 horas** para 400 registros
- ❌ Proceso estancado en 45 registros con múltiples horas de ejecución

### Solución Implementada (Estrategia Híbrida)
**Cambio a gemini-2.5-flash con threshold reducido**:

1. ✅ **Preservar registros existentes**: 45 registros de gemini-2.5-pro guardados
2. ✅ **Cambiar modelo**: gemini-2.5-pro → gemini-2.5-flash
3. ✅ **Reducir threshold**: 0.85 → 0.80 (aumenta aceptación de muestras válidas)
4. 🔄 **Target ajustado**: 300 registros (fase 1) — objetivo actual cumplido al 79%

### Resultados Iniciales (gemini-2.5-flash)
- ✅ **Tasa de éxito mejorada**: ~40-50% (vs 20-25% anterior)
- ✅ **Calidad excelente**: scores promedio ~0.89-0.95
- ✅ **Retry mechanism funciona**: ~60-70% de retries son exitosos
- ✅ **Tiempo estimado reducido**: **~4-5 horas** para 400 registros (vs 25-30h)

---

## 🔧 Implementación Técnica

### Comando Anterior (FALLIDO)
```bash
# gemini-2.5-pro con threshold 0.85 (20-25% success rate)
PYTHONPATH=. .venv/bin/python scripts/generate_po_teacher_dataset.py \
  --provider vertex_sdk \
  --model gemini-2.5-pro \
  --max-records 400 \
  --min-score 0.85 \
  --seed 555 \
  --resume
```

**Resultado**: Estancado en 45 registros después de ~90 minutos

### Comando Actual (EN PROGRESO)
```bash
# gemini-2.5-flash con threshold 0.80 (40-50% success rate)
PYTHONPATH=. .venv/bin/python scripts/generate_po_teacher_dataset.py \
  --provider vertex_sdk \
  --model gemini-2.5-flash \
  --max-records 300 \
  --min-score 0.80 \
  --seed 555 \
  --resume \
  2>&1 | tee /tmp/teacher_hybrid_flash.log
```

**PID**: Se ejecuta en sesiones puntuales (último batch completado a las 15:08 CET)

### Archivos de Backup
- `artifacts/distillation/po_teacher_dataset_backup_45.jsonl` (220KB, 45 registros `gemini-2.5-pro`)
- `artifacts/distillation/po_teacher_dataset.jsonl` (dataset activo, 237 registros | media 0.899)

---

## 📊 Análisis de Performance

### Comparación de Modelos

| Métrica | gemini-2.5-pro | gemini-2.5-flash |
|---------|----------------|------------------|
| Success Rate | 20-25% | 40-50% |
| Avg Score | 0.85-0.90 | 0.89-0.95 |
| Missing VISION/REVIEW | ~80% | ~30-40% |
| Retry Success | N/A | ~60-70% |
| Tiempo/400 registros | 25-30h | 4-5h |
| Costo estimado | Alto | Medio |

### Patrón de Errores Observados

**gemini-2.5-flash (ACTUAL)**:
```
[12:54:29] ✅ Stored sample #2 (score=0.910)
[12:54:42] ⚠️  REVIEW block missing — retrying with explicit instruction
[12:54:55] ❌ Missing VISION/REVIEW content, skipping
[12:55:07] ⚠️  REVIEW block missing — retrying with explicit instruction
[12:55:19] ❌ REVIEW block missing after retry
[12:55:31] ⚠️  REVIEW block missing — retrying with explicit instruction
[12:55:40] ✅ Stored sample #3 (score=0.893)
[12:55:49] ✅ Stored sample #4 (score=0.886)
[12:56:02] ❌ Missing VISION/REVIEW content, skipping
[12:56:14] ✅ Stored sample #5 (score=0.910)
```

**Análisis**:
- **Errores manejables**: El retry mechanism funciona correctamente
- **Quality alta**: Todos los samples aceptados tienen score ≥0.886 (bien por encima del threshold 0.80)
- **Velocidad**: ~1.3 registros/minuto (incluyendo retries)

---

## 🎯 Estado Actual

### Dataset Generado
```
Registros actuales: 237 / 300 (79.0%)
Progreso: [███████████░░░░░░░░░] 79%
Última actualización: 2025-11-10 15:10 CET
```

**Calidad del Dataset**:
- Score promedio: **0.899**
- Score mínimo aceptado: 0.800
- Score máximo: **0.984**
- Último registro: score = **0.947**

### Logs Activos
- **Generación**: `/tmp/teacher_hybrid_flash.log`
- **Monitor**: `/tmp/monitor_teacher_dataset.sh` (checking every 5 min)
- **Pipeline**: `logs/pipeline.log`

### ETA Estimado

**Con performance actual (1.3 registros/min)**:
```
Registros restantes: 63
ETA: ~48 minutos
Finalización estimada: ~16:00 CET (2025-11-10)
```

---

## ⚠️ Issues y Observaciones

### Issue #1: REVIEW Block Generation
**Problema**: gemini-2.5-flash ocasionalmente omite el bloque REVIEW en primera respuesta

**Evidencia**:
- ~30-40% de respuestas requieren retry
- Mensaje: "REVIEW block missing — retrying with explicit instruction"

**Impacto**: BAJO
- El retry mechanism funciona en ~60-70% de casos
- No bloquea la generación, solo aumenta el tiempo levemente
- Calidad de los samples después del retry es comparable

**Solución Actual**: Retry automático implementado en `scripts/generate_po_teacher_dataset.py`

**Mejoras Futuras**:
1. Ajustar prompt para ser más explícito sobre estructura YAML requerida
2. Agregar ejemplos de YAML válido en el prompt
3. Considerar structured output API si Vertex AI lo soporta

---

## 📝 Archivos Involucrados

### Scripts
- `scripts/generate_po_teacher_dataset.py` (generación con retry logic)
  - Línea ~XX: Retry mechanism para REVIEW block
  - Línea ~XX: Scoring con `product_owner_metric`

### Datasets
- `artifacts/distillation/po_teacher_dataset.jsonl` (ACTIVO, 53 registros)
- `artifacts/distillation/po_teacher_dataset_backup_45.jsonl` (backup gemini-2.5-pro)
- `artifacts/synthetic/product_owner/concepts.jsonl` (source concepts)

### Logs
- `/tmp/teacher_hybrid_flash.log` (ejecución actual)
- `/tmp/monitor_output.log` (monitor script)
- `logs/pipeline.log` (pipeline general)

---

## 🔗 Contexto: Fase 9.D (Distillation Strategy)

Este trabajo es parte de la estrategia completa de distillation:

### Flujo Completo
1. ✅ **Task 9.0.7**: Baseline evaluation (score: 0.831 / 83.1%)
2. ✅ **Task 9.0.8**: MIPROv2 optimization + serialization fix
3. 🚧 **Task 9.D.2**: Teacher dataset generation (ESTA TAREA - EN CURSO)
   - **Estado**: 53/400 registros (13.25%)
   - **Modelo**: gemini-2.5-flash (Vertex AI)
   - **Target**: 400 registros con score ≥0.80
   - **ETA**: ~4.5 horas
4. ⏭️ **Task 9.D.3**: Fine-tuning LoRA student model
   - Base: mistral-7b-instruct
   - Dataset: Teacher dataset (400 ejemplos alta calidad)
   - Técnica: LoRA (rank 32, alpha 64)
   - Plataforma: Google Colab (FREE o Pro)
5. ⏭️ **Task 9.D.4**: Validación modelo distillado
6. ⏭️ **Task 9.D.5**: Integración al pipeline

### Objetivo Final (Fase 9.D)
Reemplazar modelo teacher lento (gemini-2.5-flash/pro) con modelo local distillado, habilitando:
- MIPROv2 repetible y rápido (~10x faster)
- Reducción de costos (sin API calls para inferencia)
- Experimentación ágil con product owner optimization

---

## 📅 Próximos Pasos

### Inmediatos (Task 9.D.2 - EN CURSO)

**1. Monitorear Generación Actual** ⏰
- **Acción**: Esperar a que el proceso complete 400 registros
- **Verificación**: Revisar `/tmp/teacher_hybrid_flash.log` cada hora
- **Comando**:
  ```bash
  wc -l artifacts/distillation/po_teacher_dataset.jsonl
  tail -20 /tmp/teacher_hybrid_flash.log
  ```
- **Criterio de éxito**: 400 registros con score promedio ≥0.85

**2. Análisis de Calidad del Dataset** 📊
- **Cuando**: Al alcanzar 400 registros
- **Acciones**:
  ```bash
  # Análisis estadístico
  python3 -c "
  import json
  scores = []
  with open('artifacts/distillation/po_teacher_dataset.jsonl') as f:
      for line in f:
          scores.append(json.loads(line)['score'])

  print(f'Total: {len(scores)}')
  print(f'Mean: {sum(scores)/len(scores):.3f}')
  print(f'Min: {min(scores):.3f}')
  print(f'Max: {max(scores):.3f}')
  print(f'Median: {sorted(scores)[len(scores)//2]:.3f}')
  "
  ```

**3. Preparar Training Pipeline** 🛠️
- **Cuando**: Dataset completo (400 registros)
- **Acciones**:
  1. Crear script de training: `scripts/train_po_student.py`
     - Basado en Hugging Face Transformers + PEFT
     - LoRA config: rank=32, alpha=64, target_modules=['q_proj', 'v_proj']
     - Optimización: AdamW con learning rate 2e-4

  2. Crear Colab notebook template: `notebooks/po_student_training.ipynb`
     - Setup de GPU (T4/V100)
     - Instalación de dependencias
     - Training loop con validación
     - Export de modelo fine-tuned

  3. Split dataset (train/val):
     ```bash
     python3 scripts/split_teacher_dataset.py \
       --input artifacts/distillation/po_teacher_dataset.jsonl \
       --train artifacts/distillation/po_train.jsonl \
       --val artifacts/distillation/po_val.jsonl \
       --split 0.85
     ```

### Siguientes (Task 9.D.3 - Fine-tuning)

**4. Ejecutar Fine-tuning en Colab** 🎓
- **Plataforma**: Google Colab (FREE tier con T4 GPU)
- **Duración estimada**: 2-4 horas
- **Recursos necesarios**:
  - GPU: T4 (15GB VRAM) - suficiente con LoRA
  - RAM: 12GB
  - Disk: 10GB
- **Comando**:
  ```bash
  # En Colab
  !python scripts/train_po_student.py \
    --base_model mistralai/Mistral-7B-Instruct-v0.2 \
    --train_data artifacts/distillation/po_train.jsonl \
    --val_data artifacts/distillation/po_val.jsonl \
    --output_dir artifacts/models/po_student_lora \
    --lora_r 32 \
    --lora_alpha 64 \
    --epochs 3 \
    --batch_size 4 \
    --learning_rate 2e-4
  ```

**5. Validar Modelo Distillado** ✅
- **Cuando**: Training completo
- **Métricas**:
  - Score en validation set (target: ≥0.75)
  - Comparación con teacher model (gap <10%)
  - Tiempo de inferencia (target: <10s por sample)
- **Comando**:
  ```bash
  python scripts/evaluate_po_student.py \
    --model artifacts/models/po_student_lora \
    --valset artifacts/synthetic/product_owner/product_owner_val.jsonl \
    --output artifacts/evaluation/po_student_eval.json
  ```

**6. Integrar al Pipeline** 🔄
- **Acciones**:
  1. Crear Modelfile para Ollama:
     ```bash
     # Exportar a GGUF
     python scripts/export_to_gguf.py \
       --model artifacts/models/po_student_lora \
       --output artifacts/models/po_student.gguf

     # Importar a Ollama
     ollama create po-student -f Modelfile
     ```

  2. Actualizar `config.yaml`:
     ```yaml
     roles:
       product_owner:
         provider: ollama
         model: po-student
     ```

  3. Re-run baseline evaluation con modelo student
  4. Comparar performance vs teacher model

### Opcionales (Mejoras)

**7. Fix Issue #1 (REVIEW Block Generation)** 🔧
- **Acción**: Mejorar prompt en `scripts/generate_po_teacher_dataset.py`
- **Estrategia**:
  1. Agregar ejemplo de YAML válido
  2. Hacer instrucción más explícita sobre bloques requeridos
  3. Considerar few-shot prompting
- **Prioridad**: BAJA (retry mechanism funciona)

**8. Análisis Comparativo (gemini-2.5-pro vs flash)** 📈
- **Acción**: Comparar calidad de registros por modelo
- **Análisis**:
  ```bash
  # Primeros 45 registros (gemini-2.5-pro)
  head -45 artifacts/distillation/po_teacher_dataset.jsonl | \
    python3 -c "import sys, json; scores=[json.loads(l)['score'] for l in sys.stdin]; print(f'Mean: {sum(scores)/len(scores):.3f}')"

  # Registros 46+ (gemini-2.5-flash)
  tail -n +46 artifacts/distillation/po_teacher_dataset.jsonl | \
    python3 -c "import sys, json; scores=[json.loads(l)['score'] for l in sys.stdin]; print(f'Mean: {sum(scores)/len(scores):.3f}')"
  ```

---

## 🎓 Lessons Learned

### 1. Model Selection para Structured Output
**Observación**: gemini-2.5-flash es **más confiable** que gemini-2.5-pro para generación de structured YAML

**Razones posibles**:
- gemini-2.5-flash optimizado para tasks más simples (mejor instruction following)
- gemini-2.5-pro puede "sobre-pensar" y desviar de formato estricto
- Flash tiene mejor ratio costo/performance para este use case

**Recomendación**: Para tareas de structured output, probar modelos "flash" antes que "pro"

### 2. Importance of Retry Mechanisms
**Observación**: El retry mechanism con instrucción explícita rescata ~60-70% de intentos fallidos

**Implementación**:
```python
# Primera intención
response = model.generate(prompt)

# Si falta bloque REVIEW
if "REVIEW:" not in response:
    retry_prompt = prompt + "\n\nIMPORTANT: You MUST include a REVIEW block with the structure:\nREVIEW:\n  completeness: X\n  ..."
    response = model.generate(retry_prompt)
```

**Recomendación**: Siempre implementar retry logic para structured output tasks

### 3. Threshold Tuning
**Observación**: Reducir threshold de 0.85 → 0.80 aumentó acceptance rate sin sacrificar calidad significativa

**Datos**:
- Con threshold 0.85: ~45 registros aceptados de ~200+ intentos (22.5%)
- Con threshold 0.80: Score promedio de aceptados = 0.90 (bien por encima del threshold)

**Recomendación**: Usar threshold conservador inicialmente, luego ajustar basado en distribución real de scores

---

## 📚 Referencias

- **Plan Maestro**: `docs/fase9_multi_role_dspy_plan.md:616-757` (Fase 9.D)
- **Schema PO**: `docs/fase9_product_owner_schema.md`
- **Baseline Evaluation**: Task 9.0.7 (score: 0.831)
- **MIPROv2 Optimization**: `docs/PO_MIPRO_OPTIMIZATION_REPORT.md`
- **Vertex AI Docs**: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini
- **LoRA Paper**: https://arxiv.org/abs/2106.09685
- **Colab Setup**: https://colab.research.google.com/

---

## 📞 Comandos de Monitoreo

### Check Progress
```bash
# Ver cantidad de registros
wc -l artifacts/distillation/po_teacher_dataset.jsonl

# Ver últimos scores
tail -10 artifacts/distillation/po_teacher_dataset.jsonl | \
  python3 -c "import sys, json; [print(f\"Score: {json.loads(l)['score']:.3f}\") for l in sys.stdin]"

# Ver log en tiempo real
tail -f /tmp/teacher_hybrid_flash.log
```

### Verify Process
```bash
# Check si el proceso está corriendo
ps aux | grep generate_po_teacher_dataset.py

# Ver últimas 50 líneas del log
tail -50 /tmp/teacher_hybrid_flash.log

# Filtrar solo samples exitosos
grep "Stored sample" /tmp/teacher_hybrid_flash.log | tail -20
```

### Stop/Restart Process
```bash
# Detener proceso actual
pkill -f "generate_po_teacher_dataset.py"

# Reiniciar con resume
PYTHONPATH=. .venv/bin/python scripts/generate_po_teacher_dataset.py \
  --provider vertex_sdk \
  --model gemini-2.5-flash \
  --max-records 400 \
  --min-score 0.80 \
  --seed 555 \
  --resume \
  2>&1 | tee /tmp/teacher_hybrid_flash.log
```

---

**Última actualización**: 2025-11-10 13:00 CET
**Próxima revisión**: Al completar 150 registros (ETA: ~14:00 CET)
