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

### Ejecución 2025-11-14 (script nuevo)
- Baseline (`baseline_20251114_215442.json`, 20 casos): mean **0.841**, std 0.049, min 0.773, max 0.948, 0 errores de formato.
- Student (`student_20251114_220448.json`, 20 casos): mean **0.772**, std 0.181, min 0.375, max 0.958, 0 errores de formato.
- Hallazgos:
  - El student responde en formato correcto, pero pierde ~0.069 puntos (≈−8.2 %) frente al baseline.  
  - Variancia elevada en casos corporate (scores ≤0.45), señal de que falta señal en el dataset o el prompt no fuerza referencias a IDs.  
  - No cerrar 9.D.4 hasta que el adapter alcance ≥0.82 de media y std ≤0.10.

### Plan de Remediación
- **Dataset**: filtrar muestras teacher con `score < 0.82`, generar ≥50 casos nuevos centrados en tier corporate y rearmar el supervisado hasta ~400 ejemplos equilibrados.  
- **Prompt**: actualizar `scripts/po_prompts.py` para exigir IDs explícitos en `requirements_alignment` y al menos dos acciones concretas en `recommended_actions`; limitar la narrativa a 2-3 frases.  
- **Entrenamiento**: reentrenar con `epochs=4`, `lr=8e-5`, scheduler cosine + warmup 5 %, `gradient_accumulation_steps=12`, manteniendo `rank 32` y `alpha 64`.  
- **Evaluación**: correr `scripts/eval_po_student.py` (baseline + student) con ≥20 casos cada uno (`--retries 2`, `--max-new-tokens 1200`).  
- **Criterio de cierre**: YAML válido en ≥90 % y `mean_student ≥ 0.82`, `|mean_student - mean_baseline| ≤ 0.03`, `std_student ≤ 0.10`. Documentar resultados y adjuntar los JSON correspondientes.

## 4. Próximos pasos
- [ ] Recolectar baseline/student outputs con el nuevo script (≥20 casos).  
- [ ] Actualizar esta tabla con métricas finales, fecha, GPU y observaciones.  
- [ ] Una vez validado, pasar a 9.D.5 (integración en `config.yaml` + `make po`).  
- [ ] Mantener archivos auxiliares (zip adapters, logs) en `artifacts/models/po_student_v1/` y `logs/distillation/`.
