# Fase 5 – Integración DSPy ↔ Architect

**Objetivo**  
Adaptar el flujo del rol Architect (`scripts/run_architect.py` / `make plan`) para consumir `planning/requirements.yaml` generado por DSPy y seguir entregando historias/epics consistentes con la visión.

**Duración estimada**: 4 días  
**Owner**: Equipo DSPy / Architect  
**Prerequisitos**:  
- `dspy-integration` actualizado con la salida DSPy (BA decomisado).  
- QA puntual de Product Owner completado.  
- Servidor LLM activo (`roles.architect` en `config.yaml`).

---

## 1. Estado inicial
- `planning/requirements.yaml` ahora contiene un YAML conciso (meta + listas FR/NFR/constraints).  
- El clasificador de complejidad (`classify_complexity_with_llm`) se basa en contenido textual; podría necesitar más contexto para no etiquetar todo como “simple”.  
- Los prompts del Architect (`prompts/architect*.md`) asumen que el YAML trae detalles (visiones, stakeholders) que ya no aparecen.

---

## 2. Plan técnico detallado

1. **Auditoría de dependencias (~½ día)**  
   - Identificar dónde se usa `planning/requirements.yaml` (funciones `load_references`, `extract_original_concept`).  
   - Verificar cómo se genera `stories.yaml` y si depende de campos ausentes.

2. **Enriquecimiento de entrada (1 día)**  
   - Valorar si conviene ampliar la salida DSPy (añadir overview, stakeholders) o ajustar el prompt.  
   - Opciones:  
     - A) Modificar `ba_requirements.py` para incluir secciones extra.  
     - B) Pasar el concepto original y resúmenes al clasificador para que genere historias más ricas.

3. **Actualización de prompts/scripts (1 día)**  
   - Revisar `prompts/architect_simple/medium/corporate.md` para incluir instrucciones explícitas cuando se presenten listas vacías.  
   - Ajustar la lógica en `scripts/run_architect.py` para no fallar si ciertos campos faltan.

4. **Validación funcional (1 día)**  
   - Pipeline recomendado para dos conceptos (ej. “Plataforma de eventos”, “ERP manufactura”):  
     ```bash
     make ba CONCEPT="..."
     make po
     make plan
     ```  
   - Revisar `planning/stories.yaml`, `epics.yaml`, `architecture.yaml` y `tasks.csv`.  
   - Confirmar que cada historia tiene `acceptance`, `status` y `todos` coherentes.

5. **Documentación**  
   - Registrar hallazgos en este documento (sección “Resultados”).  
   - Actualizar `DSPY_INTEGRATION_PLAN.md` y logs correspondientes.  
   - Guardar ejemplos representativos en `artifacts/dspy/architect/`.

---

## 3. Métricas de éxito
- `make plan` produce historias parseables y alineadas con la visión.  
- Complejidad detectada (simple/medium/corporate) es razonable para al menos dos conceptos.  
- QA puntual: revisión manual de historias y aceptación.  
- Arquitectura/epics generados sin bloqueos.

---

## 4. Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Clasificador marca todo como simple | Historias cortas/imprecisas | Enriquecer entrada (overview, stakeholders) |
| Falta de campos esperados | Errores en historias/epics | Ajustar prompts o script para usar datos mínimos |
| Demasiado contenido generativo | Latencia alta | Considerar precinct en prompts y lógica |

---

## 5. Resultados
- **Fecha**: 2025-11-03  
- **Conceptos probados**:
  - Plataforma de eventos con registro y check-in
  - Sistema ERP para manufactura con gestión de producción
- **Hallazgos**:
  - El clasificador asignó tier `medium` en ambos casos; generó historias detalladas aunque aún centradas en endpoints/backend.
  - Historias (`planning/stories.yaml`) y epics (`planning/epics.yaml`) se generaron sin errores; acceptance contiene escenarios “Happy Path / Edge Case”.
  - `make po` mantiene visiones coherentes tras el reintento automático del bloque REVIEW.
- **Siguientes pasos**:
  - Ajustar prompts/entrada para cubrir áreas UI/UX (historias actuales se enfocan en testing/backend).
  - Considerar enriquecer el YAML DSPy (overview, stakeholders) para mayor variedad.
