# Fase 3b.1 – Toggle Configurable BA (DSPy ↔ Legacy)

**Objetivo**  
Introducir en `config.yaml` un flag (`features.use_dspy_ba`) que permita activar/desactivar el BA basado en DSPy. Cuando esté en `false`, el pipeline debe utilizar el flujo legacy (`scripts/run_ba.py` anterior); cuando esté en `true`, usar `dspy_baseline`.

**Duración estimada**: 2 días  
**Owner**: Equipo DSPy / BA  
**Prerequisitos**: Rama `dspy-integration` con BA DSPy ya funcionando (`make ba` actual).

---

## 1. Diseño

- `config.yaml`: añadir bloque con feature flags.
  ```yaml
  features:
    use_dspy_ba: true
  ```
- `scripts/run_ba.py`: leer `features.use_dspy_ba` y decidir si:
  - Se delega al módulo DSPy (`_run_dspy` actual).
  - O se llama a la implementación legacy (restaurar, pero aislada, el código X).
- `Makefile`: `make ba` debe llamar a un pequeño wrapper (`scripts/run_ba.py --concept`), sin hardcodear DSPy; así el script decide según config.
- Orquestadores (`scripts/orchestrate.py`) ya importan `generate_requirements`; hay que asegurar que respete el flag.

---

## 2. Plan paso a paso

1. **Agregar flag en `config.yaml`** (½ día). Actualizar `Scripts/run_product_owner.py` y otros que lean config para evitar que fallen si `features` no existe.
2. **Refactor `scripts/run_ba.py`** (1 día).
   - Separar dos funciones `_run_dspy` y `_run_legacy`.
   - `_run_legacy` puede usar snapshot del código anterior (sin sanitización extra).
   - `generate_requirements` revisa `use_dspy_ba`, ejecuta el flujo y devuelve rutas y metadata.
3. **Reintroducir el script legacy** (opcional) en `scripts/ba_legacy.py` para evitar duplicado; importarlo desde `scripts/run_ba.py`.
4. **Makefile** (½ día): `make ba` vuelve a usar `scripts/run_ba.py --concept`. Cuando `use_dspy_ba` sea false, no se tocará `dspy_baseline`.
5. **QA**:
   - `use_dspy_ba: true` → `make ba`, `make po`, `make plan`.
   - `use_dspy_ba: false` → `make ba`, etc., observando que se genera el YAML legacy.
   - Verificar que `planning/requirements.yaml` tenga la estructura correcta en ambos casos.
6. **Documentación** (½ día):  
   - Actualizar README, `DSPY_INTEGRATION_PLAN.md`, y notas.
   - Registrar hallazgos en este documento.

---

## 3. Riesgos
- Duplicar lógica legacy: puede introducir bugs si no se mantiene.
- _Edge Case_: `use_dspy_ba` cambia en medio de un ciclo (depurar consistencia de YAML).
- QA adicional para asegurar que PO/Architect siguen funcionando con el modo legacy (si se usa como fallback).

---

## 4. Resultados y próximos pasos
- **Estado**: ✅ *Completado (2025-11-03)*  
- **Validación**:
  - `config.yaml` → `features.use_dspy_ba` probado en `True` (DSPy) y `False` (legacy).
  - `make ba` genera `planning/requirements.yaml` con la salida correspondiente en ambos modos.
- **Próximos pasos**: Mantener el flag documentado para futuros flujos; eliminar el legacy definitivamente una vez que DSPy se considere estable en producción.
