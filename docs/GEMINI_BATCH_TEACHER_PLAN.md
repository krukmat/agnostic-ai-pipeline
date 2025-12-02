# Gemini Pro Batch Teacher Plan (para modelos locales)

Este documento detalla cómo utilizar Gemini Pro (vía Vertex AI Batch API) como *teacher offline* para generar datasets gold, que luego se usarán en:

- El plan de `docs/LOCAL_MODELS_OPTIMIZATION_PLAN.md` (capa de programas DSPy/MiPROv2 y LoRA sobre modelos locales).
- La distilación de comportamientos hacia modelos locales + LoRA, manteniendo el pipeline e2e libre de dependencias de nube en producción.

El objetivo NO es llamar a Gemini en cada ejecución del pipeline, sino **usar Batch sólo para generar o refrescar ejemplos gold**.

---

## 1. Relación con `LOCAL_MODELS_OPTIMIZATION_PLAN.md`

En `docs/LOCAL_MODELS_OPTIMIZATION_PLAN.md` se define una estrategia en dos capas:

1. **Capa de programas/prompting (DSPy/MiPROv2 o alternativas)**  
   - Afinar prompts/programas por rol sobre modelos locales.
   - Usar datasets gold para medir y optimizar (MiPRO o búsqueda manual).

2. **Capa de modelos (LoRA/QLoRA)**  
   - Distilar comportamientos de un teacher fuerte a modelos locales.

El uso de Gemini Pro + Batch encaja en la **capa de datasets**:
- Sirve como **teacher temporal** para producir lotes de ejemplos de alta calidad.  
- Los datasets resultantes se usan luego:
  - Como gold para DSPy/MiPRO con modelos locales.
  - Como datos de entrenamiento para LoRA/QLoRA.

El pipeline e2e (BA→PO→Architect→Dev→QA) sigue operando con **modelos locales**; Gemini entra sólo en scripts de generación/actualización de datasets.

---

## 2. Roles objetivo para generación gold

Roles donde un teacher fuerte aporta más valor:

- **BA (requirements)**  
  - Input: concepto corto.  
  - Output: `requirements.yaml` bien estructurado.

- **Product Owner (PRD/visión)**  
  - Input: requirements + contexto.  
  - Output: resumen PRD (texto estructurado, bullets).

- **Architect**  
  - Input: requirements + concepto.  
  - Output: `stories.yaml`, `epics.yaml`, `architecture.yaml`, `prd.yaml` en formatos bien definidos.

- **QA‑testcases**  
  - Input: story.  
  - Output: casos de prueba textuales (happy/unhappy), siguiendo el esquema de `dspy_baseline/data/qa_eval.yaml`.

Roles como Dev/QA (ejecución de código/tests) también se podrían beneficiar, pero suelen requerir infra o testbeds más complejos; se pueden considerar en una fase posterior.

---

## 3. Diseño del flujo Batch por rol

### 3.1 Estructura general

1. **Preparar prompts por rol**  
   - Definir un prompt muy restringido y determinista, que:
     - Reciba el input en un formato estable (YAML/JSON/markdown estructurado).
     - Devuelva la salida estrictamente en el formato que tus métricas y pipeline esperan.

2. **Construir ficheros de entrada JSONL**  
   - Cada línea representa una instancia a procesar por el modelo.  
   - Campos típicos:
     ```json
     {
       "instance_id": "ARCH_0001",
       "role": "architect",
       "input": {
         "concept": "...",
         "requirements_yaml": "...texto YAML...",
         "extra_context": "..."
       }
     }
     ```

3. **Subir a GCS y lanzar job Batch**  
   - Subir `*.jsonl` a un bucket (ej. `gs://<project>/gemini_batch/architect_input.jsonl`).  
   - Crear un Batch Job en Vertex AI con:
     - Modelo: Gemini Pro (ej. `gemini-2.5-pro` o la versión 3 cuando esté disponible).  
     - Tipo de tarea: generación de texto (con prompts embebidos).  
     - Ubicación de salida: `gs://<project>/gemini_batch/architect_output/`.

4. **Post-procesar outputs a dataset gold**  
   - Descargar el resultado (JSONL/JSON).  
   - Parsear cada salida al esquema interno:
     ```json
     {
       "input": {...},   // lo que enviaste al teacher
       "output": {...},  // stories/epics/architecture/PRD, etc.
       "metadata": {
         "teacher": "gemini-pro-batch",
         "model": "gemini-2.5-pro",
         "timestamp": "...",
         "score": <opcional, calculado con métrica del rol>
       }
     }
     ```
   - Guardar en rutas como:
     - `dspy_baseline/data/production/architect_train_gold_v3.jsonl`
     - `..._val_gold_v3.jsonl`

5. **Usar esos gold en el plan local**  
   - Alimentar DSPy/MiPRO para prompts optimizados sobre modelos locales.  
   - Entrenar LoRA/QLoRA para distilar el comportamiento del teacher a modelos locales.

---

## 4. Detalle por rol (ejemplo: Architect)

### 4.1 Prompt de teacher para Architect (conceptual)

System prompt (resumen):
- “Eres un arquitecto de software experto…”  
- Instrucciones:
  - Analiza `requirements.yaml` + `concept`.
  - Genera:
    - `EPICS` (YAML)  
    - `STORIES` (YAML, con `complexity` si quieres ya integrarlo)  
    - `ARCHITECTURE` (YAML)  
    - `PRD` (YAML/JSON, opcional)  
  - Cumple estrictamente con el esquema que ya usa el pipeline (mismo que `prompts/architect.md`).

Input para cada instancia (JSONL):
```json
{
  "instance_id": "ARCH_0001",
  "role": "architect",
  "input": {
    "concept": "Sample feature toggle app",
    "requirements_yaml": "<contenido literal de planning/requirements.yaml>",
    "architect_tier": "simple"
  }
}
```

### 4.2 Definir tamaño de batch y coste aproximado

1. Estimar tokens por instancia:
   - `requirements_yaml` + instrucciones + salida esperada ≈ 1.5k–3k tokens.  
2. Elegir nº de instancias:
   - Por ejemplo, 500–2.000 ejemplos arquitecto gold.  
3. Calcular coste aproximado:
   - Usar tabla de precios de Vertex AI (tokens in/out por millón).  
   - Aproximar:  
     `coste ≈ (tokens_in_totales / 1M) * input_price + (tokens_out_totales / 1M) * output_price`.

La elección de tamaño (500 vs 5.000) depende de tu presupuesto; como referencia, 500–1.000 ejemplos bien puntuados suelen ser suficientes para un primer LoRA + MiPRO local decente.

---

## 5. Integración en el repositorio

### 5.1 Scripts y rutas sugeridas

Para mantener coherencia con el repo:

- **Entrada Batch**:
  - `artifacts/batch/architect_teacher_input.jsonl`
  - `artifacts/batch/ba_teacher_input.jsonl`
  - `artifacts/batch/qa_teacher_input.jsonl`, etc.

- **Salida Batch (descargada de GCS)**:
  - `artifacts/batch/architect_teacher_output.jsonl`

- **Scripts de post‑proceso**:
  - `scripts/batch/postprocess_architect_teacher.py`  
    - Lee `...teacher_output.jsonl`  
    - Aplica parseo/normalización  
    - Calcula score con `architect_metric_v2`  
    - Escribe `dspy_baseline/data/production/architect_train_gold_v3.jsonl` y `..._val_gold_v3.jsonl`.

### 5.2 Conexión con LOCAL_MODELS_OPTIMIZATION_PLAN

En `docs/LOCAL_MODELS_OPTIMIZATION_PLAN.md`, la secuencia quedaría:

1. **Definir modelo local objetivo para Architect** (por ejemplo, Qwen2.5‑Coder 7B).  
2. **Generar datasets gold con Gemini + Batch** (según este documento, una vez al principio y luego esporádicamente).  
3. **Optimizar el programa DSPy Architect** con MiPRO usando esos gold, sobre el modelo local.  
4. **Entrenar LoRA local** para Architect usando los mismos gold (distilación).  
5. **Ajustar `config.yaml` + `routing_by_complexity`** para que Architect apunte al modelo local LoRA, usando la nube sólo en scripts offline de dataset/teacher.

---

## 6. Riesgos y mitigaciones

1. **Coste de Batch**  
   - Riesgo: exceder presupuesto si se mandan demasiados tokens.  
   - Mitigación: empezar con un lote pequeño (p.ej. 200–500 ejemplos) y medir coste real antes de escalar.

2. **Calidad de salida del teacher**  
   - Riesgo: Gemini genera salidas que no encajan exactamente en tu esquema.  
   - Mitigación: prompts muy estrictos + scripts de normalización (similar a `yaml_sanitizer`, `fix_stories`) + filtros por métrica.

3. **Desalineación con el modelo local**  
   - Riesgo: distilar comportamientos que el modelo local no puede reproducir bien.  
   - Mitigación: usar MiPRO sobre el modelo local para ajustar prompts; quizá limitar complejidad de las salidas gold (no pedir cosas “imposibles” para un 7B).

---

## 7. Resumen

- Gemini Pro + Batch se usa aquí como **teacher offline** para generar datasets gold en bloque, no para ejecutar el pipeline e2e.  
- Los datasets generados se integran en el plan de `LOCAL_MODELS_OPTIMIZATION_PLAN.md`:
  - Alimentan DSPy/MiPRO para prompts/programas adaptados a modelos locales.  
  - Sirven de base para entrenar LoRA/QLoRA en modelos locales.  
- El pipeline diario BA→PO→Architect→Dev→QA se ejecuta con **modelos locales (afinados)**; Gemini sólo se enciende cuando quieres crear o refrescar gold de entrenamiento.

