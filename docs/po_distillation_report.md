# Product Owner Distillation Report

## 1. Context
- **Teacher dataset**: `artifacts/distillation/po_teacher_dataset.jsonl` (319 registros, score medio 0.896).
- **Student architecture**: LoRA sobre `Qwen/Qwen2.5-7B-Instruct` con rank 32 / alpha 64 / dropout 0.05 / 3 epochs.
- **Entrenamiento**: Ejecutado en Colab T4 16 GB (`train_po_lora.py` con `--load-4bit --batch-size 1 --gradient-accumulation-steps 8`). Log almacenado en `logs/distillation/train_po_student_v1.log`.

## 2. 9.D.3 – Training Snapshot (2025-11-13)
- Convergencia: pérdida inicial 1.46 → final 0.43 (promedio 0.65) en 1h40m.
- Artefactos: `artifacts/models/po_student_v1/` (tokenizer + LoRA adapters).  
- Pendientes: crear `model_card.md`, preparar `Modelfile` para Ollama y merge opcional (`merge_lora.py`).

## 3. 9.D.4 – Evaluation Checklist
1. **Baseline run**  
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/eval_po_student.py \
     --tag baseline \
     --base-model Qwen/Qwen2.5-7B-Instruct \
     --max-samples 20 \
     --load-4bit --bnb-compute-dtype float16
   ```
2. **Student run**  
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/eval_po_student.py \
     --tag student \
     --base-model Qwen/Qwen2.5-7B-Instruct \
     --adapter-path artifacts/models/po_student_v1 \
     --max-samples 20 \
     --load-4bit --bnb-compute-dtype float16
   ```
3. **Acceptance gate**  
   - YAML válido en ≥90 % de los casos (casos restantes deben marcarse `format_error`).  
   - `metrics.mean_student >= 0.9 * metrics.mean_baseline`.  
   - Documentar diferencias clave (velocidad estimada, longitud promedio) y adjuntar archivos `inference_results/*.json`.

### Última ejecución registrada (2025-11-14)
- Dataset: 3 casos hardcodeados (`basic_blog_validation`, `ecommerce_requirements`, `incomplete_requirements`).
- Problema: ninguno de los dos modelos (baseline/student) generó bloques YAML válidos.
- Causa: Prompt no suficientemente restrictivo, sin retries, tokens limitados.
- Resultado: sin YAML válido → `product_owner_metric` no calculable.

### Plan de Relanzamiento (2025-11-15) - Estado LISTO

**Análisis completado**:
- ✅ Script `eval_po_student.py` ya implementa prompt correcto con ejemplo YAML completo
- ✅ Ya tiene retry con REMINDER si falta YAML
- ✅ Ya lee del dataset de validación real (`product_owner_val.jsonl`, 34 registros)
- ✅ Ya calcula `product_owner_metric` solo si YAML válido

**Parámetros optimizados**:
- `--retries 2` (3 intentos totales vs 1 anterior)
- `--max-new-tokens 1200` (vs 900 anterior)
- `--max-samples 20` (casos reales del valset, balanceados por tier)

**Comandos finales**:
```bash
# Baseline (sin adapter)
PYTHONPATH=. .venv/bin/python scripts/eval_po_student.py \
  --tag baseline \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --max-samples 20 \
  --retries 2 \
  --max-new-tokens 1200 \
  --load-4bit --bnb-compute-dtype float16

# Student (con LoRA adapter)
PYTHONPATH=. .venv/bin/python scripts/eval_po_student.py \
  --tag student \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --adapter-path artifacts/models/po_student_v1 \
  --max-samples 20 \
  --retries 2 \
  --max-new-tokens 1200 \
  --load-4bit --bnb-compute-dtype float16
```

**Criterio de aceptación**:
- YAML válido en ≥90% de los casos (≥18/20)
- `mean_student >= 0.9 * mean_baseline` (si baseline ~0.83, student ≥0.75)
- Documentar velocidad, longitud promedio, casos `format_error`

## 4. Próximos pasos
- [ ] Recolectar baseline/student outputs con el nuevo script (≥20 casos).  
- [ ] Actualizar esta tabla con métricas finales, fecha, GPU y observaciones.  
- [ ] Una vez validado, pasar a 9.D.5 (integración en `config.yaml` + `make po`).  
- [ ] Mantener archivos auxiliares (zip adapters, logs) en `artifacts/models/po_student_v1/` y `logs/distillation/`.
