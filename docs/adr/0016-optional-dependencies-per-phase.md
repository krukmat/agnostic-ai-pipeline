---
id: ADR-0016
title: Dependencias opcionales separadas por fase de capacidad
status: accepted
date: 2026-02-06
deciders:
  - Project lead
tags:
  - adr
  - core-pipeline
  - distilabel
  - graph-rag
  - status/accepted
  - phase/NA
supersedes:
superseded-by:
related:
  - "[[0009-graph-rag-lightrag-choice]]"
  - "[[0014-distilabel-as-wrapper]]"
---

# ADR-0016 — Dependencias opcionales separadas por fase de capacidad

## Context

El `requirements.txt` base cubre el pipeline central (BA→PO→Arch→Dev→QA).
Añadir LightRAG, Distilabel, PEFT y TRL al baseline inflaría el entorno base
con ~3–4 GB de wheels y dependencias nativas (compilación FAISS, torch, etc.)
que la mayoría de usuarios del pipeline no necesitan.

## Decision

Separar las dependencias en archivos independientes instalables por capacidad:

| Archivo | Capacidad | Dependencias clave |
|---|---|---|
| `requirements.txt` | Pipeline base | httpx, PyYAML, FastAPI, pytest |
| `requirements-rag.txt` | Graph RAG (Fase 1) | lightrag-hku[api], networkx, nano-vectordb |
| `requirements-training.txt` | Distilabel + Fine-tuning (Fase 2/3) | distilabel, peft, trl, torch, vllm |

```bash
# Instalar solo lo necesario
pip install -r requirements.txt           # pipeline base
pip install -r requirements-rag.txt       # + Graph RAG
pip install -r requirements-training.txt  # + Distilabel/fine-tuning
```

## Consequences

**Pros**
- Entorno base (~50 MB) instalable en segundos sin GPU ni compilación nativa.
- CI del pipeline base no requiere torch ni CUDA.
- Usuarios que solo quieren orquestar roles no arrastran dependencias de ML.

**Cons / Trade-offs**
- Tres comandos de instalación en lugar de uno para el stack completo.
- Posibles conflictos de versiones entre los tres archivos si no se mantienen sincronizados.

**Neutral**
- El Makefile puede envolver la instalación con `make setup-rag` y `make setup-training` para simplificar la UX.

## Alternatives Considered

- **Un `requirements-full.txt`** — descartado: un solo archivo que instala todo; el usuario no puede optar por menos.
- **extras_require en setup.py** — descartado: el proyecto no está empaquetado como librería; overhead innecesario.
- **Docker multi-stage** — complementario, no excluyente; los `requirements-*.txt` son igualmente necesarios dentro del Dockerfile.

## References

- Plan: `PLAN_implementation_distilabel_finetuning_rag.md` §D6
- Archivos: `requirements.txt`, `requirements-rag.txt`, `requirements-training.txt`
- ADRs relacionados: [[0009-graph-rag-lightrag-choice]], [[0014-distilabel-as-wrapper]]
