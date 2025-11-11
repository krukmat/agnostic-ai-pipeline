# Fase 9.D – Distillation Product Owner

## 1. Objetivo

Reducir el tiempo de inferencia del rol Product Owner (PO) reemplazando `granite4` por un modelo local (7B) distillado a partir de un modelo teacher premium (Gemini 2.5 Pro). Esto permitirá que MIPROv2 y el pipeline completo se ejecuten en minutos en lugar de horas.

## 2. Alcance

| Etapa | Descripción | Deliverables |
|-------|-------------|--------------|
| 9.D.1 | Diseño y alcance | Este documento + secciones en `docs/fase9_multi_role_dspy_plan.md` |
| 9.D.2 | Dataset maestro (teacher) | `artifacts/distillation/po_teacher_dataset.jsonl` |
| 9.D.3 | Entrenamiento LoRA/FT | `artifacts/models/po_student_v1/` (adapters/pesos) + logs |
| 9.D.4 | Validación | Reporte comparativo teacher vs student |
| 9.D.5 | Integración | `config.yaml` actualizado + pruebas `make po` |
| 9.D.6 | Beneficios esperados | Resumen en plan fase 9 |
| 9.D.7 | Próximos pasos | Checklist para futuras fases |

## 3. Diseño

### 3.1 Teacher
- **Modelo**: `gemini-2.5-pro` (Vertex AI).
- **Prompt base**: reutilizar `prompts/product_owner.md` + nota adicional “Act as senior PO; output YAML blocks EXACTLY as specified”.
- **Batching**: 20 requests por lote (`vertex_cli` o `vertex_sdk`).
- **Threshold**: `product_owner_metric >= 0.85` (regenerar si queda debajo).

### 3.2 Student
- **Modelo base**: `mistral-7b-instruct` (disponible para LoRA y deployment en Ollama).
- **Técnica**: LoRA (rank=32, alpha=64, dropout=0.05) usando `peft`.
- **Hyperparams**:
  - Epochs: 3
  - Batch size: 4
  - LR: 1e-4
  - Max seq len: 2048
- **Hardware**: GPU A100 40GB (3h aprox).
- **Salida**:
  - Adapter (`po_student_v1_lora.safetensors`)
  - Merge (`po_student_v1.safetensors`, FP16)
  - Ollama package (`po-student-v1` con quant q4_0).

## 4. Dataset maestro (9.D.2)

1. Fuente: `artifacts/synthetic/product_owner/concepts.jsonl` (228 registros) + resample para llegar a 600 entradas (se puede generar variantes adicionales con `generate_po_payloads.py` si hace falta).
2. Script: `scripts/generate_po_teacher_dataset.py`
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/generate_po_teacher_dataset.py \
     --input artifacts/synthetic/product_owner/concepts.jsonl \
     --output artifacts/distillation/po_teacher_dataset.jsonl \
     --provider vertex_sdk \
     --model gemini-2.5-pro \
     --batch-size 20 \
     --min-score 0.85
   ```
3. Validaciones:
   - Formato YAML parseable.
   - `product_owner_metric` >= 0.85.
   - Log de costos guardado en `logs/distillation/teacher_calls_YYYYMMDD.log`.

## 5. Entrenamiento (9.D.3)

1. Pre-procesamiento:
   - Convertir JSONL teacher a formato supervised (prompt + target).
   - Template (pseudo):
     ```
     ### CONCEPT
     {concept}
     ### REQUIREMENTS
     {requirements_yaml}
     ### OUTPUT
     <VISION>
     {teacher_product_vision}
     </VISION>
     <REVIEW>
     {teacher_product_owner_review}
     </REVIEW>
     ```
2. Script `train_po_lora.py` (pendiente) con args:
   ```bash
   python train_po_lora.py \
     --data artifacts/distillation/po_teacher_dataset.jsonl \
     --base mistral-7b-instruct \
     --output artifacts/models/po_student_v1 \
     --rank 32 --alpha 64 --epochs 3 --batch 4 --lr 1e-4
   ```
3. Guardar:
   - `artifacts/models/po_student_v1/adapter`
   - `logs/distillation/po_student_v1.log`
4. Conversión a full weights + quantization:
   ```bash
   python merge_lora.py --adapter artifacts/models/po_student_v1 \
     --base mistral-7b-instruct \
     --output artifacts/models/po_student_v1/po_student_v1.safetensors
   ```
   Luego crear `Modelfile` para Ollama.

## 6. Validación (9.D.4)

1. Re-ejecutar `scripts/run_product_owner.py` con el student en un subset de 50 conceptos y comparar:
   - `product_owner_metric`
   - Tiempo promedio por inferencia
   - Diferencias textuales (diff YAML)
2. Documentar en `docs/po_distillation_report.md`:
   - Tablas teacher vs student
   - Observaciones cualitativas (tonos, riesgos)
   - Recomendaciones

## 7. Integración (9.D.5)

1. `config.yaml`:
   ```yaml
   roles:
     product_owner:
       provider: ollama
       model: po-student-v1
       temperature: 0.4
       max_tokens: 4096
   ```
2. `scripts/run_product_owner.py` no requiere cambios (mismos prompts).
3. `Makefile`/`make po` sin modificaciones, pero documentar variable `PO_MODEL=po-student-v1` para toggles.

## 8. Cronograma

| Día | Actividad |
|-----|-----------|
| 1 | Generar 600 ejemplos teacher + validar |
| 2 | Entrenar LoRA + merge + empaquetar |
| 3 | Validación + actualización config + smoke test `make po` |

## 9. Consideraciones

- Conservar los 5 registros fallidos de PO (POCON-0004/0009/0012/0115/0191) para verificar si el student los maneja mejor.
- Mantener versionado del adapter (po_student_v1, v2, etc.) y del dataset maestro.
- Una vez validado PO, considerar repetir el proceso para Architect/Dev si los tiempos siguen siendo altos.

---
**Última actualización**: 2025-11-10  
**Owner**: Equipo DSPy / Product Owner  
**Estado**: Plan listo; iniciar 9.D.2 (dataset maestro).
