# Fase 2: DSPy BA Module (Baseline) - Implementation Guide

**Part of**: DSPy Comparison Plan (`DSPY_COMPARISON_PLAN.md`)
**Duration**: 3-5 días
**Status**: ✅ **COMPLETA** (2025-11-03)
**Pre-requisites**:
- ✅ Fase 0 Completa (Python 3.11.14 compatibility verified)
- ✅ Fase 1 Completa (Python 3.11.14 installed)

**Completion Summary**:
- ✅ All 5 manual tests passed (100% success rate)
- ✅ YAML válido generado en todos los casos
- ✅ Provider: Ollama local (granite4) funcionando correctamente
- ✅ Mejoras aplicadas vs documentación original (bugs corregidos, validaciones agregadas)
- ⬜ Warning DSPy menor (cosmético, no blocker)

---

## Scope

Implementar **solo BA role** con DSPy básico (sin optimización):

> ℹ️ **Nota de implementación**: El repositorio ya instala el paquete oficial `dspy-ai`, por lo que los módulos locales se ubican bajo `dspy_baseline/` para evitar un conflicto de nombres con la librería upstream. Todas las rutas indicadas a continuación se ajustaron en consecuencia.

- ✅ Usar `dspy.Predict` (no `ChainOfThought` ni optimizers todavía)
- ✅ Reutilizar `config.yaml` para credenciales LLM existentes
- ✅ Output a `artifacts/dspy/requirements_dspy.yaml`
- ✅ Baseline funcional para comparación Fase 3

---

## Estructura de Archivos a Crear

```
dspy_baseline/
├── __init__.py                    # Package init
├── modules/
│   ├── __init__.py
│   └── ba_requirements.py         # Signature + predictor BA
├── scripts/
│   ├── __init__.py
│   └── run_ba.py                  # CLI wrapper
└── config/
    └── __init__.py
```

---

## Implementación Detallada

### Paso 1: Crear Estructura Básica

```bash
mkdir -p dspy_baseline/modules dspy_baseline/scripts dspy_baseline/config
touch dspy_baseline/__init__.py
touch dspy_baseline/modules/__init__.py
touch dspy_baseline/scripts/__init__.py
touch dspy_baseline/config/__init__.py
```

**Verification**:
```bash
tree dspy_baseline/
# Expected:
# dspy_baseline/
# ├── __init__.py
# ├── config/
# │   └── __init__.py
# ├── modules/
# │   └── __init__.py
# └── scripts/
#     └── __init__.py
```

---

### Paso 2: Implementar `dspy_baseline/modules/ba_requirements.py`

Create file with complete code:

```python
"""
DSPy module for Business Analyst requirements generation.
Baseline implementation using dspy.Predict (no optimization).
"""
import dspy
from typing import Optional
import yaml


class BARequirementsSignature(dspy.Signature):
    """Generate structured requirements from business concept."""

    # Inputs
    concept: str = dspy.InputField(
        desc="Business concept or idea description from stakeholder"
    )

    # Outputs
    title: str = dspy.OutputField(
        desc="Concise project title (max 100 chars)"
    )
    description: str = dspy.OutputField(
        desc="Detailed project description (2-3 paragraphs)"
    )
    functional_requirements: str = dspy.OutputField(
        desc="List of functional requirements in YAML format"
    )
    non_functional_requirements: str = dspy.OutputField(
        desc="List of non-functional requirements in YAML format"
    )
    constraints: str = dspy.OutputField(
        desc="Project constraints and assumptions in YAML format"
    )


class BARequirementsModule(dspy.Module):
    """Business Analyst module using DSPy."""

    def __init__(self):
        super().__init__()
        # Use basic Predict (no Chain of Thought for baseline)
        self.generate = dspy.Predict(BARequirementsSignature)

    def forward(self, concept: str) -> dict:
        """
        Generate requirements from concept.

        Args:
            concept: Business idea description

        Returns:
            dict with requirements structure
        """
        # Call DSPy predictor
        prediction = self.generate(concept=concept)

        # Structure output as dict (similar to current BA output)
        result = {
            'title': prediction.title,
            'description': prediction.description,
            'functional_requirements': self._parse_yaml_field(
                prediction.functional_requirements
            ),
            'non_functional_requirements': self._parse_yaml_field(
                prediction.non_functional_requirements
            ),
            'constraints': self._parse_yaml_field(
                prediction.constraints
            )
        }

        return result

    def _parse_yaml_field(self, field_text: str) -> list:
        """
        Parse YAML string to list (best effort).

        ⚠️ WARNING: Esta lógica DUPLICA normalización existente en:
        - scripts/run_ba.py (BA tradicional ya parsea/valida YAML)
        - Potencial inconsistencia si ambas versiones divergen

        DECISIÓN REQUERIDA (Fase 4):
        - Centralizar parsing en módulo compartido (ej. scripts/common.py)
        - O documentar que DSPy y BA tradicional usan lógicas diferentes
        """
        try:
            # Try parsing as YAML
            parsed = yaml.safe_load(field_text)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]
            else:
                # Fallback: split by lines
                return [line.strip('- ') for line.strip('\n')
                        if line.strip()]
        except Exception:
            # Fallback: treat as plain text list
            return [line.strip('- ') for line in field_text.split('\n')
                    if line.strip()]


def generate_requirements(concept: str, lm: Optional[dspy.LM] = None) -> dict:
    """
    Main entry point for BA requirements generation.

    Args:
        concept: Business idea description
        lm: Optional DSPy language model (uses default if None)

    Returns:
        Requirements dict ready for YAML serialization
    """
    # Configure LM if provided
    if lm:
        dspy.configure(lm=lm)

    # Create module and run
    ba_module = BARequirementsModule()
    result = ba_module.forward(concept=concept)

    return result
```

**Verification**:
```bash
python -c "from dspy_baseline.modules.ba_requirements import BARequirementsSignature; print('OK')"
```

---

### Paso 3: Implementar `dspy_baseline/scripts/run_ba.py`

Create CLI wrapper with typer:

```python
#!/usr/bin/env python3
"""
CLI script to run DSPy BA module.
Usage: python dspy_baseline/scripts/run_ba.py --concept "Your business idea"
"""
from pathlib import Path
from typing import Optional
import os
import sys

import dspy
import typer
import yaml

ROOT = Path(__file__).parent.parent.parent
DEFAULT_CACHE_DIR = ROOT / "artifacts" / "dspy" / "cache"
DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSPY_CACHEDIR", str(DEFAULT_CACHE_DIR))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dspy_baseline.modules.ba_requirements import generate_requirements


app = typer.Typer()


def load_llm_config() -> dspy.LM:
    """
    Load LLM configuration from config.yaml (reuse existing config).
    Returns configured DSPy LM.

    TODO: Este mapeo es SIMPLIFICADO y NO maneja:
    - temperature, max_tokens (ya gestionados en config.yaml por role)
    - API keys (DSPy usa env vars: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
    - common.Client abstraction (scripts/common.py ya hace esto)

    DECISIÓN REQUERIDA:
    - Opción A: Reutilizar common.Client completamente (DSPy puede wrapearlo)
    - Opción B: Duplicar configuración (consistencia difícil de mantener)
    - Opción C: Crear adapter que traduzca config.yaml → DSPy LM config
    """
    config_path = ROOT / "config.yaml"

    if not config_path.exists():
        typer.echo(
            f"Warning: {config_path} not found, using default LM openai/gpt-4",
            err=True,
        )
        return dspy.LM("openai/gpt-4")

    config = yaml.safe_load(config_path.read_text())
    ba_config = config.get("roles", {}).get("ba", {})

    provider = ba_config.get("provider", "openai")
    model = ba_config.get("model", "gpt-4")

    if provider == "openai":
        lm_name = f"openai/{model}"
    elif provider == "claude_cli":
        lm_name = f"anthropic/{model}"
    elif provider == "ollama":
        lm_name = f"ollama/{model}"
    else:
        typer.echo(
            f"Warning: Unknown provider '{provider}', falling back to openai/gpt-4",
            err=True,
        )
        lm_name = "openai/gpt-4"

    # NOTE: Asegurarse que API keys estén en env vars antes de ejecutar
    # export OPENAI_API_KEY="..." (DSPy las lee automáticamente)
    return dspy.LM(lm_name)


@app.command()
def main(
    concept: str = typer.Option(..., help="Business concept description"),
    output: Path = typer.Option(
        ROOT / "artifacts" / "dspy" / "requirements_dspy.yaml",
        help="Output YAML file path",
    ),
    verbose: bool = typer.Option(False, help="Verbose output"),
) -> None:
    """Generate BA requirements using DSPy."""

    typer.echo("🤖 DSPy BA Generator")
    typer.echo(f"Concept: {concept[:80]}{'...' if len(concept) > 80 else ''}")

    if verbose:
        typer.echo("Loading LLM config...")
    lm = load_llm_config()

    if verbose:
        typer.echo("Generating requirements with DSPy...")

    try:
        requirements = generate_requirements(concept=concept, lm=lm)
    except Exception as e:
        typer.echo(f"❌ Error generating requirements: {e}", err=True)
        raise typer.Exit(1) from e

    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        yaml.dump(
            requirements,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    )

    typer.echo(f"✅ Requirements generated: {output}")

    if verbose:
        typer.echo("\nPreview:")
        typer.echo(
            yaml.dump(
                requirements,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        )


if __name__ == "__main__":
    app()
```

**Make executable**:
```bash
chmod +x dspy_baseline/scripts/run_ba.py
```

---

### Paso 4: Agregar Target al Makefile

Add to `Makefile`:

```makefile
# DSPy BA module target
.PHONY: dspy-ba
dspy-ba:
	@echo "Running DSPy BA module..."
	$(PY) dspy_baseline/scripts/run_ba.py --concept "$(CONCEPT)" --verbose
```

**Verification**:
```bash
make -n dspy-ba CONCEPT="test"
# Should show: .venv/bin/python dspy_baseline/scripts/run_ba.py --concept "test" --verbose
```

---

### Paso 5: Test Manual Inicial

```bash
# Ensure DSPy dependencies installed
pip install dspy-ai>=3.0.3

# Test básico
make dspy-ba CONCEPT="Un blog personal con posts y comentarios"

# Verificar output
cat artifacts/dspy/requirements_dspy.yaml

# Expected: YAML válido con structure:
# title: ...
# description: ...
# functional_requirements: [...]
# non_functional_requirements: [...]
# constraints: [...]
```

---

## Entregables

- [x] `dspy_baseline/` package structure creada (4 directorios, 4 `__init__.py`)
- [x] `dspy_baseline/modules/ba_requirements.py` implementado (102 líneas) con:
  - `BARequirementsSignature` (DSPy signature class con few-shot example)
  - `BARequirementsModule` (DSPy module con `dspy.Predict`)
  - `generate_requirements()` función principal
- [x] `dspy_baseline/scripts/run_ba.py` CLI funcional (117 líneas)
- [x] Makefile target `dspy-ba` agregado (con validación CONCEPT requerido)
- [x] **Genera YAML válido en `artifacts/dspy/requirements_dspy.yaml`** ✅
- [x] **Probado con 5 concepts manualmente** ✅ (2025-11-03)

### Resultados de Tests Manuales (2025-11-03)

**Provider**: Ollama local (granite4)
**Concepts probados**: 5 (simple → compleja)

| Concept | FRs | NFRs | Constraints | YAML válido | Tiempo aprox |
|---------|-----|------|-------------|-------------|--------------|
| Blog personal | 5 | 3 | 2 | ✅ | ~20s |
| Inventario retail | 6 | 4 | 3 | ✅ | ~25s |
| SaaS multi-tenant | 8 | 5 | 4 | ✅ | ~27s |
| Delivery app | 7 | 4 | 4 | ✅ | ~22s |
| Plataforma educativa | 6 | 4 | 3 | ✅ | ~24s |

**Success rate**: 5/5 (100%)

**Observaciones**:
- ✅ Todos generan YAML válido parseado exitosamente
- ✅ Estructura consistente (id, description, priority en cada requirement)
- ✅ Escalabilidad verificada: concepts complejos → más requirements
- ✅ Calidad semántica: requirements específicos al dominio
- ⚠️ Warning DSPy menor: recomienda usar `module()` en lugar de `module.forward()` (no blocking)

---

## Findings y Mejoras Aplicadas (2025-11-03)

### Mejoras Implementadas vs Código Documentado

**1. Bug de Sintaxis Corregido** (línea 169 de esta guía)

**Código documentado (INCORRECTO)**:
```python
return [line.strip('- ') for line.strip('\n')  # ❌ Syntax error
                        if line.strip()]
```

**Código implementado (CORRECTO)**:
```python
lines = [
    line.strip("- ").strip()
    for line in field_text.splitlines()  # ✅ Correcto
    if line.strip()
]
return lines
```

**2. Validación de Campo Vacío Agregada**

Implementación proactiva de la solución al "Problema Común 3":
```python
def _parse_yaml_field(self, field_text: str) -> List[Any]:
    if not field_text or field_text.strip() == "":  # ✅ Validación agregada
        return []
```

**3. Few-Shot Example Integrado**

Solución al "Problema Común 1" ya incluida en el signature:
```python
class BARequirementsSignature(dspy.Signature):
    """Generate structured requirements from a business concept.

    Output format example for functional_requirements:  # ✅ Previene texto libre
    - id: FR001
      description: User can create blog posts
      priority: High
    """
```

**4. DSPY_CACHEDIR Configurado Automáticamente**

Implementado desde "Debugging Tips" en el script principal:
```python
DEFAULT_CACHE_DIR = ROOT / "artifacts" / "dspy" / "cache"
DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSPY_CACHEDIR", str(DEFAULT_CACHE_DIR))
```

**5. Type Hints y Best Practices**
- Type annotations completos en todas las funciones
- Exception chaining (`raise ... from exc`)
- Lint-aware comments (`# noqa: E402`)

### Warning DSPy (No Blocker)

**Mensaje**: `Calling module.forward(...) is discouraged. Please use module(...) instead.`

**Fix recomendado**:
```python
# En dspy_baseline/modules/ba_requirements.py línea 101
# Actual:
result = ba_module.forward(concept=concept)

# Cambiar a:
result = ba_module(concept=concept)
```

**Impacto**: Cosmético, no afecta funcionalidad. Ambos métodos funcionan correctamente.

---

## Ajustes Esperados Durante Implementación

### Problema Común 1: DSPy genera texto libre en lugar de YAML estructurado

**Síntoma**: Output no es YAML parseable

**Solución**: Agregar ejemplos en docstring de Signature (few-shot manual)

```python
class BARequirementsSignature(dspy.Signature):
    """Generate structured requirements from business concept.

    Output format example for functional_requirements:
    - id: FR001
      description: User can create blog posts
      priority: High
    - id: FR002
      description: User can comment on posts
      priority: Medium
    """
    # ... rest of signature
```

### Problema Común 2: Credenciales no se pasan correctamente

**Síntoma**: `AuthenticationError` o `API key not found`

**Solución**: Exportar env vars antes de correr

```bash
export OPENAI_API_KEY="sk-..."
# O para otros providers:
export ANTHROPIC_API_KEY="..."
export VERTEX_PROJECT="..."

make dspy-ba CONCEPT="..."
```

### Problema Común 3: Output no matchea schema esperado

**Síntoma**: Campos faltantes o formato incorrecto

**Solución**: Validar y transformar en `_parse_yaml_field`

```python
# En ba_requirements.py, mejorar _parse_yaml_field:
def _parse_yaml_field(self, field_text: str) -> list:
    # Add validation
    if not field_text or field_text.strip() == "":
        return []

    # Add debug logging if needed
    print(f"DEBUG: Parsing field: {field_text[:100]}...")

    # Rest of parsing logic...
```

Documentar diferencias encontradas para revisión en Fase 4 (análisis).

---

## Out of Scope (Recordatorio)

**NO implementar en Fase 2**:

- ❌ Optimización con MIPROv2 (solo baseline en esta fase)
- ❌ Otros roles (QA, Architect, Dev)
- ❌ MLflow tracking (agregar después si útil)
- ❌ A2A integration
- ❌ Dataset creation (viene en Fase 3 si ITERATE)

**Razón**: Validar primero que DSPy baseline funciona antes de optimizar.

---

## Criterio de Éxito Fase 2

Run these checks to verify completion:

```bash
# 1. Estructura creada
ls dspy_baseline/modules/ba_requirements.py  # Existe ✅
ls dspy_baseline/scripts/run_ba.py           # Existe ✅

# 2. Ejecuta sin errores
make dspy-ba CONCEPT="Un blog simple"
echo $?  # Exit code 0 ✅

# 3. Genera YAML válido
python -c "import yaml; yaml.safe_load(open('artifacts/dspy/requirements_dspy.yaml'))"
echo $?  # Exit code 0, no exception ✅

# 4. Contiene campos esperados
grep -q "functional_requirements" artifacts/dspy/requirements_dspy.yaml && echo "✅ FR found"
grep -q "non_functional_requirements" artifacts/dspy/requirements_dspy.yaml && echo "✅ NFR found"
grep -q "title" artifacts/dspy/requirements_dspy.yaml && echo "✅ Title found"

# 5. Manual review: Calidad aceptable
cat artifacts/dspy/requirements_dspy.yaml
# Humano revisa que el contenido tenga sentido ✅
```

**All checks pass** → Fase 2 completa, proceder a Fase 3

---

## Debugging Tips

### Ver qué hace DSPy internamente

```bash
# Activar cache directory para inspeccionar
export DSPY_CACHEDIR=/tmp/dspy_cache
python dspy_baseline/scripts/run_ba.py --concept "Test" --verbose

# Ver archivos de cache
ls -lh /tmp/dspy_cache/
```

### Ver el prompt enviado al LLM

```python
# En Python interactivo
import dspy
dspy.configure(lm=dspy.LM('openai/gpt-4'))

# After running a prediction
print(dspy.settings.lm.history())
```

### Test en Python interactivo

```python
python
>>> from dspy.modules.ba_requirements import generate_requirements
>>> import dspy
>>> dspy.configure(lm=dspy.LM('openai/gpt-3.5-turbo'))  # Cheaper for testing
>>> result = generate_requirements('Un blog')
>>> print(result)
>>> import yaml
>>> print(yaml.dump(result, default_flow_style=False))
```

### Verificar imports

```bash
# Check all imports work
python -c "
from dspy.modules.ba_requirements import BARequirementsSignature, BARequirementsModule, generate_requirements
print('All imports OK')
"
```

---

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'dspy'`

**Solution**:
```bash
pip install dspy-ai>=3.0.3
```

### Error: `ImportError: cannot import name 'generate_requirements'`

**Solution**: Check Python path
```python
import sys
print(sys.path)
# Ensure project root is in path
```

Or run from project root:
```bash
cd /Users/matiasleandrokruk/Documents/agnostic-ai-pipeline
python dspy_baseline/scripts/run_ba.py --concept "test"
```

### Error: DSPy returns empty responses

**Possible causes**:
1. API key not configured
2. Model doesn't support the signature format
3. Rate limiting

**Debug**:
```bash
export DSPY_DEBUG=1
python dspy_baseline/scripts/run_ba.py --concept "test" --verbose
```

---

## Next Steps After Fase 2

Once Fase 2 is complete and all criteria pass:

1. **Document results**: Create note with 3-5 sample outputs
2. **Compare manually**: Review DSPy output vs traditional BA output (same concept)
3. **Identify patterns**: Note what works well / what needs improvement
4. **Proceed to Fase 3**: Start comparison experiment with 30 concepts

See `DSPY_COMPARISON_PLAN.md` Fase 3 for next steps.

---

**Last updated**: 2025-11-03
**Estimated effort**: 3-5 days
**Prerequisites**: ✅ Python 3.11.14, ✅ All dependencies compatible
