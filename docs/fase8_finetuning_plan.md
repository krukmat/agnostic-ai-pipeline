# Fase 8.4: Plan de Fine-Tuning LoRA

**Fecha**: 2025-11-09
**Objetivo**: Fine-tuning de Mistral-7B-Instruct con LoRA en CPU para el rol BA

---

## 1. Configuración del Modelo Base

### Modelo Seleccionado
- **Nombre**: `mistral-7b-instruct-v0.1`
- **Tamaño**: 4.4GB
- **Arquitectura**: Mistral 7B Instruct
- **Proveedor**: Ollama
- **Score Baseline**: 85.35% (post-MIPROv2)

### Justificación
- ✅ Mejor performance en evaluación inicial (72% → 85.35% con optimización)
- ✅ Tamaño manejable para CPU training
- ✅ Soporte nativo de instrucciones (Instruct tuning)
- ✅ Compatible con transformers/peft/bitsandbytes

---

## 2. Configuración LoRA (Low-Rank Adaptation)

### Parámetros LoRA

```python
from peft import LoraConfig, get_peft_model, TaskType

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,                          # Rank de las matrices LoRA (8-16 típico)
    lora_alpha=32,                # Scaling factor (alpha/r = 4.0)
    lora_dropout=0.1,             # Dropout para regularización
    target_modules=[              # Módulos a adaptar
        "q_proj",                 # Query projection
        "k_proj",                 # Key projection
        "v_proj",                 # Value projection
        "o_proj",                 # Output projection
    ],
    bias="none",                  # No adaptar bias
    inference_mode=False,         # Training mode
)
```

### Justificación de Parámetros
- **r=8**: Balance entre capacidad expresiva y eficiencia
  - Menos parámetros entrenables → menos overfitting
  - Suficiente para tarea específica de BA
- **lora_alpha=32**: Ratio alpha/r = 4.0 (estándar)
- **target_modules**: Solo attention layers (Q, K, V, O)
  - ~1-2% de parámetros totales
  - Más eficiente que adaptar FFN

### Cálculo de Parámetros Entrenables
- Modelo base: ~7B parámetros
- Con LoRA r=8: ~4M parámetros entrenables (~0.05%)
- Memoria estimada: ~500MB adicionales (4-bit quantization)

---

## 3. Configuración de Cuantización (4-bit)

### BitsAndBytes Config

```python
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,                     # Cuantización 4-bit
    bnb_4bit_use_double_quant=True,        # Double quantization (ahorra memoria)
    bnb_4bit_quant_type="nf4",             # Normal Float 4-bit (recomendado)
    bnb_4bit_compute_dtype=torch.bfloat16, # Compute en bfloat16
)
```

### Beneficios
- ✅ Reduce memoria del modelo de ~14GB a ~4GB
- ✅ Permite entrenamiento en CPU con 16GB RAM
- ✅ Mínima degradación de calidad (< 1%)
- ✅ Compatible con LoRA (QLoRA)

---

## 4. Hiperparámetros de Entrenamiento

### TrainingArguments

```python
from transformers import TrainingArguments

training_args = TrainingArguments(
    # Output
    output_dir="artifacts/finetuning/mistral-7b-ba-lora",
    overwrite_output_dir=True,

    # Training
    num_train_epochs=3,                    # 3 épocas (98 ejemplos × 3 = 294 steps)
    per_device_train_batch_size=1,         # Batch=1 para CPU
    gradient_accumulation_steps=8,         # Simular batch=8
    learning_rate=2e-4,                    # LR típico para LoRA (1e-4 a 5e-4)
    weight_decay=0.01,                     # Regularización L2
    warmup_steps=10,                       # 10% de 98 steps/epoch
    max_grad_norm=1.0,                     # Gradient clipping

    # Optimization
    optim="adamw_torch",                   # AdamW (torch nativo, no 8-bit)
    lr_scheduler_type="cosine",            # Cosine decay

    # Evaluation
    evaluation_strategy="epoch",           # Evaluar cada época
    save_strategy="epoch",                 # Guardar checkpoint cada época
    load_best_model_at_end=True,           # Cargar mejor checkpoint
    metric_for_best_model="eval_loss",     # Métrica para selección

    # Hardware
    use_cpu=True,                          # Forzar CPU (no GPU)
    dataloader_num_workers=0,              # No multiprocessing (CPU)

    # Logging
    logging_dir="artifacts/finetuning/logs",
    logging_steps=10,                      # Log cada 10 steps
    save_total_limit=2,                    # Solo 2 checkpoints (save space)

    # Misc
    seed=42,
    fp16=False,                            # No FP16 en CPU
    report_to="none",                      # Sin W&B/TensorBoard
)
```

### Justificación
- **Batch size efectivo**: 1 × 8 = 8 (gradient accumulation)
- **Learning rate**: 2e-4 (recomendado para LoRA)
- **Épocas**: 3 (balance overfitting vs convergencia)
- **Total steps**: 98 samples/epoch × 3 epochs = ~294 steps
- **Evaluación**: Cada época (98 steps) con val set (22 ejemplos)

---

## 5. Preparación de Datos

### Dataset Format
- **Train**: `artifacts/synthetic/ba_train_v2_fixed.jsonl` (98 ejemplos)
- **Val**: `artifacts/synthetic/ba_val_v2_fixed.jsonl` (22 ejemplos)

### Input Format (Instruction Tuning)

```python
def format_example(example):
    """Format example for instruction tuning."""
    concept = example["concept"]
    requirements = example["requirements"]

    # Serializar requirements a YAML
    requirements_yaml = yaml.safe_dump(requirements, allow_unicode=True)

    # Formato Mistral Instruct
    prompt = f"""[INST] You are a Business Analyst. Generate detailed business requirements for the following concept:

Concept: {concept}

Generate a structured requirements document with:
- title
- description
- functional_requirements (list with id, description, priority)
- non_functional_requirements (list with id, description, priority)
- constraints (list with id, description, priority)
[/INST]

{requirements_yaml}"""

    return {"text": prompt}
```

### Data Collator
```python
from transformers import DataCollatorForLanguageModeling

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,  # Causal LM (no masked)
)
```

---

## 6. Pipeline de Entrenamiento

### Script: `scripts/finetune_ba.py`

```python
#!/usr/bin/env python3
"""Fine-tune Mistral-7B-Instruct with LoRA for BA role."""

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset

# 1. Load tokenizer
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.1")
tokenizer.pad_token = tokenizer.eos_token

# 2. Load model with 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.1",
    quantization_config=bnb_config,
    device_map="cpu",
)

# 3. Apply LoRA
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,
    lora_alpha=32,
    lora_dropout=0.1,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    bias="none",
)
model = get_peft_model(model, lora_config)

# 4. Load datasets
train_dataset = load_dataset("json", data_files="artifacts/synthetic/ba_train_v2_fixed.jsonl", split="train")
val_dataset = load_dataset("json", data_files="artifacts/synthetic/ba_val_v2_fixed.jsonl", split="train")

# 5. Preprocess (tokenize)
def preprocess_function(examples):
    # ... format examples as shown above ...
    return tokenizer(examples["text"], truncation=True, max_length=2048)

train_dataset = train_dataset.map(preprocess_function, batched=True)
val_dataset = val_dataset.map(preprocess_function, batched=True)

# 6. Training arguments
training_args = TrainingArguments(
    # ... as defined above ...
)

# 7. Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
)

# 8. Train
trainer.train()

# 9. Save LoRA adapters
model.save_pretrained("artifacts/finetuning/mistral-7b-ba-lora")
tokenizer.save_pretrained("artifacts/finetuning/mistral-7b-ba-lora")
```

#### Modo Smoke Test

Antes de lanzar el entrenamiento completo podemos limitar la corrida directamente desde la CLI:

- `--train-limit N` / `--val-limit M`: recorta los datasets cargados a los primeros `N`/`M` ejemplos sin tocar los archivos en disco. Útil para validar tokenización y forward/backward.
- `--max-steps K`: pasa el valor a `TrainingArguments.max_steps`, forzando que el Trainer termine tras `K` steps aunque queden épocas pendientes.

Ejemplo de validación rápida:

```bash
.venv/bin/python scripts/finetune_ba.py \
  --train artifacts/synthetic/ba_train_v2_fixed.jsonl \
  --val artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/finetuning/mistral-7b-ba-lora-smoke \
  --train-limit 4 \
  --val-limit 2 \
  --max-steps 5
```

> Para el run oficial **no** usaremos estos flags; quedará registrado en `training_info.json` para auditar si se usó algún límite.

#### Checklist: preparar el modelo base sin conexión

Cuando el entorno no tiene acceso a `huggingface.co`, sigue estos pasos para traer el checkpoint y usarlo en modo totalmente local:

1. **Descargar en un host con internet**
   ```bash
   export HF_HOME=~/hf-models/mistral-7b-instruct
   huggingface-cli download mistralai/Mistral-7B-Instruct-v0.1 \
     --local-dir "$HF_HOME" \
     --local-dir-use-symlinks False
   du -sh "$HF_HOME"   # ~13 GB
   ls "$HF_HOME"
   ```
2. **Copiar los archivos al repositorio**
   ```bash
   REPO=/Users/matiasleandrokruk/Documents/agnostic-ai-pipeline
   mkdir -p "$REPO/artifacts/models/mistral-7b-instruct"
   rsync -avh "$HF_HOME"/ "$REPO/artifacts/models/mistral-7b-instruct"/
   ```
3. **Smoke test apuntando a la ruta local**
   ```bash
   cd "$REPO"
   .venv/bin/python scripts/finetune_ba.py \
     --train artifacts/synthetic/ba_train_v2_fixed.jsonl \
     --val artifacts/synthetic/ba_val_v2_fixed.jsonl \
     --output artifacts/finetuning/mistral-7b-ba-lora-smoke \
     --base-model artifacts/models/mistral-7b-instruct \
     --epochs 1 \
     --train-limit 2 \
     --val-limit 1 \
     --max-steps 2
     ```
4. **Run final**: Quitar los flags `--train-limit`, `--val-limit`, `--max-steps`, usar `--output artifacts/finetuning/mistral-7b-ba-lora` y dejar que se ejecuten las 3 épocas completas.
   - En CPU sin bitsandbytes usa `--quantization bf16` o `--quantization fp32` (más memoria, pero sin dependencias externas).
   - En entornos con bitsandbytes + GPU, usa el plan original `--quantization bnb4` para mantener el modelo en 4-bit.

---

## 7. Evaluación Post Fine-Tuning

### Métricas de Evaluación

1. **Training Loss**: Convergencia durante entrenamiento
2. **Validation Loss**: Generalization capability
3. **BA Requirements Metric**: Score en val set (target > 85.35%)

### Protocolo de Evaluación

```bash
# 1. Evaluar modelo fine-tuned
python scripts/eval_ba.py \
  --model artifacts/finetuning/mistral-7b-ba-lora \
  --dataset artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/finetuning/eval_report.json

# 2. Comparación 3-way (Baseline vs Optimized vs Fine-tuned)
python scripts/compare_models.py \
  --baseline "ollama:mistral:7b-instruct" \
  --optimized "artifacts/dspy/local_base_optimized" \
  --finetuned "artifacts/finetuning/mistral-7b-ba-lora" \
  --dataset artifacts/synthetic/ba_val_v2_fixed.jsonl
```

### Criterios de Éxito
- ✅ **Validation loss**: Convergencia sin overfitting
- ✅ **BA Metric Score**: ≥ 85.35% (baseline MIPROv2)
- ✅ **Mejora esperada**: +5-10% (target: 90-95%)

---

## 8. Timeline y Estimaciones

### Tiempo de Entrenamiento (CPU)
- **Por época**: ~30-45 min (98 samples, batch=1, grad_accum=8)
- **Total (3 épocas)**: ~1.5-2.5 horas
- **Evaluación**: ~5 min/época (22 samples)

### Recursos
- **RAM**: 8-12GB (modelo 4-bit + gradientes)
- **Disco**:
  - Modelo base: 4.4GB
  - LoRA adapters: ~50MB
  - Checkpoints: ~500MB × 2 = 1GB
  - Total: ~6GB

### Pasos de Ejecución
1. ✅ **Setup** (completado): Instalar peft, transformers, bitsandbytes
2. ⏳ **Dataset prep** (5 min): Formatear ejemplos con instruction tuning
3. ⏳ **Model download** (10 min): Descargar Mistral-7B-Instruct desde HF
4. ⏳ **Fine-tuning** (1.5-2.5h): Entrenar 3 épocas
5. ⏳ **Evaluation** (10 min): Benchmark en val set
6. ⏳ **Comparison** (5 min): 3-way comparison report

---

## 9. Integración con Pipeline

### Cargar Modelo Fine-Tuned

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.1",
    device_map="cpu",
)

# Load LoRA adapters
model = PeftModel.from_pretrained(
    base_model,
    "artifacts/finetuning/mistral-7b-ba-lora",
)

tokenizer = AutoTokenizer.from_pretrained("artifacts/finetuning/mistral-7b-ba-lora")

# Inference
prompt = "[INST] Generate requirements for: A mobile app for food delivery [/INST]"
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=2048)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

### Agregar a `config.yaml`

```yaml
roles:
  ba:
    provider: huggingface_local
    model: artifacts/finetuning/mistral-7b-ba-lora
    temperature: 0.7
    max_tokens: 2048
```

---

## 10. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Overfitting (98 samples pequeño) | Alta | Medio | - Usar dropout 0.1<br>- Rank bajo (r=8)<br>- Early stopping |
| No mejora sobre baseline | Media | Alto | - Si score < 85%, mantener baseline<br>- Iterar con más datos |
| OOM en CPU (RAM insuficiente) | Baja | Alto | - 4-bit quantization<br>- batch_size=1<br>- grad_accum=8 |
| Tiempo entrenamiento largo | Alta | Bajo | - Aceptable (1-2h es razonable)<br>- Opción: reducir a 2 épocas |
| Descarga del modelo bloqueada | Alta (sandbox sin red) | Alto | - Descargar `mistralai/Mistral-7B-Instruct-v0.1` en host con red<br>- Sincronizar la caché local (`~/.cache/huggingface/hub` o `artifacts/models/`)<br>- Invocar `finetune_ba.py` con `--base-model /ruta/local` |

---

## 11. Próximos Pasos (Post Fine-Tuning)

### Si Fine-Tuning Mejora Score (≥90%)
1. ✅ Adoptar modelo fine-tuned como nuevo baseline
2. ✅ Actualizar `config.yaml` con modelo fine-tuned
3. ✅ Re-ejecutar benchmarks completos
4. ✅ Documentar mejoras en `docs/fase8_final_report.md`
5. ⏳ **Fase 9**: Extender a otros roles (Architect, Dev, QA)

### Si No Mejora
1. ✅ Mantener baseline MIPROv2 (85.35%)
2. ✅ Análisis de errores: ¿Qué no mejoró?
3. ⏳ **Opción A**: Generar más datos sintéticos (200+ ejemplos)
4. ⏳ **Opción B**: Ajustar hiperparámetros (r=16, alpha=64, LR)
5. ⏳ **Opción C**: Probar modelo más grande (Mistral-22B)

---

## Referencias

- [PEFT Documentation](https://huggingface.co/docs/peft)
- [LoRA Paper (Hu et al., 2021)](https://arxiv.org/abs/2106.09685)
- [QLoRA Paper (Dettmers et al., 2023)](https://arxiv.org/abs/2305.14314)
- [BitsAndBytes Quantization](https://github.com/TimDettmers/bitsandbytes)
- [Mistral-7B Model Card](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1)
