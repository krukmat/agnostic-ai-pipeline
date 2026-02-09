# Plan: Perfiles de ejecución de tests (sin integración / con integración)

## Objetivo
Definir dos perfiles de ejecución claros y reproducibles:

1. **Perfil sin integración**: rápido, estable, sin dependencias pesadas ni servicios externos.
2. **Perfil con integración**: incluye tests de integración (y opcionalmente `integration_real`) con manejo robusto de dependencias opcionales.

Además, estandarizar el tratamiento de imports opcionales con `skipif/importorskip` y logging explícito previo al skip.

---

## Problema actual (diagnóstico)

La ejecución global (`pytest -q`) falla en *collection* por dependencias no instaladas en el entorno base (`uvicorn`, `psutil`, `dspy`, `rorf`, `google.genai`, etc.).

Esto impide separar correctamente:
- errores reales de lógica,
- de ausencia de dependencias opcionales.

---

## Diseño de perfiles

## 1) Perfil **sin integración**

**Propósito**: feedback rápido en local/CI general.

- Incluye: `unit`
- Excluye: `integration`, `integration_real`

Comando recomendado:

```bash
pytest -m "unit and not integration and not integration_real" -q
```

Target Makefile sugerido:

```make
test-no-integration:
	PYTHONPATH=. $(PY) -m pytest -m "unit and not integration and not integration_real" -q
```

## 2) Perfil **con integración**

**Propósito**: validar wiring, flujo entre componentes y, cuando aplique, entorno real.

- Incluye: `unit`, `integration` y `integration_real`
- Debe tolerar faltantes opcionales vía skip explícito

Comandos recomendados:

```bash
pytest -m "unit or integration or integration_real" -q
pytest -m integration -q
pytest -m integration_real -q
```

Targets Makefile sugeridos:

```make
test-integration:
	PYTHONPATH=. $(PY) -m pytest -m integration -q

test-integration-real:
	PYTHONPATH=. $(PY) -m pytest -m integration_real -q

test-all:
	PYTHONPATH=. $(PY) -m pytest -q
```

---

## Política para dependencias opcionales (skip + logging)

### Regla
Si un test depende de librería opcional:

1. Comprobar disponibilidad al inicio del módulo/fixture.
2. Loguear motivo de skip con contexto.
3. Hacer skip explícito con `pytest.importorskip(...)` o `pytest.skip(..., allow_module_level=True)`.

### Sobre `debug.error`
No existe `debug.error` como API estándar en Python.

Lo correcto es usar `logging`:
- `logger.warning(...)` para skip esperado por entorno
- `logger.error(...)` si querés elevar severidad en CI/reporte

### Patrón recomendado

```python
import importlib.util
import logging
import pytest

logger = logging.getLogger(__name__)

if importlib.util.find_spec("psutil") is None:
    logger.warning("Skipping %s: optional dependency 'psutil' not installed", __name__)
    pytest.skip("optional dependency missing: psutil", allow_module_level=True)
```

Alternativa corta:

```python
pytest.importorskip("psutil", reason="optional dependency missing: psutil")
```

---

## Helper compartido recomendado

Crear `tests/utils/optional_deps.py` para evitar duplicación:

```python
def require_optional_dep(module_name: str, level: str = "warning") -> None:
    ...
```

Responsabilidades:
- validar `find_spec`
- loguear (`warning`/`error`)
- ejecutar `pytest.skip(..., allow_module_level=True)`

Beneficio: mensajes homogéneos y menor deuda de mantenimiento.

---

## Fases de implementación

1. **Normalizar markers** en `pytest.ini` (`unit`, `integration`, `integration_real`, opcionalmente `optional_dep`).
2. **Añadir targets** de Makefile para perfiles (`test-no-integration`, `test-integration`, `test-integration-real`, `test-all`).
3. **Crear helper** `tests/utils/optional_deps.py`.
4. **Aplicar skip+log** en tests que hoy fallan por imports opcionales.
5. **Validar por perfil** y reportar `passed/skipped/failed`.

---

## Criterios de aceptación

- El perfil **sin integración** corre limpio en entorno base.
- El perfil **con integración** no se rompe en *collection* por faltantes opcionales.
- Los skips de opcionales quedan auditables con razón clara en logs.
- `pytest -q` deja de fallar por `ModuleNotFoundError` evitables en tests opcionales.
