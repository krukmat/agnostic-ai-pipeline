# DSPy Comparison Plan

**Branch**: `feature/dspy-comparison`
**Objetivo**: Comparar outputs BA tradicional vs DSPy con datos reales para decisión merge/abandon basada en métricas objetivas.

> ℹ️ **Nota**: Los módulos locales viven bajo `dspy_baseline/` para evitar conflicto con el paquete upstream `dspy` instalado vía `dspy-ai`.

---

## ⚠️ Decisión Pre-requisito Crítica

**¿Por qué Python ≥3.10?**
- DSPy 3.0 **requiere Python 3.10-3.13** (dropped 3.9 support)
- Fuente: [DSPy Releases](https://github.com/stanfordnlp/dspy/releases) - breaking change en 3.0
- **Opciones**:
  1. ✅ **Migrar a Python 3.10+** (recomendado) → Acceso a DSPy 3.0 con features completos
  2. ❌ Usar DSPy 2.x (legacy) → Sin MLflow 3.0 integration, sin multi-modal I/O
  3. ❌ Abandonar DSPy → Volver a prompt engineering manual

**Decisión**: Este plan asume **Opción 1** (migración aprobada). Si no apruebas upgrade, STOP aquí.

---

## 📊 Estado Actual del Proyecto (2025-11-03)

**Python Environment**: ✅ Python 3.11.14 ya instalado
**Dependencies**: ✅ 11/11 dependencias compatibles + ✅ dspy-ai 3.0.3 instalado
**Code Compatibility**: ✅ Zero breaking changes detectados
**DSPy BA Module**: ✅ Implementado y probado (5/5 tests exitosos)
**Comparison Experiment**: ✅ 21 pares ejecutados - DSPy wins en todas las métricas

**Resultado Fase 0**: ✅ Auditoría completa - RIESGO MUY BAJO - GO DECISION
**Resultado Fase 1**: ✅ SKIP - Sistema ya tiene Python 3.11.14 instalado
**Resultado Fase 2**: ✅ **COMPLETA** - Módulo BA baseline funcional con 100% success rate
**Resultado Fase 3**: ✅ **COMPLETA** - DSPy 12.8x más rápido + 100% schema compliance vs 81% Master

**Decisión Final**: ✅ **MERGE RECOMENDADO** - DSPy BA es claramente superior

**Siguiente paso**: Proceder a **Fase 5** (Decisión y Acción - MERGE)

Ver auditoría completa en: `docs/python310_migration_audit.md`
Ver implementación completa en: `docs/phase2_implementation_guide.md`
Ver análisis comparativo en: `docs/phase3_comparison_experiment.md`

---

## ✅ Observaciones de revisión incorporadas (2025-11-03)
- [x] Justificación Python ≥3.10 agregada arriba
- [x] Fase 1: Alineación con `make setup` y CI/CD warnings agregados
- [x] Fase 2: TODOs sobre mapeo temperatura/max_tokens/API keys documentados
- [x] Fase 2: Warning sobre duplicación de YAML parsing vs scripts/run_ba.py
- [x] Fase 3: Check git status limpio agregado a script batch
- [x] Fase 3: Prerequisitos (jq, pyenv, make targets) documentados
- [x] Fase 3: Rate limiting y throttling warnings agregados

## Fase 0: Pre-Migration Review

**Duración**: 1 día
**Status**: ✅ COMPLETA (2025-11-03)
**Resultado**: GO DECISION - Riesgo MUY BAJO

### Resumen de Auditoría Ejecutada

**Script ejecutado**: `scripts/run_phase0_audit.sh`

**Resultados**:
- ✅ Python version: **3.11.14 ya instalado** (no migration necesaria!)
- ✅ Dependencies: 11/11 compatibles con Python 3.11
- ✅ Code compatibility: Zero breaking changes detectados
- ⚠️ 2 advertencias (false positives del script de auditoría)
- ✅ Tests baseline: Ejecutado exitosamente (1 fallo preexistente no relacionado)

**Conclusión**: Sistema ya cumple requisitos DSPy 3.0. **Proceder directamente a Fase 2**.

**Detalle completo**: Ver `docs/python310_migration_audit.md`

---

### Scope Original (Completado)

### Actividades
- [ ] Revisar `requirements.txt` para dependencias incompatibles con Python 3.10+
- [ ] Verificar syntax antiguo que no funciona en 3.10+ (tipo hints, match/case)
- [ ] Identificar uso de librerías deprecated
- [ ] Revisar CI/CD configs (si existen) que especifiquen Python version
- [ ] Check archivos de runtime: `.python-version`, `runtime.txt`, `Dockerfile`

### Checklist de Compatibilidad

#### Dependencies Check
```bash
# Revisar cada dependencia en requirements.txt
cat requirements.txt | while read dep; do
  echo "Checking $dep for Python 3.10+ compatibility..."
  # Buscar en PyPI o docs oficiales
done
```

**Lista de deps a revisar**:
- [ ] `httpx>=0.25` → Compatible ✅
- [ ] `PyYAML>=6.0` → Compatible ✅
- [ ] `typer>=0.12` → Compatible ✅
- [ ] `rich>=13.7` → Compatible ✅
- [ ] `pytest>=8.0` → Compatible ✅
- [ ] `fastapi>=0.112` → Compatible ✅
- [ ] `uvicorn` → Compatible ✅
- [ ] `google-genai>=0.6.0` → Verificar
- [ ] `rorf>=0.1.0` → Verificar (custom package?)

#### Code Syntax Check
```bash
# Buscar patterns problemáticos
grep -r "from typing import" scripts/ a2a/ src/
# collections.abc vs typing (algunos movidos en 3.10)

grep -r "Union\[" scripts/ a2a/ src/
# Python 3.10 soporta | syntax (opcional, no breaking)
```

- [ ] Tipo hints con `Union`, `Optional` (funciona pero puede modernizar)
- [ ] Imports de `typing` vs `collections.abc`
- [ ] Uso de `match/case` (feature nueva 3.10, no usar aún si soporte 3.9)

#### Runtime Config Files
```bash
find . -name ".python-version" -o -name "runtime.txt" -o -name "Dockerfile"
```

- [ ] `.python-version` → Actualizar a `3.10.15` (o 3.11/3.12)
- [ ] `runtime.txt` → Actualizar si existe
- [ ] `Dockerfile` → Actualizar base image si existe
- [ ] `pyproject.toml` → Actualizar `requires-python` si existe

#### Known Breaking Changes (3.9 → 3.10+)
- [ ] **collections ABCs**: Importar de `collections.abc` no `typing`
- [ ] **Removed bpo-XXXXX**: Algunas APIs deprecated en 3.9 removidas
- [ ] **distutils deprecated**: Si se usa, migrar a setuptools

#### Test Coverage
```bash
# Correr tests en Python 3.9 actual como baseline
.venv/bin/pytest -v > /tmp/py39_test_results.txt
```

- [ ] Ejecutar tests en Python 3.9 (baseline)
- [ ] Documentar cuáles tests pasan/fallan actualmente
- [ ] Identificar tests que dependen de Python version

### Entregables
- [ ] Documento: `docs/python310_migration_audit.md` con:
  - Lista de dependencias incompatibles (si existen)
  - Breaking changes anticipados
  - Archivos a modificar
  - Riesgos identificados
- [ ] Decisión: Continuar con 3.10, 3.11, o 3.12?
  - **Recomendación**: 3.11 (balance estabilidad/performance)

### Riesgos Identificados
| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Deps incompatibles | TBD | Actualizar versions o buscar alternativas |
| Tests fallan | TBD | Fix antes de continuar |
| CI/CD breaks | Bajo | Actualizar configs en branch |
| Local dev setup | Bajo | Documentar setup con pyenv |

### Criterio de Éxito Fase 0
- ✅ Auditoría completa documentada
- ✅ Zero dependencias blocker identificadas (o plan para resolverlas)
- ✅ Tests baseline ejecutados y documentados
- ✅ **Go/No-Go decision**: ¿Proceder con migración?

### Exit Criteria
**PROCEED** a Fase 1 si:
- No hay dependencias incompatibles O hay plan para reemplazarlas
- Tests actuales tienen success rate conocido
- Equipo aprueba upgrade

**BLOCK** si:
- Dependencias críticas incompatibles sin alternativa
- Requiere refactor masivo de código

---

## Fase 1: Environment Setup

**Duración**: 1-2 días
**Status**: ✅ COMPLETA - SKIP (2025-11-03)
**Resultado**: Python 3.11.14 ya instalado - No se requiere migración

### Resumen

**Descubrimiento clave**: El sistema ya tiene Python 3.11.14 instalado y activo.

**Verificación realizada**:
```bash
python --version
# Output: Python 3.11.14
```

**Estado de dependencias DSPy**:
- `dspy-ai>=3.0.3`: ⬜ Pendiente instalación (Fase 2)
- `mlflow>=3.0`: ⬜ Pendiente instalación (Fase 2)

**Conclusión**: **Fase 1 completa automáticamente**. Todos los pasos documentados abajo ya no son necesarios. Proceder directamente a Fase 2.

---

### Scope Original (Ya no necesario - conservado para referencia)

### Paso a Paso: Setup con pyenv (Recomendado)

#### 1. Instalar pyenv (si no está instalado)
```bash
# macOS
brew install pyenv

# Linux
curl https://pyenv.run | bash

# Verificar instalación
pyenv --version
```

#### 2. Instalar Python 3.11 (recomendado)
```bash
# Listar versiones disponibles
pyenv install --list | grep "3.11"

# Instalar 3.11.9 (última stable al 2025-11)
pyenv install 3.11.9

# Verificar instalación
pyenv versions
```

#### 3. Activar Python 3.11 en el branch
```bash
# Cambiar a branch dspy-comparison
git checkout feature/dspy-comparison

# Configurar Python 3.11 local para este directorio
cd /Users/matiasleandrokruk/Documents/agnostic-ai-pipeline
pyenv local 3.11.9

# Verificar
python --version  # Debe mostrar Python 3.11.9
which python      # Debe apuntar a ~/.pyenv/versions/3.11.9/bin/python
```

#### 4. Recrear virtualenv con Python 3.11

⚠️ **IMPORTANTE**: El `Makefile` actual puede tener lógica que asume Python 3.9. Verificar antes de continuar.

```bash
# 1. Verificar qué hace make setup actualmente
cat Makefile | grep -A 10 "^setup:"

# 2. Backup del .venv anterior (por si acaso)
mv .venv .venv.bak.py39

# 3. OPCIÓN A: Recrear manualmente (si make setup no soporta Python 3.11)
python -m venv .venv
source .venv/bin/activate
python --version  # Debe ser 3.11.9

# 3. OPCIÓN B: Actualizar Makefile primero (recomendado para consistencia)
# Modificar Makefile para usar pyenv si está disponible:
# setup:
#     @command -v pyenv >/dev/null && eval "$$(pyenv init -)" || true
#     python -m venv .venv
#     .venv/bin/pip install --upgrade pip
#     .venv/bin/pip install -r requirements.txt

# Luego ejecutar:
make setup
```

**CI/CD Consideration**:
Si tienes CI/CD (GitHub Actions, GitLab CI), actualizar archivos de workflow:
```yaml
# .github/workflows/test.yml (ejemplo)
# Cambiar de:
# python-version: '3.9'
# A:
python-version: '3.11'
```

#### 5. Instalar dependencias base + DSPy
```bash
# Instalar dependencias existentes
pip install --upgrade pip
pip install -r requirements.txt

# Agregar DSPy y MLflow
pip install dspy-ai>=3.0.3 mlflow>=3.0

# Opcional: Actualizar requirements.txt
pip freeze > requirements.freeze.txt
# Revisar y mover a requirements.txt si apruebas
```

#### 6. Verificar instalación
```bash
# Check Python version
python --version

# Check DSPy instalado
pip list | grep dspy-ai
# Expected: dspy-ai       3.0.3 (o superior)

# Check MLflow instalado
pip list | grep mlflow
# Expected: mlflow        3.0.x

# Test imports
python -c "import dspy; print(f'DSPy version: {dspy.__version__}')"
python -c "import mlflow; print(f'MLflow version: {mlflow.__version__}')"
```

#### 7. Ejecutar tests existentes (regresión)
```bash
# Ejecutar todos los tests
.venv/bin/pytest -v

# Si algún test falla, documentar en audit report
# Comparar con baseline de Fase 0
diff /tmp/py39_test_results.txt <(.venv/bin/pytest -v 2>&1)
```

### Entregables
- [ ] Python 3.11.9 activo en branch (vía pyenv local)
- [ ] Archivo `.python-version` creado (automático con pyenv local)
- [ ] `.venv` recreado con Python 3.11
- [ ] `dspy-ai>=3.0.3` instalado
- [ ] `mlflow>=3.0` instalado
- [ ] Tests existentes pasan con misma success rate que Fase 0
- [ ] Documento actualizado: `docs/python310_migration_audit.md` con resultados

### Troubleshooting Común

#### Problema: pyenv no cambia versión de Python
```bash
# Verificar que shell está configurado
echo $PATH | grep pyenv  # Debe estar presente

# Agregar a ~/.zshrc o ~/.bashrc si falta:
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# Reiniciar shell
exec $SHELL
```

#### Problema: pip install dspy-ai falla
```bash
# Verificar pip actualizado
pip install --upgrade pip setuptools wheel

# Si sigue fallando, instalar deps del sistema (macOS)
brew install openssl readline sqlite3 xz zlib

# Linux
sudo apt-get install build-essential libssl-dev zlib1g-dev
```

#### Problema: Tests fallan después de upgrade
```bash
# Revisar traceback específico
.venv/bin/pytest -v --tb=short

# Buscar incompatibilidades de imports
# Ejemplo: typing.List → collections.abc.Sequence en 3.11
# Fix y documentar en audit report
```

### Criterio de Éxito
```bash
# Checklist completo
python --version                    # 3.11.9 ✅
pip list | grep dspy-ai             # Instalado ✅
pip list | grep mlflow              # Instalado ✅
.venv/bin/pytest                    # Tests pass ✅
git status                          # .python-version tracked ✅
```

### Rollback Plan (si algo falla)
```bash
# Restaurar Python 3.9
rm .python-version
mv .venv.bak.py39 .venv
pyenv local 3.9.10  # O la versión que tenías

# Verificar
python --version
source .venv/bin/activate
.venv/bin/pytest
```

---

## Fase 2: DSPy BA Module (Baseline)

**Duración**: 3-5 días
**Status**: ✅ **COMPLETA** (2025-11-03)
**Pre-requisitos**: ✅ Fase 0 Completa, ✅ Fase 1 Completa (Python 3.11.14)

### Resumen de Completitud

**Tests ejecutados**: 5/5 exitosos (100% success rate)
**Provider**: Ollama local (granite4)

| Concept | Complejidad | FRs | NFRs | Constraints | YAML válido |
|---------|-------------|-----|------|-------------|-------------|
| Blog personal | Simple | 5 | 3 | 2 | ✅ |
| Inventario retail | Media | 6 | 4 | 3 | ✅ |
| SaaS multi-tenant | Compleja | 8 | 5 | 4 | ✅ |
| Delivery app | Media | 7 | 4 | 4 | ✅ |
| Plataforma educativa | Media | 6 | 4 | 3 | ✅ |

**Resultado**: Módulo DSPy BA baseline funcional y validado.

**Ver detalles completos**: `docs/phase2_implementation_guide.md`

---

### 📖 Guía de Implementación Completa

**Ver documento detallado**: `docs/phase2_implementation_guide.md` (~600 líneas con código completo)

El documento incluye:
- Estructura de archivos completa con código
- `ba_requirements.py` (~110 líneas) - Módulo DSPy BA
- `run_ba.py` (~120 líneas) - CLI wrapper
- Makefile target `dspy-ba`
- Tests manuales y criterios de éxito
- Troubleshooting y debugging tips

### Scope (Resumen)
- Implementar **solo BA role** con DSPy básico (sin optimización)
- Usar `dspy.Predict` (no `ChainOfThought` ni optimizers todavía)
- Reutilizar `config.yaml` para credenciales LLM existentes
- Output a `artifacts/dspy/requirements_dspy.yaml`

### Quick Start

**Instalación de dependencias**:
```bash
# Instalar DSPy y MLflow
pip install dspy-ai>=3.0.3 mlflow>=3.0
```

**Pasos de implementación** (ver guía completa para código):
1. Crear estructura de directorios `dspy_baseline/modules/`, `dspy_baseline/scripts/`, `dspy_baseline/config/`
2. Implementar `dspy_baseline/modules/ba_requirements.py` (~110 líneas)
3. Implementar `dspy_baseline/scripts/run_ba.py` (~120 líneas)
4. Agregar target `dspy-ba` al Makefile
5. Ejecutar test manual: `make dspy-ba CONCEPT="Un blog simple"`

### Estructura de Archivos a Crear

```
dspy/
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

### Entregables
- [ ] `dspy_baseline/` package structure creada (4 directorios, 4 `__init__.py`)
- [ ] `dspy_baseline/modules/ba_requirements.py` implementado (~110 líneas)
- [ ] `dspy_baseline/scripts/run_ba.py` CLI funcional (~120 líneas)
- [ ] Makefile target `dspy-ba` agregado
- [ ] Genera YAML válido en `artifacts/dspy/requirements_dspy.yaml`
- [ ] Probado con 3-5 concepts manualmente

### Criterio de Éxito

Ver guía completa `docs/phase2_implementation_guide.md` para:
- ✅ Troubleshooting de 3 problemas comunes
- ✅ Debugging tips con DSPy cache
- ✅ Success criteria checklist detallado
- ✅ Out of scope items (MIPROv2, otros roles, A2A, MLflow)

---

## Fase 3: Experimento Comparativo

**Duración**: 1 semana
**Status**: ⬜ Pending
**Pre-requisito**: Fase 2 completada con DSPy BA funcional

### Scope
- Ejecutar **30 concepts** en ambas versiones (master vs DSPy branch)
- Concepts variados en complejidad y dominio
- Automatizar ejecución con script batch
- Guardar outputs + metadata (latencia, errores) para análisis

### 30 Concepts de Prueba (Definidos)

#### Simples (10 concepts - ~5 functional requirements esperados)
1. "Un blog personal con posts y comentarios"
2. "Aplicación TODO list con prioridades"
3. "Calculadora de propinas para restaurantes"
4. "Generador de contraseñas seguras"
5. "Conversor de unidades (temperatura, longitud, peso)"
6. "Registro de gastos personales"
7. "Timer Pomodoro con estadísticas"
8. "Biblioteca de recetas de cocina"
9. "Registro de hábitos diarios"
10. "Generador de códigos QR"

#### Medios (15 concepts - ~10 functional requirements esperados)
11. "E-commerce para productos artesanales con carrito de compras"
12. "API REST para reservas de restaurantes con gestión de mesas"
13. "Sistema de gestión de inventario para retail con alertas de stock"
14. "Plataforma de cursos online con videos y evaluaciones"
15. "App de seguimiento de fitness con planes de entrenamiento"
16. "Sistema de tickets de soporte técnico con asignación automática"
17. "CRM básico para gestión de contactos y pipeline de ventas"
18. "Plataforma de freelancing con perfiles y proyectos"
19. "Sistema de votaciones online con resultados en tiempo real"
20. "Marketplace de servicios profesionales con ratings"
21. "Sistema de reservas de espacios coworking"
22. "Dashboard de métricas de negocio con gráficos interactivos"
23. "Plataforma de eventos con registro y check-in"
24. "Sistema de gestión de contenidos (CMS) para sitios web"
25. "App de delivery de comida con tracking de pedidos"

#### Complejos (5 concepts - ~20+ functional requirements esperados)
26. "Plataforma SaaS multi-tenant para gestión de proyectos con roles, permisos, facturación y analytics"
27. "Sistema bancario online con cuentas, transferencias, préstamos y seguridad avanzada"
28. "Plataforma de telemedicina con videoconsultas, historia clínica, prescripciones y integración con laboratorios"
29. "Sistema ERP para manufactura con gestión de producción, supply chain, HR y finanzas"
30. "Plataforma de trading algorítmico con data en tiempo real, backtesting y ejecución automática"

### Prerequisitos para Experimento

Antes de ejecutar el script batch, verificar:

```bash
# 1. Check jq instalado (para parsing JSON logs)
command -v jq >/dev/null || echo "❌ jq no instalado. Instalar: brew install jq (macOS) o apt-get install jq (Linux)"

# 2. Check pyenv (si usaste pyenv en Fase 1)
command -v pyenv >/dev/null || echo "⚠️ pyenv no disponible, script usará Python del sistema"

# 3. Check make targets existen
make -n ba >/dev/null 2>&1 || echo "❌ 'make ba' no existe en Makefile"
make -n dspy-ba >/dev/null 2>&1 || echo "❌ 'make dspy-ba' no existe en Makefile (normal si aún no lo creaste)"

# 4. Check git working tree limpio
git status --porcelain | grep -q . && echo "⚠️ WARNING: Working tree NO está limpio. Stash cambios antes de continuar: git stash" || echo "✅ Working tree limpio"

# 5. Check credenciales LLM configuradas
[[ -z "$OPENAI_API_KEY" ]] && echo "⚠️ WARNING: OPENAI_API_KEY no configurada (si usas OpenAI)" || echo "✅ OPENAI_API_KEY configurada"
```

**Fallbacks si falta algo**:
- Sin `jq`: Comentar líneas del script que usan jq (logs se guardan igual)
- Sin `pyenv`: Script usa Python del sistema (OK si ya migraste)
- Sin targets make: Crear manualmente antes de correr script (Fase 2)

### Script de Ejecución Batch

#### Crear `scripts/run_comparison.sh`

```bash
#!/bin/bash
# Script to run comparison between master and dspy branches
# Usage: bash scripts/run_comparison.sh
#
# Prerequisites:
#   - jq installed (brew install jq)
#   - git working tree clean (git status)
#   - make ba and make dspy-ba targets exist
#   - LLM credentials configured (env vars)

set -e

# Verificar prerequisitos
command -v jq >/dev/null || { echo "❌ jq not found. Install: brew install jq"; exit 1; }

# Verificar git working tree limpio
if [[ -n $(git status --porcelain) ]]; then
  echo "⚠️  WARNING: Git working tree is NOT clean!"
  echo "Uncommitted changes will be lost when switching branches."
  read -p "Continue anyway? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborting. Run 'git stash' first."
    exit 1
  fi
fi

COMPARISON_DIR="artifacts/comparison"
CONCEPTS_FILE="$COMPARISON_DIR/concepts.txt"
LOG_FILE="$COMPARISON_DIR/execution_log.jsonl"

# Create directories
mkdir -p "$COMPARISON_DIR/master"
mkdir -p "$COMPARISON_DIR/dspy"

# Concept list (same as above)
CONCEPTS=(
  "Un blog personal con posts y comentarios"
  "Aplicación TODO list con prioridades"
  "Calculadora de propinas para restaurantes"
  "Generador de contraseñas seguras"
  "Conversor de unidades (temperatura, longitud, peso)"
  "Registro de gastos personales"
  "Timer Pomodoro con estadísticas"
  "Biblioteca de recetas de cocina"
  "Registro de hábitos diarios"
  "Generador de códigos QR"
  "E-commerce para productos artesanales con carrito de compras"
  "API REST para reservas de restaurantes con gestión de mesas"
  "Sistema de gestión de inventario para retail con alertas de stock"
  "Plataforma de cursos online con videos y evaluaciones"
  "App de seguimiento de fitness con planes de entrenamiento"
  "Sistema de tickets de soporte técnico con asignación automática"
  "CRM básico para gestión de contactos y pipeline de ventas"
  "Plataforma de freelancing con perfiles y proyectos"
  "Sistema de votaciones online con resultados en tiempo real"
  "Marketplace de servicios profesionales con ratings"
  "Sistema de reservas de espacios coworking"
  "Dashboard de métricas de negocio con gráficos interactivos"
  "Plataforma de eventos con registro y check-in"
  "Sistema de gestión de contenidos (CMS) para sitios web"
  "App de delivery de comida con tracking de pedidos"
  "Plataforma SaaS multi-tenant para gestión de proyectos con roles, permisos, facturación y analytics"
  "Sistema bancario online con cuentas, transferencias, préstamos y seguridad avanzada"
  "Plataforma de telemedicina con videoconsultas, historia clínica, prescripciones y integración con laboratorios"
  "Sistema ERP para manufactura con gestión de producción, supply chain, HR y finanzas"
  "Plataforma de trading algorítmico con data en tiempo real, backtesting y ejecución automática"
)

# Save concepts list
printf "%s\n" "${CONCEPTS[@]}" > "$CONCEPTS_FILE"
echo "📋 30 concepts saved to $CONCEPTS_FILE"

# Initialize log
echo "" > "$LOG_FILE"

CURRENT_BRANCH=$(git branch --show-current)
echo "🌿 Current branch: $CURRENT_BRANCH"

# Function to run BA and capture metrics
run_ba() {
  local branch=$1
  local concept=$2
  local index=$3
  local output_file=$4

  echo "⏳ [$branch] Running concept $index/30..."

  START_TIME=$(date +%s)
  ERROR=""

  if [[ "$branch" == "master" ]]; then
    # Run master version
    if make ba CONCEPT="$concept" 2>/dev/null; then
      cp planning/requirements.yaml "$output_file" 2>/dev/null || ERROR="No output file"
    else
      ERROR="make ba failed"
    fi
  else
    # Run DSPy version
    if make dspy-ba CONCEPT="$concept" 2>/dev/null; then
      cp artifacts/dspy/requirements_dspy.yaml "$output_file" 2>/dev/null || ERROR="No output file"
    else
      ERROR="make dspy-ba failed"
    fi
  fi

  END_TIME=$(date +%s)
  DURATION=$((END_TIME - START_TIME))

  # Log metrics
  jq -n \
    --arg branch "$branch" \
    --arg concept "$concept" \
    --arg index "$index" \
    --arg duration "$DURATION" \
    --arg error "$ERROR" \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{branch: $branch, concept: $concept, index: ($index|tonumber), duration: ($duration|tonumber), error: $error, timestamp: $timestamp}' \
    >> "$LOG_FILE"

  if [[ -n "$ERROR" ]]; then
    echo "❌ [$branch] Error: $ERROR"
    return 1
  else
    echo "✅ [$branch] Completed in ${DURATION}s"
    return 0
  fi
}

echo ""
echo "🚀 Starting comparison experiment..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Loop through concepts
for i in "${!CONCEPTS[@]}"; do
  INDEX=$((i + 1))
  CONCEPT="${CONCEPTS[$i]}"
  PADDED_INDEX=$(printf "%02d" $INDEX)

  echo ""
  echo "📝 Concept $INDEX/30: ${CONCEPT:0:60}..."

  # Master branch
  echo "  → Switching to master..."
  git checkout main >/dev/null 2>&1
  source .venv/bin/activate
  run_ba "master" "$CONCEPT" "$INDEX" "$COMPARISON_DIR/master/${PADDED_INDEX}_requirements.yaml" || true

  # DSPy branch
  echo "  → Switching to dspy-comparison..."
  git checkout feature/dspy-comparison >/dev/null 2>&1
  source .venv/bin/activate
  run_ba "dspy" "$CONCEPT" "$INDEX" "$COMPARISON_DIR/dspy/${PADDED_INDEX}_requirements.yaml" || true

  echo "  ✓ Pair $INDEX/30 completed"

  # ⚠️ RATE LIMITING: Sleep entre concepts para evitar rate limits
  # OpenAI: 3 RPM (tier free) → 20s entre requests
  # Anthropic: 5 RPM (tier 1) → 12s entre requests
  # Ajustar según tu tier:
  if [[ $INDEX -lt 30 ]]; then
    echo "  💤 Sleeping 15s to avoid rate limits..."
    sleep 15
  fi
done

# Return to original branch
git checkout "$CURRENT_BRANCH" >/dev/null 2>&1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Comparison experiment completed!"
echo ""
echo "Results:"
echo "  - Master outputs: $COMPARISON_DIR/master/"
echo "  - DSPy outputs:   $COMPARISON_DIR/dspy/"
echo "  - Execution log:  $LOG_FILE"
echo ""
echo "Summary:"
jq -s 'group_by(.branch) | map({branch: .[0].branch, total: length, errors: map(select(.error != "")) | length, avg_duration: (map(.duration) | add / length)})' "$LOG_FILE"
```

#### Crear `artifacts/comparison/.gitkeep`
```bash
mkdir -p artifacts/comparison
touch artifacts/comparison/.gitkeep
```

### Entregables
- [ ] Script `scripts/run_comparison.sh` creado y ejecutable
- [ ] 30 concepts definidos en `artifacts/comparison/concepts.txt`
- [ ] Ejecutar script completo: `bash scripts/run_comparison.sh`
- [ ] 30 pares de outputs generados:
  - `artifacts/comparison/master/01_requirements.yaml` ... `30_requirements.yaml`
  - `artifacts/comparison/dspy/01_requirements.yaml` ... `30_requirements.yaml`
- [ ] Log de ejecución: `artifacts/comparison/execution_log.jsonl` con métricas

### Metadata Capturada por Concepto

Cada línea en `execution_log.jsonl`:
```json
{
  "branch": "master",
  "concept": "Un blog personal...",
  "index": 1,
  "duration": 45,
  "error": "",
  "timestamp": "2025-11-03T10:30:00Z"
}
```

### Ejecución Manual (si script falla)

```bash
# Por cada concept manualmente
git checkout main
make ba CONCEPT="..."
cp planning/requirements.yaml artifacts/comparison/master/01_requirements.yaml

git checkout feature/dspy-comparison
make dspy-ba CONCEPT="..."
cp artifacts/dspy/requirements_dspy.yaml artifacts/comparison/dspy/01_requirements.yaml
```

### Costos Estimados y Segmentación

**Costo estimado total** (30 concepts × 2 versiones = 60 ejecuciones):
- GPT-4: ~$3-6 (dependiendo de complejidad)
- GPT-3.5: ~$0.30-0.60
- Claude Sonnet: ~$4-8
- Ollama (local): $0

**Tiempo estimado**:
- Sin throttling: ~30-60 minutos
- Con throttling (15s/concept): ~2 horas
- Rate limits incluidos: 2-3 horas

**Segmentación recomendada** (si rate limits son problema):
```bash
# Día 1: Simple concepts (1-10)
sed -n '1,10p' concepts → Ejecutar

# Día 2: Medium concepts (11-25)
sed -n '11,25p' concepts → Ejecutar

# Día 3: Complex concepts (26-30)
sed -n '26,30p' concepts → Ejecutar
```

### Troubleshooting Durante Experimento

**Problema**: Rate limit errors (429)
```bash
# Aumentar sleep en script de 15s a 30s o 60s
# O usar provider sin rate limits (Ollama local)
```

**Problema**: Algunos concepts fallan
```bash
# Continuar después del fallo, documentar en log
# El script ya maneja errores con `|| true`
```

**Problema**: Tarda mucho (>1 hora por concept)
```bash
# Reducir a subset de 15 concepts (5 simple, 7 medio, 3 complejo)
# Modificar array CONCEPTS en script
```

**Problema**: Credenciales expiran (token refresh)
```bash
# Re-exportar antes de continuar
export OPENAI_API_KEY="..."
# Continuar desde índice fallido editando script (start from INDEX=15)
```

### Criterio de Éxito Fase 3
- ✅ 30 pares de outputs generados (o mínimo 20 si algunos fallan)
- ✅ Success rate ≥66% en ambas versiones (20/30 mínimo)
- ✅ Execution log completo con durations
- ✅ Ningún crash del sistema (crashes individuales OK, documentados)
- ✅ Outputs son YAML válidos (al menos 80%)

### Análisis Preliminar (Opcional)

```bash
# Quick stats
echo "Master outputs:"
ls artifacts/comparison/master/*.yaml | wc -l

echo "DSPy outputs:"
ls artifacts/comparison/dspy/*.yaml | wc -l

echo "Avg duration master:"
jq -s 'map(select(.branch == "master")) | map(.duration) | add / length' artifacts/comparison/execution_log.jsonl

echo "Avg duration dspy:"
jq -s 'map(select(.branch == "dspy")) | map(.duration) | add / length' artifacts/comparison/execution_log.jsonl
```

---

## Fase 4: Análisis Cuantitativo

**Duración**: 2-3 días
**Status**: ⬜ Pending

### Scope
- Script de evaluación automática (`scripts/compare_ba_outputs.py`)
- Métricas objetivas:
  1. **Completitud**: % campos requeridos presentes
  2. **Granularidad**: Número de functional requirements
  3. **Estructura**: % requirements bien formados (con id, description)
  4. **Validez**: YAML parseable sin errores
  5. **Latencia**: Tiempo de generación (p50, p95)
- Evaluación manual de 5 samples (calidad semántica)

### Entregables
- [ ] `scripts/compare_ba_outputs.py` implementado
- [ ] Reporte de métricas: `artifacts/comparison/analysis.md`
- [ ] Gráficos comparativos (opcional)
- [ ] Evaluación manual documentada

### Métricas de Decisión
| Métrica | Master | DSPy | Delta | Target |
|---------|--------|------|-------|--------|
| Completitud (%) | TBD | TBD | TBD | ≥+10% |
| Granularidad (avg reqs) | TBD | TBD | TBD | ≥+2 |
| Estructura (%) | TBD | TBD | TBD | ≥+10% |
| Success rate (%) | TBD | TBD | TBD | ≥95% |
| Latencia p95 (s) | TBD | TBD | TBD | <+50% |

### Criterio de Éxito
- Análisis completo de 20+ pares
- Decisión clara: merge / abandon / iterate

---

## Fase 5: Decisión y Acción

**Duración**: 1 día
**Status**: ⬜ Pending

### Scope
Basado en resultados Fase 4, ejecutar una de tres acciones:

#### ✅ Opción A: MERGE (si DSPy gana claramente)
**Condiciones**:
- Score promedio DSPy ≥10% mejor que master
- Success rate ≥95%
- Latencia no aumentó >50%
- Evaluación manual confirma mejora

**Acciones**:
- [ ] Integrar DSPy en `scripts/run_ba.py` (reemplazar o feature flag)
- [ ] Actualizar `requirements.txt` con DSPy deps
- [ ] Actualizar README y CLAUDE.md
- [ ] PR: `feature/dspy-comparison` → `main`

#### ❌ Opción B: ABANDON (si master gana o empate)
**Condiciones**:
- Mejora <10% o DSPy peor que master
- Latencia significativamente mayor sin beneficio
- Success rate <95%

**Acciones**:
- [ ] Documentar findings en `docs/experiments/dspy_comparison_results.md`
- [ ] Extraer learnings para mejorar prompts master
- [ ] Archivar branch (no merge)

#### 🔄 Opción C: ITERATE (si resultados mixtos)
**Condiciones**:
- Mejora moderada (5-10%)
- Potencial con optimización (MIPROv2)
- Funciona bien en algunos casos, mal en otros

**Acciones**:
- [ ] Crear dataset de ejemplos (50+)
- [ ] Implementar optimización con MIPROv2
- [ ] Repetir Fase 3-4 con modelo optimizado

### Entregables
- [ ] Documento de decisión con justificación
- [ ] Acción ejecutada (merge / abandon / iterate)
- [ ] Findings documentados para futuro

---

## Métricas Globales del Experimento

### KPIs Técnicos
- **Mejora en completitud**: ¿DSPy genera requirements más completos?
- **Mejora en granularidad**: ¿DSPy genera más detalles?
- **Confiabilidad**: ¿DSPy es más consistente?
- **Performance**: ¿Latencia es aceptable?

### KPIs de Decisión
- **ROI**: ¿Beneficio justifica complejidad agregada?
- **Mantenibilidad**: ¿DSPy simplifica o complica el código?
- **Escalabilidad**: ¿Approach se puede extender a QA/Architect/Dev?

---

## Out of Scope (Explícito)

**NO hacer en este experimento**:
- ❌ Optimización con MIPROv2 (solo si ITERATE)
- ❌ Otros roles (QA, Architect, Dev)
- ❌ A2A integration con DSPy
- ❌ Upgrade de Python en main (solo en branch)
- ❌ MLflow tracking completo (nice-to-have, no blocker)
- ❌ Dataset creation de 200+ ejemplos (solo si ITERATE)

**Razón**: Validar primero si DSPy baseline ya aporta valor. Si no, optimización/extensión no tiene sentido.

---

## Dependencias Externas

- Python 3.10+ disponible en sistema
- Credenciales LLM funcionando (`config.yaml`)
- 20-30 concepts de prueba definidos
- ~1 dev dedicado por 2-3 semanas

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Python upgrade rompe tests | Media | Alto | Correr tests antes de continuar (Fase 1) |
| DSPy requiere tuning complejo | Alta | Medio | Si baseline no funciona, ABANDON sin iterar |
| Latencia muy alta | Media | Medio | Usar modelos rápidos (GPT-3.5 vs GPT-4) |
| Resultados inconclusos | Media | Bajo | Definir métricas claras ANTES de Fase 3 |

---

## Timeline Estimado

```
✅ Día 1:     Fase 0 (pre-migration review y auditoría) - COMPLETA (2025-11-03)
✅ Semana 1:  Fase 1 (setup Python 3.10+) - SKIP (Python 3.11.14 ya instalado)
✅ Semana 2:  Fase 2 (implementación BA DSPy) - COMPLETA (2025-11-03) ⚡ ADELANTADO
⬜ Semana 3:  Fase 3 (experimento comparativo) - READY TO START
⬜ Semana 4:  Fase 4 (análisis) + Fase 5 (decisión)
```

**Total**: ~2 semanas restantes para decisión Go/No-Go fundamentada en datos.

**Tiempo ahorrado**:
- 1-2 días (Python migration no necesaria)
- 2-3 días (Fase 2 completada en 1 día vs 3-5 estimados)

---

## Siguiente Paso Inmediato

✅ **Fase 0 Completa** - Auditoría ejecutada, riesgo MUY BAJO, GO decision
✅ **Fase 1 Completa** - Python 3.11.14 ya instalado (SKIP migration)
✅ **Fase 2 Completa** - Módulo DSPy BA baseline implementado y validado (5/5 tests)

**AHORA - Fase 3: Experimento Comparativo**:

**Objetivo**: Ejecutar 30 concepts en ambas versiones (master BA vs DSPy BA) y comparar outputs objetivamente.

**Prerequisitos**:
1. [ ] Verificar que git working tree esté limpio: `git status`
2. [ ] Crear script batch `scripts/run_comparison.sh` (ya documentado en Fase 3)
3. [ ] Definir los 30 concepts de prueba (10 simples, 15 medios, 5 complejos)

**Ejecución**:
```bash
# Crear script de comparación
bash scripts/run_comparison.sh

# Resultado esperado:
# - 30 pares de YAMLs: master/01_requirements.yaml ... 30_requirements.yaml
#                       dspy/01_requirements.yaml ... 30_requirements.yaml
# - execution_log.jsonl con métricas (duración, errores, timestamp)
```

**Tiempo estimado**: 2-3 horas (con rate limiting 15s entre requests)

**Estado actual**: ✅ Fase 2 completa, ⬜ Fase 3 ready to start

---

**Última actualización**: 2025-11-03
**Owner**: [Tu nombre]
**Revisores**: [Equipo]
