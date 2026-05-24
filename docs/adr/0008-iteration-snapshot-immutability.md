---
id: ADR-0008
title: Snapshots de iteración son inmutables
status: accepted
date: 2025-10-18
deciders:
  - Project lead
tags:
  - adr
  - core-pipeline
  - quality
  - status/accepted
  - phase/NA
supersedes:
superseded-by:
related:
  - "[[0004-multi-role-pipeline]]"
  - "[[0001-logging-and-status-schema]]"
---

# ADR-0008 — Snapshots de iteración son inmutables

## Context

Cada ejecución de `make iteration` produce artefactos en
`artifacts/iterations/<name>/`. Sin política de inmutabilidad, reruns sobrescriben
resultados anteriores, imposibilitando comparar iteraciones, hacer rollback o
auditar regresiones entre corridas.

## Decision

Los directorios `artifacts/iterations/<name>/` son write-once: nunca se modifican
retroactivamente. Cada nuevo run produce un snapshot con timestamp único.
El archivo `artifacts/iterations/<name>/summary.json` es el artefacto canónico
de cierre de cada iteración.

```
artifacts/iterations/
  my-feature-20260209-143022/
    summary.json          ← inmutable una vez escrito
    requirements.yaml
    stories.yaml
    qa_report.json
  my-feature-20260209-160015/   ← re-run → nuevo snapshot
    ...
```

`make clean` elimina `artifacts/` (no las iteraciones) sin tocar `artifacts/iterations/`.
`make clean FLUSH=1` es la única operación que elimina iteraciones, y es explícita.

## Consequences

**Pros**
- Reproducibilidad: cualquier iteración pasada es reconstruible.
- Comparación entre runs: `diff artifacts/iterations/v1/ artifacts/iterations/v2/`.
- Auditoría: `summary.json` registra resultado, stories y métricas de cada ciclo.

**Cons / Trade-offs**
- Acumulación de artefactos en disco (mitigado por `make clean FLUSH=1` cuando se necesita).
- El usuario debe referenciar iteraciones por timestamp, no por "la última".

**Neutral**
- `artifacts/dev/` y `artifacts/qa/` no son inmutables (se sobreescriben por story).

## Alternatives Considered

- **Sobrescribir el snapshot anterior** — descartado: pierde historial, dificulta debugging de regresiones.
- **Git para versionar artefactos** — descartado: artefactos son grandes y binarios/YAML generados; no aporta valor en git history.

## References

- Código: `scripts/orchestrate.py` (lógica de snapshot)
- CLAUDE.md §Important Constraints (Artifact Immutability)
- ADRs relacionados: [[0004-multi-role-pipeline]], [[0001-logging-and-status-schema]]
