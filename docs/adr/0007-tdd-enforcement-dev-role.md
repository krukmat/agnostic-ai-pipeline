---
id: ADR-0007
title: TDD enforced por defecto en el rol Dev
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
  - "[[0020-mock-externals-only]]"
---

# ADR-0007 — TDD enforced por defecto en el rol Dev

## Context

El rol Dev implementa stories de forma autónoma. Sin una política explícita,
hay riesgo de que el LLM genere código sin tests (el camino de menor
resistencia) y QA falle en la siguiente etapa. La política TDD alinea al Dev
con el contrato de QA: si no hay tests, QA no puede validar.

## Decision

El rol Dev escribe tests antes de la implementación por defecto. Si la story
no incluye tests al finalizar, el pipeline marca la story como fallida y
reintenta (hasta `DEV_RETRIES=3`). Dos flags de escape explícitos:

- `ALLOW_NO_TESTS=1` — permite stories sin tests (ej. stories de configuración pura).
- `STRICT_TDD=1` — fuerza que los tests fallen antes de la implementación (TDD estricto).

## Consequences

**Pros**
- QA siempre tiene algo que ejecutar; el loop Dev↔QA funciona con datos reales.
- Alineación con el principio CLAUDE.md: "TDD approach. Test first, implement, run tests."
- Los tests generados sirven como especificación ejecutable de la story.

**Cons / Trade-offs**
- LLMs tienden a generar tests triviales o de bajo valor sin guía adicional en el prompt.
- Stories de infraestructura/config no necesitan tests; requieren `ALLOW_NO_TESTS=1` explícito.

**Neutral**
- El prompt del Dev (`prompts/developer.md`) incluye instrucciones TDD; cambiar el comportamiento = editar el prompt.

## Alternatives Considered

- **Tests opcionales** — descartado: en práctica, el LLM omite tests si no son obligatorios.
- **Tests solo si la story los menciona** — descartado: la mayoría de stories no mencionan testing explícitamente.

## References

- Código: `scripts/run_dev.py`
- Config: env vars `ALLOW_NO_TESTS`, `STRICT_TDD`, `DEV_RETRIES`
- Prompts: `prompts/developer.md`
- CLAUDE.md §Important Constraints (TDD by Default)
- ADRs relacionados: [[0004-multi-role-pipeline]], [[0020-mock-externals-only]]
