# Architect DSPy Refactor Plan

## Objetivo
Ajustar la integración DSPy de Arquitecto para que funcione con modelos que no devuelven `stories_yaml`, `epics_yaml` y `architecture_yaml` en bloques separados. El plan busca estabilidad en la salida (incluyendo Vertex/Gemini y LLMs locales) sin depender de `JSONAdapter` para múltiples campos.

## Principales Cambios Propuestos
1. **Simplificar la firma DSPy** (`ArchitectSignature`)
   - Reemplazar los tres `OutputField` (`stories_yaml`, `epics_yaml`, `architecture_yaml`) por un único `response_yaml` con las tres secciones anidadas.
   - Mantener compatibilidad con el dataset actual (parser posterior generará los archivos `stories.yaml`, `epics.yaml`, `architecture.yaml`).

2. **Actualizar el prompt `prompts/architect.md`**
   - Incluir ejemplo explícito en un solo bloque con secciones `stories:`, `epics:`, `architecture:`.
   - Resaltar la necesidad de incluir siempre las tres secciones, aunque haya contenido mínimo.

3. **Agregar un post-procesador en `_run_dspy_architect()`**
   - Convertir el contenido de `response_yaml` en los tres ficheros esperados.
   - Si alguna sección está ausente, insertar una versión vacía para evitar que DSPy falle.

4. **Desactivar `JSONAdapter`** en Arquitecto hasta que se valide el nuevo formato.
   - Reducir dependencias de LiteLLM con JSON estricto.
   - Limitar la configuración de DSPy a `dspy.context(lm=...)` mientras no se verifique la compatibilidad con function-calling.

## Tareas
1. [x] Actualizar `dspy_baseline/modules/architect.py` para usar `response_yaml` y adaptar `ArchitectModule`.
2. [x] Modificar `scripts/run_architect.py` para parsear `response_yaml` y escribir `stories/epics/architecture`.
3. [x] Revisar `prompts/architect.md` con ejemplo único que incluya las tres secciones.
4. [x] Desactivar cualquier `JSONAdapter` en `run_architect.py` mientras dure el refactor.
5. [ ] Ajustar tests/manuales para validar que, aun con respuestas parciales, el parser aplanado produce los archivos requeridos.

**Estado 2025-11-18:** Tareas 1–4 completadas. El parser ya acepta respuestas parciales y rellena los YAML correspondientes. Falta una corrida completa (con proveedor confiable) para validar y documentar resultados.

## Validación
- Ejecutar `scripts/generate_architect_dataset.py` con un modelo disponible (idealmente Vertex/Gemini cuando haya permisos) y verificar que no aparezcan errores de "Actual output fields: []".
- Confirmar que los archivos `stories.yaml`, `epics.yaml`, `architecture.yaml` se regeneran correctamente tanto en DSPy como en legacy.

## Riesgos
- Los datasets existentes (jsonl) sólo contienen `stories_yaml`, `epics_yaml`, `architecture_yaml`. Al cambiar la firma, necesitaremos un parser bidireccional si usamos los datasets antiguos para tuning.
- Los scripts de BA/PO se mantienen igual; no hay riesgo allí.
