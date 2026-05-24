---
id: ADR-NNNN
title: <Título corto, una línea, modo declarativo>
status: proposed
date: YYYY-MM-DD
deciders:
  - <Nombre o rol>
tags:
  - adr
  - <dominio: core-pipeline | graph-rag | distilabel | fine-tuning | a2a | quality | process>
  - status/proposed
  - phase/<F1 | F2 | F3 | F4 | NA>
supersedes:
superseded-by:
related:
  - "[[NNNN-otro-adr]]"
---

<!--
Plantilla ADR — Agnostic AI Pipeline
====================================
Convenciones (ver docs/plan/adr-obsidian-creation.md §D):
  - 1 decisión por ADR. Si hay más, dividir.
  - Cuerpo ≤ 80 líneas idealmente, ≤ 100 hard limit.
  - Status fijo: proposed | accepted | deprecated | superseded
  - Tags: vocabulario controlado (ver MOC en docs/adr/README.md).
  - Linkear ADRs relacionados con [[NNNN-slug]] (sin .md).
  - Citar código con [[scripts/archivo.py]] o ruta Markdown estándar.
-->

# ADR-NNNN — <Título>

## Context

<Qué problema/fuerza/restricción motiva esta decisión. 3-6 líneas máximo.
Si el contexto es extenso, linkear al plan o doc fuente: [[PLAN_nombre]] §Sección.>

## Decision

<Qué se decidió, en imperativo. Una afirmación clara y verificable.
Si aplica, incluir snippet mínimo de código/config que materialice la decisión.>

## Consequences

**Pros**
- <Beneficio concreto 1>
- <Beneficio concreto 2>

**Cons / Trade-offs**
- <Costo aceptado 1>
- <Costo aceptado 2>

**Neutral**
- <Efecto secundario observable, ni bueno ni malo>

## Alternatives Considered

- **<Alternativa A>** — <Por qué se descartó, en una línea>
- **<Alternativa B>** — <Por qué se descartó>

## References

- Plan: [[PLAN_nombre_relativo_al_vault]] §Sección
- Código: `path/to/file.py:LINE`
- Commits: `hash1`, `hash2`
- Issues/PRs: #N
- ADRs relacionados: [[NNNN-otro-adr]]
