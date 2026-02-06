# Adendum al Plan: Lecciones Aprendidas del Fine-Tuning Previo

**Fecha**: 2026-02-03
**Propósito**: Integrar experiencia previa de fine-tuning con BA, PO y Architect al plan de modelos abiertos

---

## Resumen de Fine-Tuning Previo

### Stack Utilizado

| Componente | Tecnología | Estado |
|------------|------------|--------|
| **Modelo Base** | Mistral-7B-Instruct, DeepSeek-Coder-V2-Lite | ✅ Probado |
| **Técnica** | LoRA (rank=32, alpha=64) + DPO/ORPO | ✅ Implementado |
| **Infraestructura** | `post_training/` completa con scripts | ✅ Funcional |
| **Método de Data** | Rollouts (pass@k) → Preferences (chosen/rejected) | ✅ Probado |

### Datos Generados

| Rol | Dataset Original | Dataset Gold/Curado | Estado |
|-----|------------------|---------------------|--------|
| **BA** | 85 ejemplos | N/A | ✅ Suficientes datos |
| **PO** | ? | ? | ✅ Training script existe |
| **Architect** | 32 ejemplos | 8-16 ejemplos (v2) | ⚠️ **FALLÓ** - Dataset reducido |
| **Dev** | Rollouts con pass@k | Preferences DPO | ✅ Infraestructura completa |
| **QA** | 3 ejemplos | N/A | ❌ Datos insuficientes |

---

## Análisis Crítico: ¿Por Qué Falló Architect?

### Evidencia de los Datasets

```bash
# Datasets encontrados:
architect_train.jsonl          # 32 ejemplos originales
architect_train_gold.jsonl     # 8 ejemplos (75% reducción!)
architect_train_gold_v2.jsonl  # 16 ejemplos (50% reducción)
```

### Hipótesis del Fracaso

| Hipótesis | Probabilidad | Evidencia |
|-----------|--------------|-----------|
| **Calidad de datos baja** | 🔴 ALTA | Redujeron 32→8→16 ejemplos, sugiere filtrado agresivo |
| **Architect es rol más complejo** | 🔴 ALTA | Requiere razonamiento arquitectónico, no solo patterns |
| **Modelo base insuficiente** | 🟡 MEDIA | Mistral-7B puede ser pequeño para arquitectura |
| **Formato de prompt inadecuado** | 🟡 MEDIA | Architect necesita chain-of-thought explícito |
| **Pocos datos de training** | 🔴 ALTA | 8-16 ejemplos es CRÍTICO para fine-tuning |

### Lecciones Específicas de Architect

1. **Chain-of-Thought es crítico**: Architect necesita explicar razonamiento
2. **Calidad > Cantidad** (pero cantidad mínima existe): 8 ejemplos es insuficiente, necesitan 100+
3. **Ejemplos deben cubrir patrones variados**: ADR, trade-offs, constraints, NFRs
4. **Validación arquitectónica es compleja**: Difícil automatizar evaluación

---

## Diferencias Clave: Fine-Tuning Previo vs Plan Propuesto

### Lo Que Ya Funcionó (Mantener)

| Aspecto | Enfoque Previo | Plan Propuesto | ✅ Decisión |
|---------|----------------|----------------|-------------|
| **Método de datos** | Rollouts + DPO | Synthetic + SFT + DPO | **COMBINAR ambos** |
| **LoRA** | rank=32, alpha=64 | Similar | **Mantener params** |
| **Infraestructura** | Scripts en `post_training/` | Scripts en `training/` | **Unificar** |
| **Evaluación** | pass@k en held-out | Benchmarks + pass@k | **Combinar** |

### Lo Que Debe Cambiar (Plan Actualizado)

| Aspecto | Enfoque Previo | Problema | Nueva Propuesta |
|---------|----------------|----------|-----------------|
| **Modelo Base** | Mistral-7B, DeepSeek | Comerciales/semi-abiertos | **Qwen2.5 100% abierto** |
| **Datos Architect** | 32→16 ejemplos | Insuficiente | **500+ ejemplos con maestro 72B** |
| **Chain-of-Thought** | Implícito | No funciona para Architect | **Explícito en todos los roles** |
| **Destilación** | No usada | Pérdida de calidad | **Teacher-Student sistemático** |

---

## Plan Actualizado: Integración de Aprendizajes

### Fase 0.5: Aprovechar Infraestructura Existente

```bash
# ANTES de generar datos nuevos, usar lo que ya existe:

1. Migrar `post_training/` a `training/post_training/`
2. Adaptar scripts para Qwen2.5 (compatible con transformers)
3. Re-evaluar datasets existentes con modelo nuevo
```

### Fase 1: Diagnóstico de Datasets Existentes

```yaml
diagnostico:
  ba:
    ejemplos: 85
    acción: "✅ Suficientes - Usar para baseline Qwen2.5"

  po:
    ejemplos: "?"
    acción: "🔍 Verificar si hay datos generados del script train_po_lora.py"

  architect:
    ejemplos_originales: 32
    ejemplos_gold: 16
    problema: "❌ CRÍTICO - Datos insuficientes y baja calidad"
    acción: |
      1. Analizar por qué se redujo de 32 a 16
      2. Generar 500+ ejemplos nuevos con maestro 72B
      3. Incluir chain-of-thought explícito
      4. Cubrir: ADRs, patrones, trade-offs, NFRs, constraints

  dev:
    infraestructura: "✅ Completa con rollouts + DPO"
    acción: "Mantener enfoque pass@k, agregar destilación"

  qa:
    ejemplos: 3
    acción: "❌ Generar 200+ ejemplos nuevos desde cero"
```

### Fase 2: Estrategia Específica por Rol

#### BA (Ya Funciona)
```yaml
estrategia: "Baseline sólido → Fine-tune incremental"
pasos:
  1. "Evaluar Qwen2.5-7B con dataset existente (85 ejemplos)"
  2. "Si mejora >10%, publicar BA-v1"
  3. "Generar 200 ejemplos sintéticos adicionales con maestro"
  4. "Fine-tune BA-v2 con dataset combinado (285 ejemplos)"
costo_gpu: "$5-10 (LoRA 7B)"
```

#### PO (Script Existe)
```yaml
estrategia: "Verificar datos → Migrar a Qwen2.5"
pasos:
  1: "Buscar dataset usado en scripts/train_po_lora.py"
  2: "Si existe: migrar a Qwen2.5-7B"
  3: "Si no existe: generar 300 ejemplos con maestro (priorización, validación)"
costo_gpu: "$5-10 (LoRA 7B)"
```

#### Architect (FALLÓ - Prioridad Alta)
```yaml
estrategia: "Rediseño completo del dataset"
problema_raiz: "Solo 16 ejemplos de calidad + sin chain-of-thought"
solución:
  1_analisis:
    - "Revisar architect_train_gold_v2.jsonl para entender qué se consideró 'bueno'"
    - "Identificar patrones faltantes"

  2_generacion_maestro:
    modelo: "Qwen2.5-72B-Instruct"
    prompts:
      - "Diseña arquitectura para: {concepto}"
      - "Explica paso a paso el razonamiento (chain-of-thought)"
      - "Genera ADR completo con trade-offs"
      - "Identifica constraints y NFRs clave"
    ejemplos_target: 600
    variaciones_por_ejemplo: 3
    total: 1800

  3_curacion:
    filtros:
      - "Debe incluir razonamiento explícito"
      - "Debe mencionar al menos 2 trade-offs"
      - "Debe generar ADR válido"
    ejemplos_finales: 500-600

  4_fine_tune:
    base: "Qwen2.5-14B-Instruct (más capacidad)"
    lora_rank: 64  # Aumentar de 32
    lora_alpha: 128
    reasoning_transfer: true
    epochs: 5

costo_gpu:
  generacion_maestro: "$20-30 (72B, 10-15h)"
  fine_tune_estudiante: "$15-20 (14B, 5-8h)"
  total: "$35-50"
```

#### Dev (Infraestructura Completa)
```yaml
estrategia: "Mantener DPO + Agregar destilación"
ventaja: "Ya tienen infraestructura de rollouts completa"
pasos:
  1: "Ejecutar rollouts con Qwen2.5-14B o DeepSeek-Coder-7B"
  2: "Construir preferences con script existente"
  3: "NUEVO: Generar ejemplos sintéticos con maestro 72B para código"
  4: "Combinar: preferences (DPO) + synthetic (SFT)"
  5: "Fine-tune con enfoque híbrido"

ventaja_adicional: "Maestro 72B puede generar código de mejor calidad"
costo_gpu: "$30-40 (rollouts + synthetic + DPO)"
```

#### QA (Datos Insuficientes)
```yaml
estrategia: "Generación desde cero"
problema: "Solo 3 ejemplos"
solución:
  1: "Generar 300 ejemplos con maestro 72B:"
     - "Casos de prueba para diferentes tipos de sistemas"
     - "Identificación de edge cases"
     - "Análisis de bugs comunes"
  2: "Fine-tune QA-v1 con Qwen2.5-7B"
costo_gpu: "$10-15"
```

---

## Scripts a Modificar/Crear

### 1. Adapter para Post-Training Existente

```python
# training/adapters/migrate_post_training.py

"""
Migra scripts de post_training/ para usar con Qwen2.5 y nuevos modelos.
Mantiene compatibilidad con infraestructura DPO existente.
"""

def migrate_rollouts_to_qwen():
    """Adapta posttrain_collect_rollouts.py para Qwen2.5"""
    pass

def migrate_dpo_training():
    """Adapta posttrain_train_lora.py para nuevos modelos base"""
    pass
```

### 2. Analizador de Datasets Previos

```python
# training/scripts/analyze_existing_datasets.py

"""
Analiza datasets de dspy_baseline/data/production/
para entender por qué Architect falló.
"""

import json
from pathlib import Path

def analyze_architect_evolution():
    """
    Compara architect_train.jsonl vs architect_train_gold_v2.jsonl
    para identificar qué criterios usaron para filtrar.
    """

    original = load_jsonl("architect_train.jsonl")  # 32 ejemplos
    gold_v2 = load_jsonl("architect_train_gold_v2.jsonl")  # 16 ejemplos

    # ¿Qué tienen en común los 16 que quedaron?
    # ¿Qué faltó en los 16 descartados?

    return {
        "patterns_retained": [...],
        "patterns_missing": [...],
        "quality_criteria": [...]
    }

def compute_dataset_stats():
    """Estadísticas por rol."""
    return {
        "ba": {"count": 85, "avg_length": X, "coverage": Y},
        "architect": {"count": 16, "problem": "insufficient"},
        # ...
    }
```

### 3. Generador Maestro con Chain-of-Thought

```python
# training/scripts/generate_architect_cot.py

"""
Genera datos de Architect con chain-of-thought explícito
usando modelo maestro 72B.
"""

def generate_architect_example_with_cot(concept: str, teacher_model) -> dict:
    """
    Genera ejemplo de Architect con razonamiento explícito.
    """

    # Prompt con CoT obligatorio
    prompt = f"""
    Eres un arquitecto de software senior. Analiza el siguiente concepto y diseña
    la arquitectura PASO A PASO, explicando tu razonamiento.

    Concepto: {concept}

    Debes incluir:
    1. Análisis del dominio (piensa en voz alta)
    2. Identificación de componentes clave (justifica cada uno)
    3. Patrones arquitectónicos aplicables (compara opciones)
    4. Trade-offs principales (explica pros/cons)
    5. ADR final (decisión fundamentada)

    Formato de salida:
    ## Razonamiento paso a paso
    [Tu análisis detallado aquí]

    ## Arquitectura final
    [YAML con arquitectura]

    ## ADR
    [ADR formal]
    """

    response = teacher_model.generate(prompt, temperature=0.7)

    return {
        "instruction": "Como Arquitecto, diseña la arquitectura...",
        "input": concept,
        "output": extract_yaml(response),
        "reasoning": extract_reasoning(response),
        "adr": extract_adr(response),
        "quality_score": teacher_model.self_evaluate(response)
    }
```

---

## Comparativa de Costos: Previo vs Propuesto

### Setup Previo (Estimado)

| Actividad | Costo GPU | Notas |
|-----------|-----------|-------|
| BA fine-tune | ~$5 | Mistral-7B LoRA |
| PO fine-tune | ~$5 | Mistral-7B LoRA |
| Architect fine-tune (falló) | ~$10 | Múltiples intentos |
| **Total** | **~$20** | Pero Architect no funcionó |

### Propuesta Actualizada

| Actividad | Costo GPU | ROI |
|-----------|-----------|-----|
| Generación maestro (72B, todos los roles) | ~$40-60 | Reutilizable para múltiples ciclos |
| BA-v2 fine-tune | ~$8 | Mejora incremental |
| PO-v1 fine-tune | ~$8 | Nuevo modelo abierto |
| **Architect-v1 fine-tune (PRIORIDAD)** | ~$35-50 | **Resolución del problema crítico** |
| Dev-v1 (DPO + synthetic) | ~$30-40 | Mantiene pass@k + destilación |
| QA-v1 fine-tune | ~$10-15 | Nuevo desde cero |
| **Total primer ciclo** | **~$130-180** | Todos los roles funcionales |

### Ciclos Posteriores (Amortización)

| Ciclo | Costo | Notas |
|-------|-------|-------|
| **Ciclo 1** (completo) | $130-180 | Genera datos sintéticos reutilizables |
| **Ciclo 2** (incremental) | $40-60 | Solo fine-tuning, datos ya existen |
| **Ciclo 3+** (incremental) | $40-60 | Amortización completa |

---

## Cronograma Integrado

### Semana 1-2: Diagnóstico y Preparación
```
[X] Analizar por qué Architect falló (analyze_existing_datasets.py)
[X] Migrar infraestructura post_training/ a training/
[ ] Evaluar Qwen2.5-7B con datos BA existentes (baseline)
[ ] Verificar datos de PO
```

### Semana 3-4: Generación de Datos con Maestro
```
[ ] Rentar GPU A100 80GB (~$40-60, 20-30h)
[ ] Generar 600 ejemplos Architect con CoT
[ ] Generar 300 ejemplos QA
[ ] Generar 200 ejemplos adicionales BA/PO
[ ] Curar y validar datasets
```

### Semana 5-6: Fine-Tuning Architect (Prioridad 1)
```
[ ] Fine-tune Architect-v1 con Qwen2.5-14B
[ ] Evaluar en test set
[ ] Iterar si es necesario
[ ] Meta: Architect funcional >80% acceptance
```

### Semana 7-8: Fine-Tuning Otros Roles
```
[ ] BA-v2 (incremental)
[ ] PO-v1 (nuevo)
[ ] Dev-v1 (DPO + synthetic)
[ ] QA-v1 (nuevo)
```

### Semana 9: Integración y Publicación
```
[ ] Cuantizar todos los modelos (GGUF Q4_K_M)
[ ] Registrar en Ollama
[ ] Publicar en HuggingFace
[ ] Documentar resultados
```

---

## Métricas de Éxito Revisadas

### Architect (Crítico)

| Métrica | Baseline (falló) | Target | Medición |
|---------|------------------|--------|----------|
| **Aceptación de ADRs** | <50% | >80% | Validación humana de 20 ejemplos |
| **Inclusión de trade-offs** | <30% | >90% | Parsing automático |
| **Razonamiento explícito** | 0% | >95% | Detección de CoT |
| **Cobertura de patrones** | Limitada | Completa | 10+ patrones comunes |

### Otros Roles

| Rol | Métrica Clave | Baseline | Target |
|-----|---------------|----------|--------|
| **BA** | Completitud de requisitos | ~80% | >90% |
| **PO** | Priorización correcta | ? | >85% |
| **Dev** | pass@1 | ~15% | >30% |
| **QA** | Detección de bugs | ? | >85% |

---

## Decisiones Pendientes

### Inmediatas (Esta Semana)

1. **¿Qué causó el fallo de Architect?**
   - Ejecutar `analyze_existing_datasets.py`
   - Revisar manualmente 5 ejemplos "gold" vs 5 descartados

2. **¿Hay datos de PO disponibles?**
   - Buscar output de `scripts/train_po_lora.py`
   - Si no existe, generar desde cero

3. **¿Empezar con BA o Architect?**
   - **Recomendación**: BA primero (baseline rápido, bajo riesgo)
   - Architect segundo (problema crítico, pero necesita más trabajo)

### Siguiente Mes

4. **¿Modelo maestro único o múltiples?**
   - Opción A: Qwen2.5-72B para todos los roles
   - Opción B: DeepSeek-Coder-236B para Dev, Qwen-72B para resto
   - **Recomendación**: Opción A (simplicidad)

5. **¿Combinar DPO + SFT o solo SFT?**
   - Dev: **DPO** (infraestructura existe, pass@k medible)
   - Architect/BA/PO/QA: **SFT** (no hay métrica clara de preferencias)

---

## Próximos Pasos Concretos

### Hoy (2026-02-03)

```bash
# 1. Analizar datasets existentes
python training/scripts/analyze_existing_datasets.py

# 2. Buscar datos de PO
find . -name "*po*" -name "*.jsonl" | grep -v ".venv"

# 3. Evaluar Qwen2.5-7B con datos BA
# (requiere pull de Qwen2.5-7B en Ollama)
ollama pull qwen2.5:7b-instruct
```

### Esta Semana

```bash
# 1. Baseline rápido con BA + Qwen2.5
python training/scripts/eval_baseline.py \
  --role ba \
  --model qwen2.5:7b-instruct \
  --dataset dspy_baseline/data/production/ba_train_plus_more_unique.jsonl

# 2. Preparar script de generación maestro para Architect
# (pseudocódigo en training/scripts/generate_architect_cot.py)
```

### Siguiente Semana

```bash
# Si baseline BA es bueno (>10% mejora):
# 1. Rentar GPU para generación maestro
# 2. Generar 600 ejemplos Architect con CoT
# 3. Fine-tune Architect-v1
```

---

**Estado**: Draft - Integra aprendizajes del fine-tuning previo
**Autor**: Architecture
**Fecha**: 2026-02-03
**Depende de**: PLAN_open_models_finetuning.md
