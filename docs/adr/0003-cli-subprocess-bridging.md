---
id: ADR-0003
title: Bridging de CLIs externos via subprocess + JSON I/O
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
---

# ADR-0003 — Bridging de CLIs externos via subprocess + JSON I/O

## Context

Claude Code CLI (`claude`), GitHub Copilot CLI (`codex`) y Vertex AI CLI
(`gcloud`) no exponen SDK Python estable o gratuito en el momento de la
decisión, pero sí exponen CLIs con autenticación manejada por el usuario.
Necesitábamos integrarlos al [[0002-provider-agnostic-llm-client]] sin gestionar
tokens OAuth ni instalar SDKs con dependencias pesadas.

## Decision

Invocar los CLIs externos via `subprocess.run` / `asyncio.create_subprocess_exec`
pasando el prompt como JSON por stdin o argumentos, y parseando la respuesta de
stdout. El contrato es: el CLI recibe `{"prompt": "..."}` y devuelve texto plano
o JSON estructurado en stdout.

```python
# Ejemplo simplificado en scripts/llm.py
proc = await asyncio.create_subprocess_exec(
    "claude", "--print", "--output-format", "text",
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
)
stdout, _ = await proc.communicate(input=prompt.encode())
```

## Consequences

**Pros**
- Auth delegada completamente al CLI del usuario (`claude login`, `gcloud auth`).
- Sin dependencias Python adicionales para estos providers.
- El pipeline funciona con cualquier versión del CLI sin actualizar el código.

**Cons / Trade-offs**
- Parsing de stdout es frágil: stderr ruidoso, respuestas parciales o vacías requieren manejo especial (documentado en `TODO.md` Fase 3).
- `_cli_chat` y `_cli_chat_async` tienen CC muy alto (53–55) — deuda técnica explícita en `CC_TD.md` (ver [[0019-cyclomatic-complexity-gate]]).
- Latencia adicional por fork de proceso.

**Neutral**
- Cada CLI tiene flags distintos (`--print`, `--output-format`, etc.); la adaptación vive en `scripts/llm.py`, no en los roles.

## Alternatives Considered

- **SDK Anthropic directo** — requiere API key y no aprovecha contexto de `claude login`; descartado para `claude_cli` provider.
- **HTTP proxy local** — overcomplejo para el caso de uso; descartado.
- **Plugin system** — considerado para el futuro pero no necesario para 6 providers conocidos.

## References

- Código: `scripts/llm.py` (métodos `_cli_chat`, `_cli_chat_async`)
- Tech debt: `CC_TD.md` (raíz del repo), `TODO.md` §Hardening de wrappers sync/async
- ADRs relacionados: [[0002-provider-agnostic-llm-client]]
