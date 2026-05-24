---
id: ADR-0009
title: Graph RAG con LightRAG sobre Neo4j y Vector RAG puro
status: accepted
date: 2026-02-06
deciders:
  - Project lead
tags:
  - adr
  - graph-rag
  - status/accepted
  - phase/F1
supersedes:
superseded-by:
related:
  - "[[0010-graph-rag-local-stores]]"
  - "[[0011-graph-rag-embedding-bge-m3]]"
  - "[[0012-graph-rag-per-role-retrieval]]"
  - "[[0013-graph-rag-config-single-source]]"
---

# ADR-0009 — Graph RAG con LightRAG sobre Neo4j y Vector RAG puro

## Context

Los agentes del pipeline (Architect en particular) necesitan contexto
estructurado sobre relaciones causales entre artefactos del proyecto:
¿qué stories dependen de cuáles?, ¿qué decisiones de arquitectura afectan
qué componentes? Un vector RAG puro recupera fragmentos similares pero pierde
estas relaciones. Neo4j las captura pero requiere JVM y operaciones de servidor.

## Decision

Usar **LightRAG** (`lightrag-hku`) como motor de Graph RAG. LightRAG combina
un knowledge graph de entidades/relaciones con un vector store, todo en proceso
local (sin servidor externo). El modo de retrieval por defecto es `mix`
(graph + vector híbrido).

```yaml
# config.yaml
graph_rag:
  enabled: true
  default_mode: mix
  llm_model: mistral:7b-instruct
  embedding_model: bge-m3
```

## Consequences

**Pros**
- Cero dependencias de servidor: graph y vector stores corren en proceso.
- Extracción automática de entidades y relaciones por LightRAG (sin schema manual).
- Retrieval híbrido (graph + vector) en un solo engine, sin orquestar dos sistemas.
- Modo `naive/local/global/hybrid/mix` configurable por rol (ver [[0012-graph-rag-per-role-retrieval]]).

**Cons / Trade-offs**
- No escala a corpus >1M documentos sin migrar a stores externos.
- El knowledge graph se construye on-ingest con un LLM local; calidad depende del modelo de extracción.
- API de LightRAG es menos madura que Neo4j o Qdrant.

**Neutral**
- El WebUI de LightRAG (`localhost:9621`) permite visualizar el grafo sin código adicional.

## Alternatives Considered

- **Neo4j** — descartado: requiere JVM, servidor dedicado y Cypher queries; overkill para proyecto-scope.
- **ChromaDB (vector RAG puro)** — descartado: no captura relaciones entre entidades; Architect pierde dependencias entre stories.
- **Qdrant + NetworkX separados** — descartado: dos sistemas a orquestar, sincronización manual de entidades.

## References

- Plan: `PLAN_implementation_distilabel_finetuning_rag.md` §D3, §FASE 1
- Código: `graph_rag/engine.py`
- Commits: `e46b923`, `6cd7b75`
- ADRs relacionados: [[0010-graph-rag-local-stores]], [[0011-graph-rag-embedding-bge-m3]], [[0012-graph-rag-per-role-retrieval]]
