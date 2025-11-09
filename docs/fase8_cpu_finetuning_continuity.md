# Fase 8.4: Fine-Tuning en CPU - Guía de Continuidad

**Fecha Creación**: 2025-11-09
**Decisión**: Opción C - CPU con bf16 (100% local, sin GPU)
**Tiempo Estimado**: 73+ horas (3 días continuos)
**Objetivo**: Fine-tuning de Mistral-7B-Instruct con LoRA en CPU para mejorar score BA de 85.35% → 90%+

---

## Estado Actual (2025-11-09 16:54)
- ✅ Checklist previo completado (modelo local, datasets corregidos, dependencias).
- ✅ Comando lanzado en background con `nohup`:
  ```
  nohup .venv/bin/python scripts/finetune_ba.py ... --quantization bf16 > /tmp/finetune_ba_cpu_bf16.log 2>&1 &
  echo $! > /tmp/finetune_ba_pid.txt
  ```
- 🗂️ Output: `artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16`
- 🧾 Log: `/tmp/finetune_ba_cpu_bf16.log`
- 🔢 PID: `$(cat /tmp/finetune_ba_pid.txt)` (consultar antes de cerrar terminales)
- 📌 Próximo hito: dejar correr ~73 h y luego continuar con evaluación 3-way.

---

## ⚠️ ADVERTENCIA CRÍTICA

Este proceso tomará aproximadamente **73 horas (3 días)** de ejecución continua en CPU.

**Limitaciones conocidas**:
- ❌ NO usa cuantización 4-bit (bitsandbytes CPU-only no soporta)
- ❌ Modelo completo en RAM (~13GB en bf16)
- ⏱️ ~15 min por batch step (1 ejemplo)
- ⏱️ ~98 steps/época × 3 épocas = 294 steps × 15 min = **73.5 horas**

**Trade-offs aceptados**:
- ✅ 100% CPU local, $0 costo
- ✅ No requiere GPU ni cloud
- ✅ Cumple objetivo Fase 8 (pipeline local)
- ❌ No escalable a otros roles sin optimización

---

## 📋 CHECKLIST PRE-EJECUCIÓN

Antes de iniciar el fine-tuning, verificar:

### 1. Espacio en Disco
```bash
# Verificar espacio disponible (necesario: ~30GB)
df -h /Users/matiasleandrokruk/Documents/agnostic-ai-pipeline

# Breakdown:
# - Modelo Mistral-7B: ~13GB (artifacts/models/mistral-7b-instruct/)
# - Checkpoints: ~2GB por checkpoint × 2 = 4GB
# - Logs: ~500MB
# - LoRA adapters: ~50MB
# - Total: ~18GB + margen → 30GB recomendado
```

### 2. RAM Disponible
```bash
# Verificar RAM (necesario: 16GB mínimo, 32GB recomendado)
# macOS:
vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages\s+([^:]+)[^\d]+(\d+)/ and printf("%-16s % 16.2f Mi\n", "$1:", $2 * $size / 1048576);'

# Cerrar aplicaciones pesadas antes de iniciar
# - Chrome/Firefox (usar Safari si es necesario)
# - Docker Desktop
# - IDEs (VSCode, IntelliJ)
# - Aplicaciones de virtualización
```

### 3. Datasets Corregidos
```bash
# Verificar datasets existen y tienen formato correcto
ls -lh artifacts/synthetic/ba_train_v2_fixed.jsonl
ls -lh artifacts/synthetic/ba_val_v2_fixed.jsonl

# Verificar cantidad de ejemplos
wc -l artifacts/synthetic/ba_train_v2_fixed.jsonl  # Debe ser 98
wc -l artifacts/synthetic/ba_val_v2_fixed.jsonl    # Debe ser 22

# Validar formato JSONL (una línea = error)
head -n 1 artifacts/synthetic/ba_train_v2_fixed.jsonl | python3 -m json.tool > /dev/null && echo "✅ JSON válido" || echo "❌ JSON inválido"
```

### 4. Dependencias Instaladas
```bash
# Verificar librerías Python
.venv/bin/python -c "
import transformers
import peft
import bitsandbytes
import accelerate
import datasets
import torch
import typer
import yaml
print('✅ Todas las dependencias OK')
print(f'transformers: {transformers.__version__}')
print(f'peft: {peft.__version__}')
print(f'torch: {torch.__version__}')
"

# Versiones esperadas:
# - transformers: 4.48.3
# - peft: 0.17.1
# - bitsandbytes: 0.42.0 (CPU-only, warning esperado)
# - accelerate: 0.34.2
# - datasets: 3.6.0
# - torch: 2.9.0
```

### 5. Modelo Base Descargado
```bash
# Verificar si modelo existe localmente
ls -lh artifacts/models/mistral-7b-instruct/

# Si NO existe, descargarlo ANTES de ejecutar fine-tuning:
# (Requiere huggingface-cli instalado y conexión a internet)
huggingface-cli download mistralai/Mistral-7B-Instruct-v0.1 \
  --local-dir artifacts/models/mistral-7b-instruct \
  --local-dir-use-symlinks False

# Verificar tamaño (~13GB)
du -sh artifacts/models/mistral-7b-instruct
```

### 6. Script Fine-Tuning Existe
```bash
# Verificar script
ls -lh scripts/finetune_ba.py

# Probar CLI help (sin ejecutar training)
.venv/bin/python scripts/finetune_ba.py --help
```

---

## 🚀 EJECUCIÓN PASO A PASO

### PASO 1: Preparar Entorno de Ejecución

**1.1. Crear directorio de output**
```bash
mkdir -p artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16
```

**1.2. Crear archivo de log de ejecución**
```bash
# Preparar archivo de monitoreo
touch /tmp/finetune_ba_cpu_bf16.log
```

**1.3. Configurar variables de entorno (opcional)**
```bash
# Deshabilitar TensorBoard si da problemas
export WANDB_DISABLED=true
export TOKENIZERS_PARALLELISM=false
```

---

### PASO 2: Comando de Fine-Tuning

**Comando COMPLETO para ejecutar**:

```bash
cd /Users/matiasleandrokruk/Documents/agnostic-ai-pipeline

nohup .venv/bin/python scripts/finetune_ba.py \
  --train artifacts/synthetic/ba_train_v2_fixed.jsonl \
  --val artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16 \
  --base-model artifacts/models/mistral-7b-instruct \
  --epochs 3 \
  --lr 2e-4 \
  --batch-size 1 \
  --grad-accum 8 \
  --lora-r 8 \
  --lora-alpha 32 \
  --lora-dropout 0.1 \
  --max-length 2048 \
  --seed 42 \
  --quantization bf16 \
  > /tmp/finetune_ba_cpu_bf16.log 2>&1 &

# Guardar PID del proceso
echo $! > /tmp/finetune_ba_pid.txt

echo "✅ Fine-tuning iniciado en background"
echo "📄 Logs: /tmp/finetune_ba_cpu_bf16.log"
echo "🔢 PID: $(cat /tmp/finetune_ba_pid.txt)"
```

**Nota**: `nohup` + `&` permite que el proceso continúe aunque cierres la terminal.

---

### PASO 3: Monitoreo Durante Ejecución

#### 3.1. Ver Logs en Tiempo Real
```bash
# Ver últimas 100 líneas actualizadas cada 5 segundos
tail -f -n 100 /tmp/finetune_ba_cpu_bf16.log
```

#### 3.2. Verificar Proceso Activo
```bash
# Ver si el proceso sigue corriendo
ps aux | grep finetune_ba.py

# O usando el PID guardado
ps -p $(cat /tmp/finetune_ba_pid.txt)
```

#### 3.3. Monitorear Uso de RAM
```bash
# Cada 30 segundos, ver RAM usada por el proceso
watch -n 30 "ps aux | grep finetune_ba.py | grep -v grep | awk '{print \$4, \$11}'"
```

#### 3.4. Checkpoints Guardados
```bash
# Ver checkpoints generados (uno por época)
ls -lh artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/checkpoint-*

# Ver contenido de checkpoints
ls artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/checkpoint-*/
```

#### 3.5. Timeline Esperado

**Hitos clave a monitorear** (basado en logs):

| Tiempo (aprox) | Hito | Log esperado |
|----------------|------|--------------|
| T+0:00 | Inicio | `FASE 8.4: Fine-Tuning LoRA - Mistral-7B-Instruct` |
| T+0:05 | Tokenizer cargado | `Loading tokenizer from ...` |
| T+0:10 | Modelo cargado | `Loading model ... with 4-bit quantization` (fallback bf16) |
| T+0:11 | LoRA aplicado | `Applying LoRA configuration (r=8, alpha=32)...` |
| T+0:12 | Datasets tokenizados | `Tokenizing datasets...` |
| T+0:15 | Training inicia | `Starting training...` |
| T+24:30 | Época 1/3 completa | `Epoch 1/3: 100%` (98 steps × 15 min = 1,470 min = 24.5h) |
| T+24:33 | Evaluación Época 1 | `Evaluating: 100%` (22 examples) |
| T+49:03 | Época 2/3 completa | `Epoch 2/3: 100%` |
| T+49:06 | Evaluación Época 2 | `Evaluating: 100%` |
| T+73:33 | Época 3/3 completa | `Epoch 3/3: 100%` |
| T+73:36 | Evaluación Época 3 | `Evaluating: 100%` |
| T+73:37 | Guardado adapters | `Saving LoRA adapters to ...` |
| T+73:38 | COMPLETADO | `✅ Fine-tuning completed!` |

**Total estimado**: **~73.5 horas (3 días, 1.5 horas)**

---

## 🔧 MANEJO DE INTERRUPCIONES

### Si el Proceso se Interrumpe

#### 1. Verificar Estado
```bash
# Ver si el proceso sigue activo
ps -p $(cat /tmp/finetune_ba_pid.txt) && echo "✅ Proceso activo" || echo "❌ Proceso detenido"

# Ver últimos logs
tail -n 50 /tmp/finetune_ba_cpu_bf16.log
```

#### 2. Identificar Última Época Completada
```bash
# Ver checkpoints guardados
ls -lhrt artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/checkpoint-*/

# Ejemplo:
# checkpoint-98/   → Época 1 completa
# checkpoint-196/  → Época 2 completa
```

#### 3. Reiniciar desde Checkpoint (SI es posible)

**Opción A: HuggingFace Trainer resume automático**
```bash
# El Trainer detecta checkpoints y puede resumir
# Re-ejecutar el mismo comando original
# NOTA: Esto funciona si la interrupción fue limpia (ej. SIGTERM)

nohup .venv/bin/python scripts/finetune_ba.py \
  --train artifacts/synthetic/ba_train_v2_fixed.jsonl \
  --val artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16 \
  --base-model artifacts/models/mistral-7b-instruct \
  --epochs 3 \
  --lr 2e-4 \
  --batch-size 1 \
  --grad-accum 8 \
  --lora-r 8 \
  --lora-alpha 32 \
  --lora-dropout 0.1 \
  --max-length 2048 \
  --seed 42 \
  --quantization bf16 \
  > /tmp/finetune_ba_cpu_bf16_resume.log 2>&1 &
```

**Opción B: Usar checkpoint como modelo base (SI solo falta 1 época)**
```bash
# Si checkpoint-196 existe (2 épocas completadas), entrenar 1 época más
# NOTA: Esto requiere modificar el script para soportar `--resume-from-checkpoint`
# Por ahora, reiniciar desde el principio es más seguro
```

#### 4. Si Reinicio Completo es Necesario
```bash
# Limpiar output directory
rm -rf artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/*

# Re-ejecutar comando original
# (ver PASO 2)
```

---

## 📊 POST-EJECUCIÓN: VERIFICACIÓN

### 1. Verificar Finalización Exitosa
```bash
# Buscar mensaje de éxito en logs
grep "Fine-tuning completed" /tmp/finetune_ba_cpu_bf16.log

# Ver últimas líneas del log
tail -n 100 /tmp/finetune_ba_cpu_bf16.log
```

### 2. Verificar Artefactos Generados
```bash
# Estructura esperada:
ls -lhR artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/

# Archivos críticos:
# ├── adapter_config.json          # Configuración LoRA
# ├── adapter_model.bin             # Weights LoRA (~50MB)
# ├── tokenizer_config.json         # Tokenizer config
# ├── tokenizer.json                # Tokenizer
# ├── special_tokens_map.json       # Special tokens
# ├── training_info.json            # Metadatos
# └── logs/                         # TensorBoard logs

# Verificar tamaño de adapter_model.bin (~50-80MB esperado)
ls -lh artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/adapter_model.bin
```

### 3. Revisar Metadatos de Training
```bash
# Ver training_info.json
cat artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/training_info.json | python3 -m json.tool

# Campos clave a verificar:
# - "epochs": 3
# - "train_examples": 98
# - "val_examples": 22
# - "trainable_params": ~4M (0.05% del total)
```

---

## 📈 SIGUIENTE FASE: EVALUACIÓN

Una vez completado el fine-tuning exitosamente:

### Fase 8.5: Evaluación 3-Way Comparison

**Objetivo**: Comparar 3 modelos:
1. **M1 Baseline**: mistral:7b-instruct (sin optimización) - 72%
2. **M2 Optimized**: mistral:7b-instruct + MIPROv2 - **85.35%**
3. **M3 Fine-Tuned**: mistral:7b-instruct + LoRA - **TBD**

**Script a ejecutar**:
```bash
# Ver protocolo completo en:
cat docs/fase8_evaluation_strategy.md

# Comando de evaluación (a implementar):
.venv/bin/python scripts/compare_ba_models.py \
  --baseline "ollama:mistral:7b-instruct" \
  --optimized "artifacts/dspy/local_base_optimized" \
  --finetuned "artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16" \
  --dataset artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/fase8/3way_comparison.json
```

**Criterios de Decisión**:
- ✅ **Si M3 ≥ 90% Y mejora +5% sobre M2** → Adoptar fine-tuned
- ⚠️ **Si M3 mejora <5%** → Mantener M2 (simplicidad)
- ❌ **Si M3 < M2** → Mantener M2 (overfitting detectado)

---

## 🗂️ ARCHIVOS DE REFERENCIA

| Documento | Ubicación | Contenido |
|-----------|-----------|-----------|
| **Plan Fine-Tuning** | `docs/fase8_finetuning_plan.md` | Config LoRA, hyperparámetros, timeline |
| **Estrategia Evaluación** | `docs/fase8_evaluation_strategy.md` | Protocolo 3-way, métricas |
| **Progreso Fase 8** | `docs/fase8_progress.md` | Historial completo tareas |
| **Continuidad** | `docs/fase8_cpu_finetuning_continuity.md` | Este documento |
| **Script Fine-Tuning** | `scripts/finetune_ba.py` | Implementación LoRA |

---

## ⚡ COMANDOS RÁPIDOS DE REFERENCIA

```bash
# ===== INICIO =====
# 1. Verificar prerequisites
.venv/bin/python -c "import transformers, peft; print('OK')"
ls -lh artifacts/synthetic/ba_*_v2_fixed.jsonl
ls -lh artifacts/models/mistral-7b-instruct/

# 2. Iniciar fine-tuning en background
cd /Users/matiasleandrokruk/Documents/agnostic-ai-pipeline
nohup .venv/bin/python scripts/finetune_ba.py \
  --train artifacts/synthetic/ba_train_v2_fixed.jsonl \
  --val artifacts/synthetic/ba_val_v2_fixed.jsonl \
  --output artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16 \
  --base-model artifacts/models/mistral-7b-instruct \
  --quantization bf16 \
  > /tmp/finetune_ba_cpu_bf16.log 2>&1 &
echo $! > /tmp/finetune_ba_pid.txt

# ===== MONITOREO =====
# Ver logs en vivo
tail -f /tmp/finetune_ba_cpu_bf16.log

# Ver proceso activo
ps -p $(cat /tmp/finetune_ba_pid.txt)

# Ver checkpoints guardados
ls -lhrt artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/checkpoint-*/

# ===== POST-EJECUCIÓN =====
# Verificar éxito
grep "Fine-tuning completed" /tmp/finetune_ba_cpu_bf16.log

# Ver artefactos
ls -lh artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/

# Ver metadatos
cat artifacts/finetuning/mistral-7b-ba-lora-cpu-bf16/training_info.json
```

---

## 🚨 SOLUCIÓN DE PROBLEMAS

### Problema 1: Out of Memory (OOM)
**Síntoma**: Proceso termina con `Killed` o `MemoryError`

**Solución**:
1. Verificar RAM disponible: `vm_stat`
2. Cerrar aplicaciones pesadas
3. Reducir `--batch-size` a 1 (ya está en mínimo)
4. Reducir `--max-length` a 1024 (vs 2048)
5. **Última opción**: Usar modelo más pequeño (3B en lugar de 7B)

### Problema 2: Proceso Muy Lento (>20 min/step)
**Síntoma**: Steps demoran >20 min cada uno

**Solución**:
1. Verificar no hay otros procesos pesados: `top`
2. Verificar temperatura CPU: si está throttling, puede afectar
3. **Aceptar**: 15-20 min/step es esperado en CPU
4. **Alternativa**: Considerar cloud GPU (Google Colab, AWS)

### Problema 3: Checkpoints No Se Guardan
**Síntoma**: No aparecen `checkpoint-*/` después de varias horas

**Solución**:
1. Verificar espacio en disco: `df -h`
2. Ver logs por errores de permisos
3. Verificar config: `save_strategy="epoch"` está en el script

### Problema 4: Modelo No Descarga (Sin Red)
**Síntoma**: `socket.gaierror` o `URLError`

**Solución**:
1. Descargar en máquina con red:
   ```bash
   huggingface-cli download mistralai/Mistral-7B-Instruct-v0.1 \
     --local-dir ~/mistral-7b-instruct \
     --local-dir-use-symlinks False
   ```
2. Copiar a repo:
   ```bash
   rsync -avh ~/mistral-7b-instruct/ \
     /Users/matiasleandrokruk/Documents/agnostic-ai-pipeline/artifacts/models/mistral-7b-instruct/
   ```
3. Re-ejecutar con `--base-model artifacts/models/mistral-7b-instruct`

---

## 📞 CONTACTO Y CONTINUACIÓN

Si este proceso se interrumpe y necesitas continuar:

1. **Leer este documento completo** (estimado: 10 min)
2. **Verificar estado actual**: Ver sección "MANEJO DE INTERRUPCIONES"
3. **Revisar logs**: `/tmp/finetune_ba_cpu_bf16.log`
4. **Consultar referencias**: `docs/fase8_finetuning_plan.md`
5. **Reiniciar si es necesario**: Comando en sección "PASO 2"

**Todo está documentado para continuidad sin pérdida de contexto.**

---

**Última Actualización**: 2025-11-09 (antes de iniciar fine-tuning)
**Responsable**: Sistema automatizado Fase 8
**Status**: ⏳ LISTO PARA EJECUTAR
