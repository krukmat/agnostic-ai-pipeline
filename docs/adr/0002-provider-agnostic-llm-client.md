---
id: ADR-0002
title: Provider-agnostic LLM Client unificado
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
  - "[[0003-cli-subprocess-bridging]]"
  - "[[0004-multi-role-pipeline]]"
---

# ADR-0002 — Provider-agnostic LLM Client unificado

## Context

El pipeline necesita que cada rol (BA, PO, Architect, Dev, QA) pueda usar un
proveedor de LLM diferente — Ollama local para desarrollo, OpenAI para
producción, Vertex AI para integración con GCP — sin que el código de cada rol
sepa nada del proveedor. Sin abstracción, cambiar de proveedor requería
modificar cada script de rol individualmente.

## Decision

Implementar `scripts/llm.py::Client(role="<rol>")` como único punto de acceso a
todos los LLMs. El cliente resuelve el proveedor y modelo desde `config.yaml`
bajo `roles.<rol>`, y expone una interfaz única `chat(prompt)` / `chat_async(prompt)`.
Seis providers soportados: `ollama`, `openai`, `codex_cli`, `claude_cli`,
`vertex_cli`, `vertex_sdk`.

```yaml
# config.yaml — cambiar proveedor sin tocar código de roles
roles:
  dev:
    provider: claude_cli
    model: claude-sonnet-4-6
```

## Consequences

**Pros**
- Swap de proveedor por rol con un cambio de `config.yaml`, sin tocar código.
- `make set-role role=dev provider=ollama model=mistral:7b` como interfaz operacional.
- Providers CLI (claude, codex, gcloud) se incorporan sin SDK adicional.

**Cons / Trade-offs**
- Un único módulo de 892 líneas concentra lógica de 6 providers; CC inicial muy alto (resuelto parcialmente en [[0019-cyclomatic-complexity-gate]]).
- Comportamientos edge de cada provider (timeouts, stderr, respuestas vacías) son difíciles de testear de forma uniforme.

**Neutral**
- Providers CLI requieren binario en PATH y auth previa — responsabilidad del entorno, no del cliente.

## Alternatives Considered

- **LangChain** — descartado: dependencia pesada (~80 paquetes), abstracción que no cubre CLIs, overhead para un pipeline que no usa chains.
- **LiteLLM** — descartado: cubre APIs HTTP pero no subprocess-based CLIs como `claude` o `codex`.
- **SDK directo por rol** — descartado: duplica lógica de retry/async en cada script; imposible cambiar proveedor sin editar N archivos.

## References

- Código: `scripts/llm.py`
- Commits: `3797ca0`, `853ad32`
- ADRs relacionados: [[0003-cli-subprocess-bridging]], [[0019-cyclomatic-complexity-gate]]
