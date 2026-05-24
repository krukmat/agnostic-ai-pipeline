# Tareas: ADR Vault en formato Obsidian

**Fecha de creación:** 2026-05-24
**Estado:** Draft — Pendiente aprobación
**Documento de plan asociado:** [../plan/adr-obsidian-creation.md](../plan/adr-obsidian-creation.md)

---

## Escala de Effort (por CLAUDE.md)

| Level | Reasoning | Aplicable aquí |
|---|---|---|
| S  | Transcripción mecánica, sin inferencia | Plantilla, migración, índice |
| M  | Diseñar contrato corto, anticipar trade-offs | Mayoría de ADRs nuevos |
| L  | Decisiones de arquitectura cross-subsystem | No aplica (esto es documental) |
| XL | Tooling externo iterativo | No aplica |

## Orden de ejecución

**Sprint 1 — Fundación (T1–T2)**
**Sprint 2 — Core Pipeline (T3–T9)**
**Sprint 3 — Graph RAG (T10–T14)**
**Sprint 4 — Distilabel / Fine-Tuning (T15–T19)**
**Sprint 5 — Calidad y Proceso (T20–T21)**
**Sprint 6 — Cierre (T22–T23)**

---

## Tareas

### Sprint 1 — Fundación

#### T1 — Crear plantilla `_template.md`
- **Effort:** S
- **Depende de:** —
- **Output:** `docs/adr/_template.md`
- **Contenido:** Frontmatter completo con todos los campos, secciones vacías (Context, Decision, Consequences, Alternatives Considered, References).
- **Acceptance:** Frontmatter YAML válido; placeholders claramente marcados con `<...>`.
- **Handoff prompt:** "Crear `docs/adr/_template.md` con frontmatter Obsidian (`id, title, status, date, deciders, tags, supersedes, superseded-by, related, phase`) y cuerpo con secciones Context, Decision, Consequences, Alternatives Considered, References. Usar placeholders `<...>` para todos los campos variables."

#### T2 — Migrar ADR-0001 al formato Obsidian
- **Effort:** S
- **Depende de:** T1
- **Output:** `docs/adr/0001-logging-and-status-schema.md` con frontmatter agregado
- **Acceptance:** Contenido original íntegro; frontmatter agregado con `id: ADR-0001`, `status: accepted`, `date: 2025-11-24`, `tags: [adr, quality, process, status/accepted]`, `related: [[0008-iteration-snapshot-immutability]]` (pendiente que T9 exista).
- **Handoff prompt:** "Migrar `docs/adr/0001-logging-and-status-schema.md` agregando frontmatter Obsidian. No tocar el cuerpo. Status `accepted`, date `2025-11-24`, tags `[adr, quality, process, status/accepted, phase/F4]`."

---

### Sprint 2 — Core Pipeline

#### T3 — ADR-0002 Provider-agnostic LLM Client
- **Effort:** M
- **Depende de:** T1
- **Output:** `docs/adr/0002-provider-agnostic-llm-client.md`
- **Fuente:** `scripts/llm.py`, `CLAUDE.md` §Architecture
- **Acceptance:** Documenta los 6 providers soportados (`ollama, openai, codex_cli, claude_cli, vertex_cli, vertex_sdk`); alternativas consideradas (LangChain, LiteLLM); referencia a `[[0003-cli-subprocess-bridging]]`.
- **Handoff prompt:** "Escribir ADR-0002 sobre el cliente LLM unificado en `scripts/llm.py`. Documentar: contexto (necesidad de cambiar proveedor por rol sin tocar código de roles), decisión (clase `Client(role=...)` que resuelve provider desde `config.yaml`), consecuencias (un solo punto de cambio vs. acoplamiento a SDK específico), alternativas (LangChain, LiteLLM). Referenciar `[[0003-cli-subprocess-bridging]]`."

#### T4 — ADR-0003 CLI Subprocess Bridging
- **Effort:** M
- **Depende de:** T3
- **Output:** `docs/adr/0003-cli-subprocess-bridging.md`
- **Fuente:** `scripts/llm.py` (métodos `_cli_chat`, `_cli_chat_async`)
- **Acceptance:** Explica por qué Claude/Codex/Vertex se invocan via subprocess en vez de SDK directo; documenta el contrato JSON I/O; lista las consecuencias (auth delegada a CLI, latencia, parsing frágil).
- **Handoff prompt:** "Escribir ADR-0003 sobre el bridging via subprocess para CLIs externos (claude, codex, gcloud). Decisión: invocar binarios via `subprocess` con JSON o texto, en vez de usar SDKs directos. Razón: auth delegada al CLI del usuario, sin gestión de tokens. Trade-off: parsing frágil documentado en `[[CC_TD]]`."

#### T5 — ADR-0004 Multi-role pipeline BA→PO→Architect→Dev→QA
- **Effort:** M
- **Depende de:** T1
- **Output:** `docs/adr/0004-multi-role-pipeline.md`
- **Fuente:** `CLAUDE.md` §Workflow, `AGENTS.md`
- **Acceptance:** Documenta los 5 roles, sus inputs/outputs (`requirements.yaml → stories.yaml → code → tests → qa_summary.json`), y el state machine `todo→doing→done`. Alternativas: pipeline monolítico, agente único.
- **Handoff prompt:** "ADR-0004: pipeline de 5 roles secuenciales BA→PO→Architect→Dev→QA. Cada rol produce artifact YAML/JSON consumido por el siguiente. Decisión: separación por rol con prompts especializados vs. agente único con tool calling. Razón: roles permiten swap de provider por etapa según costo/calidad."

#### T6 — ADR-0005 A2A HTTP protocol
- **Effort:** M
- **Depende de:** T1
- **Output:** `docs/adr/0005-a2a-http-protocol.md`
- **Fuente:** `a2a/`, `CLAUDE.md` §A2A Framework
- **Acceptance:** Documenta el protocolo agent-to-agent HTTP, los puertos asignados, modos local vs. remote en executors. Alternativa: gRPC, message bus.
- **Handoff prompt:** "ADR-0005 sobre Agent-to-Agent via HTTP/FastAPI. Cada rol puede ejecutarse como servicio en un puerto (BA:8001, Arch:8003, Dev:8004, QA:8005). Decisión: HTTP+JSON sobre gRPC o message bus. Razón: debuggability, curl-friendly, fits Makefile workflow."

#### T7 — ADR-0006 Architect complexity tiers
- **Effort:** M
- **Depende de:** T5
- **Output:** `docs/adr/0006-architect-complexity-tiers.md`
- **Fuente:** `CLAUDE.md` §Workflow State, `scripts/run_architect.py`
- **Acceptance:** Documenta los 3 tiers (Simple/Medium/Corporate); criterios de clasificación (LLM classifier + word-count fallback); efecto sobre cantidad/granularidad de stories.
- **Handoff prompt:** "ADR-0006: Architect auto-clasifica el brief en 3 tiers (Simple/Medium/Corporate) usando LLM classifier con fallback heurístico de word-count. Tier afecta cantidad y profundidad de stories generadas. Referenciar `[[COMPLEXITY_ANALYZER]]`."

#### T8 — ADR-0007 TDD enforcement en rol Dev
- **Effort:** S
- **Depende de:** T5
- **Output:** `docs/adr/0007-tdd-enforcement-dev-role.md`
- **Fuente:** `CLAUDE.md` §Important Constraints
- **Acceptance:** Documenta TDD por defecto; flags de escape (`ALLOW_NO_TESTS`, `STRICT_TDD`); justificación.
- **Handoff prompt:** "ADR-0007 sobre TDD enforcement en Dev. Por defecto Dev escribe test primero. Override via `ALLOW_NO_TESTS=1` o `STRICT_TDD=1`. Razón: alineación con CLAUDE.md `TDD approach. Test first, implement, run tests.`"

#### T9 — ADR-0008 Iteration snapshot immutability
- **Effort:** S
- **Depende de:** T1
- **Output:** `docs/adr/0008-iteration-snapshot-immutability.md`
- **Fuente:** `CLAUDE.md` §Important Constraints (Artifact Immutability)
- **Acceptance:** Documenta política: `artifacts/iterations/<name>/` nunca se modifica retroactivamente; cambios = nuevo snapshot.
- **Handoff prompt:** "ADR-0008: snapshots de iteración en `artifacts/iterations/` son inmutables. Cambios producen nuevo snapshot timestamped, no modifican el anterior. Razón: reproducibilidad y diff entre runs."

---

### Sprint 3 — Graph RAG

#### T10 — ADR-0009 LightRAG sobre Neo4j / Vector RAG
- **Effort:** M
- **Depende de:** T1
- **Output:** `docs/adr/0009-graph-rag-lightrag-choice.md`
- **Fuente:** `PLAN_implementation_distilabel_finetuning_rag.md` §D3
- **Acceptance:** Trade-offs explícitos: Neo4j (JVM, ops cost), ChromaDB (sin relaciones), LightRAG (graph + vector híbrido local). Linkea `[[0010, 0011, 0012, 0013]]`.
- **Handoff prompt:** "ADR-0009 sobre elegir LightRAG (graph+vector híbrido) sobre Neo4j (descartado por JVM/ops) o ChromaDB (descartado por no soportar relaciones). Refs `[[PLAN_implementation_distilabel_finetuning_rag]]` §D3."

#### T11 — ADR-0010 NetworkX + NanoVectorDB local stores
- **Effort:** M
- **Depende de:** T10
- **Output:** `docs/adr/0010-graph-rag-local-stores.md`
- **Acceptance:** Justifica local-first; alternativas FAISS, Qdrant; trade-off escalabilidad vs. simplicidad operacional.
- **Handoff prompt:** "ADR-0010: stores locales (NetworkX para graph, NanoVectorDB para vector). Razón: cero dependencias de servidor, dev-first. Trade-off: no escala a >1M docs, aceptable para proyecto-scope."

#### T12 — ADR-0011 Embedding bge-m3 (1024 dims)
- **Effort:** S
- **Depende de:** T10
- **Output:** `docs/adr/0011-graph-rag-embedding-bge-m3.md`
- **Fuente:** Plan §D4
- **Acceptance:** Justifica bge-m3 sobre nomic-embed (768 dims) y otros; refs a Ollama tag.
- **Handoff prompt:** "ADR-0011: embedding `bge-m3` (1024 dims) vs `nomic-embed-text` (768). Razón: mejor recall multilingüe y dimensión más expresiva. Costo: ligeramente más RAM."

#### T13 — ADR-0012 Per-role retrieval policies
- **Effort:** M
- **Depende de:** T10
- **Output:** `docs/adr/0012-graph-rag-per-role-retrieval.md`
- **Fuente:** Plan §F1-T4, `graph_rag/retrieval.py`
- **Acceptance:** Tabla con `mode + top_k` por rol (BA mix/30, PO mix/40, Architect hybrid/60, Dev local/40, QA mix/50). Justifica por qué Architect usa más contexto (60).
- **Handoff prompt:** "ADR-0012: políticas de retrieval por rol. Tabla con role/mode/top_k. Architect usa hybrid+top_k=60 porque necesita ver dependencias del knowledge graph completo. Dev usa local+40 porque trabaja contexto puntual."

#### T14 — ADR-0013 GraphRAGConfig single source of truth
- **Effort:** S
- **Depende de:** T10
- **Output:** `docs/adr/0013-graph-rag-config-single-source.md`
- **Fuente:** `MEMORY.md` §3, `graph_rag/config.py`
- **Acceptance:** Documenta `DEFAULT_CONFIG` como canónico; `config.yaml` solo overrides; `validate_schema()` obligatorio.
- **Handoff prompt:** "ADR-0013: `GraphRAGConfig.DEFAULT_CONFIG` es fuente única. `config.yaml` aplica overrides, nunca defaults. `validate_schema()` obligatorio en startup. Razón: evitar drift como ocurría pre-AP-1."

---

### Sprint 4 — Distilabel / Fine-Tuning

#### T15 — ADR-0014 Distilabel como wrapper
- **Effort:** M
- **Depende de:** T1
- **Output:** `docs/adr/0014-distilabel-as-wrapper.md`
- **Fuente:** Plan §D1
- **Acceptance:** Justifica Distilabel sobre scripts custom (caching, retry, HF integration); referencia `training/pipelines/`.
- **Handoff prompt:** "ADR-0014: usar Distilabel como wrapper de generación sintética en lugar de scripts custom. Pros: caching, retry, HuggingFace integration. Cons: dependencia externa adicional."

#### T16 — ADR-0015 Tiered teacher model
- **Effort:** M
- **Depende de:** T15
- **Output:** `docs/adr/0015-tiered-teacher-model.md`
- **Fuente:** Plan §D2, §Evaluación de viabilidad
- **Acceptance:** Documenta Qwen2.5-14B/32B baseline + 72B selectivo. Cifras de costo: $60-160 vs $125-250 original.
- **Handoff prompt:** "ADR-0015: teacher model escalonado. Default Qwen2.5-14B/32B para 70% del volumen. Escalado a 72B solo para casos difíciles o muestras de alto valor. Reduce costo de ciclo de $125-250 a $60-160."

#### T17 — ADR-0016 Optional dependencies por fase
- **Effort:** S
- **Depende de:** T1
- **Output:** `docs/adr/0016-optional-dependencies-per-phase.md`
- **Fuente:** Plan §D6
- **Acceptance:** Documenta `requirements-rag.txt`, `requirements-training.txt`; razón: no inflar base.
- **Handoff prompt:** "ADR-0016: dependencias opcionales por fase. `requirements-rag.txt` (lightrag-hku, etc), `requirements-training.txt` (peft, trl, etc). Razón: usuarios que sólo usan el pipeline base no necesitan ~3GB de wheels de training."

#### T18 — ADR-0017 Phase 2A local/mock-first
- **Effort:** M
- **Depende de:** T15
- **Output:** `docs/adr/0017-phase2a-local-first-mock.md`
- **Fuente:** `PHASE2A_AUDITORY.MD`, `docs/PHASE2A_COMPLETION.md`
- **Acceptance:** Documenta estrategia: implementar pipelines y tests con MockLLM antes de comprometer GPU. Refs P0-R1.
- **Handoff prompt:** "ADR-0017: Phase 2A se cerró dev-first con MockLLM. Razón: validar arquitectura sin gastar GPU. Phase 2B (GPU real) queda como follow-up explícito documentado en TODO.md."

#### T19 — ADR-0018 Cost guards obligatorios
- **Effort:** S
- **Depende de:** T15
- **Output:** `docs/adr/0018-cost-guards-mandatory.md`
- **Fuente:** Plan §D7
- **Acceptance:** Documenta presupuesto máximo por fase, stop conditions automáticas, promoción por evidencia.
- **Handoff prompt:** "ADR-0018: cost guards obligatorios en synthetic data generation. Budget máximo por fase, stop conditions automáticas si excede umbral. Razón: prevenir runaway GPU spend."

---

### Sprint 5 — Calidad y Proceso

#### T20 — ADR-0019 Cyclomatic Complexity ≤ 5 + CI gate
- **Effort:** M
- **Depende de:** T1
- **Output:** `docs/adr/0019-cyclomatic-complexity-gate.md`
- **Fuente:** `MEMORY.md` §1, `CC_TD.md`, `DD_CC_REFACTOR.md`, commit `f298161`
- **Acceptance:** Documenta target CC≤5 nuevo / ≤10 warning / >10 blocker. Refs AP-1-T1, AP-1-T2, AP-1-T3 (61→9). CI gate desde Feb-26.
- **Handoff prompt:** "ADR-0019: target CC≤5 para funciones nuevas, CC 6-10 warning, >10 blocker. CI gate activo desde commit f298161. Refactors aplicados: `_ingest_directory` 8→5, `retrieve_for_role` 6→5, `Client.__init__` 61→9. Refs `[[CC_TD]]`, `[[DD_CC_REFACTOR]]`."

#### T21 — ADR-0020 Mock externals only / integration test internals
- **Effort:** S
- **Depende de:** T20
- **Output:** `docs/adr/0020-mock-externals-only.md`
- **Fuente:** `MEMORY.md` §2 (AP-2)
- **Acceptance:** Documenta política: mock solo Ollama, HTTP, filesystem; nunca engines/retrieval/ingestion internos. Markers `@pytest.mark.unit` vs `integration`. E2E ≥1 por feature crítico.
- **Handoff prompt:** "ADR-0020: mock solo dependencias externas (Ollama, HTTP, FS). Lógica interna se testea con integration tests reales. Markers `unit`/`integration`/`smoke`/`slow`. E2E mínimo 1 por feature crítico. Origen: AP-2 lessons learned tras audit Fase 1."

---

### Sprint 6 — Cierre

#### T22 — Crear MOC `docs/adr/README.md`
- **Effort:** S
- **Depende de:** T2–T21
- **Output:** `docs/adr/README.md`
- **Acceptance:**
  - Lista los 20 ADRs agrupados en 4 dominios (Core Pipeline, Graph RAG, Distilabel/Fine-tuning, Quality & Process).
  - Cada entrada: `[[NNNN-slug]] — descripción ≤80 chars`.
  - Header con leyenda de status y tags.
  - Sección "Convenciones" enlazando al `_template.md`.
- **Handoff prompt:** "Crear `docs/adr/README.md` (MOC) listando los 20 ADRs por dominio con `[[wikilinks]]`. Header con leyenda de status (`accepted/deprecated/superseded`) y vocabulario de tags. Sección 'Convenciones' enlazando a `[[_template]]`."

#### T23 — Validar grafo y consistencia
- **Effort:** S
- **Depende de:** T22
- **Output:** Log de validación (en chat, no como archivo)
- **Acceptance:**
  - `grep -r "\[\[" docs/adr/` muestra ≥1 link saliente por ADR (excepto transversales).
  - Todos los `[[xxxx-...]]` apuntan a archivo existente.
  - Todos los frontmatters parsean como YAML válido.
  - Todos los tags están en el vocabulario controlado (D6 del plan).
- **Handoff prompt:** "Validar `docs/adr/`. (1) Listar ADRs sin wikilinks salientes; reportar excepciones. (2) Detectar wikilinks rotos. (3) Validar YAML frontmatter con `python -c 'import yaml; yaml.safe_load(...)'`. (4) Comprobar tags vs vocabulario D6. Reportar resultados en una tabla resumen."

---

## Resumen

| Métrica | Valor |
|---|---|
| Total tareas | 23 |
| Total Effort S | 11 |
| Total Effort M | 12 |
| Total Effort L | 0 |
| Total Effort XL | 0 |
| Archivos creados | 22 |
| Archivos modificados | 1 |
| Tiempo estimado | ~6 h trabajo concentrado |

## Estado actual

- [x] T1
- [x] T2
- [x] T3
- [x] T4
- [x] T5
- [x] T6
- [x] T7
- [x] T8
- [x] T9
- [x] T10
- [x] T11
- [x] T12
- [x] T13
- [x] T14
- [x] T15
- [x] T16
- [x] T17
- [x] T18
- [x] T19
- [x] T20
- [x] T21
- [x] T22
- [x] T23

(Se irán marcando `[x]` al cerrar cada tarea, con commit incremental cuando aplique.)
