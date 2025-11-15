# LoRA Improvement Plan - Step 3: Training Instructions (Colab / Lightning)
**Date**: 2025-11-15
**Task**: Re-run LoRA training with optimized hyperparameters

---

## Prerequisites Checklist

- [ ] Supervised dataset ready: `artifacts/distillation/po_teacher_supervised.jsonl` (359 samples)
- [ ] Runtime con GPU (Google Colab **o** Lightning AI Studio)
- [ ] Repositorio clonado (`git clone -b dspy-multi-role ...`)
- [ ] Opcional (solo Colab): Google Drive montado si quieres respaldos adicionales

### Nota sobre Lightning AI Studio
- No es necesario (ni posible) montar Google Drive.
- El notebook detecta automáticamente si se ejecuta en Lightning y usa `/workspace/` para guardar artefactos temporales (`po_student_v2/`, `po_student_v2_adapter/`).
- Los artefactos finales se pueden descargar usando la celda de compresión (`zip`) o copiarse dentro del propio repo (`artifacts/models/...`).

---

## Step-by-Step Training Instructions

### 1. Subir / copiar el dataset al entorno

**Opción A (sólo Colab): carga directa**
```python
from google.colab import files
uploaded = files.upload()
# Upload: artifacts/distillation/po_teacher_supervised.jsonl
```

**Opción B (sólo Colab): desde Google Drive**
```python
from google.colab import drive
drive.mount('/content/drive')

# Copiar dataset dentro del entorno actual
!cp /content/drive/MyDrive/path/to/po_teacher_supervised.jsonl /content/
```

**Opción C (Lightning u otros entornos)**: subir/copy desde la máquina local o almacenamiento interno.
```bash
# Ejemplo: usar scp o gcloud para subir al directorio del proyecto
# Luego asegúrate de que el archivo exista en DATASET_PATH
```

---

### 2. Install Dependencies

```python
# Install required packages (compatible with Qwen2.5 models)
!pip install -q --upgrade --no-cache-dir \
  "transformers>=4.38.0" \
  "peft>=0.11.1" \
  "bitsandbytes>=0.43.2" \
  "accelerate>=0.28.0" \
  "datasets>=2.19.0"
!pip install -q --upgrade --no-cache-dir "transformers @ git+https://github.com/huggingface/transformers.git"

import importlib
importlib.invalidate_caches()

import transformers, peft, datasets
print("✅ transformers", transformers.__version__)
print("✅ peft", peft.__version__)
print("✅ datasets", datasets.__version__)
```

> Si aparece un error de importación tras el `pip install`, reinicia el runtime/kernel y vuelve a ejecutar esta celda para asegurarte de que se cargue la versión nueva. La segunda línea instala la última versión de desarrollo de `transformers`, necesaria para `Qwen/Qwen2.5-7B-Instruct` en algunos entornos (Lightning AI Studio).

**Expected time**: ~2-3 minutes

---

### 3. Load and Prepare Dataset

```python
import json
from datasets import Dataset

DATASET_PATH = "artifacts/distillation/po_teacher_supervised.jsonl"  # ajusta según tu entorno

# Load supervised dataset
data = []
with open(DATASET_PATH, "r") as f:
    for line in f:
        if line.strip():
            data.append(json.loads(line))

print(f"Loaded {len(data)} training examples")

# Convert to HuggingFace Dataset
train_dataset = Dataset.from_list(data)
print(train_dataset)

# Verify data structure
print("\nSample prompt (first 200 chars):")
print(train_dataset[0]["prompt"][:200])
print("\nSample response (first 200 chars):")
print(train_dataset[0]["response"][:200])
```

**Expected output**:
```
Loaded 359 training examples
Dataset({
    features: ['prompt', 'response'],
    num_rows: 359
})
```

---

### 4. Load Base Model

```python
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig
)

model_name = "Qwen/Qwen2.5-7B-Instruct"

# Configure 4-bit quantization
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

# Load model
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    trust_remote_code=True
)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print(f"Model loaded: {model_name}")
print(f"Model device: {model.device}")
```

**Expected time**: ~5-7 minutes (downloading model)

---

### 5. Configure LoRA

```python
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Prepare model for training
model = prepare_model_for_kbit_training(model)

# LoRA configuration
lora_config = LoraConfig(
    r=32,                      # Rank (unchanged)
    lora_alpha=64,             # Alpha (unchanged)
    target_modules=[           # Target all linear layers
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    lora_dropout=0.05,         # Dropout (unchanged)
    bias="none",
    task_type="CAUSAL_LM",
)

# Apply LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
```

**Expected output**:
```
trainable params: ~X,XXX,XXX || all params: ~7,XXX,XXX,XXX || trainable%: ~X.XX
```

---

### 6. Tokenize Dataset

```python
def tokenize_function(examples):
    # Combine prompt and response with chat template
    full_texts = []
    for prompt, response in zip(examples["prompt"], examples["response"]):
        # Format as chat message
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )
        full_texts.append(text)

    # Tokenize con padding fijo
    tokenized = tokenizer(
        full_texts,
        truncation=True,
        padding="max_length",
        max_length=1536,
    )

    tokenized["labels"] = tokenized["input_ids"].copy()

    return tokenized

# Apply tokenization
tokenized_dataset = train_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=train_dataset.column_names,
)

print(f"Tokenized dataset: {len(tokenized_dataset)} examples")
print(f"Sample token count: {len(tokenized_dataset[0]['input_ids'])}")
```

---

### 7. Configure Training Arguments (OPTIMIZED)

```python
from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling

training_args = TrainingArguments(
    # Output
    output_dir="/content/po_student_v2",

    # Training schedule (OPTIMIZED para T4/Lightning)
    num_train_epochs=4,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=24,        # Effective batch ≈24

    # Learning rate (OPTIMIZED)
    learning_rate=8e-5,                    # ← CHANGED from 1e-4 to 8e-5
    lr_scheduler_type="cosine",            # ← CHANGED from "linear" to "cosine"
    warmup_ratio=0.05,                     # ← CHANGED from 0.1 to 0.05

    # Optimization
    optim="paged_adamw_8bit",
    fp16=True,
    max_grad_norm=1.0,

    # Logging and saving
    logging_steps=10,
    save_strategy="epoch",
    save_total_limit=2,
    torch_empty_cache_steps=10,

    # Performance
    dataloader_num_workers=2,
    remove_unused_columns=False,
)

# Data collator
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
)

# Create trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator,
)

print("Trainer configured with OPTIMIZED hyperparameters:")
print(f"  - Epochs: {training_args.num_train_epochs}")
print(f"  - Learning rate: {training_args.learning_rate}")
print(f"  - LR scheduler: {training_args.lr_scheduler_type}")
print(f"  - Warmup ratio: {training_args.warmup_ratio}")
print(f"  - Gradient accumulation: {training_args.gradient_accumulation_steps}")
print(f"  - Effective batch size: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
```

**Key Changes from Previous Training**:
| Hyperparameter | Old Value | New Value | Rationale |
|----------------|-----------|-----------|-----------|
| `num_train_epochs` | 3 | **4** | More iterations for conflicts examples |
| `learning_rate` | 1e-4 | **8e-5** | Gentler learning for fine-grained distinction |
| `lr_scheduler_type` | linear | **cosine** | Smoother convergence at end of training |
| `warmup_ratio` | 0.1 | **0.05** | Faster ramp-up for small dataset |
| `per_device_train_batch_size` | 2 | **1** | Ajustado para GPUs T4 (Lightning) |
| `gradient_accumulation_steps` | 8 | **24** | Mantiene batch efectivo ≈24 con menos VRAM |

---

### 8. Run Training

```python
import torch
torch.cuda.empty_cache()

print("\n🚀 Starting training...\n")
trainer.train()
```

**Expected training time**: ~30-45 minutes (T4 GPU)

**Expected output**:
```
{'loss': X.XXX, 'learning_rate': X.XXXXe-XX, 'epoch': 0.XX}
{'loss': X.XXX, 'learning_rate': X.XXXXe-XX, 'epoch': 0.XX}
...
{'train_runtime': XXXX.XX, 'train_samples_per_second': X.XX, 'train_steps_per_second': X.XX, 'train_loss': X.XXX, 'epoch': 4.0}
```

**Monitoring tips**:
- Loss should decrease steadily from ~1.5-2.0 to ~0.5-0.8
- Learning rate should follow cosine curve (high → low smoothly)
- If loss plateaus early, consider increasing learning rate
- If loss oscillates wildly, decrease learning rate

---

### 9. Save Adapter

```python
# Save LoRA adapter
trainer.model.save_pretrained("/content/po_student_v2_adapter")
tokenizer.save_pretrained("/content/po_student_v2_adapter")

print("Adapter saved to /content/po_student_v2_adapter")

# Verify files
!ls -lh /content/po_student_v2_adapter
```

**Expected files**:
```
adapter_config.json
adapter_model.safetensors  (or adapter_model.bin)
tokenizer.json
tokenizer_config.json
special_tokens_map.json
```

---

### 10. Download Adapter to Local Machine

**Opción A (Colab)**: Descargar desde la UI
```python
!zip -r po_student_v2_adapter.zip /content/po_student_v2_adapter
from google.colab import files
files.download('/content/po_student_v2_adapter.zip')
```

**Option B: Save to Google Drive**
```python
# Copy to Drive
!cp -r /content/po_student_v2_adapter /content/drive/MyDrive/lora_adapters/

print("Adapter saved to Google Drive: /content/drive/MyDrive/lora_adapters/po_student_v2_adapter")
```

**Option C: Upload to Cloud Storage**
```bash
# Install gsutil (if not already available)
!pip install gsutil

# Upload to GCS bucket
!gsutil -m cp -r /content/po_student_v2_adapter gs://your-bucket-name/po_student_v2/
```

---

### 11. Verify Adapter Locally

**On local machine**, extract and verify:

```bash
# Extract downloaded zip
unzip po_student_v2_adapter.zip -d artifacts/models/

# Verify structure
ls -lh artifacts/models/po_student_v2_adapter/

# Expected output:
# adapter_config.json
# adapter_model.safetensors
# tokenizer files
```

---

## Training Hyperparameters Summary

### Final Configuration (Optimized)

```yaml
model: Qwen/Qwen2.5-7B-Instruct
quantization: 4-bit (nf4, double quant)
lora_config:
  r: 32
  lora_alpha: 64
  lora_dropout: 0.05
  target_modules: [q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj]

training:
  epochs: 4                              # ← Increased from 3
  batch_size: 2
  gradient_accumulation: 12              # ← Increased from 8
  effective_batch_size: 24               # = 2 * 12
  learning_rate: 8e-5                    # ← Decreased from 1e-4
  lr_scheduler: cosine                   # ← Changed from linear
  warmup_ratio: 0.05                     # ← Decreased from 0.1
  optimizer: paged_adamw_8bit
  fp16: true
  max_grad_norm: 1.0

dataset:
  total_samples: 359
  status_distribution:
    aligned: 240 (66.9%)
    needs_adjustment: 109 (30.4%)
    conflicts: 10 (2.8%)
  min_score: 0.82
```

---

## Expected Training Metrics

### Loss Trajectory (Estimated)

| Epoch | Expected Loss Range | Notes |
|-------|---------------------|-------|
| 0.25 | 1.5 - 2.0 | Initial high loss |
| 0.50 | 1.2 - 1.5 | Rapid initial descent |
| 1.00 | 0.9 - 1.2 | First epoch complete |
| 2.00 | 0.7 - 1.0 | Continued descent |
| 3.00 | 0.5 - 0.8 | Approaching convergence |
| 4.00 | 0.4 - 0.7 | Final epoch (cosine tail) |

### Learning Rate Schedule (Cosine)

- **Warmup phase** (steps 0-18): 0 → 8e-5
- **Cosine decay** (steps 18-359): 8e-5 → ~1e-7
- **Advantage**: Smoother convergence, less overfitting risk

---

## Troubleshooting

### Issue: Out of Memory (OOM)

**Symptoms**: `CUDA out of memory` error during training

**Solutions**:
1. Reduce `per_device_train_batch_size` to 1
2. Increase `gradient_accumulation_steps` to 24 (to maintain effective batch size)
3. Reduce `max_length` in tokenization to 1536
4. Clear cache: `torch.cuda.empty_cache()`

### Issue: Loss Not Decreasing

**Symptoms**: Loss stays high (>1.5) after 1 epoch

**Solutions**:
1. Verify dataset loaded correctly (check sample prompts/responses)
2. Check learning rate isn't too low (try 1e-4 instead of 8e-5)
3. Ensure `labels` are set correctly in tokenization
4. Check for tokenization errors (truncation issues)

### Issue: Loss Oscillating Wildly

**Symptoms**: Loss jumps up and down between steps

**Solutions**:
1. Decrease learning rate to 5e-5
2. Increase warmup ratio to 0.1
3. Check for data quality issues (malformed examples)
4. Reduce `max_grad_norm` to 0.5

### Issue: Training Too Slow

**Symptoms**: Training taking >1 hour

**Solutions**:
1. Verify GPU runtime selected (Runtime → Change runtime type → GPU)
2. Check GPU utilization: `!nvidia-smi`
3. Reduce `dataloader_num_workers` to 0 if CPU bottleneck
4. Use smaller `max_length` (1536 instead of 2048)

---

## Post-Training Checklist

- [ ] Training completed without errors
- [ ] Final loss < 0.8 (ideally < 0.7)
- [ ] Adapter files saved successfully
- [ ] Adapter downloaded to local machine
- [ ] Files extracted to `artifacts/models/po_student_v2_adapter/`
- [ ] Adapter size ~50-100 MB (safetensors) or ~100-200 MB (bin)

---

## Next Steps: Paso 4

After training completes and adapter is downloaded:

1. **Verify adapter loads locally**:
   ```bash
   PYTHONPATH=. .venv/bin/python -c "
   from peft import AutoPeftModelForCausalLM
   model = AutoPeftModelForCausalLM.from_pretrained(
       'artifacts/models/po_student_v2_adapter',
       device_map='auto',
       load_in_4bit=True
   )
   print('Model loaded successfully')
   "
   ```

2. **Run evaluation script** (Paso 4):
   ```bash
   PYTHONPATH=. .venv/bin/python scripts/eval_po_student.py \
     --adapter artifacts/models/po_student_v2_adapter \
     --max-samples 40 \
     --output inference_results/student_v2.json
   ```

3. **Compare with baseline**:
   - Baseline: `inference_results/baseline_20251114_215442.json`
   - Student v1: `inference_results/student_20251114_220448.json`
   - Student v2: `inference_results/student_v2.json`

4. **Check success criteria**:
   - Mean ≥ 0.82
   - Std ≤ 0.10
   - Delta vs baseline ≤ 0.03

---

**Prepared by**: Claude Code
**Review Status**: Ready for Colab / Lightning execution
