---
id: ADR-0020
title: Mockear solo dependencias externas; testear internos con integración real
status: accepted
date: 2026-02-07
deciders:
  - Project lead
tags:
  - adr
  - quality
  - process
  - status/accepted
  - phase/NA
supersedes:
superseded-by:
related:
  - "[[0019-cyclomatic-complexity-gate]]"
  - "[[0007-tdd-enforcement-dev-role]]"
---

# ADR-0020 — Mockear solo dependencias externas; testear internos con integración real

## Context

La auditoría AP-2 de Graph RAG encontró tests que mockeaban el engine de
LightRAG internamente. Estos tests pasaban aunque el contrato real de la
interfaz estaba roto — el mock devolvía lo que el test esperaba, no lo que
el engine real devolvería. El problema se detectó solo al correr integración
con Ollama real. Tests "verdes" generaban falsa confianza.

## Decision

Política de mocking con dos niveles:

**Solo mockear:**
- Ollama / LLM endpoints HTTP (latencia, costo, no disponibles en CI).
- Filesystem I/O cuando se testea lógica que no depende de archivos reales.
- APIs externas (HuggingFace Hub, GCP, etc.).

**Nunca mockear:**
- Engines internos (`GraphRAGEngine`, `retrieval.py`, `ingestion.py`).
- Lógica de negocio de los roles.
- Contratos entre módulos del propio proyecto.

Markers de pytest para separar niveles:
```python
@pytest.mark.unit        # mocks de externos; < 5 s por test
@pytest.mark.integration # dependencias reales (Ollama); 5–30 s
@pytest.mark.smoke       # sanity checks rápidos
@pytest.mark.slow        # > 30 s; excluidos de CI por defecto
```

Regla adicional: **≥ 1 test E2E por feature crítico** — ingest → query →
verificar resultado real. Sin E2E, los mocks pueden enmascarar regresiones
de integración.

## Consequences

**Pros**
- Los tests de integración detectan bugs de contrato que los mocks no ven.
- La separación por markers permite correr solo tests rápidos en CI y tests lentos en pre-merge.
- E2E obligatorio previene el patrón "tests verdes, producción rota".

**Cons / Trade-offs**
- Tests de integración requieren Ollama corriendo; no son "pure unit tests".
- Mayor tiempo de ejecución en la suite completa (mitigado con markers).

**Neutral**
- `training/llm_mock.py` es una excepción válida: mockea el teacher LLM en Fase 2A precisamente porque el real no está disponible localmente (ver [[0017-phase2a-local-first-mock]]).

## Alternatives Considered

- **Mockear todo para máxima velocidad** — descartado: AP-2 demostró que produce falsa confianza.
- **Sin mocks, solo integración** — descartado: imposible en CI sin Ollama ni GPU; demasiado lento para feedback en desarrollo.

## References

- Auditoría: `AUDIT_PHASE1_GRAPH_RAG.md` §AP-2
- Memoria: `MEMORY.md` §2 Testing Strategy
- Tests: `tests/test_graph_rag_*.py` (ejemplos del patrón correcto)
- ADRs relacionados: [[0019-cyclomatic-complexity-gate]], [[0007-tdd-enforcement-dev-role]], [[0017-phase2a-local-first-mock]]
