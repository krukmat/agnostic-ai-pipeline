# Fase 4 – Integración DSPy ↔ Product Owner

**Objetivo**  
Alinear `scripts/run_product_owner.py` con `planning/requirements.yaml` generado por DSPy, asegurando que `product_vision.yaml` y `product_owner_review.yaml` mantengan la calidad y estructura necesarias para el pipeline multi-role.

**Duración estimada**: 3 días  
**Owner**: Equipo DSPy / Product Owner  
**Prerequisitos**:  
- Rama funcional `dspy-integration` (contiene `dspy_baseline/` y el target `dspy-ba`).  
- Servidor LLM (Ollama u otro) accesible con el mismo modelo utilizado en Fase 3.  
- `planning/requirements.yaml` actualizado con salida DSPy (incluye `meta.original_request`).

---

## 1. Estado actual
- `planning/requirements.yaml` generado por DSPy contiene únicamente `meta`, `functional_requirements`, `non_functional_requirements` y `constraints`.  
- El PO tradicional esperaba secciones adicionales (overview, stakeholders, personas, metrics) provenientes del BA clásico.  
- `extract_original_concept()` sigue funcionando porque `meta.original_request` se conserva.  
- El prompt `prompts/product_owner.md` continúa referenciando secciones que podrían faltar.

---

## 2. Plan de trabajo detallado

1. **Revisión del prompt y dependencias (½ día)**
   - Ubicación: `prompts/product_owner.md`.  
   - Marcar los campos obligatorios: overview, stakeholders, personas, métricas, riesgos.  
   - Decidir si:
     - (A) Se amplía la salida DSPy para incluir dichos campos.  
     - (B) Se ajusta el prompt del PO para que infiera la falta de información directamente desde el concepto y los requisitos básicos.

2. **Opciones para enriquecer la salida BA (1 día)**
   - **Opción A** (enriquecer DSPy):
     - Modificar `dspy_baseline/modules/ba_requirements.py` agregando campos adicionales al signature (`overview`, `stakeholders`, `personas`, etc.).  
     - Actualizar la función `generate_requirements` y revisar el YAML resultante.  
     - Verificar parseo con `python -c "import yaml; yaml.safe_load(open('artifacts/dspy/requirements_dspy.yaml'))"`.
   - **Opción B** (ajustar PO):
     - Actualizar `build_user_payload` para pasar explícitamente el concepto original y, si falta información, instruir al LLM a generarla.  
     - Ajustar el prompt para que pueda producir visiones completas aun con requisitos resumidos.

3. **Validación funcional (1 día)**
   - Ejecutar los siguientes comandos para dos conceptos de distintos niveles:
     ```bash
     make dspy-ba CONCEPT="Plataforma de eventos con registro y check-in"
     make po
     make dspy-ba CONCEPT="Sistema ERP para manufactura"
     make po
     ```
   - Revisión manual:
     - `planning/product_vision.yaml`: ¿contiene visión completa, objetivos y métricas?  
     - `planning/product_owner_review.yaml`: ¿contiene feedback/ajustes coherentes y referencias al concepto?  
     - `artifacts/debug/debug_product_owner_response.txt`: examinar bloques `VISION` y `REVIEW` si algo falta.

4. **Ajustes finales**
   - Si la salida PO carece de campos esperados, iterar sobre el prompt o la salida DSPy hasta que la visión y el review recuperen su calidad habitual.  
   - Mantener la sanitización YAML (`sanitize_yaml`) para prevenir errores.

5. **Documentación**
   - Registrar hallazgos en este documento (sección “Resultados”).  
   - Actualizar `DSPY_INTEGRATION_PLAN.md` con conclusiones de la fase.  
   - Guardar ejemplos de visión/review en `artifacts/dspy/product_owner/` (crear carpeta si se requiere).

---

## 3. Métricas de éxito
- `make po` produce archivos parseables y listos para el pipeline (sin warnings críticos).  
- La visión incluye: resumen de producto, objetivos claros, métricas de éxito preliminares.  
- El review entrega feedback accionable (aprobación/rechazo con razones).  
- QA puntual: revisión manual de al menos dos conceptos con estatus “OK”.

---

## 4. Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| YAML DSPy demasiado breve | Visión/Review pobres | Enriquecer DSPy o prompt del PO |
| Sanitización elimina campos | Información perdida | Revisar `sanitize_yaml` y ajustar |
| LLM responde con bloques incompletos | Falta contextos clave | Añadir instrucciones explícitas en el prompt |

---

## 5. Resultados y decisiones
- **Fecha de ejecución**: 2025-11-03  
- **Conceptos probados**:
  - Plataforma de eventos con registro y check-in (DSPy BA + PO)
  - Sistema ERP para manufactura con gestión de producción (DSPy BA)
  - Demo concept (comprobación rápida post-refactor)
- **Observaciones**:
  - `planning/requirements.yaml` ahora incluye `meta.original_request` después del nuevo target `make ba`.
  - `make po` genera visión sin errores; en algunos prompts el bloque REVIEW no se incluye (seguir ajustando prompt).
- **Próximos pasos**:
  - Afinar prompt del PO para garantizar siempre REVIEW.
  - Pasar a Fase 5 (Architect) usando los mismos conceptos para continuidad.
