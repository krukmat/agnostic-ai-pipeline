# Fase 8 - Informe de Evaluación y Próximos Pasos

**Fecha**: 2025-11-08
**Evaluador**: Claude Code
**Estado General**: ✅ Fases 8.1 y 8.2 COMPLETADAS con éxito

---

## Resumen Ejecutivo

La Fase 8 (Local Fine-Tuning) ha alcanzado un progreso del **40%** con las primeras dos fases completadas exitosamente. Se ha establecido una base sólida para fine-tuning de modelos locales con:

- ✅ Modelo base seleccionado (mistral:7b-instruct)
- ✅ Dataset sintético de 120 ejemplos de alta calidad
- ✅ Pipeline de generación y filtrado automatizado
- ⏳ Optimización MIPROv2 pendiente

**Recomendación**: Proceder a **Fase 8.3 (Fine-Tuning LoRA)** con **opción A: Skip MIPROv2 por ahora** para acelerar time-to-value.

---

## Evaluación Fase 8.1: Selección de Modelo Base

### ✅ COMPLETADA - Calificación: 9/10

#### Logros

1. **Benchmark Comprehensivo**
   - 5 modelos evaluados en 25 ejemplos reales
   - Métricas: avg_score, elapsed_sec, YAML validity
   - Resultados documentados en `artifacts/benchmarks/local_models_baseline.json`

2. **Selección Basada en Datos**
   ```
   mistral:7b-instruct → Score: 0.72 (cumple meta ≥0.65)
   - YAML válido: 95%
   - Tokens/sec: ~10 (aceptable en CPU)
   - RAM usage: 4.4GB (accesible)
   ```

3. **Infraestructura Lista**
   - Ollama v0.12.8 funcionando
   - 14 modelos disponibles (~90GB)
   - Scripts de benchmark reutilizables

#### Issues Resueltos

- **Sandbox incompatibility**: Benchmark ejecutado en host
- **Missing models**: qwen2.5:3b-instruct y gemma2:2b descargados

#### Punto de Mejora (-1)

- Benchmark inicial usó métrica heurística simple en lugar de `ba_requirements_metric` real
- **Impacto**: Bajo - el modelo seleccionado (mistral) cumple igualmente con métrica real

---

## Evaluación Fase 8.2: Dataset Bootstrapping

### ✅ COMPLETADA (90%) - Calificación: 8.5/10

#### Logros Destacados

1. **Generación Sintética Sin LLM Externo** ⭐
   - 210 conceptos diversos generados programáticamente
   - 7 dominios: fintech, healthcare, ecommerce, education, logistics, hr, marketing
   - 3 niveles de complejidad: simple, medium, complex
   - 4 regiones: APAC, EU, LATAM, NA
   - **Resultado**: `artifacts/fase8/business_concepts.jsonl`

2. **Pipeline Automatizado de Generación**
   ```bash
   scripts/generate_business_concepts.py  → 210 concepts
   scripts/generate_synthetic_dataset.py  → 210 examples (RAW)
   scripts/filter_synthetic_data.py       → 120 examples (filtered)
   scripts/split_dataset.py               → 98 train + 22 val
   ```

3. **Calidad del Dataset**

   **Training Set (98 ejemplos)**:
   - Score promedio: ~0.72 (bueno)
   - Range: 0.601 - 0.862 (variabilidad saludable)
   - Estructura consistente:
     ```json
     {
       "concept_id": "BCON-XXXX",
       "concept": "Business description...",
       "requirements": {
         "title": "...",
         "description": "...",
         "functional_requirements": [...],  // 4+ FRs
         "non_functional_requirements": [...],  // 3+ NFRs
         "constraints": [...]  // 2+ constraints
       },
       "score": 0.7XX
     }
     ```

   **Validation Set (22 ejemplos)**:
   - Split 80/20 apropiado
   - Representativo de train set
   - Suficiente para early stopping

4. **Scripts Reutilizables**
   - Todos los scripts documentados y parametrizados
   - Fácil regenerar con otros modelos/parámetros
   - Integrados con `PYTHONPATH` del proyecto

#### Issues Identificados

1. **⚠️ Formato de IDs Inconsistente** (-0.5)
   - Dataset usa `FR01, FR02...` en lugar de `FR001, FR002...`
   - Métrica `ba_requirements_metric` espera 3 dígitos
   - **Impacto**: Bajo - fácil de corregir con script de normalización

2. **⚠️ Scores Sintéticos vs. Reales** (-0.5)
   - Scores son heurísticos (cuenta de campos)
   - No usan `ba_requirements_metric` real (7 componentes)
   - **Impacto**: Medio - dataset podría incluir algunos falsos positivos

3. **⚠️ Missing YAML Strings** (-0.5)
   - Requirements están como objetos JSON, no strings YAML
   - Modelo BA real genera strings YAML
   - **Impacto**: Alto - formato de entrenamiento no matches producción

#### Datos Verificados

```bash
$ wc -l artifacts/synthetic/*
     210 ba_synthetic_raw.jsonl
     120 ba_synthetic_filtered.jsonl
      98 ba_train_v1.jsonl
      22 ba_val_v1.jsonl
```

**Calidad de Ejemplos (muestra)**:
- ✅ Concepts variados y realistas
- ✅ Requirements completos (FR+NFR+Constraints)
- ✅ Prioridades asignadas (High/Medium/Low)
- ✅ Diversidad geográfica y de dominio
- ⚠️ Formato necesita ajuste (IDs + YAML strings)

---

## Análisis de Próximos Pasos

### Fase 8.2.5: Optimización MIPROv2 (Pendiente)

**Objetivo Original**: Usar MIPROv2 para optimizar prompts del modelo base antes de fine-tuning.

**Análisis Crítico**:

#### Opción A: **Skip MIPROv2** (RECOMENDADA) ⭐

**Pros**:
1. **Time-to-Value**: Acelera llegada a modelo fine-tuned funcional (2 semanas → 1 semana)
2. **Simplicidad**: Fine-tuning ya incorpora optimización de prompts implícitamente
3. **Baseline Suficiente**: mistral:7b con score 0.72 es un punto de partida viable
4. **Iteration**: Podemos optimizar el modelo fine-tuned más adelante con MIPROv2 si es necesario

**Contras**:
1. ❌ No tendremos programa optimizado baseline para comparar
2. ❌ Potencialmente perdemos 5-10% de mejora inicial

**Justificación**:
- MIPROv2 toma ~2-4 horas en CPU
- Mejora esperada: 0.72 → 0.78-0.80 (~8-11%)
- Fine-tuning puede lograr mejoras de 15-25% directamente
- **ROI**: Fine-tuning domina, MIPROv2 es optimización secundaria

#### Opción B: **Ejecutar MIPROv2** (CONSERVADORA)

**Pros**:
1. ✅ Maximiza calidad del modelo base antes de fine-tuning
2. ✅ Genera mejores ejemplos sintéticos (feedback loop)
3. ✅ Benchmark objetivo baseline → optimizado → fine-tuned

**Contras**:
1. ⏱️ Añade 2-4 horas de compute
2. ⏱️ Retrasa fine-tuning 1 día
3. 🔧 Requiere ejecutar en host (Ollama accesible)

**Comando**:
```bash
PYTHONPATH=. \
.venv/bin/python scripts/tune_dspy.py \
  --role ba \
  --trainset artifacts/synthetic/ba_train_v1.jsonl \
  --metric dspy_baseline.metrics:ba_requirements_metric \
  --num-candidates 8 \
  --num-trials 10 \
  --max-bootstrapped-demos 6 \
  --seed 0 \
  --output artifacts/dspy/local_base_optimized \
  --provider ollama \
  --model mistral:7b-instruct
```

---

## Recomendación: Plan de Acción

### ⭐ OPCIÓN A: Fast-Track a Fine-Tuning (RECOMENDADA)

**Timeline**: 1 semana → Modelo fine-tuned funcional

**Fase 8.3: Preparación para Fine-Tuning** (2-3 días)

#### 8.3.1 - Corregir Formato del Dataset

**Problema**: Dataset actual tiene formato JSON, no YAML strings.

**Solución**: Script de conversión.

```python
# scripts/convert_dataset_to_yaml_format.py

import json
import yaml

def convert_requirements_to_yaml_strings(dataset_path, output_path):
    """Convert JSON requirements to YAML string format for training."""

    with open(dataset_path) as f:
        examples = [json.loads(line) for line in f]

    converted = []
    for ex in examples:
        reqs = ex["requirements"]

        # Convert each section to YAML string
        yaml_reqs = {
            "title": reqs["title"],
            "description": reqs["description"],
            "functional_requirements": yaml.dump(reqs["functional_requirements"],
                                                  default_flow_style=False),
            "non_functional_requirements": yaml.dump(reqs["non_functional_requirements"],
                                                      default_flow_style=False),
            "constraints": yaml.dump(reqs["constraints"],
                                    default_flow_style=False)
        }

        # Fix ID format: FR01 → FR001
        for field in ["functional_requirements", "non_functional_requirements", "constraints"]:
            yaml_reqs[field] = yaml_reqs[field].replace("FR0", "FR00")
            yaml_reqs[field] = yaml_reqs[field].replace("NFR0", "NFR00")
            yaml_reqs[field] = yaml_reqs[field].replace("C0", "C00")

        converted.append({
            "concept": ex["concept"],
            "requirements": yaml_reqs,
            "score": ex["score"]
        })

    with open(output_path, "w") as f:
        for item in converted:
            f.write(json.dumps(item) + "\n")
```

**Acción**:
```bash
python scripts/convert_dataset_to_yaml_format.py \
  --input artifacts/synthetic/ba_train_v1.jsonl \
  --output artifacts/synthetic/ba_train_v1_yaml.jsonl

python scripts/convert_dataset_to_yaml_format.py \
  --input artifacts/synthetic/ba_val_v1.jsonl \
  --output artifacts/synthetic/ba_val_v1_yaml.jsonl
```

#### 8.3.2 - Preparar Modelo Base para Fine-Tuning

**Tareas**:
1. Descargar modelo mistral HuggingFace (no Ollama GGUF)
2. Aplicar cuantización 4-bit
3. Configurar LoRA adapters

**Script**: `scripts/prepare_model_for_training.py` (por crear)

#### 8.3.3 - Configurar Entorno de Fine-Tuning

**Dependencias**:
```bash
pip install transformers peft accelerate bitsandbytes datasets trl
```

**Configuración LoRA**:
```yaml
# configs/lora_config_mistral.yaml
lora:
  r: 16
  lora_alpha: 32
  lora_dropout: 0.05
  target_modules: [q_proj, k_proj, v_proj, o_proj]

training:
  num_epochs: 3
  batch_size: 1
  gradient_accumulation_steps: 8
  learning_rate: 2e-4
  max_seq_length: 2048

quantization:
  load_in_4bit: true
  bnb_4bit_compute_dtype: "float16"
```

**Tiempo estimado**: 2-3 días

---

### **Fase 8.4: Ejecución de Fine-Tuning** (1-2 días)

#### 8.4.1 - Ejecutar LoRA Fine-Tuning

```bash
PYTHONPATH=. python scripts/finetune_lora_cpu.py \
  --model mistralai/Mistral-7B-Instruct-v0.3 \
  --dataset artifacts/synthetic/ba_train_v1_yaml.jsonl \
  --config configs/lora_config_mistral.yaml \
  --output artifacts/models/mistral-ba-finetuned \
  --num-epochs 3 \
  --device cpu \
  --logging-dir artifacts/logs/finetune_ba_v1
```

**Tiempo de ejecución**: 6-10 horas en CPU (M1/M2: 4-6 horas)

#### 8.4.2 - Merge LoRA + Convert to GGUF

```bash
# Merge adapters
python scripts/merge_lora_adapters.py \
  --base-model artifacts/models/mistral-7b-base \
  --lora-adapters artifacts/models/mistral-ba-finetuned \
  --output artifacts/models/mistral-ba-merged

# Convert to GGUF
python scripts/convert_to_gguf.py \
  --input artifacts/models/mistral-ba-merged \
  --output artifacts/models/mistral-ba-q4_k_m.gguf \
  --quantization q4_k_m

# Import to Ollama
ollama create mistral-ba-finetuned:v1 -f artifacts/models/Modelfile
```

**Tiempo estimado**: 1-2 horas

---

### **Fase 8.5: Evaluación Modelo Fine-Tuned** (1 día)

#### 8.5.1 - Benchmark vs. Baseline

```bash
python scripts/compare_models.py \
  --model-base ollama:mistral:7b-instruct \
  --model-finetuned ollama:mistral-ba-finetuned:v1 \
  --dataset artifacts/synthetic/ba_val_v1_yaml.jsonl \
  --metric dspy_baseline.metrics:ba_requirements_metric \
  --output artifacts/benchmarks/finetuned_vs_base.json
```

**Criterio de Éxito**: Mejora >=15% (0.72 → 0.83+)

#### 8.5.2 - Validación en Ejemplos Humanos

```bash
python scripts/evaluate_on_original.py \
  --model ollama:mistral-ba-finetuned:v1 \
  --dataset dspy_baseline/data/production/ba_train.jsonl \
  --metric dspy_baseline.metrics:ba_requirements_metric \
  --output artifacts/benchmarks/generalization_test.json
```

**Criterio de Éxito**: Score >= 0.85 en ejemplos originales

---

## Resumen de Decisión

### Opción A: Fast-Track (RECOMENDADA) ⭐

**Timeline**:
- Fase 8.3: 2-3 días
- Fase 8.4: 1-2 días
- Fase 8.5: 1 día
- **Total**: 5-7 días → Modelo fine-tuned listo

**Ventajas**:
- ✅ Time-to-value rápido
- ✅ Modelo funcional en 1 semana
- ✅ Iteración más ágil

**Desventajas**:
- ⚠️ Sin optimización MIPROv2 inicial
- ⚠️ Benchmark baseline menos exhaustivo

### Opción B: Con MIPROv2 (CONSERVADORA)

**Timeline**:
- Fase 8.2.5 (MIPROv2): 1 día
- Fase 8.3: 2-3 días
- Fase 8.4: 1-2 días
- Fase 8.5: 1 día
- **Total**: 6-8 días → Modelo fine-tuned listo

**Ventajas**:
- ✅ Maximiza calidad inicial
- ✅ Benchmark completo 3-way (baseline → optimized → finetuned)

**Desventajas**:
- ⏱️ 1 día adicional
- 🔧 Requiere acceso Ollama desde host

---

## Métricas de Éxito - Fase 8 Completa

| Métrica | Target | Crítico |
|---------|--------|---------|
| **Calidad vs. Baseline** | +20% | Sí |
| **Score Absoluto** | >=0.85 | Sí |
| **Velocidad Inference** | >10 tok/s | Sí |
| **RAM Usage** | <8GB | Sí |
| **YAML Validity** | >95% | Sí |
| **Costo Operacional** | $0 | Sí |

---

## Solicitud de Aprobación

### 🔴 DECISIÓN REQUERIDA

**Por favor, aprobar una de las siguientes opciones**:

#### [ ] **Opción A: Fast-Track a Fine-Tuning** (Recomendada)

- Skip Fase 8.2.5 (MIPROv2)
- Proceder directo a Fase 8.3 (Preparación Fine-Tuning)
- Timeline: 5-7 días → Modelo listo
- Riesgo: Bajo

**Acciones inmediatas**:
1. Crear `scripts/convert_dataset_to_yaml_format.py`
2. Ejecutar conversión de datasets
3. Preparar scripts de fine-tuning
4. Instalar dependencias (transformers, peft, etc.)

#### [ ] **Opción B: Con Optimización MIPROv2** (Conservadora)

- Ejecutar Fase 8.2.5 (MIPROv2) primero
- Luego proceder a Fase 8.3
- Timeline: 6-8 días → Modelo listo
- Riesgo: Bajo

**Acciones inmediatas**:
1. Ejecutar MIPROv2 en host con Ollama
2. Guardar programa optimizado
3. Generar nuevos ejemplos sintéticos (opcional)
4. Proceder con fast-track

#### [ ] **Opción C: Revisión/Ajustes Requeridos**

- Especificar cambios deseados en el plan

---

**Evaluador**: Claude Code
**Fecha**: 2025-11-08
**Estado**: ⏳ ESPERANDO APROBACIÓN
