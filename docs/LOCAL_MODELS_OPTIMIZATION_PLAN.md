# Local Models Optimization Plan (DSPy, MiPROv2, LoRA)

**Objetivo**  
Ejecutar el pipeline AGNOSTIC AI PIPELINE principalmente con modelos locales, reduciendo al mínimo la dependencia de proveedores de nube, manteniendo calidad razonable en BA → PO → Architect → Dev → QA.

---

## 1. Contexto y hallazgos actuales

- El pipeline ya soporta:
  - Routing por rol vía `config.yaml` (`roles.*`).
  - Routing por complejidad de story vía `routing_by_complexity` + `Client(complexity=...)`.
  - Roles BA/PO/Architect/QA‑testcases con módulos DSPy + MiPROv2 (en distintos grados de madurez).
- En la práctica:
  - Hemos validado Dev y QA (allow_no_tests) contra Vertex (`vertex_sdk`/`vertex_cli`) usando routing por complejidad.
  - Architect genera historias a veces sin el campo `complexity`; `fix_stories.py` usa un analizador heurístico basado en keywords, número de criterios de aceptación e indicadores de profundidad técnica para clasificarlas inteligentemente como simple/medium/complex.
  - DSPy se usa hoy sobre todo en BA/PO/Architect/QA‑testcases; Dev y QA (ejecución de código) siguen un patrón más "prompt + tests".

Conclusión: la arquitectura está lista para experimentar con modelos locales + routing + DSPy, pero falta una estrategia clara para **optimizar prompts/programas** y **adaptar modelos** específicamente a hardware limitado.

---

## 2. Estrategia general (dos capas)

Separar claramente:

1. **Capa de programas/prompting**: definir bien las tareas por rol (I/O, métrica) y optimizar prompts/programas sobre el modelo local elegido, sin tocar pesos.
2. **Capa de modelos**: una vez que los programas están razonablemente estables, afinar modelos locales (LoRA/QLoRA) con datasets derivados del pipeline (distilación).

DSPy entra principalmente en la primera capa; LoRA en la segunda.

### 2.1 Motivación para modelos locales

**Beneficios**:
- **Cero costo de API**: Eliminación de facturas de Vertex/OpenAI/Anthropic
- **Privacidad**: Datos sensibles no salen del hardware local
- **Latencia**: Reducción de 2-5s (API round-trip) a <1s (local inference)
- **Independencia**: No depender de outages de proveedores externos
- **Control total**: Ajustar modelos específicamente para el dominio del pipeline

**Casos de uso ideales**:
- Desarrollo/testing frecuente (cientos de iteraciones)
- Conceptos/código propietario sensible
- Pipelines batch nocturnos
- Entornos sin conexión a internet

**Limitaciones**:
- Calidad inicial menor que GPT-4/Claude (mitigable con LoRA + prompt optimization)
- Requiere hardware adecuado (8GB+ VRAM recomendado para 7B models)
- Setup inicial más complejo (instalación de Ollama, descarga de modelos, etc.)

---

## 3. Capa de programas/prompting con DSPy/MiPROv2 (u otras formas)

### 3.1 Roles candidatos ideales para DSPy

Más beneficiados:
- **BA (requirements)** – salida YAML estructurada (`planning/requirements.yaml`).
- **Product Owner** – PRD + refinamiento de requisitos (estructurado).
- **Architect** – epics/stories/architecture/PRD (`epics.yaml`, `stories.yaml`, `architecture.yaml`, `prd.yaml`).
- **QA‑testcases** – generación de casos de prueba descritos con esquema acotado.

Menos críticos para DSPy:
- **Dev** – implementa código: la métrica real es “pasan los tests”; el beneficio de programas DSPy es menor vs. buenos prompts + feedback de tests.
- **QA ejecución** – orquesta herramientas (pytest/npm); no es un generador principal.

### 3.2 Trabajo propuesto con DSPy en modelos locales

Para roles BA/PO/Architect/QA‑testcases:

1. **Elegir modelos locales por rol (baseline)**
   - Ejemplo: `qwen2.5-coder:7b` o similar para Architect/PO; un 7–14B generalista para BA; un 7B centrado en texto para QA‑testcases.
   - Configurar `routing_by_complexity` **por rol** para que:
     - `dev.simple`/`dev.medium` → modelos locales (ej. `ollama/qwen2.5-coder:7b`)
     - `qa.simple`/`qa.medium` → modelos locales (ej. `ollama/qwen2.5-coder:7b`)
     - `dev.complex`/`qa.complex` → modelos locales potentes (14B) o nube como fallback
   - Roles sin routing por complejidad (BA/PO/Architect) siguen usando `roles.<role>.provider` directamente en `config.yaml`.

2. **Reconfigurar DSPy para usar esos modelos locales**
   - Ajustar la inicialización de LM en los módulos DSPy:
     - Modificar `dspy_baseline/modules/*.py` para usar modelos locales vía `dspy.OpenAI` (para Ollama) o `dspy.OllamaLocal`
     - Configurar variables de entorno o pasar parámetros de modelo en scripts de optimización
     - Ejemplo: `scripts/tune_dspy.py` usa el modelo especificado en flag `--teacher_model`

3. **Ejecutar MiPROv2 de forma “agresiva pero controlada”**  
   - Dataset pequeño pero de alta calidad (20–40 ejemplos por rol) usando los gold que ya tienes en `dspy_baseline/data/production` y `artifacts/synthetic`.
   - Correr MiPRO sobre el modelo local con:
     - Pocas trials (p.ej. 16–32) para adaptarse a hardware limitado.
     - Métrica del rol (ya existen para Architect y PO; BA/QA tienen métricas básicas).
   - Guardar `program_components.json` por rol y activarlo vía `features.<role>.use_optimized_prompt` + `prompt_override_file`.

4. **Costes de MiPROv2 con modelos locales**

   **Estimación de tokens para MiPRO** (32 trials, 40 training examples):
   - Prompts generados: ~32 variantes × 40 ejemplos = 1,280 evaluaciones
   - Tokens por ejemplo: ~500 input + ~1,000 output = 1,500 tokens
   - **Total: ~1.9M tokens**

   **Tiempos esperados** (modelo local 7B en RTX 3060 / M1 Pro 16GB):
   - Architect: ~6-8 horas
   - BA: ~4-6 horas
   - PO: ~3-5 horas

   **Alternativa económica**: Reducir trials a 8 y usar 20 ejemplos → ~240K tokens (~1-2 horas)

   **Recomendación**: Ejecutar MiPRO en background overnight con `--num_trials=16`

5. **Alternativa ligera si MiPRO es demasiado caro**
   - Mantener estructura DSPy (firmas I/O, módulos) pero:
     - Probar manualmente 5–10 variantes de prompts por rol.
     - Medir con la métrica de rol sobre el mini‑gold.
     - Elegir el mejor prompt a mano y guardarlo como override en `program_components.json` "manual".

### 3.3 Roles Dev/QA sin DSPy pesado

Para Dev:
- Mantener prompts bien definidos (como el `prompts/developer.md` actual).
- Depender de tests + drivers como métrica real de calidad.
- Uso de routing por complejidad para decidir modelo local vs (opcional) nube.
- Opcional: un pequeño bucle de “self‑refinement” barato:
  - Si los tests fallan, generar un segundo intento con un prompt de corrección específico, en lugar de un pipeline DSPy completo.

Para QA ejecución:
- Se centra en lanzar pytest/npm y analizar logs.
- Aquí la mejora está más en heurísticas de análisis de logs y en la selección de modelos para QA‑testcases (ya está parcialmente en DSPy QA).

---

## 4. Capa de modelos (LoRA / QLoRA)

Una vez que la capa de programas está estabilizada para modelos locales, pasamos a ajustar los modelos mismos.

### 4.1 Datasets por rol

Reutilizar el pipeline actual para generar datasets de distilación:

- **BA**: pares `(concepto → requirements.yaml)` de alta calidad.
- **PO**: `(requirements → PRD/visión refinada)`.
- **Architect**: `(requirements + concepto → (epics, stories, architecture, prd))`.
- **Dev**: `(story + contexto → código + tests que pasan)`.
- **QA‑testcases**: `(story → casos de prueba textuales)`.

Formato:
- JSONL con `{input: {...}, output: {...}, metadata: {...}}`, reusando los esquemas ya presentes en `dspy_baseline/data/production` y `artifacts/synthetic`.

### 4.2 LoRA/QLoRA en modelos pequeños

Para hardware limitado:

1. **Elegir modelos locales por rol (baseline)**
   - Ejemplo: `qwen2.5-coder:7b` o similar para Architect/PO; un 7–14B generalista para BA; un 7B centrado en texto para QA‑testcases.
   - Configurar `routing_by_complexity` **por rol** para que:
     - `dev.simple`/`dev.medium` → modelos locales (ej. `ollama/qwen2.5-coder:7b`)
     - `qa.simple`/`qa.medium` → modelos locales (ej. `ollama/qwen2.5-coder:7b`)
     - `dev.complex`/`qa.complex` → modelos locales potentes (14B) o nube como fallback
   - Roles sin routing por complejidad (BA/PO/Architect) siguen usando `roles.<role>.provider` directamente en `config.yaml`.

2. Entrenar LoRA (o QLoRA 4‑bit) por rol o grupo de roles:
   - Opción 1: un adapter general para “texto estructurado YAML/JSON” (BA/PO/Architect/QA‑testcases).
   - Opción 2: un adapter orientado a código/tests (Dev/QA code).

3. Distilación:
   - Primer objetivo: imitar al teacher fuerte (Vertex/OpenAI) usando los datasets gold.
   - Segundo objetivo (si se quiere): refinar el LoRA con la métrica del rol (por ejemplo, valorando outputs con tu métrica de Architect).

4. Integración con el pipeline:
   - Publicar el modelo local ajustado como endpoint (Ollama u otro servidor local).
   - Actualizar `config.yaml` y `routing_by_complexity` para que los roles correspondan a esos modelos LoRA locales en simple/medium; dejar cloud solo como backup en `backup_models`.

5. **Workflow práctico de LoRA para este pipeline**:
   - Usar `unsloth` o `axolotl` para 4-bit QLoRA training en hardware consumer
   - Entrenar adapters sobre datasets de `dspy_baseline/data/production/*.jsonl`
   - Merge adapter con base model O servir vía adapter-aware endpoint
   - Registrar como modelo custom en Ollama: `ollama create <role>-tuned -f Modelfile`
   - Actualizar `config.yaml` provider entries para apuntar a modelos custom

6. **Requisitos de hardware**:
   - 7B LoRA: 8-12GB VRAM (RTX 3060, M1 Pro 16GB)
   - 14B LoRA: 16-24GB VRAM (RTX 3090, M1 Max 32GB)
   - CPU-only: Posible con QLoRA 4-bit pero 10x más lento

### 4.3 Generación de datasets de calidad (el gap crítico)

**Problema**: DSPy/MiPRO y LoRA requieren datasets de alta calidad, pero generar datos sintéticos inventados no sirve para entrenar modelos productivos.

**Solución: Bootstrapping progresivo con validación automática**

#### 4.3.1 Fase 1: Recolección automática con teacher cloud

**Estrategia**: Usar teacher cloud (Vertex/GPT-4) en producción temporal para generar datos gold

```bash
# 1. Ejecutar pipeline completo con teacher cloud en 100+ conceptos diversos
CONCEPT_FILE=datasets/diverse_concepts.txt  # Lista curada de conceptos
for concept in $(cat $CONCEPT_FILE); do
    # Ejecutar con teacher cloud
    PYTHONPATH=. CONCEPT="$concept" \
    .venv/bin/python scripts/run_ba.py >> artifacts/bootstrap/ba_outputs.jsonl

    PYTHONPATH=. .venv/bin/python scripts/run_architect.py >> artifacts/bootstrap/architect_outputs.jsonl

    # Solo si pasó QA, guardar como gold
    if [ qa_status == "passed" ]; then
        echo "✓ $concept -> saved to gold dataset"
    fi
done
```

**Filtrado de calidad**:
- BA: Solo conceptos que PO aprobó (tienen `product_owner_review.yaml`)
- Architect: Solo stories que Dev implementó sin errores
- Dev: Solo código que pasó QA con 100% tests passing
- **Resultado**: ~50-100 ejemplos reales de alta calidad por rol

#### 4.3.2 Fase 2: Ampliación con variaciones sintéticas

Una vez con 50+ ejemplos gold, ampliar con variaciones:

```python
# scripts/generate_synthetic_variations.py
from scripts.utils.synthetic_data import vary_concept

gold_concepts = load_gold_dataset("artifacts/bootstrap/ba_outputs.jsonl")

for example in gold_concepts:
    # Generar 3-5 variaciones por concepto gold
    variations = [
        vary_concept(example, "change_domain"),      # Coffee shop → Bookstore
        vary_concept(example, "change_complexity"),  # Agregar feature
        vary_concept(example, "simplify"),           # Remover feature
    ]

    # Ejecutar teacher sobre variaciones
    for variant in variations:
        output = run_teacher(variant)

        # Validar con métrica de rol
        if metric_score(output) > 0.7:
            save_to_training_set(variant, output)
```

**Resultado**: 50 gold × 3 variaciones = 150 ejemplos por rol

#### 4.3.3 Fase 3: Active learning - cerrar el loop

**Problema**: Modelos locales fallan en casos específicos

**Solución**: Recolectar failures como datos de entrenamiento

```python
# scripts/active_learning_loop.py

while degradation_rate > 0.10:  # Mientras >10% fallos
    # 1. Ejecutar pipeline con modelo local
    failures = run_pipeline_batch(local_model, test_concepts)

    # 2. Re-ejecutar failures con teacher cloud
    gold_outputs = run_teacher_on_failures(failures)

    # 3. Agregar (failure_input, gold_output) a training set
    training_set.extend(zip(failures, gold_outputs))

    # 4. Re-entrenar LoRA con dataset ampliado
    retrain_lora(training_set)

    # 5. Medir nuevo degradation rate
    degradation_rate = measure_quality(local_model)

    print(f"Iteration complete. New degradation: {degradation_rate:.1%}")
```

**Beneficio**: Dataset crece automáticamente en áreas donde el modelo local es débil

#### 4.3.4 Estrategia de distilación teacher→student

**Opción 1: Direct imitation** (más simple)
1. Usar datasets de Fase 1 (gold real) + Fase 2 (variaciones validadas)
2. Entrenar LoRA student para imitar teacher outputs directamente
3. No requiere métricas complejas, solo datos limpios

**Opción 2: Preference optimization** (mejor calidad)
1. Generar outputs de teacher (strong) y student (weak) para mismo input
2. Usar métrica de rol para rankear outputs (ej. `architect_metric_v2`)
3. Entrenar con DPO (Direct Preference Optimization) sobre rankings
4. Iterar: student mejora → generar nuevos outputs → re-rankear

**Recomendación**:
- **Primera iteración**: Opción 1 con Fase 1+2 (bootstrap rápido)
- **Segunda iteración**: Opción 2 + Fase 3 (refinamiento continuo)

#### 4.3.5 Curación de conceptos diversos (crítico para calidad)

**No usar conceptos inventados aleatorios**. Curar manualmente lista de dominios:

```yaml
# datasets/diverse_concepts.yaml
categories:
  web_apis:
    - REST API for e-commerce with payments
    - GraphQL API for social network
    - WebSocket real-time chat application

  data_processing:
    - ETL pipeline for financial data
    - Real-time analytics dashboard
    - Data warehouse with OLAP cubes

  business_apps:
    - CRM system for sales team
    - Inventory management for retail
    - Project management tool with Gantt charts

  infrastructure:
    - Kubernetes deployment automation
    - Multi-tenant SaaS platform
    - Event-driven microservices architecture

  mobile_apps:
    - Fitness tracking app with GPS
    - Food delivery mobile app
    - Augmented reality game
```

**Estrategia**: 20 categorías × 5 conceptos = 100 conceptos diversos

**Validación de diversidad**:
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Medir similaridad entre conceptos
vectors = TfidfVectorizer().fit_transform(concepts)
similarity_matrix = cosine_similarity(vectors)

# Rechazar conceptos con >80% similaridad
if max(similarity_matrix[i]) > 0.8:
    print(f"⚠️  Concepto {i} muy similar a otro, reemplazar")
```

### 4.4 Dataset mínimo requerido (actualizado)

**Para MiPROv2 (prompt optimization)**:
- Architect: 40 train + 10 val = **50 ejemplos** (diverse, gold quality)
- BA: 30 train + 10 val = **40 ejemplos**
- PO: 25 train + 10 val = **35 ejemplos**

**Para LoRA training (model fine-tuning)**:
- Architect: **100-150 ejemplos** (diverse concepts)
- BA: **80-120 ejemplos**
- PO: **60-100 ejemplos**
- Dev: **150-200 ejemplos** (code quality varies more)

### 4.5 Costo y tiempo de generación de datasets

**Tokens estimados por concepto completo** (BA → Architect → Dev → QA):
- Input: ~26,500 tokens (prompts + context)
- Output: ~31,000 tokens (YAML + código + tests)

**Fase 1: 100 conceptos gold con teacher cloud**

| Teacher Model | Input $/1M | Output $/1M | Total/100 concepts | Success Rate | Real Cost |
|---------------|------------|-------------|---------------------|--------------|-----------|
| Vertex Gemini 2.5 Flash | $0.075 | $0.30 | $1.13 | ~60% ⚠️ | **$0.70-1.20** |
| **Gemini 3 Pro Preview** | $2.00 | $12.00 | **$42.50** | ~95% ✅ | **$40-45** |
| **Gemini 3 Pro Batch** | $1.00 | $6.00 | **$21.25** | ~95% ✅ | **$20-22** |
| **Claude Sonnet 4.5** | $3.00 | $15.00 | **$54.45** | ~98% 🎯 | **$50-60** |
| OpenAI o1 | $15.00 | $60.00 | $226.13 | ~99% | $200-230 |

**Notas**:
- Gemini 2.5 Flash/Pro ya probados en tu pipeline → **no alcanzan calidad suficiente**
- Success Rate = % de conceptos que pasan QA completo sin intervención manual
- **Gemini 3 Batch API**: 50% descuento, pero resultados en 24h (no real-time)

**Fuentes de pricing** (verificadas enero 2025):
- Gemini 3: https://ai.google.dev/pricing
- Claude Sonnet 4.5: https://claude.com/pricing

**Recomendaciones según presupuesto**:

1. **Balance costo/calidad ($20-22)**: Gemini 3 Pro Batch API ⭐
   - 95% success → casi todos los conceptos pasan
   - Solo 5% requiere re-run o ajuste manual
   - **Recomendado**: Ejecutar batch overnight, resultados en 24h
   - Perfecto para BA/PO/Architect (YAML estructurado)

2. **Real-time necesario ($40-45)**: Gemini 3 Pro Preview
   - Mismo 95% success que Batch
   - Resultados inmediatos (no esperar 24h)
   - Usar si necesitas feedback rápido durante desarrollo

3. **Máxima calidad ($50-60)**: Claude Sonnet 4.5 via Codex CLI 🎯
   - 98% success → mínimo waste
   - **Crítico para Dev role**: código complejo + tests
   - Mejor reasoning para arquitecturas complejas
   - Prompt caching reduce costo en iteraciones (cache read $0.30/1M)

**Fase 2: 300 variaciones sintéticas (validation only)**

| Teacher | Costo/300 validations |
|---------|----------------------|
| Gemini 3 Pro Batch | $6.38 |
| Gemini 3 Pro Preview | $12.75 |
| Sonnet 4.5 | $16.34 |

**Fase 3: Active Learning (5 iteraciones, ~20 failures/iter)**

| Teacher | Costo total (5 iters) |
|---------|----------------------|
| Gemini 3 Pro Batch | $10.63 |
| Gemini 3 Pro Preview | $21.25 |
| Sonnet 4.5 (con caching) | $18.45 |

**Total estimado por estrategia**:

| Teacher | Fase 1 | Fase 2 | Fase 3 | **TOTAL** |
|---------|--------|--------|--------|-----------|
| **Gemini 3 Pro Batch** | $21.25 | $6.38 | $10.63 | **~$38** ⭐ |
| Gemini 3 Pro Preview | $42.50 | $12.75 | $21.25 | **~$76** |
| Sonnet 4.5 + caching | $54.45 | $16.34 | $18.45 | **~$89** 🎯 |

**Estrategia híbrida recomendada** (mejor ROI):

**Opción A: Budget-conscious ($45-50)**
1. **BA/PO/Architect**: Gemini 3 Pro Batch ($38)
   - YAML estructurado, 95% success suficiente
   - Batch API overnight (resultados en 24h)

2. **Dev**: Gemini 3 Pro Batch ($38) + manual review 5%
   - 95% código funcional
   - Review manual de 5 conceptos fallidos

**Opción B: Production-grade ($60-65)** ✅ RECOMENDADO
1. **BA/PO/Architect**: Gemini 3 Pro Batch ($38)
2. **Dev**: Claude Sonnet 4.5 con prompt caching ($55)
   - 98% código funcional + tests
   - Caching reduce costo en re-runs
   - Crítico para LoRA training data

**Total híbrido**: ~$60-65 para dataset gold de producción

**Tiempo de ejecución** (batch overnight):
- 100 conceptos × ~5 min/concepto = **8-10 horas**
- Ejecutar durante 2-3 noches para completar Fase 1+2

---

## 5. DSPy vs otras formas en hardware limitado

### 5.1 Dónde DSPy tiene mejor retorno

- BA/PO/Architect/QA‑testcases:
  - E/S estructurada.
  - Métricas definidas.
  - Datasets pequeños pero de alta calidad.
  - Aquí MiPROv2 (aunque sea con pocas trials) tiene un ROI alto incluso en hardware modesto.

### 5.2 Dónde DSPy es opcional

- **Dev** y **QA ejecución**:
  - La señal real viene de tests automáticos (pytest/npm).
  - Lo más importante es:
    - Prompts cuidadosos que generen código testable.
    - Datasets de distilación de "código que pasa tests" para LoRA.
  - DSPy puede ayudar a estructurar el problema, pero el coste no siempre compensa frente a una combinación de buenos prompts + tests + LoRA.

- **Excepción importante: QA-testcases**:
  - QA-testcases (generación de casos de prueba) SÍ se beneficia de DSPy porque:
    - Output es estructurado (descripciones de test cases)
    - Métrica puede validar coverage y claridad
    - Ya existe `dspy_baseline/modules/qa_testcases.py` y métricas
  - Diferente de **QA ejecución** (pytest runner), que es orquestación de herramientas

### 5.3 Alternativas adicionales

Si DSPy/MiPRO resultan demasiado costosos:

- Mantener la noción de “programa” manualmente: funciones puras por rol con firmas claras y tests de regresión.
- Usar optimización de prompts basada en búsqueda simple:
  - Grid search de 5–10 prompts.
  - Métrica simple (por ejemplo, porcentaje de outputs válidos) en minibatches de ejemplos.

---

## 6. Integración con el routing por complejidad

El routing por complejidad se vuelve especialmente útil con modelos locales:

- `simple`:
  - Siempre a modelos locales pequeños (7B) + prompts afinados con DSPy/MiPRO o equivalente.
- `medium`:
  - Modelos locales medianos (o mismos 7B con mejor LoRA).
- `complex`:
  - Opcionalmente a modelos locales más grandes (14B) o a un teacher cloud, sólo si el caso lo justifica.

Orden de decisión (según implementación en `scripts/llm.py:Client.__init__`):

1. **RoRF** (si `MODEL_RECO_ENABLED=1`) analiza prompt y sugiere modelo
2. **Complexity routing** (si `routing_by_complexity_enabled: true`) sobrescribe según story complexity
3. **Fallback a role default** (si no hay routing) usa `roles.<role>.provider`
4. **Backup models** (si falla la ejecución) intenta providers en `backup_models`

**Para maximizar uso local**:
- RoRF puede sugerir modelo local fuerte (14B) para prompts complejos
- Complexity routing fuerza modelos locales en simple/medium
- Cloud solo en `backup_models` como última opción

---

## 7. Roadmap sugerido

1. **Definir stack local objetivo por rol** (1–2 modelos por grupo de roles).
2. **Alinear `config.yaml` + `routing_by_complexity`** a esos modelos.
3. **Reconfigurar DSPy** para que use LM locales y ejecutar MiPROv2 de forma moderada en BA/PO/Architect/QA‑testcases.
4. **Recolectar datasets gold** de alta calidad por rol (apoyándose en el teacher cloud si hace falta, pero fuera del loop normal).
5. **Entrenar adapters LoRA/QLoRA** sobre esos datasets por rol/grupo.
6. **Actualizar routing** para preferir siempre los modelos LoRA locales en simple/medium, dejando cloud sólo como teacher o backup extremo.
7. **Medir**:
   - Tiempos y costes (latencia, CPU/GPU).
   - Calidad por rol usando las métricas ya existentes.
   - Tasa de éxito Dev/QA (tests que pasan) con modelos locales vs anteriores.

8. **Validar e iterar**:
   - Ejecutar smoke tests comparando local vs cloud teacher (mismas stories)
   - Medir degradation rate: ¿cuántos stories fallan QA con modelos locales?
   - Si degradation > 20%: recolectar failure cases, agregar a training set, re-entrenar LoRA
   - Si degradation < 10%: promover modelos locales a producción en `config.yaml`
   - Documentar findings y configuración final en `docs/LOCAL_MODELS_RESULTS.md`
   - Iterar ciclo: deployment → medición → mejora → re-deployment

Este documento sirve como base para implementar, paso a paso, un pipeline centrado en modelos locales con prompts/programas afinados (DSPy/MiPRO u optimización ligera) y modelos mejorados vía LoRA, reduciendo al máximo la necesidad de proveedores de nube pagos.

