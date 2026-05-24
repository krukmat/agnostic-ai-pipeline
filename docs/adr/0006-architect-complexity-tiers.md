---
id: ADR-0006
title: Architect auto-clasifica briefs en 3 tiers de complejidad
status: accepted
date: 2025-11-01
deciders:
  - Project lead
tags:
  - adr
  - core-pipeline
  - status/accepted
  - phase/NA
supersedes:
superseded-by:
related:
  - "[[0004-multi-role-pipeline]]"
---

# ADR-0006 — Architect auto-clasifica briefs en 3 tiers de complejidad

## Context

El rol Architect genera stories a partir de `requirements.yaml`. Un brief de
"to-do list" y un brief de "plataforma enterprise multi-tenant" requieren
outputs radicalmente distintos en granularidad y cantidad de stories. Sin
clasificación, o el Architect sobregenera para casos simples (costo, latencia)
o subestima para casos complejos (stories incompletas, QA failures).

## Decision

El Architect clasifica automáticamente el brief en uno de tres tiers usando un
clasificador LLM con fallback heurístico basado en word-count del brief:

| Tier | Criterio orientativo | Stories generadas |
|---|---|---|
| `Simple` | Brief < 100 palabras, feature único | 2–4 stories amplias |
| `Medium` | Brief 100–300 palabras, múltiples features | 5–10 stories |
| `Corporate` | Brief > 300 palabras o términos enterprise | 10–20 stories granulares |

El tier se persiste en `planning/architecture.yaml` y puede sobreescribirse con
`ARCHITECT_TIER=Corporate make plan`.

## Consequences

**Pros**
- Costo y latencia calibrados al tamaño real del proyecto.
- Stories más granulares en proyectos complejos encajan mejor en context window del Dev.
- Override manual disponible sin tocar código.

**Cons / Trade-offs**
- Clasificación LLM puede ser inconsistente en briefs borderline; el fallback word-count es heurístico.
- Un tier incorrecto propaga historias mal calibradas al Dev y QA.

**Neutral**
- La clasificación se registra en `artifacts/` para auditoría posterior.

## Alternatives Considered

- **Tier fijo por proyecto** — descartado: requiere intervención manual en cada uso del pipeline.
- **Solo heurística word-count** — descartado: no capta complejidad semántica (brief corto pero con 10 dominios).
- **Tier definido por el usuario siempre** — descartado: elimina la automatización que da valor al pipeline.

## References

- Código: `scripts/run_architect.py`
- Config: env var `ARCHITECT_TIER`
- Docs: `docs/COMPLEXITY_ANALYZER.md`, `docs/COMPLEXITY_POLICY.md`
- CLAUDE.md §Workflow State Management §Architect Tiers
- ADRs relacionados: [[0004-multi-role-pipeline]]
