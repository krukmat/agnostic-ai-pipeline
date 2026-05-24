---
id: ADR-0005
title: Protocolo Agent-to-Agent via HTTP/FastAPI
status: accepted
date: 2025-11-01
deciders:
  - Project lead
tags:
  - adr
  - a2a
  - core-pipeline
  - status/accepted
  - phase/NA
supersedes:
superseded-by:
related:
  - "[[0004-multi-role-pipeline]]"
---

# ADR-0005 — Protocolo Agent-to-Agent via HTTP/FastAPI

## Context

El [[0004-multi-role-pipeline]] se ejecuta por defecto en modo local (llamadas
directas entre funciones Python). Para despliegues distribuidos —roles en
máquinas distintas, paralelización, o integración con sistemas externos— se
necesita un protocolo de comunicación entre agentes que no acople los roles en
el mismo proceso.

## Decision

Implementar A2A como servicios HTTP independientes con FastAPI. Cada rol expone
un endpoint `POST /run` que acepta el artefacto de entrada y devuelve el de
salida. Los puertos son fijos por rol: BA:8001, PO:8002, Architect:8003,
Dev:8004, QA:8005. El orquestador usa `a2a/executors.py` para seleccionar entre
ejecución local o remota transparentemente.

```bash
# Arrancar rol como servicio
python scripts/run_ba.py serve   # escucha en :8001
make warmup                      # pre-inicializa todos los servicios
```

## Consequences

**Pros**
- Roles desplegables en containers/VMs independientes.
- `curl`-friendly: fácil de debuggear sin código Python.
- Orquestador agnóstico al modo de ejecución (local vs. remoto).
- Compatible con `make warmup` para pre-inicialización en entornos con cold start.

**Cons / Trade-offs**
- Overhead de serialización JSON + latencia de red en modo distribuido.
- Requiere gestionar disponibilidad de servicios (health checks, retries).
- Auth entre servicios es básica (token en `config.yaml §a2a`); no production-grade.

**Neutral**
- En uso local habitual el modo A2A está inactivo; el pipeline funciona sin levantarlo.

## Alternatives Considered

- **gRPC** — descartado: schema protobuf añade complejidad de codegen para artefactos YAML que cambian frecuentemente.
- **Message bus (RabbitMQ / Redis Streams)** — descartado: overkill para un pipeline secuencial; introduce broker como dependencia operacional.
- **Shared filesystem** — descartado: no escala a roles en máquinas distintas; ya es el modo local actual.

## References

- Código: `a2a/runtime.py`, `a2a/server.py`, `a2a/client.py`, `a2a/executors.py`
- Config: `config.yaml` §a2a
- CLAUDE.md §A2A (Agent-to-Agent) Service Mode
- ADRs relacionados: [[0004-multi-role-pipeline]]
