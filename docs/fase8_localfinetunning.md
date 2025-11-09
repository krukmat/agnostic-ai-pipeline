# Fase 8: Local Fine-Tuning (100% CPU, $0 Cost)

**Objetivo**: Pipeline completo funcionando con modelos locales fine-tuned en CPU, sin costos de modelos comerciales.

**Restricciones Críticas**:
- ✅ 100% CPU-only (sin GPU requerida)
- ✅ $0 costo inicial (sin APIs comerciales)
- ✅ 100% local y gratuito
- ✅ Accesible para cualquier desarrollador con laptop/desktop estándar

---

## Filosofía de Diseño

### Estrategia de Bootstrapping Gradual

En lugar de usar modelos comerciales costosos para generar datasets, usamos un **enfoque iterativo de auto-mejora**:

```
Modelo Base Local (3B)
    ↓
Prompt Engineering + DSPy MIPROv2
    ↓
Genera Dataset Sintético (100 ejemplos)
    ↓
Fine-Tuning CPU (LoRA 4-bit)
    ↓
Modelo Mejorado v1
    ↓
Genera Más Dataset (200 ejemplos)
    ↓
Fine-Tuning v2
    ↓
Modelo Producción Final
```

**Ventaja**: Cada iteración mejora el modelo sin costos externos.

---

## Fase 8.1: Selección y Evaluación de Modelos Base (Semana 1)

### Objetivo
Identificar el mejor modelo base local (3-7B parámetros) que funcione eficientemente en CPU para el rol BA.

### Modelos Candidatos

| Modelo | Tamaño | RAM Req. | Tokens/sec (CPU) | Calidad Esperada |
|--------|--------|----------|------------------|------------------|
| **Qwen2.5:3b-instruct** | 3B | 4GB | ~15-20 | ⭐⭐⭐⭐ |
| **Phi-3-mini** | 3.8B | 4GB | ~12-18 | ⭐⭐⭐⭐ |
| **Gemma-2:2b-instruct** | 2B | 3GB | ~20-25 | ⭐⭐⭐ |
| **Mistral:7b-instruct-v0.3** | 7B | 8GB | ~8-12 | ⭐⭐⭐⭐⭐ |
| **Llama3.2:3b-instruct** | 3B | 4GB | ~15-20 | ⭐⭐⭐⭐ |

**Recomendación Inicial**: **Qwen2.5:3b-instruct**
- Mejor balance rendimiento/velocidad
- Excelente en tareas estructuradas (YAML, JSON)
- Soporta contextos largos (32K tokens)
- Muy bien optimizado para CPU

### Tareas

#### 1.1. Instalar Modelos Candidatos
```bash
# Descargar todos los modelos candidatos
ollama pull qwen2.5:3b-instruct
ollama pull phi3:3.8b
ollama pull gemma2:2b-instruct
ollama pull mistral:7b-instruct-v0.3
ollama pull llama3.2:3b-instruct
```

**Comando Make**:
```bash
make ollama-install-candidates
```

**Tiempo estimado**: 30-60 minutos (descarga de ~15GB total)

#### 1.2. Crear Benchmark de Evaluación Baseline
```bash
# Script: scripts/benchmark_local_models.py

# Evaluar cada modelo en dataset BA existente (25 ejemplos)
PYTHONPATH=. .venv/bin/python scripts/benchmark_local_models.py \
  --models qwen2.5:3b-instruct phi3:3.8b gemma2:2b-instruct \
  --dataset dspy_baseline/data/production/ba_train.jsonl \
  --metric dspy_baseline.metrics:ba_requirements_metric \
  --output artifacts/benchmarks/local_models_baseline.json
```

**Métricas a Medir**:
- Calidad (ba_requirements_metric): 0.0-1.0
- Velocidad (tokens/segundo)
- Uso de RAM
- YAML validity rate
- Completeness rate

**Output Esperado**:
```json
{
  "qwen2.5:3b-instruct": {
    "avg_score": 0.72,
    "tokens_per_sec": 18.5,
    "ram_usage_mb": 4200,
    "yaml_valid_rate": 0.88
  },
  "phi3:3.8b": {
    "avg_score": 0.68,
    "tokens_per_sec": 15.2,
    "ram_usage_mb": 4800,
    "yaml_valid_rate": 0.82
  }
}
```

#### 1.3. Seleccionar Modelo Ganador
**Criterios de Decisión**:
1. Score > 0.65 (mínimo viable)
2. YAML validity > 80%
3. Tokens/sec > 10 (usabilidad)
4. RAM < 8GB (accesibilidad)

**Decisión**: Elegir el modelo con mejor `avg_score` que cumpla restricciones.

**Deliverables**:
- [ ] Benchmark completo en `artifacts/benchmarks/local_models_baseline.json`
- [ ] Reporte comparativo en `docs/fase8_model_selection.md`
- [ ] Variable de entorno `LOCAL_BASE_MODEL` configurada

**Tiempo estimado**: 2-3 días

---

## Fase 8.2: Dataset Bootstrapping con Prompt Engineering (Semana 1-2)
**Estado al 2025-11-08**:
- ✔ Conceptos sintéticos (210) generados sin LLM (`artifacts/fase8/business_concepts.jsonl`).
- ✔ Dataset RAW (210 ejemplos) y filtrado (120 ejemplos) en `artifacts/synthetic/`.
- ✔ Split train/val listo (`ba_train_v1.jsonl`, `ba_val_v1.jsonl`).
- ⚠ Optimización MIPROv2 pendiente de correr en host con mistral:7b-instruct + `scripts/tune_dspy.py`.


### Objetivo
Generar dataset sintético de 100-200 ejemplos usando el modelo base local + MIPROv2 optimization.

### Estrategia: Synthetic Data Generation

En lugar de ejemplos humanos costosos, generamos ejemplos sintéticos de alta calidad:

1. **Seed Examples**: Usar los 25 ejemplos actuales como base
2. **Concept Expansion**: LLM local genera variaciones de conceptos de negocio
3. **Self-Evaluation**: Filtramos ejemplos con `ba_requirements_metric > 0.7`
4. **Diversity Injection**: Asegurar variedad de dominios (fintech, healthcare, e-commerce, etc.)

### Tareas

#### 2.1. Optimizar Modelo Base con MIPROv2
```bash
# Ejecutar MIPROv2 en modelo local para encontrar mejores prompts
PYTHONPATH=. .venv/bin/python scripts/tune_dspy.py \
  --role ba \
  --trainset dspy_baseline/data/production/ba_train.jsonl \
  --metric dspy_baseline.metrics:ba_requirements_metric \
  --num-candidates 8 \
  --num-trials 10 \
  --max-bootstrapped-demos 6 \
  --seed 0 \
  --output artifacts/dspy/local_base_optimized \
  --provider ollama \
  --model qwen2.5:3b-instruct
```

**Resultado Esperado**: Instrucciones optimizadas que mejoren el modelo base de ~0.72 → ~0.78-0.80

**Tiempo estimado**: 4-6 horas de ejecución

#### 2.2. Generar Conceptos de Negocio Diversos
```bash
# Script: scripts/generate_business_concepts.py

PYTHONPATH=. .venv/bin/python scripts/generate_business_concepts.py \
  --seed-file dspy_baseline/data/production/ba_train.jsonl \
  --num-concepts 200 \
  --domains fintech,healthcare,ecommerce,education,logistics,hr,marketing \
  --output artifacts/synthetic/business_concepts.jsonl \
  --provider ollama \
  --model qwen2.5:3b-instruct
```

**Estrategia de Generación**:
- Por cada ejemplo seed, generar 3-5 variaciones
- Cambiar dominio (e.g., "blog" → "medical records system")
- Cambiar complejidad (simple → enterprise)
- Cambiar audiencia (startup → corporate)

**Output**: 200 conceptos únicos y diversos

**Tiempo estimado**: 2-3 horas

#### 2.3. Generar Requirements con Programa Optimizado
```bash
# Script: scripts/generate_synthetic_dataset.py

PYTHONPATH=. .venv/bin/python scripts/generate_synthetic_dataset.py \
  --concepts artifacts/synthetic/business_concepts.jsonl \
  --optimized-program artifacts/dspy/local_base_optimized/ba/program.pkl \
  --output artifacts/synthetic/ba_synthetic_raw.jsonl \
  --provider ollama \
  --model qwen2.5:3b-instruct
```

**Proceso**:
1. Cargar programa optimizado de Fase 8.2.1
2. Por cada concepto, generar requirements
3. Aplicar métrica de calidad
4. Guardar ejemplos con scores

**Tiempo estimado**: 4-6 horas (depende de CPU)

#### 2.4. Filtrar y Validar Dataset Sintético
```bash
# Filtrar solo ejemplos de alta calidad
python scripts/filter_synthetic_data.py \
  --input artifacts/synthetic/ba_synthetic_raw.jsonl \
  --min-score 0.70 \
  --output artifacts/synthetic/ba_synthetic_filtered.jsonl \
  --min-examples 100
```

**Criterios de Filtrado**:
- `ba_requirements_metric >= 0.70`
- YAML válido en todos los campos
- Al menos 2 functional requirements
- Al menos 1 non-functional requirement
- Título entre 10-100 caracteres
- Descripción >= 100 caracteres

**Target**: Mínimo 100 ejemplos de alta calidad

**Tiempo estimado**: 30 minutos

#### 2.5. Crear Train/Validation Split
```bash
python scripts/split_dataset.py \
  --input artifacts/synthetic/ba_synthetic_filtered.jsonl \
  --train artifacts/synthetic/ba_train_v1.jsonl \
  --val artifacts/synthetic/ba_val_v1.jsonl \
  --split 0.8
```

**Split**:
- Training: 80% (~80-120 ejemplos)
- Validation: 20% (~20-30 ejemplos)

**Tiempo estimado**: 5 minutos

**Deliverables**:
- [ ] Programa optimizado en `artifacts/dspy/local_base_optimized/`
- [ ] 200 conceptos diversos en `artifacts/synthetic/business_concepts.jsonl`
- [ ] Dataset sintético filtrado (100+ ejemplos alta calidad)
- [ ] Train/val split listos para fine-tuning

**Tiempo total estimado**: 3-4 días

---

## Fase 8.3: Fine-Tuning en CPU con LoRA (Semana 2-3)

### Objetivo
Fine-tune del modelo base local usando el dataset sintético, 100% en CPU con técnicas eficientes.

### Stack Tecnológico

```bash
# Instalar dependencias de fine-tuning
pip install llama-cpp-python transformers peft accelerate bitsandbytes datasets trl
```

**Componentes**:
- **LoRA (Low-Rank Adaptation)**: Fine-tuning eficiente con <1% de parámetros
- **4-bit Quantization**: Reducir memoria de 8GB → 2-3GB
- **llama.cpp**: Inferencia ultra-optimizada para CPU
- **Unsloth** (opcional): Aceleración adicional si es compatible

### Estrategia: LoRA 4-bit Fine-Tuning

**Por qué LoRA?**
- Solo entrena ~0.5-1% de parámetros (vs. 100% full fine-tuning)
- Requiere 4-8x menos RAM
- 2-3x más rápido en CPU
- Resultados comparables a full fine-tuning

**Por qué 4-bit?**
- Reduce memoria de activaciones 4x
- Permite modelos 7B en laptops con 8GB RAM
- Pérdida mínima de calidad (~2-3% vs. fp16)

### Tareas

#### 3.1. Convertir Dataset a Formato HuggingFace
```bash
# Script: scripts/convert_to_hf_format.py

python scripts/convert_to_hf_format.py \
  --train artifacts/synthetic/ba_train_v1.jsonl \
  --val artifacts/synthetic/ba_val_v1.jsonl \
  --output artifacts/synthetic/ba_hf_dataset \
  --format chat
```

**Formato de Salida** (Chat Template):
```json
{
  "messages": [
    {
      "role": "system",
      "content": "As a Business Analyst, generate comprehensive software project specifications..."
    },
    {
      "role": "user",
      "content": "Concept: Smart task management platform for distributed teams"
    },
    {
      "role": "assistant",
      "content": "title: Distributed Team Task Management Platform\n\ndescription: ...\n\nfunctional_requirements:\n- id: FR001\n  description: ...\n  priority: High\n..."
    }
  ]
}
```

**Tiempo estimado**: 15 minutos

#### 3.2. Preparar Modelo Base para Fine-Tuning
```bash
# Script: scripts/prepare_model_for_training.py

python scripts/prepare_model_for_training.py \
  --model-name qwen2.5:3b-instruct \
  --output-dir artifacts/models/qwen25-3b-base \
  --quantization 4bit
```

**Proceso**:
1. Descargar modelo desde Ollama/HuggingFace
2. Aplicar cuantización 4-bit
3. Preparar configuración LoRA
4. Verificar compatibilidad

**Tiempo estimado**: 20-30 minutos

#### 3.3. Configurar LoRA Training
```python
# Config: configs/lora_config.yaml

lora:
  r: 16                    # LoRA rank (higher = more capacity, slower)
  lora_alpha: 32           # Scaling factor
  lora_dropout: 0.05       # Regularization
  target_modules:          # Qué capas fine-tunear
    - q_proj
    - k_proj
    - v_proj
    - o_proj
    - gate_proj
    - up_proj
    - down_proj
  bias: "none"
  task_type: "CAUSAL_LM"

training:
  num_epochs: 3
  batch_size: 1            # CPU constraint
  gradient_accumulation_steps: 8  # Simular batch_size=8
  learning_rate: 2e-4
  warmup_steps: 10
  save_steps: 50
  eval_steps: 25
  logging_steps: 10
  max_seq_length: 2048
  optim: "adamw_8bit"      # Optimizador eficiente en memoria

quantization:
  load_in_4bit: true
  bnb_4bit_compute_dtype: "float16"
  bnb_4bit_quant_type: "nf4"
  bnb_4bit_use_double_quant: true
```

**Memoria Esperada**: ~3-4GB RAM para modelo 3B con LoRA 4-bit

#### 3.4. Ejecutar Fine-Tuning
```bash
# Script: scripts/finetune_lora_cpu.py

PYTHONPATH=. python scripts/finetune_lora_cpu.py \
  --model artifacts/models/qwen25-3b-base \
  --dataset artifacts/synthetic/ba_hf_dataset \
  --config configs/lora_config.yaml \
  --output artifacts/models/qwen25-ba-finetuned \
  --num-epochs 3 \
  --device cpu \
  --logging-dir artifacts/logs/finetune_ba_v1
```

**Proceso de Entrenamiento**:
1. Cargar modelo base 4-bit
2. Aplicar adaptadores LoRA
3. Train loop: 3 epochs × ~100 ejemplos = 300 iteraciones
4. Validación cada 25 steps
5. Guardar checkpoints cada 50 steps
6. Early stopping si validation loss no mejora

**Tiempo estimado**:
- CPU Intel i7/i9: 6-8 horas
- CPU AMD Ryzen 7/9: 5-7 horas
- MacBook M1/M2: 3-4 horas (Metal acceleration)

**Monitoreo**:
```bash
# En otra terminal, monitorear progreso
tail -f artifacts/logs/finetune_ba_v1/training.log

# Ver métricas con TensorBoard
tensorboard --logdir artifacts/logs/finetune_ba_v1
```

**Salida Esperada**:
```
Epoch 1/3 - Step 100/300 - Loss: 1.234 - Val Loss: 1.456
Epoch 2/3 - Step 200/300 - Loss: 0.892 - Val Loss: 1.123
Epoch 3/3 - Step 300/300 - Loss: 0.678 - Val Loss: 0.987

✅ Training complete!
✅ Best checkpoint: step 275 (val_loss: 0.954)
✅ LoRA adapters saved to: artifacts/models/qwen25-ba-finetuned/
```

#### 3.5. Merge LoRA con Modelo Base
```bash
# Fusionar adaptadores LoRA con modelo base
python scripts/merge_lora_adapters.py \
  --base-model artifacts/models/qwen25-3b-base \
  --lora-adapters artifacts/models/qwen25-ba-finetuned \
  --output artifacts/models/qwen25-ba-merged \
  --quantize-output 4bit
```

**Resultado**: Modelo completo listo para exportar a Ollama

**Tiempo estimado**: 15-20 minutos

#### 3.6. Convertir a GGUF para Ollama
```bash
# Convertir modelo HuggingFace → GGUF (formato de llama.cpp)
python scripts/convert_to_gguf.py \
  --input artifacts/models/qwen25-ba-merged \
  --output artifacts/models/qwen25-ba-q4_k_m.gguf \
  --quantization q4_k_m
```

**Cuantizaciones Disponibles**:
- `q4_0`: Más rápido, menos calidad
- `q4_k_m`: Balance óptimo (recomendado)
- `q5_k_m`: Mejor calidad, más lento
- `q8_0`: Máxima calidad, más memoria

**Tiempo estimado**: 10 minutos

#### 3.7. Importar a Ollama
```bash
# Crear Modelfile
cat > artifacts/models/Modelfile <<EOF
FROM artifacts/models/qwen25-ba-q4_k_m.gguf

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
"""

PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
EOF

# Importar a Ollama
ollama create qwen25-ba-finetuned:v1 -f artifacts/models/Modelfile

# Verificar
ollama list | grep qwen25-ba
```

**Output Esperado**:
```
qwen25-ba-finetuned:v1   3.2 GB   4 hours ago
```

**Tiempo estimado**: 5 minutos

**Deliverables**:
- [ ] Modelo fine-tuned con LoRA en `artifacts/models/qwen25-ba-finetuned/`
- [ ] Modelo merged en GGUF format
- [ ] Modelo importado en Ollama como `qwen25-ba-finetuned:v1`
- [ ] Logs de entrenamiento en TensorBoard
- [ ] Script de conversión reutilizable

**Tiempo total estimado**: 8-12 horas (mayoría es training time, hands-off)

---

## Fase 8.4: Evaluación y Validación del Modelo Fine-Tuned (Semana 3)

### Objetivo
Comparar el modelo fine-tuned contra el baseline para validar mejora de calidad.

### Tareas

#### 4.1. Benchmark Modelo Fine-Tuned vs. Base
```bash
# Evaluar ambos modelos en validation set
python scripts/compare_models.py \
  --model-base ollama:qwen2.5:3b-instruct \
  --model-finetuned ollama:qwen25-ba-finetuned:v1 \
  --dataset artifacts/synthetic/ba_val_v1.jsonl \
  --metric dspy_baseline.metrics:ba_requirements_metric \
  --output artifacts/benchmarks/finetuned_vs_base.json
```

**Métricas Comparativas**:
- Overall score (ba_requirements_metric)
- YAML validity rate
- Field completeness
- ID format compliance
- Requirement quantity
- Inference speed

**Resultado Esperado**:
```json
{
  "qwen2.5:3b-instruct": {
    "avg_score": 0.72,
    "yaml_valid": 0.88,
    "tokens_per_sec": 18.5
  },
  "qwen25-ba-finetuned:v1": {
    "avg_score": 0.85,     // +18% improvement 🎯
    "yaml_valid": 0.96,     // +9% improvement
    "tokens_per_sec": 17.8  // Similar speed
  }
}
```

**Criterio de Éxito**: Mejora de al menos **10%** en avg_score

**Tiempo estimado**: 1-2 horas

#### 4.2. Validación Cualitativa (Human-in-the-Loop)
```bash
# Generar ejemplos lado-a-lado para revisión manual
python scripts/generate_comparison_samples.py \
  --concepts artifacts/synthetic/business_concepts.jsonl \
  --model-base ollama:qwen2.5:3b-instruct \
  --model-finetuned ollama:qwen25-ba-finetuned:v1 \
  --num-samples 10 \
  --output artifacts/validation/side_by_side_comparison.html
```

**Proceso**:
1. Generar 10 requirements con ambos modelos
2. Presentar lado-a-lado en HTML interactivo
3. Revisión manual de calidad
4. Identificar áreas de mejora

**Tiempo estimado**: 30 minutos

#### 4.3. Evaluar en Dataset Original (Generalización)
```bash
# Probar en los 25 ejemplos originales humanos
python scripts/evaluate_on_original.py \
  --model ollama:qwen25-ba-finetuned:v1 \
  --dataset dspy_baseline/data/production/ba_train.jsonl \
  --metric dspy_baseline.metrics:ba_requirements_metric \
  --output artifacts/benchmarks/generalization_test.json
```

**Propósito**: Verificar que el modelo no se sobreajustó al dataset sintético y generaliza a ejemplos humanos.

**Criterio de Éxito**: Score >= 0.80 en ejemplos originales

**Tiempo estimado**: 30 minutos

#### 4.4. Stress Test: Conceptos Complejos
```bash
# Probar con conceptos muy complejos o ambiguos
python scripts/stress_test_model.py \
  --model ollama:qwen25-ba-finetuned:v1 \
  --test-cases configs/stress_test_cases.yaml \
  --output artifacts/validation/stress_test_results.json
```

**Test Cases**:
- Conceptos multi-dominio
- Requisitos con dependencias complejas
- Conceptos ambiguos o vagos
- Proyectos enterprise de gran escala

**Tiempo estimado**: 1 hora

**Deliverables**:
- [ ] Benchmark comparativo en `artifacts/benchmarks/finetuned_vs_base.json`
- [ ] Reporte de validación cualitativa
- [ ] Test de generalización pasado (score >= 0.80)
- [ ] Stress test completado
- [ ] Decisión Go/No-Go para deploy a producción

**Tiempo total estimado**: 1 día

---

## Fase 8.5: Integración al Pipeline (Semana 3-4)

### Objetivo
Actualizar configuración del pipeline para usar el modelo fine-tuned local como default para el rol BA.

### Tareas

#### 5.1. Actualizar config.yaml
```yaml
# config.yaml

roles:
  ba:
    provider: ollama
    model: qwen25-ba-finetuned:v1  # ← Modelo fine-tuned local
    temperature: 0.7
    max_tokens: 2048
    timeout: 120
```

**Tiempo estimado**: 2 minutos

#### 5.2. Crear Wrapper DSPy para Modelo Fine-Tuned
```python
# dspy_baseline/modules/ba_requirements.py

class BARequirementsModule(dspy.Module):
    """BA module using fine-tuned local model."""

    def __init__(self, use_finetuned: bool = True):
        super().__init__()

        if use_finetuned:
            # Modelo fine-tuned no necesita instrucciones largas
            # El fine-tuning ya internalizó el comportamiento
            self.generate = dspy.Predict(BARequirementsSignatureSimple)
        else:
            # Modelo base necesita instrucciones detalladas
            self.generate = dspy.Predict(BARequirementsSignature)

    def forward(self, concept: str):
        prediction = self.generate(concept=concept)
        return prediction
```

**Ventaja**: Modelo fine-tuned requiere prompts más cortos = más rápido

**Tiempo estimado**: 30 minutos

#### 5.3. Test End-to-End del Pipeline
```bash
# Probar pipeline completo con modelo fine-tuned
make ba CONCEPT="Modern telemedicine platform for rural areas"

# Verificar que genera requirements.yaml válido
cat planning/requirements.yaml
```

**Validación**:
- requirements.yaml se genera correctamente
- Todos los campos presentes (title, description, functional_requirements, etc.)
- YAML es válido
- IDs tienen formato correcto (FR001, NFR001, C001)
- Calidad es comparable o superior a modelo comercial

**Tiempo estimado**: 15 minutos

#### 5.4. Actualizar Documentación
```bash
# Actualizar README.md con instrucciones de modelo local
# Actualizar CLAUDE.md con nueva configuración
```

**Secciones a Agregar**:
- Cómo instalar el modelo fine-tuned
- Diferencias vs. modelos comerciales
- Cómo re-entrenar con nuevos datos
- Troubleshooting común

**Tiempo estimado**: 1 hora

#### 5.5. Crear Script de Re-Entrenamiento
```bash
# Script: scripts/retrain_ba_model.sh

#!/bin/bash
# Re-entrena el modelo BA con dataset actualizado

# 1. Generar nuevo dataset sintético (si es necesario)
python scripts/generate_synthetic_dataset.py \
  --concepts artifacts/synthetic/business_concepts_v2.jsonl \
  --output artifacts/synthetic/ba_train_v2.jsonl

# 2. Fine-tune
python scripts/finetune_lora_cpu.py \
  --model artifacts/models/qwen25-3b-base \
  --dataset artifacts/synthetic/ba_train_v2.jsonl \
  --output artifacts/models/qwen25-ba-finetuned-v2

# 3. Convertir y deploy
python scripts/merge_lora_adapters.py --base-model ... --output ...
python scripts/convert_to_gguf.py ...
ollama create qwen25-ba-finetuned:v2 -f Modelfile

echo "✅ Modelo v2 listo: qwen25-ba-finetuned:v2"
```

**Uso Futuro**: Cuando se acumulen nuevos ejemplos, re-entrenar fácilmente.

**Tiempo estimado**: 30 minutos

**Deliverables**:
- [ ] config.yaml actualizado con modelo fine-tuned
- [ ] Módulo DSPy ajustado para fine-tuned model
- [ ] Pipeline end-to-end testeado exitosamente
- [ ] Documentación actualizada
- [ ] Script de re-entrenamiento listo
- [ ] ✅ Pipeline 100% local funcionando

**Tiempo total estimado**: 1 día

---

## Fase 8.6: Optimización y Escalado (Semana 4+)

### Objetivo
Aplicar la misma estrategia a otros roles (Architect, Dev, QA) para tener pipeline 100% local.

### Tareas

#### 6.1. Replicar Proceso para Rol Architect
```bash
# 1. Generar dataset sintético
python scripts/generate_synthetic_dataset.py \
  --role architect \
  --concepts artifacts/synthetic/architecture_concepts.jsonl \
  --output artifacts/synthetic/architect_train_v1.jsonl

# 2. Fine-tune
python scripts/finetune_lora_cpu.py \
  --model artifacts/models/qwen25-3b-base \
  --dataset artifacts/synthetic/architect_train_v1.jsonl \
  --output artifacts/models/qwen25-architect-finetuned

# 3. Deploy
ollama create qwen25-architect-finetuned:v1 -f Modelfile
```

**Desafío**: Architect es más complejo (genera stories, epics, architecture)
**Solución**: Usar modelo 7B (Mistral) en lugar de 3B

**Tiempo estimado**: 2-3 días (similar a BA)

#### 6.2. Replicar para Developer
```bash
# Developer requiere modelo más grande (código completo)
# Usar Qwen2.5-Coder:7B o CodeLlama:13B

python scripts/finetune_lora_cpu.py \
  --model qwen2.5-coder:7b \
  --dataset artifacts/synthetic/dev_train_v1.jsonl \
  --output artifacts/models/qwen25-dev-finetuned
```

**Consideración**: Developer puede generar código largo, requiere más RAM

**Tiempo estimado**: 3-4 días

#### 6.3. Replicar para QA
```bash
# QA puede usar modelo más pequeño (análisis de tests)
python scripts/finetune_lora_cpu.py \
  --model qwen2.5:3b \
  --dataset artifacts/synthetic/qa_train_v1.jsonl \
  --output artifacts/models/qwen25-qa-finetuned
```

**Tiempo estimado**: 2 días

#### 6.4. Configuración Final Multi-Modelo
```yaml
# config.yaml - Pipeline 100% Local

roles:
  ba:
    provider: ollama
    model: qwen25-ba-finetuned:v1

  architect:
    provider: ollama
    model: qwen25-architect-finetuned:v1

  dev:
    provider: ollama
    model: qwen25-coder-dev-finetuned:v1

  qa:
    provider: ollama
    model: qwen25-qa-finetuned:v1
```

**Tiempo estimado**: 5 minutos

**Deliverables**:
- [ ] 4 modelos fine-tuned (BA, Architect, Dev, QA)
- [ ] Pipeline completo 100% local
- [ ] $0 costo operacional
- [ ] Documentación completa de re-entrenamiento

**Tiempo total estimado**: 2-3 semanas

---

## Fase 8.7: Iteración Continua (Ongoing)

### Objetivo
Mejorar continuamente los modelos con feedback real de usuarios.

### Estrategia: Feedback Loop

```
Usuario ejecuta pipeline
    ↓
Genera código/artifacts
    ↓
Usuario califica calidad (1-5 estrellas)
    ↓
Ejemplos de alta calidad (5 estrellas) → Training dataset
    ↓
Re-entrenamiento mensual con nuevos datos
    ↓
Deploy modelo v2, v3, v4...
```

### Tareas

#### 7.1. Implementar Sistema de Calificación
```python
# scripts/rate_output.py

# Después de cada ejecución, preguntar:
print("¿Cómo calificarías la calidad del output? (1-5)")
rating = int(input("> "))

if rating >= 4:
    # Guardar ejemplo para futuro entrenamiento
    save_to_training_pool(concept, output, rating)
```

**Tiempo estimado**: 1 hora de desarrollo

#### 7.2. Script de Re-Entrenamiento Mensual
```bash
# Cron job mensual
0 0 1 * * /path/to/scripts/monthly_retrain.sh
```

**Proceso**:
1. Recopilar ejemplos con rating >= 4 del mes anterior
2. Merge con dataset existente
3. Re-entrenar modelos
4. Benchmark vs. versión anterior
5. Deploy si hay mejora >= 5%

**Tiempo estimado**: Setup 2 horas, luego automático

**Deliverables**:
- [ ] Sistema de calificación implementado
- [ ] Cron job de re-entrenamiento mensual
- [ ] Dashboard de métricas de calidad
- [ ] Proceso de continuous improvement establecido

**Tiempo total estimado**: 1 semana setup + ongoing

---

## Resumen de Costos y Recursos

### Hardware Mínimo Requerido

| Componente | Mínimo | Recomendado | Óptimo |
|------------|--------|-------------|--------|
| **CPU** | 4 cores | 8 cores | 16+ cores |
| **RAM** | 8GB | 16GB | 32GB |
| **Storage** | 50GB | 100GB | 200GB |
| **OS** | Linux/macOS/Windows | Linux | Linux |

**Nota**: MacBook M1/M2/M3 son excelentes (Metal acceleration)

### Costos Totales

| Categoría | Costo |
|-----------|-------|
| **Software/Licencias** | **$0** (todo open-source) |
| **Modelos Comerciales** | **$0** (solo local) |
| **Cloud Compute** | **$0** (local CPU) |
| **Total Setup** | **$0** |
| **Costo Operacional Mensual** | **$0** |

**Electricidad**: ~$5-10/mes (si fine-tuning frecuente)

### Tiempo Total Estimado

| Fase | Tiempo | Hands-On |
|------|--------|----------|
| 8.1. Selección Modelo | 2-3 días | 4 horas |
| 8.2. Dataset Bootstrapping | 3-4 días | 6 horas |
| 8.3. Fine-Tuning | 1 día | 2 horas |
| 8.4. Evaluación | 1 día | 4 horas |
| 8.5. Integración | 1 día | 4 horas |
| 8.6. Escalado (otros roles) | 2-3 semanas | 16 horas |
| 8.7. Iteración Continua | Setup 1 semana | 8 horas |
| **TOTAL** | **4-5 semanas** | **44 horas** |

**Tiempo Real**: ~1 mes de calendario, ~1 semana de trabajo efectivo

---

## Métricas de Éxito

### KPIs Fase 8

| Métrica | Target | Crítico |
|---------|--------|---------|
| **Calidad vs. Baseline** | +15% | Sí |
| **Velocidad Inference** | >10 tok/s | Sí |
| **Costo Operacional** | $0 | Sí |
| **RAM Usage** | <8GB | Sí |
| **YAML Validity** | >90% | Sí |
| **User Satisfaction** | >4/5 stars | No |
| **Pipeline Success Rate** | >80% | Sí |

### Validación Go/No-Go

**Criterios para Considerar Éxito**:
- ✅ Modelo fine-tuned mejora >=10% vs. base
- ✅ Pipeline completo funciona 100% local
- ✅ Costos $0 (no APIs comerciales)
- ✅ Documentación completa para replicación
- ✅ Proceso de mejora continua establecido

**Si algún criterio falla**: Iterar en esa fase específica.

---

## Riesgos y Mitigaciones

### Riesgo 1: Modelo Base Local Tiene Calidad Muy Baja (<0.65)
**Probabilidad**: Media
**Impacto**: Alto
**Mitigación**:
- Probar múltiples modelos base (Qwen, Phi, Mistral, Llama)
- Usar modelo 7B en lugar de 3B (más lento pero mejor calidad)
- Invertir más en prompt engineering antes de fine-tuning

### Riesgo 2: Fine-Tuning en CPU es Demasiado Lento (>24h)
**Probabilidad**: Media
**Impacto**: Medio
**Mitigación**:
- Reducir dataset a 50-80 ejemplos (en lugar de 100)
- Usar LoRA rank más bajo (r=8 en lugar de r=16)
- Reducir epochs (2 en lugar de 3)
- Considerar usar cloud CPU temporal (Google Colab CPU gratis)

### Riesgo 3: Dataset Sintético Tiene Baja Diversidad
**Probabilidad**: Media
**Impacto**: Medio
**Mitigación**:
- Generar 2-3x más ejemplos y filtrar agresivamente
- Inyectar diversidad manual en seed concepts
- Usar multiple prompts para generación (variabilidad)

### Riesgo 4: Modelo Fine-Tuned Se Sobre-Ajusta (Overfitting)
**Probabilidad**: Baja
**Impacto**: Alto
**Mitigación**:
- Monitorear validation loss durante training
- Early stopping si val_loss aumenta
- Aumentar LoRA dropout (0.05 → 0.1)
- Reducir learning rate

### Riesgo 5: GGUF Conversion Falla o Corrompe Modelo
**Probabilidad**: Baja
**Impacto**: Alto
**Mitigación**:
- Testear conversión con modelo pequeño primero
- Mantener múltiples formatos (HF, GGUF)
- Validar modelo después de cada conversión

---

## Próximos Pasos Inmediatos

### Semana 1: Quick Start

1. **Lunes**:
   ```bash
   # Instalar modelos candidatos
   make ollama-install-candidates

   # Benchmark inicial
   python scripts/benchmark_local_models.py
   ```

2. **Martes-Miércoles**:
   ```bash
   # Optimizar modelo base con MIPROv2
   python scripts/tune_dspy.py --provider ollama --model qwen2.5:3b-instruct
   ```

3. **Jueves-Viernes**:
   ```bash
   # Generar dataset sintético
   python scripts/generate_business_concepts.py
   python scripts/generate_synthetic_dataset.py
   python scripts/filter_synthetic_data.py
   ```

4. **Fin de Semana**:
   ```bash
   # Ejecutar fine-tuning (hands-off, dejar corriendo)
   python scripts/finetune_lora_cpu.py
   ```

### Semana 2: Validación y Deploy

1. **Lunes**:
   ```bash
   # Evaluar modelo fine-tuned
   python scripts/compare_models.py
   ```

2. **Martes**:
   ```bash
   # Integrar al pipeline
   # Actualizar config.yaml
   make ba CONCEPT="Test concept"
   ```

3. **Miércoles-Viernes**:
   - Documentación
   - Testing end-to-end
   - Ajustes finales

---

## Referencias y Recursos

### Papers y Técnicas
- **LoRA**: [Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- **QLoRA**: [4-bit Quantized LoRA](https://arxiv.org/abs/2305.14314)
- **DSPy MIPROv2**: [Multi-prompt Instruction Proposal](https://arxiv.org/abs/2406.11695)

### Herramientas Open-Source
- **Ollama**: https://ollama.ai
- **llama.cpp**: https://github.com/ggerganov/llama.cpp
- **Hugging Face PEFT**: https://github.com/huggingface/peft
- **Unsloth**: https://github.com/unslothai/unsloth

### Modelos Recomendados
- **Qwen2.5**: https://huggingface.co/Qwen
- **Phi-3**: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct
- **Mistral**: https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3

### Community Support
- Ollama Discord
- Hugging Face Forums
- DSPy GitHub Discussions

---

## Conclusión

**Fase 8 permite**:
- ✅ Pipeline 100% local y gratuito
- ✅ $0 costos operacionales
- ✅ Privacidad total (datos nunca salen del servidor)
- ✅ Independencia de proveedores comerciales
- ✅ Democratización del acceso (cualquiera con laptop puede usarlo)
- ✅ Mejora continua con feedback real

**Entregable Final**: Pipeline de desarrollo de software completo (BA → PO → Architect → Dev → QA) funcionando 100% con modelos locales fine-tuned, sin costos, listo para ser usado por startups, estudiantes, y desarrolladores sin presupuesto para APIs comerciales.

---

**Documento**: `docs/fase8_localfinetunning.md`
**Versión**: 1.0
**Fecha**: 2025-11-08
**Estado**: ✅ Plan Completo - Listo para Ejecución
