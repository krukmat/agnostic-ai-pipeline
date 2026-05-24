---
id: ADR-0018
title: Cost guards obligatorios en generación de datos sintéticos
status: accepted
date: 2026-02-06
deciders:
  - Project lead
tags:
  - adr
  - distilabel
  - fine-tuning
  - process
  - status/accepted
  - phase/F2
supersedes:
superseded-by:
related:
  - "[[0014-distilabel-as-wrapper]]"
  - "[[0015-tiered-teacher-model]]"
  - "[[0017-phase2a-local-first-mock]]"
---

# ADR-0018 — Cost guards obligatorios en generación de datos sintéticos

## Context

Los pipelines de generación sintética con GPU pueden incurrir en costos
inesperados si un bug provoca un loop de regeneración, si el quality gate
rechaza demasiados ejemplos forzando reintentos, o si el batch size está
mal calibrado. Sin límites explícitos, un run de fine-tuning puede exceder
el presupuesto asignado por fase sin señal de alerta.

## Decision

Todo pipeline de generación sintética debe implementar tres guards obligatorios:

1. **Presupuesto máximo por fase** — configurado en `training/configs/base.yaml`:
   ```yaml
   cost_guard:
     max_usd_per_run: 30.0      # F2: Distilabel
     max_usd_per_cycle: 90.0    # F2: ciclo completo 5 roles
   ```

2. **Stop condition automática** — si el costo estimado acumulado supera
   `max_usd_per_run`, el pipeline para y persiste el checkpoint. El run se
   puede retomar desde donde quedó.

3. **Promoción por evidencia, no por volumen** — un rol no avanza a fine-tuning
   (Fase 3) hasta demostrar calidad del dataset con métricas concretas
   (`quality_score > 0.7` en ≥80% de ejemplos), independientemente del número
   de muestras generadas.

## Consequences

**Pros**
- Presupuesto controlable: el peor caso es `max_usd_per_run`, no ilimitado.
- Checkpointing + stop condition permite retomar sin perder trabajo.
- Criterio de promoción basado en calidad previene fine-tuning con datos malos.

**Cons / Trade-offs**
- El costo estimado es aproximado (basado en tokens × precio por token); puede divergir del costo real de la GPU rentada.
- La configuración manual de `max_usd_per_run` requiere conocer el costo del proveedor GPU elegido.

**Neutral**
- En Fase 2A (mock local) los cost guards están presentes en código pero no se activan (costo = $0).

## Alternatives Considered

- **Sin límites, monitoreo manual** — descartado: riesgo de runaway spend en un pipeline de horas.
- **Límite fijo en número de ejemplos** — descartado: el costo real depende del modelo usado (14B vs 72B), no solo del volumen.

## References

- Plan: `PLAN_implementation_distilabel_finetuning_rag.md` §D7, §Guardrails de costo
- Config: `training/configs/base.yaml §cost_guard`
- ADRs relacionados: [[0014-distilabel-as-wrapper]], [[0015-tiered-teacher-model]]
