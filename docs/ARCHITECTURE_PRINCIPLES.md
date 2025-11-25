# Architecture And Code Quality Principles (Phase 7)

This document captures the design/architecture and code‑quality principles we adopt across the pipeline. It serves as a compact reference for reviews, refactors, and future contributions.

## 1) Design & Architecture Principles

Single Responsibility Principle (SRP)
- Cada módulo / clase debe tener una sola razón para cambiar.
- Evita “God classes” y facilita testear y refactorizar.

Separation of Concerns (SoC)
- Separa claramente UI, lógica de negocio, acceso a datos, integración, etc.
- Reduce el impacto de cambios y hace más legible el sistema completo.

Low coupling, high cohesion
- Alta cohesión: cosas que están juntas hacen tareas relacionadas.
- Bajo acoplamiento: pocas dependencias rígidas entre módulos.
- Facilita mantenimiento, testeo y reemplazo de componentes.

SOLID (además de SRP)
- OCP (Open/Closed): abierto a extensión, cerrado a modificación.
- LSP (Liskov): subclases deben sustituir a la superclase sin romper nada.
- ISP (Interface Segregation): mejor varias interfaces pequeñas que una gigante.
- DIP (Dependency Inversion): depende de abstracciones, no de implementaciones.

KISS (Keep It Simple, Stupid)
- Prefiere soluciones simples que cubran el caso real antes que arquitectura innecesariamente compleja.

YAGNI (You Aren’t Gonna Need It)
- No implementes hoy lo que quizá necesitarás mañana.
- Menos código, menos bugs, menos deuda.

Design for testability
- Inversión de dependencias, interfaces y adaptadores, evitar singletons y estado global oculto.
- Facilita tests unitarios/integración desde el principio.

## 2) Principios de calidad del código

DRY (Don’t Repeat Yourself)
- Evitar duplicar lógica; centralizar reglas de negocio.

Clean Code (código limpio)
- Nombres claros y significativos; funciones/métodos cortos; evitar exceso de parámetros.
- Comentarios solo donde aportan contexto (no para explicar código confuso).

Defensive Programming
- Validar entradas; manejar errores explícitamente; no asumir que “eso nunca va a pasar”.

Error handling coherente
- Estrategia clara de excepciones/retornos; logs con contexto suficiente.

Security by design
- Validar y sanitizar datos de entrada; gestión segura de credenciales/secretos; principio de mínimo privilegio.

## 3) Cómo se aplican en esta branch

- Logging estandarizado (RUN/SKIP/ERROR) por área ([DEV]/[QA]) con mensajes accionables.
- Summaries estructurados (dev_summary.json, qa_summary.json) con paths relativos y RC normalizados.
- Normalización de “skip” como éxito (rc=0); 127 reservado para herramientas ausentes.
- Refactors planificados (bajo acoplamiento/alta cohesión): separar loader/validator/cli en drivers, extraer runner util para subprocess/env.
- Testabilidad: smokes backend/web; tests unitarios ligeros en driver layer; mocks para detecciones de toolchain.
- Seguridad en shell/env: añadir PYTHONPATH sin sobrescribir; preferir listas de args en subprocess donde sea viable.

## 4) Checklist de aplicación (extracto)

- [x] Prefijos de log unificados por rol/área.
- [x] RC de skip normalizado a 0 en QA; summaries con RC/estatus normalizados.
- [x] Paths relativos en summaries (portables).
- [x] Drivers SRP/SoC (split loader/validator/cli). BUG-7.2-001 Fixed
- [x] Runner util (subprocess/env) + tests.
- [x] Endurecimiento shell/env (7.4): validator bloquea chaining/redirecciones; runner usa argv (shell=False) por defecto.
- [ ] Linting/typing básico en módulos nuevos.

---

## Bugs

### BUG-7.2-001: drivers/registry.py no reexporta load_driver ni VALID_CATEGORIES

**Severity**: High (rompe imports existentes)

**Context**: Fase 7.2 refactorizó el driver layer separando validator/loader/cli (SRP/SoC). El módulo `registry.py` se convirtió en un wrapper legacy que solo reexporta `main` para preservar el CLI (`python -m drivers.registry`), pero no reexporta las funciones que otros módulos importan.

**Reproduction**:
```bash
python -c "from drivers.registry import load_driver; print('OK')"
# ImportError: cannot import name 'load_driver' from 'drivers.registry'
```

**Affected files** (importan desde `drivers.registry`):
- `scripts/run_dev.py:19` - `from drivers.registry import load_driver`
- `scripts/run_qa.py:9` - `from drivers.registry import load_driver`
- `scripts/orchestrate.py:25` - `from drivers.registry import load_driver, VALID_CATEGORIES`
- `scripts/drivers_scaffold.py:13` - `from drivers.registry import load_driver`
- `scripts/drivers_show.py:13` - `from drivers.registry import load_driver, VALID_CATEGORIES`

**Current state**: `drivers/registry.py` (líneas 1-3):
```python
from .cli import main  # re-export for python -m drivers.registry
```

**Fix required**: Agregar reexports en `drivers/registry.py`:
```python
from .cli import main  # re-export for python -m drivers.registry
from .loader import load_driver, VALID_CATEGORIES  # re-export for backward compatibility
```

**Alternative fix**: Actualizar todos los imports para usar directamente `drivers.loader`:
```python
from drivers.loader import load_driver, VALID_CATEGORIES
```

**Status**: Fixed

**Resolution**: `drivers/registry.py` ahora reexporta correctamente:
```python
from .cli import main
from .loader import load_driver
from .validator import VALID_CATEGORIES
```
Verificado: todos los imports existentes funcionan correctamente.

---

### BUG-7.3-001: run_dev.py IndentationError en _run_emb function

**Severity**: Critical (rompe ejecución de Dev)

**Context**: Fase 7.3 integró `run_driver_cmd` en `run_dev.py` pero la función helper `_run_emb` quedó con indentación incorrecta.

**Reproduction**:
```bash
python -c "from scripts.run_dev import main"
# IndentationError: unexpected unindent at line 441
```

**Affected file**: `scripts/run_dev.py:441`
```python
                    # Execute optional commands (best‑effort, logs in run_dir)
            def _run_emb(cmd: str, name: str) -> int:  # ← Indentación incorrecta (4 niveles en vez de 5)
                if not cmd:
                    return 0
```

**Expected**: La función `_run_emb` debe estar indentada dentro del bloque `try` del embedded driver execution.

**Fix required**: Corregir indentación de `_run_emb` (líneas 441-445).

**Status**: Fixed
**Resolution**: Reescrita `_run_emb` para delegar en `run_driver_cmd` con indentación correcta y logs estandarizados. Ver `scripts/run_dev.py:435-452`.

---

### BUG-7.3-002: run_dev.py no importa run_driver_cmd

**Severity**: High (NameError en runtime)

**Context**: `run_dev.py` usa `run_driver_cmd` (líneas 445, 558) pero no tiene el import correspondiente.

**Reproduction** (después de corregir BUG-7.3-001):
```bash
# Al ejecutar Dev con drivers habilitados
# NameError: name 'run_driver_cmd' is not defined
```

**Affected file**: `scripts/run_dev.py`
- Línea 445: `return run_driver_cmd(cmd, f"embedded_{emb.id}_{name}", ROOT, logf, logger, role="DEV")`
- Línea 558: `return run_driver_cmd(cmd, name, ROOT, logf, logger, role="DEV")`

**Fix required**: Agregar import al inicio del archivo:
```python
from scripts.utils.runner import run_driver_cmd
```

**Status**: Fixed
**Resolution**: Agregado `from scripts.utils.runner import run_driver_cmd` en encabezado de `scripts/run_dev.py`. Verificado que `run_dev.py` compila y los tests de runner pasan.

**Note**: `scripts/run_qa.py:10` SÍ tiene el import correcto.

---

### BUG-7.4-001: esp32c3_riscv.yaml usa operador && prohibido

**Severity**: High (bloquea validación de drivers)

**Context**: Fase 7.4 endureció la validación de comandos en drivers para prevenir shell injection. El validator ahora rechaza operadores de chaining (`&&`, `||`, `;`, `|`, `>`, `<`) en comandos de build/test/lint.

**Reproduction**:
```bash
python -m drivers.registry validate --all
# ❌ embedded/esp32c3_riscv.yaml: build.command contains disallowed shell operators (use single commands)
```

**Affected file**: `drivers/embedded/esp32c3_riscv.yaml:24`
```yaml
build:
  command: idf.py set-target esp32c3 && idf.py build
```

**Root cause**: El comando usa `&&` para encadenar dos comandos, lo cual viola las nuevas reglas de seguridad de 7.4.

**Technical analysis**:
- `shlex.split("idf.py set-target esp32c3 && idf.py build")` → `['idf.py', 'set-target', 'esp32c3', '&&', 'idf.py', 'build']`
- Con `shell=False`, subprocess intentaría ejecutar `&&` como binario, fallando
- Validator correctamente rechaza este patrón inseguro

**Fix options**:
1. **Script wrapper**: Crear `drivers/embedded/esp32c3_riscv/scripts/build.sh` que ejecute ambos comandos secuencialmente
2. **Comando único**: Usar solo `idf.py build` (set-target se configura una vez por proyecto)
3. **Pre-build hook**: Agregar campo `pre_build` en schema para comandos de setup (requiere cambio de schema)

**Recommended fix**: Opción 1 (script wrapper) - mantiene funcionalidad sin cambiar schema.

**Status**: Fixed
**Resolution**: Reemplazado `build.command` por un wrapper script:
`drivers/embedded/esp32c3_riscv/scripts/build.sh` (ejecuta `idf.py set-target esp32c3` y `idf.py build`).
Se marcó como ejecutable y drivers-validate vuelve a pasar.

---

### 7.4 — Endurecimiento shell/env (documentación de implementación)

**Drivers validator**
- Bloquea operadores peligrosos en `build/test/lint` (`&&`, `||`, `;`, `|`, `>`, `<`).
- Rechaza comandos multi‑línea y valida token inicial (binario/script) con patrón seguro.
- Archivo: `drivers/validator.py` (función `_validate_command_string`).

**Runner**
- Usa `shlex.split()` y ejecuta con `shell=False` cuando es posible; cae a `shell=True` solo si no se puede dividir.
- Añade PYTHONPATH para backend sin sobrescribir el resto del entorno.
- Archivo: `scripts/utils/runner.py` (`run_driver_cmd`).
