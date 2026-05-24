---
id: ADR-0019
title: Cyclomatic Complexity ≤ 5 target con CI gate obligatorio
status: accepted
date: 2026-02-09
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
  - "[[0020-mock-externals-only]]"
  - "[[0003-cli-subprocess-bridging]]"
---

# ADR-0019 — Cyclomatic Complexity ≤ 5 target con CI gate obligatorio

## Context

La auditoría externa AP-1 de Graph RAG detectó funciones con CC extremadamente
alto: `Client.__init__` (CC=61), `_cli_chat_async` (CC=55), `_cli_chat` (CC=53).
Funciones con CC alto son difíciles de testear en aislamiento, propensas a bugs
en paths poco ejercidos y costosas de mantener. La deuda se había acumulado sin
señal de alerta porque no había gate automatizado.

## Decision

Establecer umbrales de CC con enforcement en CI a partir del commit `f298161`:

| Nivel | CC | Acción |
|---|---|---|
| **Target** | ≤ 5 | Ideal para funciones nuevas |
| **Warning** | 6–10 | Revisable; documentar trade-off si se acepta |
| **Blocker** | > 10 | PR bloqueado; requiere refactor o justificación documentada |

Herramienta: `radon cc <file> -n B` (grade B = CC ≤ 10). El gate corre en
`.github/workflows/` en cada PR.

Funciones pre-existentes con CC > 10 en `scripts/llm.py` están documentadas
como deuda técnica explícita en `CC_TD.md` con plan de refactor. No bloquean
el gate porque son anteriores a la política.

**Resultados de refactors aplicados (AP-1):**

| Función | CC antes | CC después | Técnica |
|---|---|---|---|
| `Client.__init__` | 61 | 9 | Extracción de 5 helpers (`_initialize_*`) |
| `_ingest_directory` | 8 | ≤5 | Extracción de `_should_ingest_file`, `_build_file_metadata` |
| `retrieve_for_role` | 6 | ≤5 | Extracción de `_resolve_policy` |

## Consequences

**Pros**
- Feedback inmediato en PR antes de que la deuda se acumule.
- Funciones con CC ≤ 5 son testables con menos mocks y paths más claros.
- La política de extracción de helpers es reproducible y documentada.

**Cons / Trade-offs**
- El gate puede bloquear PRs legítimos con lógica inherentemente compleja (ej. parsers de protocolo); se resuelve con justificación documentada.
- `_cli_chat` / `_cli_chat_async` siguen con CC > 10 como deuda documentada — el gate no los detecta porque están en la lista de exclusiones.

**Neutral**
- CC no mide calidad semántica del código; es una proxy, no un oráculo.

## Alternatives Considered

- **Solo revisión manual en PR** — descartado: la auditoría AP-1 demostró que la deuda se acumula sin gate automatizado.
- **Limite CC ≤ 10 directo** — descartado: demasiado permisivo; target ≤ 5 con warning 6–10 da espacio sin ser dogmático.
- **SonarQube** — descartado: overhead de infraestructura para un proyecto personal.

## References

- Commits: `f298161` (CI gate), `853ad32` (refactor `Client.__init__` 61→9)
- Docs: `CC_TD.md`, `DD_CC_REFACTOR.md`, `REFACTOR_TASK_TREE.md`
- Memoria: `MEMORY.md` §1 Complejidad Ciclomática
- ADRs relacionados: [[0020-mock-externals-only]], [[0003-cli-subprocess-bridging]]
