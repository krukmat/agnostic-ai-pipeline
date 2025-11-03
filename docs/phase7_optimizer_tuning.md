# Fase 7 – Optimización DSPy (MIPROv2 para BA/QA)

**Objetivo**  
Compilar las firmas DSPy de Business Analyst y QA Testcases con `dspy.MIPROv2`, usando datasets curados para mejorar consistencia, cobertura de escenarios negativos y reducir iteraciones manuales.

- **Duración estimada**: 5 días  
- **Owner**: Equipo DSPy / Optimización  
- **Prerequisitos**:
  - Fases 3–6 completadas (BA/PO/Architect/QA integrados al flujo DSPy).
  - Datasets iniciales disponibles (`dspy_baseline/data/ba_demo.json`, `qa_eval.yaml`).
  - Paquete DSPy 3.x instalado y proveedor LLM accesible para compilaciones prolongadas.

---

## 1. Alcance y entregables

- Wrapper MIPROv2 reutilizable (`dspy_baseline/optimizers/mipro.py`) y exportado en `__init__.py`.
- Script `scripts/tune.py` (o equivalente) que permita optimizar BA y QA con parámetros configurables (trainset, metric, max_iters, num_candidates, seed).
- Datasets ampliados para entrenamiento/evaluación (mínimo 50 ejemplos para PoC).
- Métricas de comparación (baseline vs optimizado) documentadas en `artifacts/dspy/optimizer/`.
- Documentación de resultados y conclusiones Go/No-Go para producción.

---

## 2. Plan paso a paso

1. **Preparar infraestructura (½ día)**
   - Crear directorio `dspy_baseline/optimizers/` con `__init__.py`.
   - Añadir módulo `mipro.py` con función `optimize_program(...)` (firma definida en `05-optimizer.md`).

2. **Ampliar datasets (1 día)**
   - BA: recopilar ≥50 pares concepto→requirements verificados (`dspy_baseline/data/ba_train.json`, `ba_eval.json`).
   - QA: sintetizar ≥50 historias con casos esperados (`dspy_baseline/data/qa_train.json`, `qa_eval.json`), alineado con `qa_eval.yaml`.
   - Normalizar formato (JSONL o YAML) y documentar criterios de aceptación.

3. **Implementar script de tuning (1 día)**
   - Archivo: `scripts/tune_dspy.py` (o similar).
   - Parámetros: `--role {ba,qa}`, `--trainset`, `--metric`, `--num-candidates`, `--max-iters`, `--seed`.
   - Salidas: programa compilado (`artifacts/dspy/optimizer/<role>/<timestamp>/program.pkl`), métricas (`metrics.json`), log (`stdout.log`).

4. **Ejecutar optimización piloto (1 día)**
   - Configuración sugerida: `num_candidates=8`, `max_iters=8`, `seed=0`.
   - Correr para BA y QA con datasets preparados.
   - Registrar métricas: completitud YAML (BA), cobertura negativa (QA), latencia promedio.

5. **Evaluar resultados (½ día)**
   - Comparar outputs optimizados vs baseline en 10 conceptos/historias nuevas.
   - Documentar hallazgos en esta fase (sección Resultados) y en `artifacts/dspy/optimizer/report.md`.

6. **Documentar y decidir (½ día)**
   - Actualizar README (sección DSPy) y `DSPY_INTEGRATION_PLAN.md` con conclusiones.
   - Proponer rollout (Fase 8) si mejora supera umbral (≥20% en cobertura negativa o reducción de iteraciones manuales).

---

## 3. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Dataset insuficiente | Optimización inestable | Recolectar ejemplos adicionales o reutilizar logs históricos |
| Costos/latencia altos | Retrasa pipeline | Ejecutar fuera de horas pico, ajustar `num_candidates`/`max_iters` |
| Falta de reproducibilidad | Resultados no confiables | Guardar seed, trainset exacto y artefactos compilados |
| Incompatibilidad DSPy versión | Bloquea tuning | Fijar versión DSPy en `requirements.txt`, pruebas locales antes de CI |

---

## 4. Métricas de éxito

- BA optimizado:
  - Completitud YAML ≥98%
  - Reducción de tiempo de revisión manual ≥25%
- QA optimizado:
  - Cobertura negativa (según lint) ≥95%
  - Reducción de notas post‑QA ≥20%
- Operacional:
  - Tiempo de compilación ≤6 min por rol
  - Artefactos reproducibles (mismos inputs → misma métrica ±5%)

---

## 5. Resultados (pendiente)

- **Fecha**: _(a completar)_  
- **Roles optimizados**: BA / QA  
- **Hallazgos**:  
  - _Completar tras piloto_
- **Siguientes pasos**:  
  - _Completar tras piloto_

---

## 6. Dependencias con fases futuras

- Fase 8 (si Go): Integrar programas compilados al pipeline (`make ba` / `make dspy-qa`) con flag `USE_OPTIMIZED_PROGRAMS`.
- Fase 9: Automatizar re‑tuning (p.ej., cron mensual) y seguimiento en MLflow.

