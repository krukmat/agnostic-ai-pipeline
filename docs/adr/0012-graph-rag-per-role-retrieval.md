---
id: ADR-0012
title: Políticas de retrieval diferenciadas por rol en Graph RAG
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
  - "[[0004-multi-role-pipeline]]"
  - "[[0013-graph-rag-config-single-source]]"
---

# ADR-0012 — Políticas de retrieval diferenciadas por rol en Graph RAG

## Context

Cada rol del [[0004-multi-role-pipeline]] tiene necesidades de contexto
distintas. El Architect necesita traversal profundo del knowledge graph para
ver dependencias entre componentes. El Dev necesita contexto puntual y local.
Un único `mode + top_k` global sub-sirve a unos roles y sobre-carga a otros
con contexto irrelevante.

## Decision

Definir una política `mode + top_k` por rol en `graph_rag/retrieval.py`.
Override por llamada disponible via parámetro opcional.

| Rol | Mode | top_k | Justificación |
|---|---|---|---|
| BA | `mix` | 30 | Necesita panorama general sin profundidad de grafo |
| PO | `mix` | 40 | Validación requiere más contexto que BA |
| Architect | `hybrid` | 60 | Traversal pesado de grafo para detectar dependencias entre stories |
| Dev | `local` | 40 | Contexto puntual de la story en curso; evita ruido global |
| QA | `mix` | 50 | Validación cruzada entre código, tests y requisitos |

```python
# graph_rag/retrieval.py
DEFAULT_POLICIES = {
    "architect": {"mode": "hybrid", "top_k": 60},
    "dev":       {"mode": "local",  "top_k": 40},
    ...
}
```

## Consequences

**Pros**
- Architect recibe el contexto más rico donde más impacta (diseño de dependencias).
- Dev recibe contexto enfocado; reduce tokens enviados al LLM y latencia.
- Override por llamada permite experimentación sin cambiar políticas globales.

**Cons / Trade-offs**
- Políticas son heurísticas: valores `top_k` no se basan en benchmarks formales del corpus real.
- Si el número de roles crece, la tabla de políticas requiere mantenimiento.

**Neutral**
- Las políticas se documentan en `graph_rag/retrieval.py` como `DEFAULT_POLICIES`; son visibles sin abrir `config.yaml`.

## Alternatives Considered

- **Política única global** — descartado: top_k=60 para Dev genera ruido; top_k=30 para Architect pierde dependencias.
- **Política definida en `config.yaml` por el usuario** — complementario, no excluyente; el override ya existe.
- **Aprendizaje automático de top_k** — descartado: overcomplejo para el tamaño del corpus actual.

## References

- Plan: `PLAN_implementation_distilabel_finetuning_rag.md` §F1-T4
- Código: `graph_rag/retrieval.py`
- ADRs relacionados: [[0009-graph-rag-lightrag-choice]], [[0013-graph-rag-config-single-source]]
