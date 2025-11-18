# Arquitecto DSPy Modular Pipeline Plan

## Objetivo
Dividir el rol “Arquitecto” en varios módulos DSPy (stories/epics, arquitectura, PRD/tareas) para reducir truncamientos, mejorar la optimización (MIPRO) y facilitar su uso desde MiPRO.

## Módulos Propuestos
1. **Stories/Epics**
   - Entrada: contexto del producto (concepto + requirements + visión).
   - Salida: historias/épicas en JSON estructurado.
   - Firma DSPy: `GenerateStoriesAndEpics`.

2. **Arquitectura**
   - Entradas: contexto del producto + historias/épicas.
   - Salida: arquitectura backend/frontend/integraciones.
   - Firma DSPy: `GenerateArchitecture`.

3. **PRD/Tasks (opcional)**
   - Entradas: contexto + historias/épicas + arquitectura.
   - Salida: PRD/Tasks estructurado para herramientas de planificación.
   - Firma DSPy: `GeneratePRDAndTasks`.

## Tareas
1. [x] Crear nueva firma DSPy y módulo para stories/epics.
2. [x] Crear firma/módulo para arquitectura que consuma la salida anterior.
3. [ ] (Opcional) Crear firma/módulo para PRD/Tasks.
4. [x] Actualizar `scripts/run_architect.py` para orquestar los módulos en pipeline:
   - Generar stories/epics, alimentar al módulo de arquitectura, etc.
   - Escribir los resultados en `planning/stories.yaml`, `epics.yaml`, `architecture.yaml` (y opcional PRD/tareas).
5. [ ] Ajustar `prompts/*.md` específicos por módulo (cada módulo con ejemplos propios).
6. [ ] Actualizar métricas para MIPROv2 (uno por módulo).
7. [ ] Documentar y validar la nueva arquitectura (en docs y/o plan 9.X).

## Beneficios
- Prompts y salidas más cortas → menor probabilidad de truncación.
- Optimización (MIPRO) coherente (cada módulo tiene su métrica).
- Reutilización y reejecución independiente de cada etapa.
- Menor coste y mayor trazabilidad para MiPRO.

## Próximos pasos
- Solicitar aprobación para implementar la división modular.
- Al aprobarse, ejecutar las tareas 1–7, actualizando docs y tests.

## Implementación actual
- `dspy_baseline/modules/architect.py`: contiene las firmas/módulos `StoriesEpicsModule` y `ArchitectureModule` (PRD quedó opcional). `stories_epics_json` sustituye a los tres OutputField originales.
- `scripts/run_architect.py`: introduce `_run_dspy_pipeline()` para secuenciar ambos módulos, convertir el JSON de historias en `stories.yaml`/`epics.yaml`, y sanitizar el YAML de arquitectura.
- README/fase 9 ya mencionan la división modular y que el flag `use_dspy_architect` activa el pipeline DSPy pero mantiene el legacy disponible.
- El intento de muestreo pequeño (`generate_architect_dataset.py --max-records 5`) confirma que el truncado sigue ocurriendo con Gemini pese al pipeline; la siguiente iteración consistirá en dividir la ejecución en dos llamadas firmes (stories vs disposición técnica).

### Código incorporado (resumen)

**1. Nuevas firmas/módulos DSPy** (`dspy_baseline/modules/architect.py:1-88`)

```python
class StoriesEpicsSignature(dspy.Signature):
    concept: str = dspy.InputField(...)
    requirements_yaml: str = dspy.InputField(...)
    product_vision: str = dspy.InputField(...)
    complexity_tier: str = dspy.InputField(...)
    stories_epics_json: str = dspy.OutputField(...)

class StoriesEpicsModule(dspy.Module):
    def __init__(self) -> None:
        self.generate = dspy.Predict(StoriesEpicsSignature)

class ArchitectureSignature(dspy.Signature):
    ...
    stories_epics_json: str = dspy.InputField(...)
    architecture_yaml: str = dspy.OutputField(...)

class ArchitectureModule(dspy.Module):
    def __init__(self) -> None:
        self.generate = dspy.Predict(ArchitectureSignature)
```

- `stories_epics_json` encapsula historias y épicas en un único bloque para evitar pérdidas de contexto al pasar entre módulos.
- Ambos módulos normalizan `complexity_tier` para que MIPRO pueda reutilizar seeds simples/medium/corporate sin duplicar prompts.

**2. Orquestación del pipeline** (`scripts/run_architect.py:63-137`)

```python
def _run_dspy_pipeline(...):
    lm = build_lm_for_role("architect")
    stories_module = StoriesEpicsModule()
    architecture_module = ArchitectureModule()
    with dspy.context(lm=lm):
        stories_prediction = stories_module(...)
        architecture_prediction = architecture_module(
            ..., stories_epics_json=stories_prediction.stories_epics_json
        )
    stories_yaml, epics_yaml = _convert_stories_epics_to_yaml(
        stories_prediction.stories_epics_json
    )
    architecture_yaml = _sanitize_yaml_block(
        architecture_prediction.architecture_yaml
    )
    return {
        "stories_yaml": stories_yaml,
        "epics_yaml": epics_yaml,
        "architecture_yaml": architecture_yaml,
    }
```

- El contexto DSPy se abre una sola vez para compartir el mismo LM por ejecución y reducir overhead.
- `_convert_stories_epics_to_yaml` y `_sanitize_yaml_block` limpian fences ``` y vuelcan listas/dict a YAML estable antes de escribir en `planning/`.

**3. Compatibilidad Legacy vs DSPy**

- `config.yaml` mantiene `features.use_dspy_architect`; `_use_dspy_architect()` (líneas 36-62) permite conmutar el pipeline desde config/env.
- README.md (sección *Architect role*) deja claro que el modo DSPy usa el pipeline modular y que el modo legacy sigue disponible sin cambios.

## Conclusión
Aunque la estructura modular ya está implementada, los modelos actuales (Gemini/T4 locales) siguen truncando salidas cuando la generación se hace en una sola llamada. La siguiente iteración deberá dividir efectivamente las llamadas (por ejemplo, stories vs arquitectura) o usar un LM con contexto suficiente (LoRA/Gemini Pro); sólo así podremos producir samples que pasen el filtro del dataset sin cortes.

En el corto plazo:
- Reduciremos tokens máximos por módulo y añadiremos métricas específicas (faltan Tareas 5 y 6).
- Ajustaremos prompts/evaluadores independientes para stories y arquitectura antes de relanzar MiPRO.
- Validaremos la escritura de `planning/*.yaml` con lotes pequeños para detectar truncados antes de escalar.
