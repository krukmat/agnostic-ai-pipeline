---
id: ADR-0013
title: GraphRAGConfig como única fuente de verdad de configuración
status: accepted
date: 2026-02-07
deciders:
  - Project lead
tags:
  - adr
  - graph-rag
  - quality
  - status/accepted
  - phase/F1
supersedes:
superseded-by:
related:
  - "[[0009-graph-rag-lightrag-choice]]"
  - "[[0012-graph-rag-per-role-retrieval]]"
---

# ADR-0013 — GraphRAGConfig como única fuente de verdad de configuración

## Context

Durante la auditoría AP-1 de Graph RAG se detectó **config drift**: defaults
duplicados en `engine.py`, `config.yaml` y `config.py` con valores distintos.
El comportamiento en runtime dependía del orden de carga. `auto_ingest: true`
estaba declarado en config pero sin lógica de implementación (feature falsa).

## Decision

`graph_rag/config.py::GraphRAGConfig.DEFAULT_CONFIG` es la única fuente de
defaults. `config.yaml §graph_rag` solo aplica **overrides**; nunca define
defaults propios. `validate_schema()` se llama obligatoriamente en startup
para detectar valores inválidos antes de la primera query.

```python
# graph_rag/config.py
class GraphRAGConfig:
    DEFAULT_CONFIG = {
        "default_mode": "mix",
        "top_k": 40,
        "embedding_dim": 1024,
        "auto_ingest": False,   # feature no implementada: declarada False
        ...
    }

    def validate_schema(self):
        assert self["top_k"] in range(1, 101), "top_k must be 1-100"
        assert self["default_mode"] in VALID_MODES
```

## Consequences

**Pros**
- Un solo lugar para cambiar un default; sin riesgo de inconsistencia entre archivos.
- `validate_schema()` falla rápido con mensaje claro en lugar de comportamiento silencioso.
- Features no implementadas declaradas explícitamente como `false` — no hay promesas falsas.

**Cons / Trade-offs**
- Cualquier nuevo campo de config requiere actualizar `DEFAULT_CONFIG` además de `config.yaml`.

**Neutral**
- Property accessors (`cfg.llm_model`) garantizan type hints consistentes; preferir sobre `cfg["llm_model"]`.

## Alternatives Considered

- **`config.yaml` como fuente única** — descartado: YAML no tiene type hints ni validación sin código adicional.
- **Pydantic model** — considerado; descartado para esta fase por no querer añadir dependencia; candidato para revisión futura.

## References

- Auditoría: `AUDIT_PHASE1_GRAPH_RAG.md`, `AUDIT_PHASE1_GRAPH_RAG_EXTERNAL_FINDINGS.md`
- Código: `graph_rag/config.py`
- Memoria: `MEMORY.md` §3 Configuration Management
- ADRs relacionados: [[0009-graph-rag-lightrag-choice]], [[0012-graph-rag-per-role-retrieval]]
