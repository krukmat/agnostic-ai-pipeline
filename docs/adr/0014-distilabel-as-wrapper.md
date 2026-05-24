---
id: ADR-0014
title: Distilabel como wrapper de generación de datos sintéticos
status: accepted
date: 2026-02-06
deciders:
  - Project lead
tags:
  - adr
  - distilabel
  - status/accepted
  - phase/F2
supersedes:
superseded-by:
related:
  - "[[0015-tiered-teacher-model]]"
  - "[[0016-optional-dependencies-per-phase]]"
  - "[[0017-phase2a-local-first-mock]]"
  - "[[0018-cost-guards-mandatory]]"
---

# ADR-0014 — Distilabel como wrapper de generación de datos sintéticos

## Context

Para fine-tunear modelos abiertos por rol (BA, PO, Architect, Dev, QA) se
necesita un pipeline de generación de datos sintéticos que sea reproducible,
con caching de resultados parciales, retry en llamadas al teacher model y
exportación directa a HuggingFace Hub. La alternativa era scripts Python custom
como los ya existentes (`scripts/generate_po_teacher_dataset.py`).

## Decision

Usar **Distilabel** (`distilabel>=1.0`) como framework de orquestación de la
generación sintética. Distilabel envuelve la lógica de steps (CoT generation,
quality filter, format validation) y gestiona checkpointing, retry y exportación
a HuggingFace. Un pipeline por rol hereda de `BasePipeline`:

```
training/pipelines/
  base_pipeline.py    ← clase base con checkpoint + retry
  ba_pipeline.py
  po_pipeline.py
  architect_pipeline.py
  dev_pipeline.py
  qa_pipeline.py
```

## Consequences

**Pros**
- Checkpointing automático: un pipeline interrumpido retoma desde el último batch.
- Retry nativo en llamadas al teacher model sin código custom.
- Exportación directa a HuggingFace Hub con metadata estructurada.
- Reutilización de steps comunes (`cot_generator`, `quality_filter`, `format_validator`).

**Cons / Trade-offs**
- Dependencia externa adicional (`requirements-training.txt`); no en el baseline (ver [[0016-optional-dependencies-per-phase]]).
- API de Distilabel cambia entre versiones; requiere pin de versión.
- El modo GPU (`distilabel` con vLLM) no se testeó en Fase 2A (ver [[0017-phase2a-local-first-mock]]).

**Neutral**
- Los scripts custom existentes (`generate_po_teacher_dataset.py`) se mantienen como referencia pero no se extienden.

## Alternatives Considered

- **Scripts Python custom** — descartado: no tienen checkpointing; un run de 12h interrumpido pierde todo el progreso.
- **LangChain pipelines** — descartado: overhead de dependencias sin beneficio sobre Distilabel para este caso.
- **Axolotl data generation** — descartado: orientado a fine-tuning, no a generación de datasets sintéticos con quality gates.

## References

- Plan: `PLAN_implementation_distilabel_finetuning_rag.md` §D1, §FASE 2
- Código: `training/pipelines/`, `training/steps/`
- Docs: `docs/DISTILABEL_USAGE.md`, `docs/DISTILABEL_TROUBLESHOOTING.md`
- ADRs relacionados: [[0015-tiered-teacher-model]], [[0016-optional-dependencies-per-phase]], [[0017-phase2a-local-first-mock]]
