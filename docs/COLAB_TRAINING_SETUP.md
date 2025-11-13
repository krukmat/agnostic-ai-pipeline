# Google Colab Training Setup - PO LoRA Fine-tuning

**Fecha**: 2025-11-13
**Objetivo**: Entrenar modelo Product Owner usando LoRA en Google Colab Free (T4 GPU)

---

## 🚀 Setup Completo para Colab

### 1. Verificación Inicial

```python
# Cell 1: Verificar GPU disponible
!nvidia-smi

# Verificar CUDA
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
```

**Output esperado**: T4 con ~15GB VRAM, CUDA 11.x o 12.x

---

### 2. Instalación de Dependencias

```python
# Cell 2: Instalar librerías necesarias
!pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
!pip install -q transformers==4.36.0 peft==0.7.0 bitsandbytes==0.41.0 accelerate==0.25.0 datasets==2.16.0
!pip install -q typer

# Verificar instalación
import transformers
import peft
import bitsandbytes
import datasets
import typer
print("✅ All packages installed successfully")
```

**Versiones recomendadas**:
- `transformers>=4.36.0` - Para soporte de Qwen2.5
- `peft>=0.7.0` - Para LoRA
- `bitsandbytes>=0.41.0` - Para quantization 4-bit
- `accelerate>=0.25.0` - Para distributed training
- `datasets>=2.16.0` - Para data loading

---

### 3. Subir Archivos a Colab

```python
# Cell 3: Montar Google Drive o subir archivos manualmente
from google.colab import drive
drive.mount('/content/drive')

# Opción A: Si subiste el repo completo a Drive
%cd /content/drive/MyDrive/agnostic-ai-pipeline

# Opción B: Clonar desde GitHub
# !git clone https://github.com/tu-usuario/agnostic-ai-pipeline.git
# %cd agnostic-ai-pipeline

# Opción C: Subir solo archivos necesarios
from google.colab import files
uploaded = files.upload()  # Sube scripts/train_po_lora.py y el dataset
```

**Archivos necesarios**:
- `scripts/train_po_lora.py` (script de entrenamiento)
- `artifacts/distillation/po_teacher_supervised.jsonl` (dataset, ~1.7MB)

---

### 4. Verificar Dataset

```python
# Cell 4: Verificar que el dataset esté correcto
import json

dataset_path = "/content/agnostic-ai-pipeline/artifacts/distillation/po_teacher_supervised.jsonl"

# Contar registros
with open(dataset_path) as f:
    samples = [line for line in f if line.strip()]
    print(f"✅ Dataset tiene {len(samples)} registros")

# Ver primer sample
with open(dataset_path) as f:
    first = json.loads(f.readline())
    print(f"\n📝 Keys: {list(first.keys())}")
    print(f"📏 Prompt length: {len(first['prompt'])} chars")
    print(f"📏 Response length: {len(first['response'])} chars")
    print(f"\n🔍 Preview prompt:")
    print(first['prompt'][:200] + "...")
```

**Output esperado**:
- ~200+ registros
- Keys: `['prompt', 'response']`
- Longitudes entre 1500-4000 caracteres

---

### 5. Ejecutar Training (Versión Optimizada para T4)

```python
# Cell 5: Training con parámetros optimizados para T4 (15GB VRAM)
!python scripts/train_po_lora.py \
    --data-path /content/agnostic-ai-pipeline/artifacts/distillation/po_teacher_supervised.jsonl \
    --base-model Qwen/Qwen2.5-7B-Instruct \
    --output-dir /content/agnostic-ai-pipeline/artifacts/models/po_student_v1 \
    --rank 32 \
    --alpha 64 \
    --dropout 0.05 \
    --epochs 3 \
    --batch-size 1 \
    --gradient-accumulation-steps 8 \
    --lr 1e-4 \
    --max-length 2048 \
    --load-4bit \
    --bnb-compute-dtype float16 \
    --gradient-checkpointing
```

**Parámetros clave**:
- `--load-4bit`: Carga modelo en 4-bit (ahorra ~10GB VRAM)
- `--gradient-checkpointing`: Reduce VRAM adicional
- `--batch-size 1 --gradient-accumulation-steps 8`: Batch efectivo de 8 sin VRAM extra
- `--max-length 2048`: Reduce memoria vs 4096

**Tiempo estimado**: ~3-5 horas en T4 para 3 epochs con ~200 samples

---

### 6. Monitoreo Durante Training

```python
# Cell 6 (en otra celda mientras corre): Monitorear progreso
!tail -50 /content/agnostic-ai-pipeline/artifacts/models/po_student_v1/training_log.txt

# Ver uso de GPU
!nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total --format=csv -l 10
```

---

## 🔍 Troubleshooting

### Error 1: `CUDA out of memory`

**Causa**: Model + gradients no caben en 15GB VRAM

**Soluciones**:
```python
# Opción A: Reducir max_length
--max-length 1024  # En vez de 2048

# Opción B: Reducir LoRA rank
--rank 16 --alpha 32  # En vez de 32/64

# Opción C: Aumentar gradient accumulation
--gradient-accumulation-steps 16  # En vez de 8
```

---

### Error 2: `ModuleNotFoundError: No module named 'bitsandbytes'`

**Causa**: bitsandbytes no instalado correctamente

**Solución**:
```python
!pip uninstall -y bitsandbytes
!pip install bitsandbytes==0.41.0 --no-cache-dir

# Verificar
import bitsandbytes
print(bitsandbytes.__version__)
```

---

### Error 3: `OSError: Qwen/Qwen2.5-7B-Instruct does not appear to be a valid model`

**Causa**: Error descargando modelo desde HuggingFace

**Soluciones**:
```python
# Verificar conectividad
!curl -I https://huggingface.co

# Login a HuggingFace (si el modelo es privado)
from huggingface_hub import login
login()  # Te pedirá tu token

# Pre-descargar modelo
from transformers import AutoTokenizer, AutoModelForCausalLM
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
print("✅ Model downloaded successfully")
```

---

### Error 4: `RuntimeError: No CUDA GPUs are available`

**Causa**: Colab no asignó GPU o runtime no es GPU

**Solución**:
1. Runtime → Change runtime type → Hardware accelerator: **T4 GPU**
2. Reiniciar runtime y ejecutar Cell 1 nuevamente

---

### Error 5: `FileNotFoundError: po_teacher_supervised.jsonl`

**Causa**: Path incorrecto al dataset

**Solución**:
```python
# Verificar ubicación exacta
!find /content -name "po_teacher_supervised.jsonl" 2>/dev/null

# Usar path correcto
# Si está en /content/drive/..., ajustar el comando:
--data-path /content/drive/MyDrive/agnostic-ai-pipeline/artifacts/distillation/po_teacher_supervised.jsonl
```

---

### Error 6: Training muy lento (< 1 it/s)

**Causa**: Gradient accumulation alto + batch processing

**Soluciones**:
```python
# Reducir gradient accumulation si tienes suficiente VRAM
--gradient-accumulation-steps 4  # En vez de 8

# Reducir max_length
--max-length 1536  # En vez de 2048

# Desactivar algunas features (solo si es necesario)
--gradient-checkpointing false  # Aumenta speed pero usa más VRAM
```

---

## 📊 Métricas Esperadas

### Durante Training

```
Epoch 1/3: 100%|██████████| 25/25 [12:34<00:00,  0.05it/s]
{'loss': 1.2345, 'learning_rate': 9.5e-05, 'epoch': 1.0}

Epoch 2/3: 100%|██████████| 25/25 [12:31<00:00,  0.05it/s]
{'loss': 0.8912, 'learning_rate': 5.0e-05, 'epoch': 2.0}

Epoch 3/3: 100%|██████████| 25/25 [12:29<00:00,  0.05it/s]
{'loss': 0.6234, 'learning_rate': 5.0e-06, 'epoch': 3.0}
```

**Indicadores de éxito**:
- ✅ Loss decreciente (1.2 → 0.6)
- ✅ No crashes por OOM
- ✅ ~0.03-0.05 it/s en T4
- ✅ Checkpoints guardados cada epoch

---

## 💾 Guardar Resultados

```python
# Cell 7: Descargar modelo entrenado
from google.colab import files
import shutil

# Comprimir modelo
!zip -r po_student_v1.zip /content/agnostic-ai-pipeline/artifacts/models/po_student_v1

# Descargar
files.download('po_student_v1.zip')

# O copiar a Drive
!cp -r /content/agnostic-ai-pipeline/artifacts/models/po_student_v1 /content/drive/MyDrive/
```

---

## 🧪 Probar Modelo Entrenado

```python
# Cell 8: Quick inference test
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

base_model = "Qwen/Qwen2.5-7B-Instruct"
adapter_path = "/content/agnostic-ai-pipeline/artifacts/models/po_student_v1"

# Cargar
tokenizer = AutoTokenizer.from_pretrained(base_model)
model = AutoModelForCausalLM.from_pretrained(
    base_model,
    load_in_4bit=True,
    device_map="auto"
)
model = PeftModel.from_pretrained(model, adapter_path)

# Test prompt
test_prompt = """[INSTRUCTIONS]
You are a Product Owner validating requirements...

[REQUIREMENTS]
- Users should be able to create blog posts
- Posts must have a title and content
- Authentication is required

[YOUR RESPONSE]"""

inputs = tokenizer(test_prompt, return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=512)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

---

## 📝 Comandos Resumidos

### Comando Original (Tu intento)
```bash
!python scripts/train_po_lora.py \
    --data-path /content/agnostic-ai-pipeline/artifacts/distillation/po_teacher_supervised.jsonl \
    --base-model Qwen/Qwen2.5-7B-Instruct \
    --output-dir /content/agnostic-ai-pipeline/artifacts/models/po_student_v1 \
    --rank 32 --alpha 64 --dropout 0.05 \
    --epochs 3 --batch-size 1 --gradient-accumulation-steps 8 \
    --lr 1e-4 --max-length 2048 \
    --load-4bit --bnb-compute-dtype float16
```

### Comando Optimizado para T4 Free
```bash
!python scripts/train_po_lora.py \
    --data-path /content/agnostic-ai-pipeline/artifacts/distillation/po_teacher_supervised.jsonl \
    --base-model Qwen/Qwen2.5-7B-Instruct \
    --output-dir /content/agnostic-ai-pipeline/artifacts/models/po_student_v1 \
    --rank 16 \
    --alpha 32 \
    --dropout 0.05 \
    --epochs 3 \
    --batch-size 1 \
    --gradient-accumulation-steps 16 \
    --lr 1e-4 \
    --max-length 1536 \
    --load-4bit \
    --bnb-compute-dtype float16 \
    --gradient-checkpointing
```

**Cambios clave**:
- Rank reducido: 16 (ahorra VRAM)
- Gradient accumulation: 16 (batch efectivo se mantiene)
- Max length: 1536 (reduce picos de memoria)
- Gradient checkpointing: Explícitamente activado

---

## ⚠️ Limitaciones de Colab Free

1. **Timeout**: Colab Free desconecta después de 12 horas (o antes si hay inactividad)
   - **Solución**: Entrenamiento debería terminar en 3-5 horas

2. **Disconnection**: Puede desconectarse si dejas la pestaña inactiva
   - **Solución**: Ejecuta este snippet para evitar inactividad:
   ```javascript
   // En console de navegador (F12):
   function KeepClicking(){
       console.log("Clicking");
       document.querySelector("colab-connect-button").click()
   }
   setInterval(KeepClicking,60000)
   ```

3. **VRAM**: T4 tiene 15GB pero compartido con otros procesos
   - **Solución**: Usa 4-bit quantization obligatorio

4. **Disk Space**: ~100GB disponible pero se llena con caché de HF
   - **Solución**: Limpia caché periódicamente:
   ```python
   !rm -rf ~/.cache/huggingface/hub/*
   ```

---

## 🔗 Referencias

- **HuggingFace Qwen2.5**: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- **PEFT Documentation**: https://huggingface.co/docs/peft/
- **bitsandbytes**: https://github.com/TimDettmers/bitsandbytes
- **Training Script**: `scripts/train_po_lora.py`

---

**Última actualización**: 2025-11-13
**Próxima tarea**: Task 9.D.4 - Validar modelo distilado
