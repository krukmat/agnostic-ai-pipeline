# Reporte de Fases y Tareas - Plan de Implementación

**Documento**: PLAN_implementation_distilabel_finetuning_rag.md
**Fecha de creación**: 2026-02-06
**Estado**: Draft - Pendiente aprobación
**Objetivo general**: Implementar los 3 pilares faltantes (Graph RAG + Distilabel + Fine-tuning) para convertir agnostic-ai-pipeline en framework 100% open-source.

---

## Resumen Ejecutivo

### Viabilidad: ✅ VIABLE con ajustes costo-optimizados

**Cambios respecto a draft original**:
1. ✅ Teacher model en capas: Qwen2.5-14B/32B (default) + 72B (selectivo)
2. ✅ Dependencias separadas: `requirements-rag.txt`, `requirements-training.txt`
3. ✅ Orden optimizado: Quick wins → RAG → Distilabel → Fine-tuning
4. ✅ Costo total reducido: **$60-160 por ciclo** (vs $125-250 original)

### Timeline Total: **~7 semanas** (puede solaparse)

| Fase | Duración | GPU | Costo |
|------|----------|-----|-------|
| **F1: Graph RAG** | 2 semanas | No | $0 |
| **F2: Distilabel** | 2 semanas | A100/L40S | $30-90 |
| **F3: Fine-tuning** | 2 semanas | A100 | $30-70 |
| **F4: Integración** | 1 semana | No | $0 |
| **TOTAL** | 7 semanas | - | **$60-160** |

⚠️ **Nota**: Fases 1 y 2 pueden ejecutarse en paralelo (RAG local mientras se renta GPU para Distilabel).

---

## FASE 1: Graph RAG con LightRAG

**Duración**: ~2 semanas
**GPU**: No requerida
**Costo**: $0
**Valor**: Knowledge Graph del proyecto (relaciones causales entre artifacts)

### Decisiones Clave

| Decisión | Opción Elegida | Alternativa |
|----------|----------------|-------------|
| **RAG Type** | **LightRAG (Graph)** | ChromaDB (vector), Neo4j (overkill) |
| **Graph Store** | NetworkX (local) | Neo4j (requiere JVM) |
| **Vector Store** | NanoVectorDB (local) | FAISS, Qdrant |
| **Embedding Model** | **bge-m3** (1024 dims) | nomic-embed (768 dims) |
| **Retrieval Mode** | **mix** (graph + vector) | naive, local, global, hybrid |

### Tareas (7 tareas)

#### F1-T1: Setup LightRAG + dependencias
```
STATUS: [ ] PENDING
DEPENDENCIES: Ollama running
OUTPUT: lightrag-hku[api] installed, bge-m3 model pulled
FILES AFFECTED:
  - requirements-rag.txt (NEW)
```

#### F1-T2: Implementar wrapper GraphRAGEngine
```
STATUS: [ ] PENDING
DEPENDENCIES: F1-T1
OUTPUT: GraphRAGEngine singleton class, Ollama integrated
FILES TO CREATE:
  - graph_rag/__init__.py
  - graph_rag/engine.py (main wrapper)
  - graph_rag/config.py
TESTS: test_graph_rag_engine.py
```

#### F1-T3: Ingestion pipeline para artifacts
```
STATUS: [ ] PENDING
DEPENDENCIES: F1-T2
OUTPUT: Auto-ingest planning/, project/, artifacts/, docs/
LOGIC:
  - MD5 dedup (solo archivos nuevos/modificados)
  - Metadata tagging [Source: ...] [Type: ...]
  - Auto entity/relation extraction by LightRAG
FILES TO CREATE:
  - graph_rag/ingestion.py
TESTS: test_graph_rag_ingestion.py
```

#### F1-T4: Retrieval adapter para agentes
```
STATUS: [ ] PENDING
DEPENDENCIES: F1-T3
OUTPUT: Per-role retrieval policies
POLICIES:
  - BA:       mode=mix, top_k=30
  - PO:       mode=mix, top_k=40
  - Architect: mode=hybrid, top_k=60  (graph-heavy)
  - Dev:      mode=local, top_k=40
  - QA:       mode=mix, top_k=50
FILES TO CREATE:
  - graph_rag/retrieval.py
TESTS: test_graph_rag_retrieval.py
```

#### F1-T5: Integración con LLM Client
```
STATUS: [ ] PENDING
DEPENDENCIES: F1-T4
OUTPUT: RAG hook en scripts/llm.py
LOGIC:
  if graph_rag_enabled:
    context = retriever.retrieve_for_role(role, query)
    user_prompt = prepend_context(context, user)
FILES MODIFIED:
  - scripts/llm.py
  - config.yaml (agregar graph_rag section)
TESTS: test_rag_integration.py
```

#### F1-T6: Makefile targets para Graph RAG
```
STATUS: [ ] PENDING
DEPENDENCIES: F1-T5
TARGETS:
  - make rag-index         → Construir/actualizar Knowledge Graph
  - make rag-status        → Mostrar entidades, relaciones, chunks
  - make rag-query QUERY="..." MODE=mix
  - make rag-visualize     → Abrir WebUI (localhost:9621)
FILES MODIFIED:
  - Makefile
  - CLAUDE.md
```

#### F1-T7: Tests E2E Graph RAG
```
STATUS: [ ] PENDING
DEPENDENCIES: F1-T6
TEST CASES:
  1. Ingest planning/ → query "arquitectura" → verificar entidades
  2. Ingest stories.yaml → query "S3 depends on S1" → graph traversal
  3. RAG-enhanced Architect run → contexto estructurado
  4. Latency benchmark (<100ms p95)
  5. Incremental ingestion (solo archivos nuevos)
FILES TO CREATE:
  - tests/test_graph_rag_integration.py
  - tests/test_graph_rag_pipeline.py
ACCEPTANCE CRITERIA:
  ✓ make rag-index sin error
  ✓ make rag-query retorna entidades + relaciones
  ✓ make rag-visualize muestra Knowledge Graph
  ✓ Latencia < 100ms (p95)
  ✓ Todos los tests pasan
```

### Archivos Fase 1 (10 nuevos, 5 modificados)

```
NEW (5 archivos módulo):
  graph_rag/__init__.py
  graph_rag/engine.py          ← GraphRAGEngine wrapper (crítico)
  graph_rag/ingestion.py       ← Artifact ingestion con dedup
  graph_rag/retrieval.py       ← Role-based retrieval policies
  graph_rag/config.py          ← Configuration

NEW (5 tests):
  tests/test_graph_rag_engine.py
  tests/test_graph_rag_ingestion.py
  tests/test_graph_rag_retrieval.py
  tests/test_graph_rag_integration.py
  tests/test_graph_rag_pipeline.py

MODIFIED:
  scripts/llm.py               ← RAG hook en Client.chat()
  config.yaml                  ← graph_rag: section
  requirements-rag.txt         ← lightrag-hku[api] (NEW FILE)
  Makefile                     ← rag-* targets
  CLAUDE.md                    ← Documentar comandos
```

---

## FASE 2: Distilabel - Pipeline de Datos Sintéticos

**Duración**: ~2 semanas
**GPU**: A100/L40S (12-30h total)
**Costo**: $30-90 (estrategia tiered: 70% con 14B/32B, 30% con 72B selectivo)
**Valor**: Datasets sintéticos para fine-tuning (reemplaza Gemini comercial)

### Decisiones Clave

| Decisión | Opción Elegida | Razón |
|----------|----------------|-------|
| **Teacher Model** | **Qwen2.5-14B/32B + 72B** | Reduce costo vs Qwen2.5-72B always |
| **Distilabel** | **Sí, como wrapper** | Caching, retry, HF integration |
| **Generación** | **Híbrida por lotes** | cheap_pass → quality_gate → expensive_regen |
| **Validación** | **Reutilizar validators** | post_training/src/validators.py |

### Tareas (8 tareas)

#### F2-T1: Setup Distilabel
```
STATUS: [ ] PENDING
DEPENDENCIES: GPU rentada disponible
ACTIONS:
  - pip install distilabel[vllm,hf]
  - Setup vLLM con A100/L40S
  - Smoke test: generar 5 ejemplos
FILES AFFECTED:
  - requirements-training.txt (NEW)
```

#### F2-T2: Pipeline base Distilabel
```
STATUS: [ ] PENDING
DEPENDENCIES: F2-T1
OUTPUT: BaseSyntheticPipeline class
DESIGN:
  Load seed data → Generate (14B/32B) → Quality Filter → [Regen failed with 72B]
FILES TO CREATE:
  - training/__init__.py
  - training/pipelines/base_pipeline.py  ← BaseSyntheticPipeline
TESTS: test_distilabel_base.py
```

#### F2-T3: Pipeline Architect con CoT
```
STATUS: [ ] PENDING
DEPENDENCIES: F2-T2
OUTPUT: Architect-specific pipeline con chain-of-thought
CRITICAL: Architect falló antes (16 ejemplos gold, sin CoT)
STRATEGY:
  1. Generar con CoT obligatorio
  2. Extract reasoning + ADR + trade-offs
  3. Auto-evaluate con quality scorer
FILES TO CREATE:
  - training/pipelines/architect_pipeline.py
  - training/steps/cot_generator.py
TARGET: 600+ ejemplos con razonamiento explícito
```

#### F2-T4: Pipelines para todos los roles
```
STATUS: [ ] PENDING
DEPENDENCIES: F2-T3
ROLES:
  BA:       500 ejemplos (de 85)
  PO:       400+ ejemplos (de 319)
  Architect: 600+ ejemplos con CoT (de 16) ← PRIORIDAD
  Dev:      1000+ ejemplos + test patterns
  QA:       300+ ejemplos (de 3)
FILES TO CREATE:
  - training/pipelines/ba_pipeline.py
  - training/pipelines/po_pipeline.py
  - training/pipelines/dev_pipeline.py
  - training/pipelines/qa_pipeline.py
```

#### F2-T5: Integración con validators existentes
```
STATUS: [ ] PENDING
DEPENDENCIES: F2-T4
OUTPUT: QualityFilterStep que reutiliza validators.py
LOGIC:
  - product_owner_metric >= 0.85 (PO validation)
  - YAML schema validation
  - Custom per-role metrics
FILES MODIFIED:
  - training/steps/quality_filter.py ← Wrapper de validators
```

#### F2-T6: Script GPU rental
```
STATUS: [ ] PENDING
DEPENDENCIES: F2-T5
OUTPUT: Script all-in-one para sesión GPU
FEATURES:
  - Auto setup vLLM + Distilabel
  - Ejecución por rol con checkpoints
  - --teacher-tier 14B|32B|72B
  - --regen-failed-only (cost optimization)
  - Auto-shutdown al completar
FILES TO CREATE:
  - training/scripts/gpu_session.sh
  - training/scripts/run_synthetic_pipeline.py
```

#### F2-T7: Makefile targets Distilabel
```
STATUS: [ ] PENDING
DEPENDENCIES: F2-T6
TARGETS:
  - make synthetic-data ROLE=ba       → Generar dataset
  - make synthetic-validate ROLE=ba   → Validar output
  - make synthetic-stats              → Estadísticas de datasets
  - make synthetic-stats-all          → Todas las fases
FILES MODIFIED:
  - Makefile
  - CLAUDE.md
```

#### F2-T8: Tests E2E Distilabel
```
STATUS: [ ] PENDING
DEPENDENCIES: F2-T7
TEST CASES:
  1. BA pipeline genera 10+ ejemplos (dry run con Qwen2.5-3B)
  2. Quality filter rechaza score < 0.7
  3. Format validator acepta YAML válido
  4. Pipeline resume desde checkpoint
  5. Tiered execution (14B → 72B para failed)
ACCEPTANCE CRITERIA:
  ✓ make synthetic-data genera >= 100 ejemplos
  ✓ Quality score promedio >= 0.85
  ✓ Ejecución híbrida sin errores
  ✓ Datasets formateados HuggingFace
  ✓ Todos los tests pasan
```

### Archivos Fase 2 (15 nuevos, 3 modificados)

```
NEW (module):
  training/__init__.py
  training/pipelines/__init__.py
  training/pipelines/base_pipeline.py          ← BaseSyntheticPipeline (crítico)
  training/pipelines/ba_pipeline.py
  training/pipelines/po_pipeline.py
  training/pipelines/architect_pipeline.py    ← CoT (crítico)
  training/pipelines/dev_pipeline.py
  training/pipelines/qa_pipeline.py
  training/steps/__init__.py
  training/steps/quality_filter.py             ← Reutiliza validators
  training/steps/cot_generator.py
  training/steps/format_validator.py
  training/configs/distilabel_base.yaml
  training/configs/roles/ba.yaml
  training/configs/roles/po.yaml
  training/configs/roles/architect.yaml
  training/configs/roles/dev.yaml
  training/configs/roles/qa.yaml
  training/scripts/gpu_session.sh
  training/scripts/run_synthetic_pipeline.py

NEW (tests):
  tests/test_distilabel_base.py
  tests/test_distilabel_architect_cot.py
  tests/test_distilabel_tiered.py

MODIFIED:
  requirements-training.txt          ← distilabel[vllm,hf]
  Makefile                           ← synthetic-* targets
  CLAUDE.md
```

### Estrategia Costo-Optimizada

```
Generación masiva (cheap):
  └─ Qwen2.5-14B o 32B → 70% del dataset
     ├─ A100 40GB: ~$1.50/h
     ├─ Tiempo: 15-20h para 5 roles
     └─ Costo: $22-30

Regeneración selectiva (expensive):
  └─ Qwen2.5-72B → solo ejemplos con score < 0.80
     ├─ A100 80GB: ~$2-3/h
     ├─ Tiempo: 3-5h (muestras rechazadas)
     └─ Costo: $6-15

Overhead (infra, checkpoints):
  └─ $2-5

TOTAL: $30-50 por ciclo (vs $75-150 con 72B always)
```

---

## FASE 3: Fine-Tuning con Modelos Abiertos

**Duración**: ~2 semanas
**GPU**: A100 40GB (10-20h total)
**Costo**: $30-70 (entrenamiento priorizado, no paralelo)
**Valor**: 5 modelos especializados por rol

### Decisiones Clave

| Decisión | Opción Elegida | Razón |
|----------|----------------|-------|
| **Orden** | **PO → Architect → BA → Dev → QA** | ROI decreciente |
| **Método** | **SFT (BA/PO/Arch/QA) + DPO (Dev)** | Infraestructura existente |
| **LoRA** | rank=32, alpha=64 | Balance VRAM vs calidad |
| **Quantization** | GGUF Q4_K_M | VRAM eficiente + Ollama |

### Tareas (9 tareas)

#### F3-T1: Remediar PO student (QUICK WIN)
```
STATUS: [ ] PENDING
DEPENDENCIES: Distilabel datasets (F2)
OUTPUT: PO-v2 con score >= 0.841
ACTIONS:
  1. Filtrar teacher dataset: score >= 0.85 (de 319 → ~200)
  2. Ajustar hyperparams:
     - epochs: 3 → 4
     - lr: 1e-4 → 8e-5
     - warmup: 0% → 5%
  3. Retrain con train_po_lora.py
  4. Evaluar vs baseline (0.841)
COST: <$5 GPU
FILES MODIFIED:
  - scripts/train_po_lora.py
  - docs/po_distillation_report.md
TIMEFRAME: 1-2 días (no bloquea otras fases)
```

#### F3-T2: Unificar infraestructura training
```
STATUS: [ ] PENDING
DEPENDENCIES: F3-T1 (aprendizajes)
OUTPUT: Script unificado train_role.py
INTERFACE:
  python training/scripts/train_role.py \
    --role ba \
    --method sft \
    --dataset training/datasets/ba_synthetic \
    --lora-rank 32 \
    --epochs 3
FILES TO CREATE:
  - training/scripts/train_role.py       ← Unificado
  - training/scripts/merge_adapter.py    ← LoRA merge
  - training/scripts/quantize_gguf.py    ← Cuantización
```

#### F3-T3: Fine-tune BA-v1
```
STATUS: [ ] PENDING
DEPENDENCIES: F3-T2 + F2 (BA dataset)
OUTPUT: BA-v1 fine-tuned modelo
DATASET: 85 reales + sintéticos → ~300 total
MODEL: Qwen2.5-7B
METHOD: SFT (LoRA, rank=32, epochs=3)
TARGET: >30% pass@1 (+15% vs baseline)
COST: ~$8
TIMELINE: 3-4 horas entrenamiento
```

#### F3-T4: Fine-tune Architect-v1 (PRIORIDAD)
```
STATUS: [ ] PENDING
DEPENDENCIES: F3-T3 + F2 (Architect con CoT)
OUTPUT: Architect-v1 con razonamiento
DATASET: 600+ exemplos con CoT (de 16)
MODEL: Qwen2.5-14B (capacidad para arquitectura)
METHOD: SFT (LoRA, rank=64, alpha=128, epochs=5)
TARGET: >80% acceptance rate (ADR quality, trade-offs)
COST: ~$15-20
TIMELINE: 5-8 horas entrenamiento
CRITICAL: Este rol FALLÓ antes. CoT es clave.
```

#### F3-T5: Fine-tune Dev-v1 y QA-v1
```
STATUS: [ ] PENDING
DEPENDENCIES: F3-T4 + F2 (datasets)

DEV-v1:
  DATASET: Rollouts existentes + sintéticos (1000+)
  MODEL: DeepSeek-Coder-7B o Qwen2.5-14B
  METHOD: DPO (infraestructura existente)
  TARGET: pass@1 > 20% en held-out
  COST: ~$20-25

QA-v1:
  DATASET: 300+ ejemplos generados (de 3)
  MODEL: Qwen2.5-7B
  METHOD: SFT (LoRA)
  TARGET: >85% bug detection rate
  COST: ~$8

Gate: No entrenar QA si baseline <10% en eval offline
```

#### F3-T6: Pipeline cuantización + deploy
```
STATUS: [ ] PENDING
DEPENDENCIES: F3-T5 (todos los modelos entrenados)
OUTPUT: Modelos en Ollama listos para usar
PROCESS:
  1. Merge LoRA adapter → base model
  2. Cuantizar GGUF (Q4_K_M para VRAM eficiente)
  3. Crear Modelfile por rol
  4. ollama create agnostic-pipeline/ba-v1
COST: <$5 (computación local, no GPU)
FILES TO CREATE:
  - training/deploy/modelfiles/*.Modelfile (5 files)
  - training/deploy/register_ollama.sh
```

#### F3-T7: Evaluation framework
```
STATUS: [ ] PENDING
DEPENDENCIES: F3-T6 (modelos cuantizados)
OUTPUT: Held-out test sets + reportes
STRUCTURE:
  - training/evaluation/test_sets/ba_held_out.jsonl    (never used in training)
  - training/evaluation/test_sets/architect_held_out.jsonl
  - training/evaluation/test_sets/dev_held_out.jsonl
  - training/evaluation/test_sets/qa_held_out.jsonl
  - training/evaluation/evaluator.py
METRICS:
  - pass@1, pass@8 (code generation)
  - ADR quality (Architect)
  - Requirement completeness (BA)
  - Bug detection rate (QA)
GATES:
  ✓ +5% pass@1 vs baseline
  ✓ -3% pass@8 máximo degradation
  ✓ Latencia +20% máximo
```

#### F3-T8: Integrar con config.yaml
```
STATUS: [ ] PENDING
DEPENDENCIES: F3-T7
OUTPUT: Modelos especializados usables por pipeline
CONFIG:
  specialized_models:
    enabled: true
    fallback_to_base: true
    models:
      ba:
        base: qwen2.5:7b
        specialized: agnostic-pipeline/ba-v1
      architect:
        base: qwen2.5:14b
        specialized: agnostic-pipeline/architect-v1
      ... (otros roles)
FILES MODIFIED:
  - config.yaml
  - scripts/llm.py (model selection logic)
```

#### F3-T9: Makefile targets
```
STATUS: [ ] PENDING
DEPENDENCIES: F3-T8
TARGETS:
  - make train ROLE=ba METHOD=sft
  - make evaluate ROLE=ba
  - make quantize ROLE=ba QUANT=Q4_K_M
  - make deploy ROLE=ba
  - make train-all                    ← Sequential por costo
FILES MODIFIED:
  - Makefile
  - CLAUDE.md
```

### Archivos Fase 3 (12 nuevos, 4 modificados)

```
NEW (scripts):
  training/scripts/train_role.py              ← Unificado (crítico)
  training/scripts/merge_adapter.py
  training/scripts/quantize_gguf.py

NEW (evaluation):
  training/evaluation/evaluator.py            ← Role-specific eval
  training/evaluation/test_sets/ba_held_out.jsonl
  training/evaluation/test_sets/architect_held_out.jsonl
  training/evaluation/test_sets/dev_held_out.jsonl
  training/evaluation/test_sets/qa_held_out.jsonl

NEW (deploy):
  training/deploy/modelfiles/ba.Modelfile
  training/deploy/modelfiles/architect.Modelfile
  training/deploy/modelfiles/dev.Modelfile
  training/deploy/modelfiles/qa.Modelfile
  training/deploy/register_ollama.sh

NEW (tests):
  tests/test_training_train_role.py
  tests/test_training_evaluation.py
  tests/test_training_quantization.py

MODIFIED:
  scripts/llm.py                      ← Specialized model loading
  scripts/train_po_lora.py            ← Hyperparameter fixes
  config.yaml                         ← specialized_models section
  Makefile                            ← train, evaluate, quantize, deploy
  docs/po_distillation_report.md      ← Updated results
```

### Timeline de Entrenamiento (Secuencial para costo)

```
GPU Session #1: PO remediation
  ├─ Task: Retrain PO-v2
  ├─ GPU: A100 40GB
  ├─ Tiempo: 2-3h
  └─ Costo: ~$4

GPU Session #2: Architect-v1 (PRIORITARIO)
  ├─ Task: Fine-tune Architect-v1 con CoT
  ├─ GPU: A100 80GB (14B model)
  ├─ Tiempo: 6-8h
  └─ Costo: ~$15-20

GPU Session #3: BA-v1 + Dev-v1
  ├─ Task1: BA-v1 (3-4h)
  ├─ Task2: Dev-v1 (4-5h)
  ├─ GPU: A100 40GB
  └─ Costo: ~$12-15

GPU Session #4: QA-v1
  ├─ Task: QA-v1 SFT
  ├─ GPU: A100 40GB
  ├─ Tiempo: 2-3h
  └─ Costo: ~$4

TOTAL TRAINING: ~15-21h GPU
COSTO: ~$35-55 (más overhead = $40-70 total)
```

---

## FASE 4: Integración y Publicación Comunitaria

**Duración**: ~1 semana
**GPU**: No requerida
**Costo**: $0
**Valor**: Framework listo para comunidad

### Tareas (4 tareas)

#### F4-T1: Documentación para la comunidad
```
STATUS: [ ] PENDING
DEPENDENCIES: F3 completada
DELIVERABLES:
  - README actualizado (RAG + Distilabel + Fine-tuning sections)
  - docs/GETTING_STARTED_RAG.md
  - docs/GETTING_STARTED_FINETUNING.md
  - docs/ADR_*.md (2-3 architecture decisions)
  - Diagramas Mermaid actualizados
```

#### F4-T2: Publicación en HuggingFace
```
STATUS: [ ] PENDING
DEPENDENCIES: F3 completada + F4-T1
ARTIFACTS:
  - Datasets:
    ├─ agnostic-pipeline/ba-synthetic-v1
    ├─ agnostic-pipeline/architect-synthetic-v1
    ├─ agnostic-pipeline/dev-synthetic-v1
    ├─ agnostic-pipeline/qa-synthetic-v1
    └─ agnostic-pipeline/po-synthetic-v1

  - Modelos:
    ├─ agnostic-pipeline/ba-v1 (GGUF)
    ├─ agnostic-pipeline/architect-v1 (GGUF)
    ├─ agnostic-pipeline/dev-v1 (GGUF)
    └─ agnostic-pipeline/qa-v1 (GGUF)

LICENSING:
  - Code: Apache 2.0
  - Models: Apache 2.0 (si base model lo permite)
  - Datasets: CC-BY-4.0
```

#### F4-T3: Demo end-to-end
```
STATUS: [ ] PENDING
DEPENDENCIES: F4-T2
DELIVERABLES:
  - make demo CONCEPT="..."
    └─ Ejecuta pipeline completo (BA→PO→Arch→Dev→QA)
        con RAG + modelos fine-tuned

  - Comparativa automática:
    ├─ Baseline (sin fine-tune, sin RAG)
    ├─ + Fine-tuned
    ├─ + RAG
    └─ + Fine-tuned + RAG

  - Reporte de calidad (HTML/Markdown)
```

#### F4-T4: CI/CD para training
```
STATUS: [ ] PENDING
DEPENDENCIES: F4-T3
DELIVERABLES:
  - GitHub Actions workflow para tests
  - Workflow para re-training automático (trigger-based)
  - Automated quality gates
  - Model registry en HuggingFace
```

### Archivos Fase 4 (5 nuevos, 5 modificados)

```
NEW (documentation):
  docs/GETTING_STARTED_RAG.md
  docs/GETTING_STARTED_FINETUNING.md
  docs/ADR_graph_rag_choice.md
  docs/ADR_tiered_teacher_strategy.md
  .github/workflows/train-ci.yml       ← CI/CD

MODIFIED:
  README.md                          ← RAG + Fine-tuning sections
  CLAUDE.md                          ← Comandos completos
  Makefile                           ← make demo
  docs/ARCHITECTURE.md               ← Actualizar diagramas
```

---

## Métricas de Éxito Global

| Métrica | Target | Medición | Status |
|---------|--------|----------|--------|
| **Graph RAG hit-rate** | >80% | Top-5 contienen respuesta | [ ] |
| **Graph RAG latency** | <250ms p95 | Local CPU/GPU ligera | [ ] |
| **Graph RAG multi-hop** | >70% | Queries con dependencias | [ ] |
| **Distilabel quality** | >0.85 avg | Auto-eval del teacher | [ ] |
| **BA pass@1** | >30% (+15%) | Held-out concepts | [ ] |
| **Architect acceptance** | >80% | Human eval 20 examples | [ ] |
| **PO remediated** | ≥0.841 | product_owner_metric | [ ] |
| **Dev pass@1** | >20% | Held-out code tasks | [ ] |
| **QA bug detection** | >85% | Held-out test cases | [ ] |
| **Pipeline E2E** | Sin errores | make iteration | [ ] |
| **Costo/ciclo** | <$160 | GPU tracking | [ ] |

---

## Estimación de Recursos

### Tiempo Total por Rol

| Rol | F1-F4 Horas |
|-----|-------------|
| Implementador (Full-time) | 200-250h (~5-6 semanas) |
| DevOps (GPU setup) | 20-30h (~1 semana) |
| QA/Testing | 30-40h (~1 semana) |
| **TOTAL EFFORT** | **250-320h (~1.5-2 meses full-time, o 3-4 part-time)** |

### Dependencias Externas

- ✅ Ollama (ya disponible)
- ✅ LLM models (qwen2.5, deepseek-coder, bge-m3)
- 🔄 GPU rental (RunPod/Vast.ai/Lambda - requiere créditos)
- ✅ Python 3.10+ environment

### Riesgos Críticos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| LightRAG entity extraction imprecisa | Media | Medio | Ajustar max_gleaning, usar modelo >7B |
| Datasets generados con bias | Media | Alto | Diversificar seeds, review humano |
| Fine-tuned models regresan en benchmarks | Media | Alto | Held-out test sets, strict gates |
| GPU rental más caro | Media | Medio | Spot instances, modo tiered |
| LightRAG KG crece demasiado | Baja | Bajo | Parcheo a Neo4j si >1M nodos |

---

## Quick Start - Próximos Pasos

### Esta Semana
- [ ] Leer y aprobar este plan
- [ ] Provisionar GPU rental ($30-50 test)
- [ ] Iniciar F1-T1 (Setup LightRAG)

### Próxima Semana
- [ ] Completar Fase 1 (Graph RAG)
- [ ] Iniciar Fase 2-T1 (Distilabel setup) en GPU

### Mes 1
- [ ] F1 + F2 completas
- [ ] Datasets sintéticos generados

### Mes 2
- [ ] F3 completa (modelos fine-tuned)
- [ ] Iniciar F4 (publicación)

### Mes 3
- [ ] F4 completa
- [ ] Framework listo para comunidad

---

**Documento**: PLAN_implementation_distilabel_finetuning_rag.md
**Estado**: READY FOR REVIEW
**Aprobación pendiente de**: Product Owner / Tech Lead
**Última actualización**: 2026-02-06
