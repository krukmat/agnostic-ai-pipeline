# Plan de Implementación: Distilabel + Fine-Tuning + RAG

**Objetivo**: Implementar los tres pilares faltantes del framework para convertir `agnostic-ai-pipeline` en un framework comunitario 100% open-source.

**Fecha de creación**: 2026-02-06
**Estado**: Draft - Pendiente aprobación
**Prerrequisitos**: Documentos previos revisados (rag_concept_architecture.md, PLAN_open_models_finetuning.md, PLAN_synthetic_data_frameworks.md, PLAN_open_models_ADDENDUM_lessons_learned.md)

## Evaluación de viabilidad técnica (revisión 2026-02-06)

### Veredicto
**Viable**, pero el draft original sobreestima infraestructura (Qwen2.5-72B + A100 80GB como baseline) y subestima costo operativo total. Se recomienda un enfoque escalonado para minimizar costo sin bloquear calidad.

### Ajustes clave aplicados en este documento
1. **Teacher model por capas (cost-aware)**:
   - Baseline: Qwen2.5-14B/32B para generación masiva.
   - Escalado selectivo a 72B solo para casos difíciles o muestras de alto valor.
2. **Dependencias opcionales por fase** (no inflar `requirements.txt` base):
   - `requirements-rag.txt`
   - `requirements-training.txt`
3. **Orden de ejecución optimizado por costo**:
   - Quick wins sin GPU primero (PO remediation + RAG mínimo viable)
   - Distilabel/Fine-tuning por rol priorizado (no entrenar 5 roles de una vez).
4. **Objetivos de rendimiento realistas**:
   - Ajuste de latencia target para Graph RAG en modo `mix`.
5. **Estimación económica revisada**:
   - Se reduce el rango esperado de un ciclo inicial mediante estrategia híbrida y gates de calidad por lote.

---

## Inventario de Infraestructura Existente

### Lo que YA existe (no reimplementar)

| Componente | Ubicación | Madurez | Notas |
|------------|-----------|---------|-------|
| LLM Client agnóstico | `scripts/llm.py` (892 líneas) | **Alta** | Soporta 6 providers, async, retry |
| Teacher dataset generation | `scripts/generate_po_teacher_dataset.py` | **Alta** | Funciona con Gemini 2.5 Pro |
| LoRA training | `scripts/train_po_lora.py` | **Alta** | PEFT/Transformers, 4-bit quant |
| Student evaluation | `scripts/eval_po_student.py` | **Alta** | Métricas pass@k |
| DPO/ORPO pipeline | `post_training/scripts/` | **Alta** | Rollouts → Preferences → Train |
| Architect dataset gen | `scripts/generate_architect_dataset.py` | **Media** | Funcional pero datasets insuficientes |
| Pipeline completo | `scripts/run_*.py` | **Alta** | BA→PO→Arch→Dev→QA funcional |
| A2A protocol | `a2a/` | **Alta** | HTTP agent protocol |
| Model recommender | `src/recommend/model_recommender.py` | **Media** | RoRF routing |
| Config system | `config.yaml` | **Alta** | Per-role provider/model mapping |

### Lo que NO existe (implementar)

| Componente | Prioridad | Complejidad | Dependencias |
|------------|-----------|-------------|--------------|
| **Distilabel pipelines** | Alta | Media | `distilabel>=1.4`, GPU rental |
| **Teacher abierto (Qwen2.5-72B)** | Alta | Baja | Adaptar scripts existentes |
| **Graph RAG: LightRAG integration** | Alta | Media | `lightrag-hku`, Ollama |
| **Graph RAG: Ingestion pipeline** | Alta | Media | LightRAG |
| **Graph RAG: Agent integration** | Media | Baja | LightRAG + LLM Client |
| **Graph RAG: Retrieval adapter** | Media | Baja | LightRAG |
| **Datasets expandidos** (QA, Architect) | Alta | Media | Teacher + Distilabel |
| **PO student remediation** | Alta | Baja | Hyperparameter tuning |

### Datasets actuales (insuficientes para fine-tuning)

| Rol | Ejemplos | Mínimo requerido | Gap |
|-----|----------|-------------------|-----|
| BA | 85 (ba_train_plus_more.jsonl) | 500 | -415 |
| PO | 319 (teacher dataset) | 400 | -81 |
| Architect | 16 (gold_v2) | 600 | -584 |
| Dev | ~rollouts (infraestructura DPO) | 1000 | ~-1000 |
| QA | 3 | 300 | -297 |

---

## Decisiones de Diseño

### D1: Distilabel vs Scripts Custom

**Decisión**: **Distilabel como wrapper de los scripts existentes**

Justificación:
- Los scripts custom ya funcionan y tienen lógica domain-specific (validators, metrics)
- Distilabel aporta: caching, retry, progress, HuggingFace integration, reproducibilidad
- La comunidad conoce Distilabel → adopción más fácil
- Migrar de Gemini → Qwen2.5-72B requiere cambios de cualquier manera

**Enfoque híbrido**:
```
Distilabel Pipeline (orquestación)
  └── Steps custom (lógica de negocio existente)
       └── Validators existentes (post_training/src/posttrain/validators.py)
```

### D2: Teacher Model (ajustado para costo)

**Decisión**: **Estrategia tiered teacher**
- Tier 1 (default): **Qwen2.5-14B-Instruct** o **Qwen2.5-32B-Instruct**
- Tier 2 (selectivo): **Qwen2.5-72B-Instruct** solo para hard prompts / data de alto impacto

Justificación:
- Mantiene stack 100% open-source
- Reduce costo GPU en generación masiva
- Permite usar 72B donde sí agrega valor (Architect/QA edge-cases)
- Compatible con Distilabel + vLLM

**Regla práctica**:
- Generar 70-85% del dataset con 14B/32B
- Regenerar únicamente muestras de baja calidad con 72B

### D3: Graph RAG en lugar de Vector RAG

**Decisión**: **LightRAG** (HKUDS) — Knowledge Graph + Vector hybrid

Justificación (por qué Graph RAG en vez de vector puro):
- Los artefactos del pipeline tienen **relaciones naturales**: requirements → stories → architecture → code → tests
- Las decisiones arquitectónicas (ADRs) se referencian entre sí — un grafo captura esto, un vector no
- Los agentes producen artefactos que **se conectan semánticamente**: PO valida lo que BA genera, Architect descompone, Dev implementa, QA verifica
- Graph RAG responde preguntas **multi-hop**: "¿qué historias dependen del componente X que fue diseñado por la decisión Y?"
- Vector RAG solo encuentra documentos similares, Graph RAG entiende **relaciones causales**

Justificación (por qué LightRAG específicamente):

| Criterio | LightRAG | MS GraphRAG | ChromaDB (vector) | Neo4j |
|----------|----------|-------------|-------------------|-------|
| **Token cost** | **6000x menor** | 610K/query | N/A | N/A |
| **Latencia** | ~80ms | Alta | ~50ms | ~200ms |
| **Local-first** | **NetworkX + NanoVectorDB** | Complejo | SQLite | Requiere JVM server |
| **Ollama nativo** | **Sí** | No | No | No |
| **Auto KG construction** | **Sí** (extrae entidades/relaciones) | Sí | No | Manual |
| **Licencia** | **MIT** | MIT | Apache 2.0 | GPL/AGPL |
| **Retrieval modes** | **5** (naive/local/global/hybrid/mix) | 2 | 1 (vector) | Cypher queries |
| **Dependencias** | Ligeras | Pesadas | Media | JVM + server |
| **Paper académico** | **EMNLP 2025** | Microsoft Research | No | No |

LightRAG es un **strict upgrade** sobre ChromaDB: provee **tanto** graph **como** vector retrieval en un solo framework, sin servidor adicional.

**Componentes internos de LightRAG**:
```
LightRAG
├── Knowledge Graph (NetworkX)     ← Entidades + relaciones extraídas automáticamente
├── Vector Store (NanoVectorDB)    ← Embeddings de chunks (similar a ChromaDB)
├── Entity Extraction (LLM-based)  ← Usa el LLM para construir el grafo
├── Retrieval Modes
│   ├── naive     → Solo vector similarity (como ChromaDB)
│   ├── local     → Entidades cercanas en el grafo
│   ├── global    → Comunidades/clusters del grafo
│   ├── hybrid    → local + global combinados
│   └── mix       → graph + vector combinados (RECOMENDADO)
└── LLM Cache (built-in)          ← Reduce costos de re-extraction
```

### D4: Embedding Model

**Decisión**: **bge-m3** via Ollama

Justificación:
- Recomendado por LightRAG para máxima compatibilidad
- Open source, 1024 dimensiones, multilingüe
- Ejecutable en Ollama: `ollama pull bge-m3`
- Superior a nomic-embed para multilingual (nuestros prompts mezclan ES/EN)
- Sin dependencia de APIs externas

**Alternativa**: `nomic-embed-text-v1.5` (768 dims, más ligero si se necesita menos RAM)

### D5: Orden de Implementación (ajustado)

**Decisión**: **Quick wins primero**, luego RAG base, luego Distilabel/Fine-tuning por prioridad

Orden recomendado:
1. PO remediation (quick win, costo casi cero)
2. Graph RAG mínimo viable
3. Distilabel por rol prioritario (Architect/QA primero por gap)
4. Fine-tuning incremental por impacto

Justificación:
- Genera valor medible temprano sin alquiler GPU prolongado
- Evita producir datos sintéticos para roles que quizá no lo necesiten aún
- Reduce riesgo de gastar en entrenamiento antes de validar retrieval/contexto

### D6: Gestión de dependencias

**Decisión**: separar dependencias por dominio en lugar de cargar todo en `requirements.txt`.

Justificación:
- Menor fricción en entorno local/CI
- Menos conflictos de versiones (vLLM, distilabel, lightrag)
- Instalaciones más rápidas y baratas en runners

---

## Fases de Implementación

### FASE 1: Graph RAG con LightRAG
**Duración estimada**: ~2 semanas
**GPU requerida**: No (solo CPU local + Ollama)
**Costo**: $0

#### Objetivo
Implementar Graph RAG usando LightRAG para que cada agente acceda a un **knowledge graph** del proyecto que captura entidades, relaciones y contexto estructurado de artifacts, decisiones y código.

#### Por qué Graph RAG > Vector RAG para este proyecto

```
VECTOR RAG (ChromaDB/FAISS):
  Query: "¿Qué componente implementa autenticación?"
  → Busca chunks similares por embedding → Retorna fragmentos de texto sueltos
  → NO entiende relaciones entre componentes

GRAPH RAG (LightRAG):
  Query: "¿Qué componente implementa autenticación?"
  → Busca en Knowledge Graph → Encuentra:
    [AuthService] --implements--> [S3: User Authentication]
    [S3] --depends_on--> [S1: Database Setup]
    [S3] --designed_by--> [ADR-002: JWT vs Session]
    [AuthService] --tested_by--> [test_auth.py]
  → Retorna contexto ESTRUCTURADO con relaciones causales
```

#### Tareas

##### F1-T1: Setup LightRAG + dependencias
- [ ] Instalar lightrag-hku con soporte API
- [ ] Pull embedding model en Ollama (bge-m3)
- [ ] Verificar compatibilidad con venv existente
- [ ] Smoke test: insertar documento, query, verificar KG

**Dependencias nuevas**:
```
lightrag-hku[api]>=1.0.0     # Graph RAG framework (MIT license)
# Dependencias internas de LightRAG:
#   - networkx (graph store, local, sin servidor)
#   - nano-vectordb (vector store, local, sin servidor)
#   - ollama (LLM + embeddings)
```

**Setup Ollama**:
```bash
ollama pull bge-m3            # Embedding model (1024 dims, multilingual)
# LLM para entity extraction: usa el modelo ya configurado por rol
```

**Archivos afectados**:
- `requirements-rag.txt` — agregar `lightrag-hku[api]>=1.0.0`

##### F1-T2: Implementar wrapper GraphRAG sobre LightRAG
- [ ] Crear módulo `graph_rag/`
- [ ] Implementar wrapper que configura LightRAG con Ollama
- [ ] Implementar ingestion de artifacts del pipeline
- [ ] Implementar retrieval con modo configurable por rol
- [ ] Tests unitarios

**Archivos a crear**:
```
graph_rag/
├── __init__.py
├── engine.py             # LightRAG engine wrapper (singleton)
├── ingestion.py          # Ingest pipeline artifacts into KG
├── retrieval.py          # Retrieval adapter for agents
└── config.py             # Graph RAG configuration

tests/
├── test_graph_rag_engine.py
├── test_graph_rag_ingestion.py
└── test_graph_rag_retrieval.py
```

**Diseño del engine wrapper**:
```python
# graph_rag/engine.py
from lightrag import LightRAG, QueryParam
from lightrag.llm.ollama import ollama_model_complete, ollama_embed

class GraphRAGEngine:
    """
    Wrapper sobre LightRAG configurado para el pipeline.
    Construye un Knowledge Graph automáticamente a partir de documentos.
    Soporta 5 modos de retrieval: naive, local, global, hybrid, mix.
    """

    _instance = None

    def __init__(self, config: dict):
        self.config = config
        self.rag = LightRAG(
            working_dir=config.get("working_dir", "./artifacts/graph_rag"),
            llm_model_func=ollama_model_complete,
            llm_model_name=config.get("llm_model", "qwen2.5-coder:7b"),
            llm_model_max_async=4,
            embedding_func=ollama_embed,
            embedding_model_name=config.get("embedding_model", "bge-m3"),
            embedding_dim=config.get("embedding_dim", 1024),
            chunk_token_size=config.get("chunk_token_size", 1200),
            entity_extract_max_gleaning=config.get("max_gleaning", 1),
            enable_llm_cache=True,   # Reduce costos de re-extraction
        )

    async def initialize(self):
        """Required initialization before use."""
        await self.rag.initialize_storages()

    async def ingest(self, text: str):
        """Insert document into the Knowledge Graph."""
        await self.rag.ainsert(text)

    async def query(self, question: str, mode: str = "mix") -> str:
        """
        Query the Knowledge Graph.

        Modes:
        - naive:  Vector similarity only (like ChromaDB)
        - local:  Nearby entities in the graph
        - global: Community/cluster summaries
        - hybrid: local + global combined
        - mix:    graph + vector combined (RECOMMENDED)
        """
        return await self.rag.aquery(
            question,
            param=QueryParam(
                mode=mode,
                top_k=self.config.get("top_k", 60),
                response_type="Multiple Paragraphs",
                only_need_context=False,  # Return full response
            )
        )

    async def get_context_only(self, question: str, mode: str = "mix") -> str:
        """Retrieve context without LLM generation (for prompt injection)."""
        return await self.rag.aquery(
            question,
            param=QueryParam(
                mode=mode,
                top_k=self.config.get("top_k", 60),
                only_need_context=True,  # Raw context, no generation
            )
        )

    async def finalize(self):
        """Cleanup resources."""
        await self.rag.finalize_storages()

    @classmethod
    def instance(cls, config: dict = None):
        if cls._instance is None and config:
            cls._instance = cls(config)
        return cls._instance
```

##### F1-T3: Implementar ingestion pipeline para artifacts
- [ ] Ingest planning/ (requirements, stories, architecture, ADRs)
- [ ] Ingest project/ (código generado, tests)
- [ ] Ingest artifacts/ (QA reports, iteration summaries)
- [ ] Ingest docs/ (distillation reports, plans)
- [ ] Incremental ingestion (solo archivos nuevos/modificados)
- [ ] Tests unitarios

**Diseño**:
```python
# graph_rag/ingestion.py
from pathlib import Path
import hashlib

class PipelineIngestion:
    """
    Ingests pipeline artifacts into LightRAG Knowledge Graph.
    LightRAG automatically extracts entities and relationships.
    """

    CONTENT_TYPES = {
        "planning": ["*.yaml", "*.md"],
        "code": ["*.py", "*.js", "*.ts"],
        "artifacts": ["*.json", "*.yaml", "*.md"],
        "docs": ["*.md"],
    }

    def __init__(self, engine: GraphRAGEngine):
        self.engine = engine
        self.ingested_hashes = self._load_ingested_hashes()

    async def ingest_all(self):
        """Ingest all pipeline sources."""
        await self.ingest_directory("planning/", "planning")
        await self.ingest_directory("project/", "code")
        await self.ingest_directory("artifacts/", "artifacts")
        await self.ingest_directory("docs/", "docs")

    async def ingest_directory(self, path: str, content_type: str):
        """Ingest files with dedup (only new/modified)."""
        patterns = self.CONTENT_TYPES.get(content_type, ["*"])
        base = Path(path)
        if not base.exists():
            return

        for pattern in patterns:
            for file in base.rglob(pattern):
                if file.is_file():
                    content = file.read_text(errors="ignore")
                    file_hash = hashlib.md5(content.encode()).hexdigest()

                    if file_hash not in self.ingested_hashes:
                        # Prepend metadata header for better entity extraction
                        tagged = (
                            f"[Source: {file}] [Type: {content_type}]\n\n"
                            f"{content}"
                        )
                        await self.engine.ingest(tagged)
                        self.ingested_hashes[file_hash] = str(file)

    async def ingest_artifact(self, artifact_text: str, metadata: dict):
        """Ingest a single agent artifact (called after each pipeline step)."""
        tagged = (
            f"[Agent: {metadata.get('role', 'unknown')}] "
            f"[Step: {metadata.get('step', 'unknown')}]\n\n"
            f"{artifact_text}"
        )
        await self.engine.ingest(tagged)
```

**Valor clave del Graph RAG**: Cuando LightRAG ingiere `stories.yaml`, automáticamente extrae:
- Entidades: `S1: Database Setup`, `S3: User Authentication`, `AuthService`
- Relaciones: `S3 --depends_on--> S1`, `S3 --acceptance_criteria--> "JWT tokens"`
- Estas relaciones permiten queries multi-hop que vector RAG no puede hacer

##### F1-T4: Implementar retrieval adapter para agentes
- [ ] Crear adapter que los agentes llamen para obtener contexto
- [ ] Soportar modos por rol (mix para Architect, naive para BA)
- [ ] Soportar `only_need_context=True` para prompt injection
- [ ] Budget management (limitar tokens de contexto)
- [ ] Tests unitarios

**Diseño**:
```python
# graph_rag/retrieval.py
class AgentRetriever:
    """
    Retrieval adapter for pipeline agents.
    Each role gets a configured retrieval policy.
    """

    ROLE_POLICIES = {
        "ba": {
            "mode": "mix",        # Graph + vector para requirements existentes
            "top_k": 30,
            "context_only": True,  # Solo contexto, no generación
        },
        "product_owner": {
            "mode": "mix",
            "top_k": 40,
            "context_only": True,
        },
        "architect": {
            "mode": "hybrid",     # Graph-heavy para relaciones arquitectónicas
            "top_k": 60,
            "context_only": True,
        },
        "dev": {
            "mode": "local",      # Local entities para código específico
            "top_k": 40,
            "context_only": True,
        },
        "qa": {
            "mode": "mix",        # Full context para testing
            "top_k": 50,
            "context_only": True,
        },
    }

    def __init__(self, engine: GraphRAGEngine):
        self.engine = engine

    async def retrieve_for_role(self, role: str, query: str) -> str:
        """Retrieve context appropriate for the agent's role."""
        policy = self.ROLE_POLICIES.get(role, {"mode": "mix", "top_k": 30})

        if policy.get("context_only"):
            return await self.engine.get_context_only(
                question=query,
                mode=policy["mode"]
            )
        else:
            return await self.engine.query(
                question=query,
                mode=policy["mode"]
            )
```

##### F1-T5: Integrar Graph RAG con LLM Client existente
- [ ] Modificar `scripts/llm.py` para soportar Graph RAG pre-processing
- [ ] Agregar configuración Graph RAG en `config.yaml`
- [ ] Auto-ingest artifacts después de cada step del pipeline
- [ ] Tests de integración

**Archivos afectados**:
- `scripts/llm.py` — agregar hook de retrieval en `Client.chat()`
- `config.yaml` — agregar sección `graph_rag:` y per-role config

**Diseño de integración**:
```python
# Modificación a scripts/llm.py - Client.chat()
async def chat(self, system: str, user: str, **kwargs):
    # Graph RAG pre-processing (NUEVO)
    if self._graph_rag_enabled():
        from graph_rag.retrieval import AgentRetriever
        from graph_rag.engine import GraphRAGEngine

        retriever = AgentRetriever(GraphRAGEngine.instance())
        context = await retriever.retrieve_for_role(
            role=self.role,
            query=user
        )
        if context:
            user = (
                f"## Relevant Project Context (from Knowledge Graph)\n\n"
                f"{context}\n\n"
                f"---\n\n"
                f"## Task\n\n"
                f"{user}"
            )

    # Existing LLM call (sin cambios)
    return await self._call_provider(system, user, **kwargs)
```

**Config YAML**:
```yaml
# Agregar a config.yaml
graph_rag:
  enabled: true
  working_dir: "./artifacts/graph_rag"
  llm_model: "qwen2.5-coder:7b"           # Para entity extraction
  embedding_model: "bge-m3"                # Multilingual embeddings
  embedding_dim: 1024
  chunk_token_size: 1200
  top_k: 60
  default_mode: "mix"                      # Graph + vector combined
  auto_ingest: true                        # Ingest artifacts after each step
  sources:
    - "planning/"
    - "project/"
    - "artifacts/"
    - "docs/"

roles:
  architect:
    provider: ollama
    model: qwen2.5-coder:14b
    graph_rag:                              # NUEVO
      enabled: true
      mode: "hybrid"                        # Graph-heavy para arquitectura
      top_k: 60

  dev:
    provider: ollama
    model: deepseek-coder-v2:lite
    graph_rag:                              # NUEVO
      enabled: true
      mode: "local"                         # Entidades locales para código
      top_k: 40
```

##### F1-T6: Crear Makefile targets para Graph RAG
- [ ] `make rag-index` — Construir/actualizar Knowledge Graph
- [ ] `make rag-status` — Mostrar estado del KG (entidades, relaciones, chunks)
- [ ] `make rag-query QUERY="..." MODE=mix` — Query de prueba
- [ ] `make rag-visualize` — Visualizar Knowledge Graph (LightRAG WebUI)
- [ ] Documentar en CLAUDE.md

**Archivos afectados**:
- `Makefile` — agregar targets
- `CLAUDE.md` — documentar comandos

**Bonus**: LightRAG incluye WebUI para visualizar el Knowledge Graph:
```bash
# Visualizar el grafo de conocimiento del proyecto
lightrag-server --working-dir ./artifacts/graph_rag --port 9621
# Abrir http://localhost:9621 para ver entidades y relaciones
```

##### F1-T7: Tests de integración end-to-end Graph RAG
- [ ] Test: ingest planning/ → query entidades → verificar relaciones
- [ ] Test: ingest stories.yaml → query "stories that depend on S1" → verificar graph traversal
- [ ] Test: Graph RAG-enhanced pipeline run (Architect con KG vs sin KG)
- [ ] Benchmark: latency (<100ms p95), memory footprint
- [ ] Test: incremental ingestion (solo archivos nuevos)

**Archivos a crear**:
```
tests/
├── test_graph_rag_integration.py     # End-to-end Graph RAG flow
└── test_graph_rag_pipeline.py        # Pipeline with Graph RAG enabled
```

**Criterio de aceptación Fase 1**:
- [ ] `make rag-index` construye Knowledge Graph sin error
- [ ] `make rag-query QUERY="arquitectura del sistema"` retorna entidades y relaciones relevantes
- [ ] `make rag-query QUERY="qué stories dependen de S1" MODE=hybrid` responde con graph traversal
- [ ] Pipeline con Graph RAG habilitado produce respuestas con contexto estructurado del proyecto
- [ ] Latencia de retrieval < 100ms (p95) — LightRAG benchmark: ~80ms
- [ ] `make rag-visualize` muestra Knowledge Graph del proyecto
- [ ] Todos los tests pasan

---

### FASE 2: Distilabel - Pipeline de Datos Sintéticos
**Duración estimada**: ~2 semanas
**GPU requerida**: Sí (preferible A100/L40S, pero con ejecución híbrida)
**Costo estimado**: $30-90 GPU rental (enfoque tiered)

#### Objetivo
Implementar pipelines Distilabel para generar datos sintéticos de entrenamiento usando estrategia tiered (Qwen2.5-14B/32B + 72B selectivo), reemplazando la dependencia de Gemini (comercial).

#### Tareas

##### F2-T1: Setup Distilabel
- [ ] Instalar distilabel con dependencias vLLM
- [ ] Verificar compatibilidad con entorno existente
- [ ] Crear estructura de directorios para pipelines
- [ ] Tests de importación y smoke test

**Dependencias nuevas**:
```
distilabel[vllm,hf]>=1.4.0
vllm>=0.4.0              # Solo en GPU instance
```

**Archivos a crear**:
```
training/
├── __init__.py
├── pipelines/
│   ├── __init__.py
│   ├── base_pipeline.py          # Pipeline base reutilizable
│   ├── ba_pipeline.py            # BA-specific pipeline
│   ├── po_pipeline.py            # PO-specific pipeline
│   ├── architect_pipeline.py     # Architect with CoT
│   ├── dev_pipeline.py           # Dev code generation
│   └── qa_pipeline.py            # QA test generation
├── steps/
│   ├── __init__.py
│   ├── quality_filter.py         # Custom quality scoring step
│   ├── cot_generator.py          # Chain-of-Thought generation step
│   └── format_validator.py       # Output format validation step
└── configs/
    ├── distilabel_base.yaml      # Base pipeline config
    └── roles/
        ├── ba.yaml
        ├── po.yaml
        ├── architect.yaml
        ├── dev.yaml
        └── qa.yaml
```

##### F2-T2: Implementar pipeline base Distilabel
- [ ] Crear clase `BaseSyntheticPipeline` que integre con scripts existentes
- [ ] Implementar steps custom para quality filtering (reusando `validators.py`)
- [ ] Implementar steps custom para format validation
- [ ] Implementar strategy de generación por lotes: `cheap_pass -> quality_gate -> expensive_regen`
- [ ] Tests unitarios para cada step

**Diseño**:
```python
# training/pipelines/base_pipeline.py
from distilabel.pipeline import Pipeline
from distilabel.llms import vLLM
from distilabel.steps import LoadDataFromDicts
from distilabel.steps.tasks import TextGeneration

class BaseSyntheticPipeline:
    """
    Pipeline base para generación de datos sintéticos.
    Integra Distilabel con validators existentes del proyecto.
    """

    def __init__(self, role: str, teacher_model: str = "Qwen/Qwen2.5-72B-Instruct"):
        self.role = role
        self.teacher = vLLM(model=teacher_model)
        self.config = self._load_role_config()

    def build(self) -> Pipeline:
        with Pipeline(name=f"synthetic-{self.role}") as pipeline:
            # Step 1: Load seed data
            load = LoadDataFromDicts(data=self._get_seeds())

            # Step 2: Generate with teacher
            generate = TextGeneration(
                llm=self.teacher,
                system_prompt=self._get_system_prompt(),
                num_generations=self.config["num_generations"]
            )

            # Step 3: Quality filter (REUSES existing validators)
            quality = QualityFilterStep(
                role=self.role,
                min_score=self.config["min_quality_score"]
            )

            load >> generate >> quality
        return pipeline
```

##### F2-T3: Implementar pipeline Architect con Chain-of-Thought
- [ ] Pipeline específico que genera razonamiento explícito
- [ ] Step de CoT extraction y validación
- [ ] Basado en lecciones de `PLAN_open_models_ADDENDUM_lessons_learned.md`
- [ ] Tests con datos existentes de `architect_train_gold_v2.jsonl`

**Prioridad alta**: Architect es el rol que FALLÓ en fine-tuning previo por:
1. Solo 16 ejemplos gold (insuficiente)
2. Sin chain-of-thought explícito
3. Modelo base (Mistral-7B) insuficiente para arquitectura

##### F2-T4: Implementar pipelines para todos los roles
- [ ] BA pipeline (aumentar de 85 → 500 ejemplos)
- [ ] PO pipeline (migrar de Gemini → Qwen2.5-72B, generar 400+)
- [ ] Dev pipeline (code generation + test-first patterns, 1000+)
- [ ] QA pipeline (edge cases + test design, 300+)
- [ ] Tests por rol

##### F2-T5: Integrar steps custom con validators existentes
- [ ] Adapter de `post_training/src/posttrain/validators.py` para Distilabel steps
- [ ] Reuse de `product_owner_metric` como quality gate
- [ ] Reuse de schema validators para format compliance
- [ ] Tests de integración

**Archivos afectados**:
- `post_training/src/posttrain/validators.py` — referenciar desde Distilabel steps
- `training/steps/quality_filter.py` — wrapper que usa validators existentes

##### F2-T6: Script de ejecución para GPU rentada
- [ ] Script all-in-one para sesión GPU
- [ ] Auto-setup de vLLM + Distilabel
- [ ] Ejecución por rol con checkpoints
- [ ] Auto-shutdown al completar
- [ ] Soporte `--teacher-tier` (14B/32B/72B) y `--regen-failed-only`
- [ ] Documentar proceso de GPU rental

**Archivos a crear**:
```
training/scripts/
├── gpu_session.sh                # Setup + run en GPU rentada
├── run_synthetic_pipeline.py     # CLI para ejecutar pipelines
└── validate_datasets.py          # Validar datasets generados
```

##### F2-T7: Crear Makefile targets para Distilabel
- [ ] `make synthetic-data ROLE=ba` — Generar datos sintéticos
- [ ] `make synthetic-validate ROLE=ba` — Validar dataset generado
- [ ] `make synthetic-stats` — Estadísticas de datasets
- [ ] Documentar en CLAUDE.md

**Archivos afectados**:
- `Makefile` — agregar targets
- `CLAUDE.md` — documentar comandos

##### F2-T8: Tests end-to-end Distilabel
- [ ] Test: pipeline BA genera ≥10 ejemplos (dry run con modelo pequeño)
- [ ] Test: quality filter rechaza ejemplos de baja calidad
- [ ] Test: format validator acepta YAML válido
- [ ] Test: pipeline resume desde checkpoint

**Criterio de aceptación Fase 2**:
- [ ] `make synthetic-data ROLE=ba` genera dataset con ≥100 ejemplos
- [ ] Quality score promedio ≥ 0.85 en dataset generado
- [ ] Pipeline ejecuta en modo híbrido (14B/32B + 72B selectivo) sin errores
- [ ] Datasets publicables en formato HuggingFace
- [ ] Todos los tests pasan

---

### FASE 3: Fine-Tuning con Modelos Abiertos
**Duración estimada**: ~2 semanas
**GPU requerida**: Sí (A100 40-80GB)
**Costo estimado**: $30-70 GPU rental (entrenamiento incremental por rol)

#### Objetivo
Fine-tune modelos especializados por rol usando datasets generados por Distilabel, 100% con modelos abiertos.

#### Tareas

##### F3-T1: Remediar PO student (quick win)
- [ ] Filtrar teacher dataset: solo score ≥ 0.85 (de los 319 records actuales)
- [ ] Ajustar hyperparams: epochs=4, lr=8e-5, warmup=5%
- [ ] Re-entrenar con `scripts/train_po_lora.py` modificado
- [ ] Evaluar: target ≥ 0.841 (baseline actual)
- [ ] Documentar resultados

**Archivos afectados**:
- `scripts/train_po_lora.py` — ajustar hyperparams
- `docs/po_distillation_report.md` — actualizar con resultados

**Por qué primero**: El PO ya tiene 319 records y scripts funcionales. Es el quick win para validar el proceso antes de escalar.

##### F3-T2: Unificar infraestructura de training
- [ ] Crear script unificado de fine-tuning que soporte todos los roles
- [ ] Integrar con datasets de Distilabel (Fase 2)
- [ ] Soportar SFT, DPO, ORPO via config
- [ ] Mantener compatibilidad con `post_training/` existente

**Archivos a crear**:
```
training/scripts/
├── train_role.py                 # Script unificado de training
├── merge_adapter.py              # Merge LoRA adapter con base model
└── quantize_gguf.py              # Cuantización a GGUF para Ollama
```

**Diseño**:
```python
# training/scripts/train_role.py
"""
Unified fine-tuning script for all roles.
Supports: SFT, DPO, ORPO via --method flag.
"""

def train(
    role: str,              # ba, po, architect, dev, qa
    method: str = "sft",    # sft, dpo, orpo
    base_model: str = None, # Auto from config
    dataset_path: str = None,
    output_dir: str = None,
    lora_rank: int = 32,
    lora_alpha: int = 64,
    epochs: int = 3,
    lr: float = 2e-4,
    batch_size: int = 4,
):
    """Train a role-specific model."""
```

##### F3-T3: Fine-tune BA-v1 (baseline con datos existentes + sintéticos)
- [ ] Combinar 85 ejemplos reales + sintéticos de Distilabel
- [ ] Fine-tune Qwen2.5-7B con LoRA
- [ ] Evaluar vs baseline (Qwen2.5-7B sin fine-tune)
- [ ] Cuantizar a GGUF Q4_K_M
- [ ] Registrar en Ollama como `agnostic-pipeline/ba-v1`

##### F3-T4: Fine-tune Architect-v1 (PRIORIDAD - rol que falló)
- [ ] Usar dataset de 600+ ejemplos con CoT (generado en Fase 2)
- [ ] Fine-tune Qwen2.5-14B con LoRA (rank=64, alpha=128)
- [ ] Evaluar: ADR quality, trade-offs, CoT presence
- [ ] Target: >80% acceptance
- [ ] Cuantizar y registrar

##### F3-T5: Fine-tune Dev-v1 y QA-v1
- [ ] Dev: Combinar rollouts (DPO existente) + sintéticos
- [ ] QA: Usar 300+ ejemplos generados por Distilabel
- [ ] Fine-tune con método apropiado (Dev=DPO, QA=SFT)
- [ ] Evaluar y cuantizar
- [ ] Gate de costo: no entrenar rol si no supera baseline en evaluación offline previa

##### F3-T6: Pipeline de cuantización y deploy
- [ ] Script de merge LoRA → base model
- [ ] Script de cuantización GGUF (Q4_K_M, Q5_K_M)
- [ ] Script de registro en Ollama
- [ ] Modelfile templates por rol
- [ ] Tests de inferencia post-deploy

**Archivos a crear**:
```
training/deploy/
├── modelfiles/
│   ├── ba.Modelfile
│   ├── architect.Modelfile
│   ├── dev.Modelfile
│   └── qa.Modelfile
└── register_ollama.sh            # Batch register all models
```

##### F3-T7: Evaluation framework
- [ ] Crear held-out test sets por rol (nunca usados en training)
- [ ] Implementar evaluación automática (pass@k, quality metrics)
- [ ] Quality gates: +5% pass@1, ≤-3% pass@8, ≤+20% latency
- [ ] Reportes comparativos (baseline vs fine-tuned)

**Archivos a crear**:
```
training/evaluation/
├── evaluator.py                  # Role-specific evaluation
├── test_sets/
│   ├── ba_held_out.jsonl
│   ├── architect_held_out.jsonl
│   ├── dev_held_out.jsonl
│   └── qa_held_out.jsonl
└── reports/                      # Auto-generated reports
```

##### F3-T8: Integrar modelos fine-tuned con config.yaml
- [ ] Agregar sección `specialized_models` a config.yaml
- [ ] Implementar fallback: specialized → base model
- [ ] Modificar `scripts/llm.py` para cargar modelos especializados
- [ ] Tests de integración

**Archivos afectados**:
- `config.yaml` — agregar sección `specialized_models:`
- `scripts/llm.py` — lógica de model selection

##### F3-T9: Makefile targets para fine-tuning
- [ ] `make train ROLE=ba METHOD=sft` — Fine-tune por rol
- [ ] `make evaluate ROLE=ba` — Evaluar modelo
- [ ] `make quantize ROLE=ba QUANT=Q4_K_M` — Cuantizar
- [ ] `make deploy ROLE=ba` — Registrar en Ollama
- [ ] `make train-all` — Ciclo completo para todos los roles

**Criterio de aceptación Fase 3**:
- [ ] PO student ≥ 0.841 (baseline) — remediated
- [ ] BA-v1 >10% mejora vs baseline
- [ ] Architect-v1 >80% acceptance rate
- [ ] Todos los modelos funcionan en Ollama localmente
- [ ] Latencia ≤ +20% vs modelos base
- [ ] Todos los tests pasan

---

### FASE 4: Integración y Publicación Comunitaria
**Duración estimada**: ~1 semana
**GPU requerida**: No
**Costo**: $0

#### Tareas

##### F4-T1: Documentación para la comunidad
- [ ] README actualizado con secciones RAG, Distilabel, Fine-tuning
- [ ] Getting Started guide para cada componente
- [ ] Architectural Decision Records (ADRs) para decisiones tomadas
- [ ] Diagramas actualizados

##### F4-T2: Publicación de artifacts
- [ ] Datasets en HuggingFace Hub
- [ ] Modelos fine-tuned en HuggingFace Hub
- [ ] Scripts reproducibles
- [ ] Licenciamiento (Apache 2.0 código, CC-BY-4.0 datos)

##### F4-T3: Demo end-to-end
- [ ] `make demo CONCEPT="..."` — Pipeline completo con RAG + modelos fine-tuned
- [ ] Comparativa automática: base vs fine-tuned vs fine-tuned+RAG
- [ ] Reportes de calidad publicables

##### F4-T4: CI/CD para training
- [ ] GitHub Actions para tests
- [ ] Workflow para re-training automático (trigger-based)
- [ ] Automated quality gates

---

## Dependencias entre Fases

```
FASE 1 (Graph RAG / LightRAG) ────────────────────────────────────┐
  No depende de GPU                                                │
  Valor inmediato: Knowledge Graph del proyecto                    │
  ~10 archivos nuevos (LightRAG reduce código custom)              │
                                                                   ├── FASE 4
FASE 2 (Distilabel) ─── genera datasets ──── FASE 3 (Fine-tune) ──┘
  Requiere GPU (A100/L40S)                    Requiere GPU (A100 40GB)
  Prerequisito de Fase 3                      Usa datasets de Fase 2
```

**Fases 1 y 2 pueden ejecutarse en paralelo** si hay disponibilidad para rentar GPU mientras se desarrolla Graph RAG localmente.

**Sinergia Fase 1 + Fase 3**: Los modelos fine-tuned (Fase 3) producen mejores artifacts → el Knowledge Graph (Fase 1) se enriquece → los agentes obtienen mejor contexto → ciclo virtuoso de mejora.

---

## Resumen de Archivos por Fase

### Fase 1: Graph RAG (~10 archivos nuevos — simplificado gracias a LightRAG)
```
NEW:  graph_rag/__init__.py
NEW:  graph_rag/engine.py           # LightRAG wrapper (singleton, Ollama config)
NEW:  graph_rag/ingestion.py        # Pipeline artifact ingestion with dedup
NEW:  graph_rag/retrieval.py        # Role-based retrieval adapter
NEW:  graph_rag/config.py           # Graph RAG configuration
NEW:  tests/test_graph_rag_engine.py
NEW:  tests/test_graph_rag_ingestion.py
NEW:  tests/test_graph_rag_retrieval.py
NEW:  tests/test_graph_rag_integration.py
NEW:  tests/test_graph_rag_pipeline.py
MOD:  scripts/llm.py              — Graph RAG hook in Client.chat()
MOD:  config.yaml                 — graph_rag: section + per-role config
MOD:  requirements-rag.txt        — lightrag-hku[api]
MOD:  Makefile                    — rag-index, rag-status, rag-query, rag-visualize
MOD:  CLAUDE.md                   — documentar comandos Graph RAG
```

**Nota**: LightRAG reduce significativamente la cantidad de código custom:
- NO se necesita `knowledge_hub/chunkers.py` — LightRAG chunka internamente
- NO se necesita `retrieval_gateway/fusion.py` — LightRAG fusiona graph+vector internamente
- NO se necesita `context_manager/compression.py` — LightRAG maneja contexto
- NO se necesita BM25 separado — LightRAG combina graph traversal + vector similarity

### Fase 2: Distilabel (~15 archivos nuevos)
```
NEW:  training/__init__.py
NEW:  training/pipelines/__init__.py
NEW:  training/pipelines/base_pipeline.py
NEW:  training/pipelines/ba_pipeline.py
NEW:  training/pipelines/po_pipeline.py
NEW:  training/pipelines/architect_pipeline.py
NEW:  training/pipelines/dev_pipeline.py
NEW:  training/pipelines/qa_pipeline.py
NEW:  training/steps/__init__.py
NEW:  training/steps/quality_filter.py
NEW:  training/steps/cot_generator.py
NEW:  training/steps/format_validator.py
NEW:  training/configs/distilabel_base.yaml
NEW:  training/configs/roles/*.yaml (5 files)
NEW:  training/scripts/gpu_session.sh
NEW:  training/scripts/run_synthetic_pipeline.py
NEW:  training/scripts/validate_datasets.py
NEW:  tests/test_distilabel_*.py (3+ files)
MOD:  requirements-training.txt   — distilabel
MOD:  Makefile                    — synthetic-data, synthetic-validate
MOD:  CLAUDE.md                   — documentar comandos
```

### Fase 3: Fine-Tuning (~12 archivos nuevos)
```
NEW:  training/scripts/train_role.py
NEW:  training/scripts/merge_adapter.py
NEW:  training/scripts/quantize_gguf.py
NEW:  training/evaluation/evaluator.py
NEW:  training/evaluation/test_sets/*.jsonl (4 files)
NEW:  training/deploy/modelfiles/*.Modelfile (4 files)
NEW:  training/deploy/register_ollama.sh
NEW:  tests/test_training_*.py (3+ files)
MOD:  scripts/llm.py              — specialized model loading
MOD:  scripts/train_po_lora.py    — hyperparameter fixes
MOD:  config.yaml                 — specialized_models: section
MOD:  Makefile                    — train, evaluate, quantize, deploy
MOD:  docs/po_distillation_report.md — updated results
```

### Fase 4: Integración (~5 archivos)
```
MOD:  CLAUDE.md                   — documentación completa
MOD:  Makefile                    — make demo
NEW:  docs/ADR_*.md (2-3 files)
NEW:  docs/GETTING_STARTED_RAG.md
NEW:  docs/GETTING_STARTED_FINETUNING.md
```

---

## Estimación de Costos Totales

| Fase | GPU | Costo Estimado | Notas |
|------|-----|----------------|-------|
| Fase 1 (RAG) | No | $0 | Solo CPU local |
| Fase 2 (Distilabel) | A100/L40S, ~12-30h | $30-90 | Generación híbrida 14B/32B + 72B selectivo |
| Fase 3 (Fine-tune) | A100 40GB, ~10-20h | $30-70 | Entrenamiento priorizado por rol (no todo en paralelo) |
| Fase 4 (Integración) | No | $0 | Solo documentación |
| **TOTAL** | - | **$60-160** | Ciclo inicial optimizado por costo |

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Qwen2.5-72B no genera calidad suficiente | Baja | Alto | Fallback a Llama-3.1-70B, ajustar prompts |
| LightRAG entity extraction imprecisa | Media | Medio | Ajustar max_gleaning, usar modelo más grande para extraction |
| KG crece demasiado (memory) | Baja | Bajo | LightRAG usa NetworkX on-disk; migrar a Neo4j si >1M nodos |
| Datasets generados con bias | Media | Alto | Diversificar seeds, human-in-the-loop review |
| GPU rental más cara de lo estimado | Media | Medio | Usar spot/preemptible, ventanas nocturnas, regen selectivo |
| Distilabel API breaks entre versiones | Baja | Medio | Pin versión, tests de compatibilidad |
| Fine-tuned models regresan en otros benchmarks | Media | Alto | Held-out test sets, quality gates estrictos |
| Dependencias pesadas rompen entorno base | Media | Medio | Separar requirements por fase + lockfiles |

---

## Métricas de Éxito del Proyecto Completo

| Métrica | Target | Medición |
|---------|--------|----------|
| **Graph RAG retrieval hit-rate** | >80% | Top-5 entidades contienen respuesta relevante |
| **Graph RAG latency** | <250ms p95 (modo `mix`) | Benchmark local CPU/GPU ligera |
| **Graph RAG multi-hop accuracy** | >70% | Queries que requieren graph traversal (e.g., dependencias) |
| **Distilabel dataset quality** | >0.85 avg score | Auto-evaluación del teacher |
| **Fine-tuned BA pass@1** | >30% (+15% vs baseline) | Held-out concepts |
| **Fine-tuned Architect acceptance** | >80% | Human eval 20 examples |
| **Fine-tuned PO** | ≥0.841 (fix regression) | product_owner_metric |
| **Pipeline end-to-end** | Completa sin errores | `make iteration` con modelos fine-tuned + RAG |
| **Costo por ciclo** | <$160 (objetivo inicial) | GPU rental tracking |

---

## Tracking de Progreso

### Fase 1: Graph RAG (LightRAG)
- [ ] F1-T1: Setup LightRAG + dependencias + Ollama bge-m3
- [ ] F1-T2: GraphRAGEngine wrapper (Ollama integration)
- [ ] F1-T3: Ingestion pipeline (planning/, project/, artifacts/, docs/)
- [ ] F1-T4: Retrieval adapter (per-role policies, context_only mode)
- [ ] F1-T5: Integración con LLM Client (scripts/llm.py)
- [ ] F1-T6: Makefile targets (rag-index, rag-query, rag-visualize)
- [ ] F1-T7: Tests E2E Graph RAG (multi-hop queries, pipeline integration)

### Fase 2: Distilabel
- [ ] F2-T1: Setup Distilabel
- [ ] F2-T2: Pipeline base Distilabel
- [ ] F2-T3: Pipeline Architect con CoT
- [ ] F2-T4: Pipelines todos los roles
- [ ] F2-T5: Integración con validators existentes
- [ ] F2-T6: Script GPU rental
- [ ] F2-T7: Makefile targets Distilabel
- [ ] F2-T8: Tests E2E Distilabel

### Fase 3: Fine-Tuning
- [ ] F3-T1: Remediar PO student (quick win)
- [ ] F3-T2: Unificar infraestructura training
- [ ] F3-T3: Fine-tune BA-v1
- [ ] F3-T4: Fine-tune Architect-v1 (PRIORIDAD)
- [ ] F3-T5: Fine-tune Dev-v1 y QA-v1
- [ ] F3-T6: Pipeline cuantización + deploy
- [ ] F3-T7: Evaluation framework
- [ ] F3-T8: Integrar con config.yaml
- [ ] F3-T9: Makefile targets fine-tuning

### Fase 4: Integración
- [ ] F4-T1: Documentación comunidad
- [ ] F4-T2: Publicación HuggingFace
- [ ] F4-T3: Demo end-to-end
- [ ] F4-T4: CI/CD

---

**Estado**: DRAFT - Pendiente aprobación
**Autor**: Architecture
**Fecha**: 2026-02-06
**Documentos relacionados**:
- `rag_concept_architecture.md` — Arquitectura conceptual RAG
- `PLAN_open_models_finetuning.md` — Plan original de fine-tuning
- `PLAN_open_models_ADDENDUM_lessons_learned.md` — Lecciones aprendidas
- `PLAN_synthetic_data_frameworks.md` — Comparativa de frameworks
- `docs/po_distillation_report.md` — Estado actual PO distillation
- `post_training/PROJECT_PLAN.md` — Plan post-training existente
