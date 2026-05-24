# ADR Index — Agnostic AI Pipeline

**Map of Content (MOC)** — Índice navegable del vault de decisiones arquitectónicas.
Cada entrada es un [[wikilink]] a un ADR atómico (1 decisión = 1 documento).

> **Convenciones:**
> - Status: `accepted` · `proposed` · `deprecated` · `superseded`
> - Tags de dominio: `core-pipeline` · `graph-rag` · `distilabel` · `fine-tuning` · `a2a` · `quality` · `process`
> - Para crear un nuevo ADR: copiar [[_template]] y seguir la numeración.
> - Plan de creación: [[../plan/adr-obsidian-creation]]

---

## Core Pipeline

Decisiones fundamentales de la arquitectura multi-rol y su infraestructura de ejecución.

| ADR | Título | Status |
|---|---|---|
| [[0002-provider-agnostic-llm-client]] | Cliente LLM unificado para 6 providers via `config.yaml` | accepted |
| [[0003-cli-subprocess-bridging]] | Bridging de CLIs externos (claude/codex/gcloud) via subprocess + JSON I/O | accepted |
| [[0004-multi-role-pipeline]] | Pipeline secuencial BA→PO→Architect→Dev→QA con artefactos YAML entre etapas | accepted |
| [[0005-a2a-http-protocol]] | Agent-to-Agent via HTTP/FastAPI; cada rol como servicio independiente | accepted |
| [[0006-architect-complexity-tiers]] | Auto-clasificación Simple/Medium/Corporate con LLM classifier + fallback word-count | accepted |
| [[0007-tdd-enforcement-dev-role]] | TDD enforced por defecto en Dev; escape via `ALLOW_NO_TESTS` y `STRICT_TDD` | accepted |
| [[0008-iteration-snapshot-immutability]] | Snapshots de iteración write-once; `FLUSH=1` como única operación destructiva | accepted |

---

## Graph RAG (Fase 1)

Decisiones del knowledge graph sobre artefactos del proyecto con LightRAG.

| ADR | Título | Status |
|---|---|---|
| [[0009-graph-rag-lightrag-choice]] | LightRAG sobre Neo4j (JVM) y ChromaDB (sin relaciones); retrieval híbrido local | accepted |
| [[0010-graph-rag-local-stores]] | NetworkX + NanoVectorDB: cero infraestructura, suficiente para proyecto-scope | accepted |
| [[0011-graph-rag-embedding-bge-m3]] | bge-m3 1024 dims por soporte multilingüe y calidad semántica | accepted |
| [[0012-graph-rag-per-role-retrieval]] | Políticas `mode + top_k` por rol; Architect hybrid/60, Dev local/40 | accepted |
| [[0013-graph-rag-config-single-source]] | `GraphRAGConfig.DEFAULT_CONFIG` como única fuente de defaults; `validate_schema()` obligatorio | accepted |

---

## Distilabel + Fine-Tuning (Fases 2/3)

Decisiones del pipeline de generación de datos sintéticos y fine-tuning de modelos abiertos.

| ADR | Título | Status |
|---|---|---|
| [[0014-distilabel-as-wrapper]] | Distilabel sobre scripts custom: checkpointing + retry + HuggingFace export | accepted |
| [[0015-tiered-teacher-model]] | Qwen2.5-14B/32B baseline + 72B selectivo: $60–160 vs $125–250 por ciclo | accepted |
| [[0016-optional-dependencies-per-phase]] | `requirements-rag.txt` y `requirements-training.txt` separados del baseline | accepted |
| [[0017-phase2a-local-first-mock]] | Fase 2A cerrada con MockLLM; Fase 2B (GPU real) pendiente y documentada | accepted |
| [[0018-cost-guards-mandatory]] | Stop condition automática + budget por run + promoción por calidad, no volumen | accepted |

---

## Quality & Process

Políticas transversales de calidad de código y testing aplicables a todo el proyecto.

| ADR | Título | Status |
|---|---|---|
| [[0001-logging-and-status-schema]] | Prefijos de log estándar y schema JSON unificado para summaries QA/Dev | accepted |
| [[0019-cyclomatic-complexity-gate]] | CC ≤ 5 target · 6–10 warning · >10 blocker en CI; resultados AP-1 documentados | accepted |
| [[0020-mock-externals-only]] | Mock solo externos (Ollama/HTTP/FS); integración real para lógica interna; E2E ≥ 1 | accepted |

---

## Árbol de dependencias entre ADRs

```
0002 (LLM Client)
 ├── 0003 (CLI subprocess)
 └── 0004 (Multi-role pipeline)
       ├── 0005 (A2A HTTP)
       ├── 0006 (Complexity tiers)
       ├── 0007 (TDD enforcement) ──── 0020 (Mock externals)
       └── 0008 (Snapshot immutability)

0009 (LightRAG)
 ├── 0010 (Local stores)
 ├── 0011 (bge-m3 embedding)
 ├── 0012 (Per-role retrieval)
 └── 0013 (Config single source)

0014 (Distilabel wrapper)
 ├── 0015 (Tiered teacher)  ──── 0018 (Cost guards)
 ├── 0016 (Optional deps)
 └── 0017 (Phase 2A mock)  ──── 0018 (Cost guards)

0019 (CC gate) ──── 0020 (Mock externals)
0001 (Logging) ──── 0008 (Snapshot immutability)
```

---

## Estadísticas del vault

| Métrica | Valor |
|---|---|
| Total ADRs | 20 |
| Status `accepted` | 20 |
| Status `proposed` | 0 |
| Status `deprecated` | 0 |
| Dominios | 4 (core-pipeline, graph-rag, distilabel/fine-tuning, quality/process) |
| Primer ADR | 0001 — 2025-11-24 |
| Último ADR | 0020 — 2026-02-09 |
