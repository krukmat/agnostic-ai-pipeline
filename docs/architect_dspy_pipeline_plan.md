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
    stories_module = StoriesEpicsModule()
    architecture_module = ArchitectureModule()
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

- Cada módulo trae su LM limitado (`max_output_tokens`) para evitar truncados y permitir tuning independiente.
- `_convert_stories_epics_to_yaml` y `_sanitize_yaml_block` limpian fences ``` y vuelcan listas/dict a YAML estable antes de escribir en `planning/`.

**3. Compatibilidad Legacy vs DSPy**

- `config.yaml` mantiene `features.use_dspy_architect`; `_use_dspy_architect()` (líneas 36-62) permite conmutar el pipeline desde config/env.
- README.md (sección *Architect role*) deja claro que el modo DSPy usa el pipeline modular y que el modo legacy sigue disponible sin cambios.

### Dataset generation

- `scripts/generate_architect_dataset.py` ahora ejecuta DOS llamadas LM por sample (StoriesEpicsModule y ArchitectureModule) y valida JSON/YAML antes de escribir.
- Las respuestas truncadas/invalidas se descartan automáticamente, conservando los mismos flags CLI (`--max-records`, `--min-score`, `--resume`).
- Esto nos permite alimentar MiPRO/MIPROv2 con muestras limpias sin depender de `run_architect_job` ni de archivos intermedios en `planning/`.
- `config.yaml` expone `roles.architect.output_caps.{stories,architecture}` para controlar los `max_output_tokens` de cada módulo sin tocar código (por defecto usan 8 % del presupuesto global con un mínimo de 600 tokens).

### Modo Architecture‑Only (`features.architect.arch_only`)

- Propósito: generar dataset de Architect enfocando solo la etapa de arquitectura y usando historias/épicas mínimas derivadas de BA para reducir truncado, coste y dependencias.
- Activación: en `config.yaml` añade:

  ```yaml
  features:
    architect:
      arch_only: true
  ```

- Comportamiento:
  - El generador de dataset salta `StoriesEpicsModule` y arma un stub de historias/épicas a partir de BA (≤3 historias, una frase) con `_build_stub_stories_from_requirements()`.
  - Luego llama únicamente a `ArchitectureModule` con ese JSON de soporte.
  - Registra el modo elegido y el LM real usado: “MODE=arch_only. Using stubbed stories. …”.

- Referencias de código (clickables):
  - Leer flag y loguear modo/LM: `scripts/generate_architect_dataset.py:350-368`, `scripts/generate_architect_dataset.py:372-380` y `scripts/generate_architect_dataset.py:357-365`.
  - Construcción de stub: `scripts/generate_architect_dataset.py:223-276`.
  - Bifurcación del flujo (usar stub vs. DSPy stories): `scripts/generate_architect_dataset.py:417-435`.

- Ejecución sugerida (1–3 registros):
  ```bash
  PYTHONPATH=. .venv/bin/python scripts/generate_architect_dataset.py \
    --ba-path dspy_baseline/data/production/ba_train_plus_extra.jsonl \
    --out-train dspy_baseline/data/production/architect_train.jsonl \
    --out-val dspy_baseline/data/production/architect_val.jsonl \
    --min-score 0.6 --max-records 3 --seed 42 --resume
  ```

## Conclusión
Aunque la estructura modular ya está implementada, los modelos actuales (Gemini/T4 locales) siguen truncando salidas cuando la generación se hace en una sola llamada. La siguiente iteración deberá dividir efectivamente las llamadas (por ejemplo, stories vs arquitectura) o usar un LM con contexto suficiente (LoRA/Gemini Pro); sólo así podremos producir samples que pasen el filtro del dataset sin cortes.

En el corto plazo:
- Reduciremos tokens máximos por módulo y añadiremos métricas específicas (faltan Tareas 5 y 6).
- Ajustaremos prompts/evaluadores independientes para stories y arquitectura antes de relanzar MiPRO.
- Validaremos la escritura de `planning/*.yaml` con lotes pequeños para detectar truncados antes de escalar.
