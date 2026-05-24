---
id: ADR-0011
title: Embedding model bge-m3 (1024 dims) para Graph RAG
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
  - "[[0009-graph-rag-lightrag-choice]]"
  - "[[0010-graph-rag-local-stores]]"
---

# ADR-0011 — Embedding model bge-m3 (1024 dims) para Graph RAG

## Context

LightRAG necesita un modelo de embeddings para indexar los chunks de texto y
hacer retrieval semántico. El corpus del proyecto mezcla inglés y español
(artefactos YAML, prompts, documentación). La elección del modelo afecta
calidad del retrieval, RAM requerida y latencia de ingestión.

## Decision

Usar **`bge-m3`** via Ollama como modelo de embeddings:

```yaml
# config.yaml
graph_rag:
  embedding_model: bge-m3
  embedding_dim: 1024
```

`bge-m3` se descarga con `ollama pull bge-m3` y corre localmente sin API key.
Dimensión de embedding: 1024.

## Consequences

**Pros**
- Soporte multilingüe nativo (inglés + español del corpus mixto del proyecto).
- 1024 dims captura semántica más rica que modelos de 768 dims.
- Integración directa via Ollama: mismo runtime que los LLMs del pipeline.
- Sin API key ni costo por embedding.

**Cons / Trade-offs**
- Mayor RAM que modelos de 384 o 768 dims.
- Latencia de ingestión más alta vs. modelos más pequeños (trade-off aceptado: ingestión es batch, no tiempo real).

**Neutral**
- Si se migra a un vector store externo (FAISS, Qdrant), la dimensión 1024 es compatible sin cambio de modelo.

## Alternatives Considered

- **`nomic-embed-text` (768 dims)** — descartado: menor dimensionalidad, soporte multilingüe más limitado.
- **`text-embedding-3-small` (OpenAI)** — descartado: requiere API key y costo por token; rompe la premisa local-first.
- **`all-MiniLM-L6` (384 dims)** — descartado: demasiado pequeño para corpus técnico con terminología específica.

## References

- Plan: `PLAN_implementation_distilabel_finetuning_rag.md` §D4
- Config: `config.yaml §graph_rag.embedding_model`
- Código: `graph_rag/config.py` (DEFAULT_CONFIG)
- ADRs relacionados: [[0009-graph-rag-lightrag-choice]], [[0010-graph-rag-local-stores]]
