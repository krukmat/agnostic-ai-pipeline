---
id: ADR-0004
title: Pipeline de 5 roles secuenciales BA→PO→Architect→Dev→QA
status: accepted
date: 2025-10-18
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
  - "[[0002-provider-agnostic-llm-client]]"
  - "[[0005-a2a-http-protocol]]"
  - "[[0006-architect-complexity-tiers]]"
  - "[[0007-tdd-enforcement-dev-role]]"
  - "[[0008-iteration-snapshot-immutability]]"
---

# ADR-0004 — Pipeline de 5 roles secuenciales BA→PO→Architect→Dev→QA

## Context

El objetivo es automatizar el SDLC completo: de un concepto de negocio a código
en producción. La pregunta central fue cómo organizar la inteligencia: ¿un
agente único con muchas herramientas, o roles especializados con prompts
dedicados y artefactos intermedios explícitos?

## Decision

Pipeline de 5 roles con responsabilidades separadas y contrato de artefactos
entre etapas:

| Rol | Input | Output |
|---|---|---|
| BA | `CONCEPT` (texto libre) | `planning/requirements.yaml` |
| PO | `requirements.yaml` | `planning/product_owner_review.yaml` |
| Architect | `requirements.yaml` + review | `planning/stories.yaml`, `architecture.yaml` |
| Dev | `stories.yaml` (una story) | código en `project/` + tests |
| QA | código + tests | `artifacts/qa/<story>/qa_summary.json` |

State machine de stories: `todo → doing → done`. El orquestador (`scripts/orchestrate.py`) coordina el ciclo completo o el sub-loop Dev↔QA.

## Consequences

**Pros**
- Cada rol usa el proveedor/modelo óptimo para su tarea (costo/calidad por etapa).
- Artefactos YAML/JSON son legibles, versionables y depurables.
- Roles reemplazables individualmente sin tocar los demás.
- Soporte para A2A (cada rol como servicio HTTP independiente, ver [[0005-a2a-http-protocol]]).

**Cons / Trade-offs**
- Latencia acumulada: 5 llamadas LLM + I/O en disco por iteración.
- Artefactos intermedios pueden desincronizarse si el pipeline se interrumpe (`make fix-stories` como remedio operacional).
- Stories deben ser granulares para caber en el context window del Dev.

**Neutral**
- Cada rol tiene su propio prompt template en `prompts/*.md`; cambiar comportamiento = editar el prompt, no el código.

## Alternatives Considered

- **Agente único con tool calling** — descartado: un solo context window mezcla BA, arquitectura y código; swap de modelo por etapa imposible.
- **LangGraph / CrewAI** — descartado: dependencia externa que duplica lo que el orquestador ya hace con más control sobre artefactos y retries.
- **Pipeline de 3 roles** (BA+PO merged, Dev+QA merged) — considerado; descartado porque PO y QA aportan perspectiva de validación independiente del generador.

## References

- Código: `scripts/run_*.py`, `scripts/orchestrate.py`, `prompts/`
- Config: `config.yaml` §roles
- CLAUDE.md §Architecture, §Workflow State Management
- ADRs relacionados: [[0005-a2a-http-protocol]], [[0006-architect-complexity-tiers]]
