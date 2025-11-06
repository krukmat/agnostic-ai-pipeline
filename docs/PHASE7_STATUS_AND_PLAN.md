# Fase 7: Optimizer Tuning (MIPROv2) - Estado y Planificación

**Fecha de análisis:** 2025-11-06
**Branch:** dspy-integration
**Status:** ❌ **NO EJECUTADA** - Documentación completa, implementación pendiente

---

## 📊 Resumen Ejecutivo

### ✅ Lo que existe:
- Documentación técnica completa (`docs/phase7_optimizer_tuning.md`)
- Plan detallado de 6 pasos (5 días estimados)
- Métricas de éxito definidas
- Análisis de riesgos y mitigaciones

### ❌ Lo que NO existe:
- Código de optimización (`dspy_baseline/optimizers/`)
- Datasets ampliados (≥50 ejemplos para BA y QA)
- Scripts de tuning (`scripts/tune_dspy.py`)
- Experimentos ejecutados
- Resultados medibles

---

## 🚧 Prerequisitos BLOQUEANTES

**La Fase 7 requiere que estén completas las Fases 3-6:**

| Fase | Nombre | Status | Bloqueante? |
|------|--------|--------|-------------|
| Fase 0 | Auditoría técnica | ✅ COMPLETA | No |
| Fase 1 | Python upgrade | ⏭️ SKIP | No |
| Fase 2 | DSPy BA baseline | ✅ COMPLETA | No |
| Fase 3 | Experimento comparativo | ✅ COMPLETA | No |
| **Fase 4** | **PO integration** | ❌ **PENDIENTE** | **Sí** |
| **Fase 5** | **Architect integration** | ❌ **PENDIENTE** | **Sí** |
| **Fase 6** | **QA integration** | ❌ **PENDIENTE** | **Sí** |

**Conclusión:** ⛔ No se puede ejecutar Fase 7 sin completar Fases 4-6

---

## 🎯 Scope de la Fase 7

### Objetivo:
Compilar las firmas DSPy de BA y QA con `dspy.MIPROv2` usando datasets curados para mejorar:
- Consistencia de outputs
- Cobertura de escenarios negativos
- Reducción de iteraciones manuales

### Entregables:
1. Wrapper MIPROv2 reutilizable (`dspy_baseline/optimizers/mipro.py`)
2. Script de tuning (`scripts/tune_dspy.py`)
3. Datasets ampliados (≥50 ejemplos cada uno)
4. Métricas de comparación (baseline vs optimizado)
5. Documentación de resultados

### Métricas de Éxito:
- **BA optimizado:**
  - Completitud YAML ≥98%
  - Reducción de tiempo de revisión manual ≥25%

- **QA optimizado:**
  - Cobertura negativa ≥95%
  - Reducción de notas post-QA ≥20%

- **Operacional:**
  - Tiempo de compilación ≤6 min por rol
  - Reproducibilidad (mismos inputs → ±5% métrica)

---

## 📋 Plan de Implementación (5 días)

### Día 1: Infraestructura (½ día) + Datasets (½ día)

**Crear estructura:**
```bash
mkdir -p dspy_baseline/optimizers
mkdir -p artifacts/dspy/optimizer/{ba,qa}
```

**Archivos a crear:**
```
dspy_baseline/
├── optimizers/
│   ├── __init__.py
│   └── mipro.py                    # Wrapper MIPROv2
├── data/
│   ├── ba_train.json               # ≥50 ejemplos
│   ├── ba_eval.json                # ≥10 ejemplos
│   ├── qa_train.json               # ≥50 ejemplos
│   └── qa_eval.json                # ≥10 ejemplos
```

**Formato datasets:**
- `ba_train.json`: `{"concept": "...", "requirements": {...}}`
- `qa_train.json`: `{"story": {...}, "expected_testcases": [...]}`

**Fuentes de datos:**
- Reutilizar los 21 conceptos del experimento comparativo (Fase 3)
- Agregar 29+ conceptos nuevos validados manualmente
- Extraer historias reales del pipeline existente

---

### Día 2: Script de tuning

**Crear `scripts/tune_dspy.py`:**

```python
#!/usr/bin/env python3
"""
Optimiza módulos DSPy con MIPROv2.

Usage:
    python scripts/tune_dspy.py --role ba --num-candidates 8 --max-iters 8
    python scripts/tune_dspy.py --role qa --num-candidates 8 --max-iters 8
"""

# Ver implementación completa en PHASE7_STATUS_AND_PLAN.md
```

**Parámetros:**
- `--role {ba,qa}`: Rol a optimizar
- `--num-candidates`: Número de candidatos (default: 8)
- `--max-iters`: Iteraciones máximas (default: 8)
- `--seed`: Seed para reproducibilidad (default: 0)

**Outputs:**
- `artifacts/dspy/optimizer/<role>/<timestamp>/program.pkl`
- `artifacts/dspy/optimizer/<role>/<timestamp>/metrics.json`
- `artifacts/dspy/optimizer/<role>/<timestamp>/stdout.log`

---

### Día 3: Ejecutar optimización piloto

```bash
# Optimizar BA
python scripts/tune_dspy.py \
  --role ba \
  --num-candidates 8 \
  --max-iters 8 \
  --seed 0

# Optimizar QA
python scripts/tune_dspy.py \
  --role qa \
  --num-candidates 8 \
  --max-iters 8 \
  --seed 0
```

**Métricas a capturar:**
- Completitud YAML (BA)
- Cobertura negativa (QA)
- Latencia promedio
- Costo de compilación

---

### Día 4: Evaluación (½ día) + Scripts de eval (½ día)

**Crear scripts de evaluación:**
- `scripts/eval_ba_optimized.py`
- `scripts/eval_qa_optimized.py`

**Comparar en 10 conceptos/historias NUEVOS:**
- Baseline (sin optimización) vs Optimizado (MIPROv2)
- Medir mejora en métricas definidas
- Documentar trade-offs (latencia, calidad, costo)

---

### Día 5: Documentación y decisión

**Actualizar:**
1. `docs/phase7_optimizer_tuning.md` - Sección "Resultados"
2. `DSPY_INTEGRATION_PLAN.md` - Conclusiones Fase 7
3. `README.md` - Sección DSPy con findings
4. `artifacts/dspy/optimizer/report.md` - Reporte técnico completo

**Criterio Go/No-Go:**
- ✅ **GO:** Mejora ≥20% en métricas críticas → Proceder a Fase 8 (rollout)
- ❌ **NO-GO:** Mejora <20% → Documentar y continuar con baseline

---

## 🚦 Recomendación Actual

### ⛔ NO EJECUTAR FASE 7 TODAVÍA

**Razones:**

1. **Prerequisitos incompletos:** Faltan Fases 4-6 (PO, Architect, QA integration con DSPy)

2. **ROI cuestionable en este momento:**
   - Fase 3 ya demostró que DSPy BA baseline es **12.8x más rápido** y tiene **100% schema compliance**
   - Master BA tiene solo 81% compliance → DSPy ya es una mejora masiva
   - Optimizar algo que ya funciona perfectamente tiene diminishing returns

3. **Complejidad vs beneficio:**
   - MIPROv2 requiere datasets curados (≥50 ejemplos validados)
   - Compilación toma tiempo (~6-10 min por rol)
   - Costos de LLM durante compilación
   - Mantenimiento de programas compilados

4. **Prioridad del merge:**
   - DSPy BA baseline ya ganó el experimento comparativo
   - Merge a `main` está pendiente desde Fase 3
   - Adoptar baseline primero, optimizar después si es necesario

---

## 🗺️ Roadmap Recomendado

### Corto Plazo (Próximas 2 semanas):

1. ✅ **Fase 5 (Merge):** Merge `dspy-integration` → `main`
   - Adoptar DSPy BA como implementación oficial
   - Actualizar `scripts/run_ba.py` → `dspy_baseline/scripts/run_ba.py`
   - Archivar Master BA en `archive/`
   - Update CLAUDE.md

2. 📊 **Monitoreo post-merge:**
   - Ejecutar pipeline en producción con DSPy BA
   - Capturar métricas reales (latencia, error rate, schema compliance)
   - Identificar edge cases o problemas

3. ✅ **Documentar decisión:**
   - Crear `docs/decisions/001_dspy_ba_adoption.md`
   - Registrar findings del experimento comparativo
   - Justificación técnica del merge

---

### Medio Plazo (1-2 meses, OPCIONAL):

4. 🔬 **Evaluar Fases 4-6:**
   - **Fase 4:** ¿Vale la pena DSPy para PO? (probablemente no - poco complejidad)
   - **Fase 5:** ¿Vale la pena DSPy para Architect? (posiblemente - clasificación compleja)
   - **Fase 6:** ¿Vale la pena DSPy para QA? (probablemente sí - generación de testcases)

5. 📈 **Análisis de necesidad de optimización:**
   - ¿El baseline tiene problemas de calidad?
   - ¿Se detectaron casos donde falla sistemáticamente?
   - ¿El ROI de MIPROv2 justifica el esfuerzo?

---

### Largo Plazo (3+ meses, FUTURE WORK):

6. 🔬 **Fase 7 (si aplica):** Optimizer tuning con MIPROv2
   - Solo ejecutar si hay problemas claros con baseline
   - Requisito: Tener Fases 4-6 completas
   - Evaluar trade-offs cuidadosamente

7. 🤖 **Fase 8 (si Fase 7 tiene GO):** Rollout de programas optimizados
   - Integrar programas compilados al pipeline
   - Flag `USE_OPTIMIZED_PROGRAMS` en config
   - A/B testing baseline vs optimizado

8. 📊 **Fase 9 (si Fase 8 tiene GO):** Automatización
   - Cron job para re-tuning mensual
   - MLflow tracking para observability
   - Continuous optimization

---

## 📝 Conclusiones

### Estado Actual:
- ✅ Fase 7 está **100% documentada**
- ❌ Fase 7 **NO está implementada** ni ejecutada
- ⛔ **No es ejecutable** sin completar Fases 4-6

### Próximo Paso Crítico:
🔥 **MERGE de `dspy-integration` a `main`**

**Justificación:**
- DSPy BA baseline ya demostró ser superior (Fase 3)
- Adoption > Optimization en este momento
- Fase 7 es "nice to have", no "must have"

### ¿Cuándo ejecutar Fase 7?
Solo si se cumplen TODAS estas condiciones:

1. ✅ DSPy BA adoptado en producción (post-merge)
2. ✅ Fases 4-6 completadas (PO, Architect, QA con DSPy)
3. ✅ Problemas de calidad detectados en baseline
4. ✅ Datasets ≥50 ejemplos disponibles y validados
5. ✅ ROI claro (mejora esperada ≥20%)

---

**Última actualización:** 2025-11-06
**Autor:** Análisis técnico branch dspy-integration
**Siguiente revisión:** Post-merge a main
