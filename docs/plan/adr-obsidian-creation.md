# Plan: ADR Vault en formato Obsidian

**Fecha de creación:** 2026-05-24
**Estado:** Draft — Pendiente aprobación
**Autor:** Claude (sesión interactiva)
**Documento de tareas asociado:** [../tasks/adr-obsidian-creation.md](../tasks/adr-obsidian-creation.md)

---

## 1. Objetivo

Crear un conjunto consolidado de **Architecture Decision Records (ADRs)** en formato compatible con **Obsidian** (frontmatter YAML + `[[wikilinks]]` + MOC) que documente las decisiones arquitectónicas reales tomadas en `agnostic-ai-pipeline` desde su inicio hasta hoy.

El objetivo no es planificar trabajo nuevo, sino **rescatar y formalizar** decisiones que hoy viven dispersas en:
- Planes de implementación (ej. `PLAN_implementation_distilabel_finetuning_rag.md` de 1155 líneas).
- Reportes de auditoría (`PHASE2A_AUDITORY.MD`, `AUDIT_PHASE1_GRAPH_RAG*.md`).
- Lecciones aprendidas (`MEMORY.md`, `CC_TD.md`).
- Commits y código (sin documento dedicado).

Resultado esperado: cualquier persona (o yo en 6 meses) puede abrir el vault, navegar el grafo y entender el **por qué** detrás de cada decisión sin leer 5000 líneas de planes.

## 2. Alcance

### Incluido
- 1 plantilla reutilizable (`_template.md`).
- 1 MOC (`README.md`) como índice navegable.
- 1 migración del ADR-0001 existente al nuevo formato (sin cambio semántico).
- 19 ADRs nuevos extraídos de la historia del proyecto.

### Excluido
- Cambios de código en el repo.
- Refactor de planes existentes (los planes seguirán existiendo; los ADRs los complementan, no los reemplazan).
- Decisiones sobre Fase 3 (fine-tuning) que aún no se tomaron — no se documenta lo que no se decidió.
- Limpieza de deuda documental (109 markdowns en raíz) — ése es un plan separado.

## 3. Decisiones de diseño

### D1 — Formato Obsidian sobre MADR plano
**Decisión:** Frontmatter YAML con campos `id, title, status, date, deciders, tags, supersedes, superseded-by, related, phase` + cuerpo Markdown con `[[wikilinks]]`.

**Por qué:** El ADR-0001 actual es MADR plano. Migrar permite (a) renderizado nativo del grafo en Obsidian, (b) búsqueda por tags, (c) trazabilidad supersedes/superseded-by automática, (d) cross-referencing sin paths frágiles.

**Trade-off:** Pierde compatibilidad estricta con MADR canónico. Aceptado: el vault es interno, no contractual.

### D2 — Numeración 4 dígitos secuencial
**Decisión:** `0001`, `0002`, … `0099`. Se preserva el `0001` ya emitido.

**Por qué:** Convención dominante. Permite ordenamiento alfabético = orden cronológico.

### D3 — Status enumerado fijo
**Decisión:** `proposed | accepted | deprecated | superseded`.

**Por qué:** Refleja ciclo de vida real de un ADR. `superseded-by` apunta al ADR que lo reemplaza.

### D4 — Una decisión por ADR
**Decisión:** Si un plan tiene 7 decisiones (caso `PLAN_implementation_distilabel_finetuning_rag.md` con D1..D7), se generan 7 ADRs separados.

**Por qué:** El valor de un ADR es la atomicidad — permite supersession granular. Mezclar decisiones en un solo doc reproduce el problema que estamos resolviendo.

### D5 — Longitud máxima ~80 líneas por ADR
**Decisión:** Si el contexto requiere más profundidad, se enlaza al plan original con `[[...]]`.

**Por qué:** Un ADR es un contrato corto, no un manual. La profundidad va en docs satelitales.

### D6 — Tags consistentes
**Decisión:** Vocabulario controlado de tags:
- Dominio: `core-pipeline`, `graph-rag`, `distilabel`, `fine-tuning`, `a2a`, `quality`, `process`
- Status (redundante con frontmatter, útil para búsqueda): `status/accepted`, `status/deprecated`
- Fase: `phase/F1`, `phase/F2`, `phase/F3`, `phase/F4`

**Por qué:** Permite queries Dataview en Obsidian sin parsear texto libre.

### D7 — MOC en `docs/adr/README.md`
**Decisión:** Un único índice agrupado por dominio, con descripción de una línea por ADR.

**Por qué:** GitHub renderiza `README.md` automáticamente al entrar al directorio. Obsidian lo trata como nota normal. Doble propósito.

## 4. Archivos afectados

### Nuevos (22 archivos)

```
docs/adr/_template.md                                    [NEW]
docs/adr/README.md                                       [NEW]
docs/adr/0002-provider-agnostic-llm-client.md            [NEW]
docs/adr/0003-cli-subprocess-bridging.md                 [NEW]
docs/adr/0004-multi-role-pipeline.md                     [NEW]
docs/adr/0005-a2a-http-protocol.md                       [NEW]
docs/adr/0006-architect-complexity-tiers.md              [NEW]
docs/adr/0007-tdd-enforcement-dev-role.md                [NEW]
docs/adr/0008-iteration-snapshot-immutability.md         [NEW]
docs/adr/0009-graph-rag-lightrag-choice.md               [NEW]
docs/adr/0010-graph-rag-local-stores.md                  [NEW]
docs/adr/0011-graph-rag-embedding-bge-m3.md              [NEW]
docs/adr/0012-graph-rag-per-role-retrieval.md            [NEW]
docs/adr/0013-graph-rag-config-single-source.md          [NEW]
docs/adr/0014-distilabel-as-wrapper.md                   [NEW]
docs/adr/0015-tiered-teacher-model.md                    [NEW]
docs/adr/0016-optional-dependencies-per-phase.md         [NEW]
docs/adr/0017-phase2a-local-first-mock.md                [NEW]
docs/adr/0018-cost-guards-mandatory.md                   [NEW]
docs/adr/0019-cyclomatic-complexity-gate.md              [NEW]
docs/adr/0020-mock-externals-only.md                     [NEW]
docs/plan/adr-obsidian-creation.md                       [NEW — este doc]
docs/tasks/adr-obsidian-creation.md                      [NEW]
```

### Modificados (1 archivo)

```
docs/adr/0001-logging-and-status-schema.md              [MIGRATED — frontmatter agregado]
```

## 5. Dependencias entre módulos / decisiones

Las dependencias relevantes son **semánticas entre ADRs**, no de código:

```
0002 (Provider-agnostic LLM)
  ├── 0003 (CLI subprocess bridging) — depende de 0002
  └── 0004 (Multi-role pipeline) — usa 0002

0005 (A2A HTTP) — independiente, ortogonal a 0004
0006 (Complexity tiers) — refina 0004
0007 (TDD enforcement) — refina 0004 (rol Dev)
0008 (Snapshot immutability) — refina 0004 (artifacts/)

0009 (LightRAG choice)
  ├── 0010 (Local stores) — implementación de 0009
  ├── 0011 (bge-m3) — implementación de 0009
  ├── 0012 (Per-role retrieval) — política sobre 0009
  └── 0013 (Config single source) — gobernanza de 0009..0012

0014 (Distilabel wrapper)
  ├── 0015 (Tiered teacher) — refina 0014
  ├── 0017 (Phase 2A local-first) — refina 0014
  └── 0018 (Cost guards) — refina 0014

0016 (Optional deps per phase) — transversal

0019 (CC ≤ 5 + CI gate) — proceso transversal
0020 (Mock externals only) — proceso transversal, deriva de 0019
```

Estas dependencias se materializan en el campo `related:` del frontmatter de cada ADR.

## 6. Fuentes primarias por ADR

| ADR | Fuente principal |
|---|---|
| 0001 (existente) | `docs/adr/0001-logging-and-status-schema.md` |
| 0002, 0003 | `scripts/llm.py`, `CLAUDE.md` §Architecture, §Provider-Specific Setup |
| 0004 | `CLAUDE.md` §Workflow, `AGENTS.md` |
| 0005 | `a2a/`, `CLAUDE.md` §A2A Framework |
| 0006 | `CLAUDE.md` §Workflow State, `scripts/run_architect.py` |
| 0007 | `CLAUDE.md` §Important Constraints (TDD by Default) |
| 0008 | `CLAUDE.md` §Important Constraints (Artifact Immutability) |
| 0009 | `PLAN_implementation_distilabel_finetuning_rag.md` §D3 |
| 0010 | Plan §FASE 1 (tabla Decisiones Clave) |
| 0011 | Plan §D4 |
| 0012 | Plan §F1-T4 (tabla policies) |
| 0013 | `MEMORY.md` §3 Configuration Management, `graph_rag/config.py` |
| 0014 | Plan §D1 |
| 0015 | Plan §D2, §Evaluación de viabilidad |
| 0016 | Plan §D6 |
| 0017 | `PHASE2A_AUDITORY.MD`, `docs/PHASE2A_COMPLETION.md` |
| 0018 | Plan §D7 |
| 0019 | `MEMORY.md` §1, `CC_TD.md`, `DD_CC_REFACTOR.md`, commit `f298161` |
| 0020 | `MEMORY.md` §2 (Mock Philosophy, AP-2) |

## 7. Criterios de aceptación globales

1. ✅ Los 22 archivos nuevos existen en `docs/adr/`.
2. ✅ ADR-0001 conserva su contenido original; sólo gana frontmatter.
3. ✅ Cada ADR tiene frontmatter parseable (YAML válido).
4. ✅ Cada ADR tiene al menos un `[[wikilink]]` saliente (excepto los puramente transversales).
5. ✅ `docs/adr/README.md` (MOC) lista los 20 ADRs agrupados por dominio.
6. ✅ Ninguna referencia `[[...]]` apunta a archivo inexistente.
7. ✅ Ningún ADR supera 100 líneas (incluido frontmatter).
8. ✅ Vocabulario de tags consistente con D6.
9. ✅ Commit final con mensaje conventional (`docs(adr): …`) — pendiente aprobación explícita del usuario.

## 8. Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| ADR demasiado terso pierde matiz | Media | Cada ADR linkea al plan original con `[[wikilink]]` |
| Decisiones que el usuario querría documentar quedan fuera | Media | Esta lista se valida con el usuario **antes** de escribir |
| Decisiones cambiaron y el ADR queda obsoleto | Baja | Status `deprecated` + `superseded-by` cubre el caso |
| Frontmatter no parsea en Obsidian | Baja | T1 (template) valida el formato antes de replicar 19 veces |
| Confusión con docs ya existentes (PHASE4_*, AUDIT_*) | Media | MOC nota explícita: "ADRs documentan decisiones; planes documentan ejecución" |

## 9. Out of scope explícito

- **No** se borra ningún archivo existente.
- **No** se modifica código fuera de `docs/`.
- **No** se ejecutan tests (los ADRs son docs, no código).
- **No** se hace commit ni push hasta aprobación final.
- **No** se decide la "Ruta A/B/C" del análisis previo — ese es plan separado.
