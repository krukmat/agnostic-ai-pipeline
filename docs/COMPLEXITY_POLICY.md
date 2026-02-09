# Complexity Policy (CI Gate)

Esta política define cómo se gobierna la complejidad ciclomática en PRs usando `radon`.

## Alcance

- Se evalúan **solo archivos Python tocados en el PR**.
- El objetivo es evitar deuda nueva crítica sin bloquear por deuda histórica fuera del cambio.

## Reglas

1. **Bloqueo duro** para bloques nuevos o empeorados con severidad **E/F**.
2. Los bloques **D** nuevos o empeorados requieren excepción explícita.
3. Bloques **A/B/C** no bloquean por política de gate.

## Excepciones para D

Las excepciones viven en `.github/complexity_exceptions.json` bajo `allow_d`.

Formato ejemplo:

```json
{
  "allow_d": [
    {
      "file": "scripts/llm.py",
      "kind": "M",
      "name": "Client._legacy_method",
      "issue": "TECH-123",
      "reason": "Refactor planificado para siguiente iteración"
    }
  ]
}
```

Campos de matching efectivos para el gate:
- `file`
- `kind` (F/M/C)
- `name`

Se recomienda además documentar siempre:
- `issue` (ticket)
- `reason` (justificación)

## Implementación técnica

- Workflow: `.github/workflows/complexity-gate.yml`
- Script: `scripts/ci/complexity_gate.py`

## Ejecución local

```bash
python scripts/ci/complexity_gate.py --base-ref origin/main --head-ref HEAD
```
