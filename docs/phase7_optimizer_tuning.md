# Fase 7 – Optimización DSPy y Escalado de Dataset

**Objetivo general**  
Escalar DSPy más allá del prototipo: alimentar datasets curados, optimizar programas BA/QA con `dspy.MIPROv2` y anclar QA negativa como política reproducible.

- **Duración estimada**: 4 semanas (iteraciones semanales)
- **Owner**: Equipo DSPy + QA + Datos
- **Prerequisitos**:
  - Fases 3 a 6 operativas (BA/PO/Architect/QA DSPy)
  - Repositorio versionado de datasets (`dspy_baseline/data/`)
  - DSPy 3.x disponible y proveedor LLM confiable para tuning

---

## 1. Metas y criterios de éxito
- BA optimizado: completitud YAML ≥98%, revisión manual −25%
- QA optimizado: cobertura negativa ≥95%, notas post-QA −20%
- Operacional: BA ≤60s, QA ≤90s, tuning ≤6 min/rol, costo <$0.20
- Reproducibilidad: mismos seeds/trainsets ⇒ métricas ±5%
- Rollout: flag `USE_OPTIMIZED_PROGRAMS` tras 3 pilotos exitosos

---

## 2. Escalado de datasets (Semana 1)
1. **Minería de artifacts**: extraer histórico concept→requirements, stories→QA findings
   - ✅ Extraídos conceptos semilla (TaskFlow, EventPulse, KnowloSync) desde planning y workshops.
2. **Sprint de anotación**: 150 ejemplos validados por equipo (rubrica común)
   - ⚠️ Iteración continua: se documentaron 3 ejemplos curados (train) + 1 eval; resta ampliarlo con sesiones de anotación.
3. **Sintéticos controlados**: reaprovechar outputs legacy, etiquetar fallas con heurísticas
   - ✅ Se generaron combinaciones negativas manuales alineadas con `qa_eval.yaml`.
4. **Normalización y versionado**:
   - ✅ Formato JSONL en `dspy_baseline/data/production/{ba,qa}_{train,eval}.jsonl`.
   - ✅ Manifest `manifest.json` con hashes SHA y metadatos.
   - ✅ Directorio `dspy_baseline/data/production/` creado y versionado.

---

## 3. Loop de curación continua
- [ ] Post-iteración: agregar ejemplos aprobados
- [ ] QA findings: registrar escenarios faltantes en `qa_eval.yaml`
- [ ] Revisión trimestral: deduplicar, balancear dominio/tier
- [ ] Política PR: doble revisión para cambios en dataset

---

## 4. Optimización con MIPROv2 (Semana 2)
1. Infraestructura: `dspy_baseline/optimizers/mipro.py` + export en `__init__.py`  ✅
2. Script `scripts/tune_dspy.py` con CLI (`--role`, `--trainset`, `--metric`, `--num-candidates`, `--max-iters`, `--seed`)  ✅
3. Pilotos (BA y QA): `num_candidates=8`, `max_iters=8`, `seed=0`  ⚠️ pendiente (bloqueado por falta de proveedor DSPy)
4. Métricas: completitud YAML, cobertura negativa, latencia. Guardar en `artifacts/dspy/optimizer/...`  ⚠️ pendiente
5. Decisión: report en `artifacts/dspy/optimizer/report.md`; Go/No-Go para flag  ⚠️ pendiente

---

## 5. Integración con pipeline (Semana 3)
- [ ] Story ↔ testcase: campo `testcases_path` en `planning/stories.yaml`
- [ ] Subtareas DSPy: generar TODOs desde Unhappy Paths (`planning/tasks.csv`)
- [ ] Gate dev opcional: `STRICT_ACCEPTANCE=1 make dev STORY=S#` ejecuta lint de la historia
- [ ] Cross-check tests reales: script que detecte historias sin test pytest/Jest asociado a keywords DSPy
- [ ] Dashboard: grafica cobertura, latencia, incidencias (JSON → Grafana/MLflow)

---

## 6. Integración CI/CD (Semana 4)
- [ ] Tests dataset: validar schema JSONL, duplicados, required keys
- [ ] Lint en PRs: `make dspy-qa-lint` (usar `DSPY_QA_STUB=1` si no hay modelo)
- [ ] Job nocturno: `DSPY_QA_STUB=1 make dspy-qa && make dspy-qa-lint`
- [ ] Snapshot artefactos: versionar programa compilado + hash dataset + seed

---

## 7. Produktización y documentación
- [ ] Actualizar README (sección DSPy en producción)
- [ ] Crear `docs/dspy_playbook.md` (guía anotación, tuning, troubleshooting)
- [ ] Workshop interno: proceso de anotación y lectura de lint
- [ ] Roadmap Fase 8: activar flag `USE_OPTIMIZED_PROGRAMS`, automatizar re-tuning mensual

---

## 8. Métricas y reporting
- KPIs BA/QA: ver sección 1
- Operacionales: % historias con enlace Markdown, % subtareas DSPy completadas, tasa de falsos positivos/negativos lint
- Reporting: dashboard mensual + reunión DSPy/QA/Dev

---

## 9. Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Dataset sesgado/insuficiente | Modelos sobreajustados | Curación continua + eval set separado |
| Costos tuning altos | Cuellos en pipeline | Ajustar hyperparams, ejecutar off-peak |
| Divergencia sandbox/host | Resultados inconsistentes | Flags `DSPY_QA_SKIP_IF_MISSING` / `DSPY_QA_STUB`, documentar proveedores |
| Falta de tests reales | Lint sin respaldo | Gate dev + script cross-check tests |

---

## 10. Estado actual
- Plan Fase 7 documentado ✅
- Semana 1 ejecutada (dataset bootstrap):
  - Directorio `dspy_baseline/data/production/` + manifest con hashes ✅
  - `ba_train.jsonl` (3 ejemplos curados) y `ba_eval.jsonl` (1 ejemplo holdout) ✅
  - `qa_train.jsonl` / `qa_eval.jsonl` con escenarios felices/infelices y palabras clave ✅
  - Documentado progreso y gaps (falta sesión de anotación masiva) ✅
- Semana 2 en curso (optimización):
  - Wrapper `dspy_baseline/optimizers/mipro.py` + export en `__init__.py` ✅
  - CLI `scripts/tune_dspy.py` con parámetros de tuning ✅
  - Pilotos dependientes de proveedor DSPy (pendiente) ⚠️
- Pendientes inmediatos (detalle):
  1. **Piloto MIPROv2 (bloqueado por proveedor)**
     - Validar disponibilidad de un modelo accesible desde este entorno (codex_cli, vertex_cli o endpoint HTTP).
     - Instalar dependencias DSPy en la venv (`pip install dspy-ai datasets`).
     - Ejecutar `scripts/tune_dspy.py` por rol (`ba`, `qa`) usando los JSONL de `dspy_baseline/data/production/` y registrar artefactos en `artifacts/dspy/optimizer/`.
     - Comparar métricas vs baseline y anexar reporte en `artifacts/dspy/optimizer/report.md`.
  2. **Sprint de anotación ampliado (≥150 ejemplos)**
     - Preparar pauta y checklist para revisores (campos obligatorios, estilo YAML/Markdown).
     - Convocar sesión interna de 1-2 días; distribuir conceptos por dominio (web/app/api) y complejidad (simple/medium/corporate).
     - Volcar los nuevos ejemplos en `dspy_baseline/data/production/*_train.jsonl`, actualizando `manifest.json` (hash + fecha + curator).
  3. **Automatización y observabilidad inicial**
     - Definir job nocturno (script o Jenkins/GitHub Actions) que corra `DSPY_QA_STUB=1 make dspy-qa && make dspy-qa-lint` para validar coherencia diaria de datasets/políticas.
     - Instrumentar un dashboard mínimo (tabla HTML o notebook) con métricas: tamaño dataset, cobertura lint, errores recientes.
     - Documentar procedimiento en `docs/dspy_playbook.md` (pendiente de creación).
