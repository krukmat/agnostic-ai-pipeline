---
id: ADR-0010
title: NetworkX + NanoVectorDB como stores locales del Graph RAG
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
  - "[[0011-graph-rag-embedding-bge-m3]]"
---

# ADR-0010 — NetworkX + NanoVectorDB como stores locales del Graph RAG

## Context

[[0009-graph-rag-lightrag-choice]] eligió LightRAG como engine. LightRAG es
configurable en sus backends de almacenamiento: graph store y vector store son
intercambiables. La elección de backend determina dependencias operacionales,
límites de escala y simplicidad de setup.

## Decision

Usar los stores por defecto de LightRAG para entorno local:
- **Graph store**: NetworkX (in-memory, persistido en JSON).
- **Vector store**: NanoVectorDB (fichero local).

Ambos requieren cero infraestructura adicional. El directorio de datos del
graph RAG se configura en `config.yaml §graph_rag.working_dir` y por defecto
apunta a `.graph_rag/` (ignorado en `.gitignore`).

## Consequences

**Pros**
- Setup en un comando: `pip install lightrag-hku` — sin Docker, sin JVM, sin servicios.
- Portabilidad total: mover el directorio de trabajo = mover el knowledge graph.
- Suficiente para el corpus del proyecto (~100–1000 artefactos).

**Cons / Trade-offs**
- NetworkX es in-memory: carga completa del graph en RAM al iniciar.
- NanoVectorDB no soporta búsqueda aproximada eficiente a >100K vectores.
- Migración a FAISS o Neo4j en el futuro requiere re-ingestar todo el corpus.

**Neutral**
- La deduplicación MD5 en `graph_rag/ingestion.py` previene re-ingestión innecesaria al hacer `make rag-index`.

## Alternatives Considered

- **FAISS** — descartado para esta fase: requiere compilación nativa y no mejora el caso de uso a escala del proyecto.
- **Qdrant** — descartado: servidor adicional que rompe la premisa local-first.
- **Neo4j** — descartado: ver [[0009-graph-rag-lightrag-choice]] §Alternatives.

## References

- Plan: `PLAN_implementation_distilabel_finetuning_rag.md` §FASE 1 (tabla Decisiones Clave)
- Código: `graph_rag/engine.py`, `graph_rag/ingestion.py`
- Config: `config.yaml §graph_rag.working_dir`
- ADRs relacionados: [[0009-graph-rag-lightrag-choice]]
