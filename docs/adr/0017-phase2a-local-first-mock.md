---
id: ADR-0017
title: Fase 2A cerrada en modo local/mock antes de integración GPU real
status: accepted
date: 2026-02-08
deciders:
  - Project lead
tags:
  - adr
  - distilabel
  - process
  - status/accepted
  - phase/F2
supersedes:
superseded-by:
related:
  - "[[0014-distilabel-as-wrapper]]"
  - "[[0015-tiered-teacher-model]]"
  - "[[0018-cost-guards-mandatory]]"
---

# ADR-0017 — Fase 2A cerrada en modo local/mock antes de integración GPU real

## Context

La Fase 2 (Distilabel) requiere acceso a GPU A100/L40S para ejecutar los
teacher models reales (Qwen2.5-14B/32B/72B). Renter GPU sin validar la
arquitectura del pipeline supone riesgo de gastar $30–90 en una corrida que
falla por un bug de integración en el primer batch. Se necesita una estrategia
que permita iterar la arquitectura sin costo de GPU.

## Decision

Dividir la Fase 2 en dos etapas explícitas:

- **Fase 2A (local/dev-first):** Toda la arquitectura de pipelines, steps,
  checkpointing y CLI se implementa y testea con `MockLLM` — un teacher
  simulado que devuelve respuestas deterministas. Se cierra cuando la suite
  de tests pasa y `make synthetic-data ROLE=ba MODE=local NUM_SAMPLES=5` genera
  output válido.

- **Fase 2B (GPU real):** Sustituir `MockLLM` por Qwen2.5 real via vLLM.
  Bloqueada hasta tener acceso a GPU. Estado actual: **pendiente**.

El riesgo P0-R1 (GPU integration no probada) se acepta explícitamente y se
documenta en `PHASE2A_AUDITORY.MD`.

## Consequences

**Pros**
- Arquitectura validada sin gastar GPU; bugs de integración detectados en local.
- La suite de tests (6 passed en Fase 2A) corre en CI sin GPU.
- Fase 2B arranca con confianza en la estructura; solo cambia el backend LLM.

**Cons / Trade-offs**
- `validators_adapter.py` usa heurística de longitud como proxy de calidad (no ML real); aceptado para 2A.
- Las estrategias de regeneración (`cheap_pass → expensive_regen`) no están implementadas en 2A.
- El comportamiento real del pipeline con GPU puede diferir del mock.

**Neutral**
- `MockLLM` queda en `training/llm_mock.py` como fixture reutilizable para tests futuros.

## Alternatives Considered

- **Ir directo a GPU desde el inicio** — descartado: riesgo de $30–90 en una corrida fallida por bug arquitectural.
- **Usar un modelo pequeño local (Qwen2.5-0.5B via Ollama) como mock** — considerado; descartado: requiere descargar modelo grande y añade latencia sin aportar más validación que el mock.

## References

- Auditoría: `PHASE2A_AUDITORY.MD` §P0-R1
- Completion: `docs/PHASE2A_COMPLETION.md`
- Código: `training/llm_mock.py`, `training/pipelines/base_pipeline.py:46-52`
- ADRs relacionados: [[0014-distilabel-as-wrapper]], [[0018-cost-guards-mandatory]]
