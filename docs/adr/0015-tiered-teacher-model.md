---
id: ADR-0015
title: Teacher model escalonado Qwen2.5-14B/32B base + 72B selectivo
status: accepted
date: 2026-02-06
deciders:
  - Project lead
tags:
  - adr
  - distilabel
  - fine-tuning
  - status/accepted
  - phase/F2
supersedes:
superseded-by:
related:
  - "[[0014-distilabel-as-wrapper]]"
  - "[[0018-cost-guards-mandatory]]"
---

# ADR-0015 — Teacher model escalonado Qwen2.5-14B/32B base + 72B selectivo

## Context

El draft original del plan de fine-tuning asumía Qwen2.5-72B como teacher
model único para toda la generación sintética, resultando en un costo estimado
de $125–250 por ciclo completo de 5 roles. Este costo hace inviable la
iteración frecuente del pipeline. Se necesita reducir el costo sin sacrificar
la calidad de los ejemplos de entrenamiento.

## Decision

Estrategia de teacher model en dos capas:

- **Baseline (70% del volumen):** Qwen2.5-14B o Qwen2.5-32B para la mayoría
  de los ejemplos — casos simples, formato estándar, alta temperatura.
- **Selectivo (30% del volumen):** Qwen2.5-72B solo para ejemplos difíciles
  o muestras de alto valor identificadas por el quality gate.

La selección entre capas la decide el `quality_filter` step en Distilabel:
si un ejemplo no supera el umbral de calidad con el modelo base, se regenera
con el modelo grande.

```yaml
# training/configs/quality_thresholds.yaml
cheap_pass_threshold: 0.7    # pasa con 14B/32B
expensive_regen_threshold: 0.5  # regenerar con 72B si score < 0.7
discard_threshold: 0.3          # descartar si 72B tampoco supera 0.5
```

## Consequences

**Pros**
- Reducción de costo de ciclo: **$60–160** vs $125–250 original (38–52% menos).
- El 70% procesado con modelo más pequeño también es más rápido (menor latencia por batch).
- Quality gate garantiza que el 30% de alto valor sí recibe atención del modelo grande.

**Cons / Trade-offs**
- Distribución real de "casos difíciles" desconocida hasta ejecutar el primer ciclo real con GPU.
- Dos modelos en pipeline = dos configuraciones de vLLM a gestionar.
- El umbral `cheap_pass_threshold: 0.7` es heurístico; requiere calibración post-primera-corrida.

**Neutral**
- El `validators_adapter.py` actual usa heurística de longitud como proxy de calidad (aceptado para Fase 2A mock).

## Alternatives Considered

- **Qwen2.5-72B siempre** — descartado: $125–250 por ciclo; inviable para iteración frecuente.
- **Solo 14B** — descartado: calidad insuficiente para ejemplos complejos de Architect y Dev roles.
- **Gemini 2.5 Pro como teacher** — descartado: rompe la premisa open-source del proyecto; dependencia externa de pago.

## References

- Plan: `PLAN_implementation_distilabel_finetuning_rag.md` §D2, §Evaluación de viabilidad
- Config: `training/configs/quality_thresholds.yaml`
- Código: `training/steps/quality_filter.py`, `training/steps/validators_adapter.py`
- ADRs relacionados: [[0014-distilabel-as-wrapper]], [[0018-cost-guards-mandatory]]
