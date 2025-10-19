# AGNOSTIC AI PIPELINE 🏗️

**Enterprise-Grade AI Pipeline for Automated Application Generation**

Autonomous system that generates **complete commercial web applications** with integrated QA, Intelligent Architecture, and End-to-End Quality Cycles.

## 🔥 Main Features

- **🏆 INTEGRAL TDD**: Tests are mandatory part of each user story - no separate test stories
- **🧠 Intelligent QA**: Severity analysis for selective force-approval (only P1/P0 with valid reasons)
- **🔄 AUTO-RESTART**: Automatic quality assessment and rework when necessary
- **🎯 Intelligent Dependencies**: Stories automatically released when dependencies are completed
- **📊 Advanced Quality Gates**: Multiple states (debugging, quality_gate_waiting, blocked_various)
- **👐 Modular Architecture**: FastAPI + Express.js + Optional React Native
- **🚀 End-to-End Generation**: From business concept → deployable functional application

## 📊 Proven Results

**Generates complete applications:** 15 user stories → functional e-commerce (auth, catalog, cart, checkout) with >200 passing tests.

**Executions:**
```bash
15 stories completed in 13 iterations = 100% success rate
System demonstrated: Full TDD + Intelligent QA + Selective force-approval
```

## 🎯 System Differentiation

### ❌ Before (Basic Systems)
```yaml
- Some basic dev tool
- Optional/desynchronized tests
- Manual/blind force-approval
- Stories separated from quality
```

### ✅ Now (AGNOSTIC AI PIPELINE)
```yaml
- Mandatory TDD: integral tests in each story
- Intelligent QA: force-approval only for P1/P0 with severity analysis
- Dependency system: automatic release when dependencies complete
- Advanced Quality Gates: debugging, blocked_critical, quality_gate_waiting, etc.
```

## 🚀 Quick Start

### 1. Optimized Setup
```bash
make setup
# Installs: httpx, PyYAML, typer, rich, pytest

make set-role role=ba        provider=ollama model="granite4:latest"
make set-role role=architect provider=ollama model="qwen2.5-coder:32b-instruct-q8_0"
make set-role role=dev       provider=ollama model="mistral:7b-instruct-v0.1"
make set-role role=qa        provider=ollama model="qwen2.5-coder:7b"
```

### 2. Business Concept → Complete Application
```bash
read -r -d '' CONCEPT <<'TXT'
Product: E-commerce MVP (FastAPI backend, Express.js frontend).
Features: signup/login, catalog, shopping cart, simulated checkout.
Goal: Mobile-first retail platform with quality focus.
TXT

# Execute complete pipeline
ALLOW_NO_TESTS=1 MAX_LOOPS=20 ARCHITECT_INTERVENTION=1 make ba plan loop
# Result: Complete application generated automatically
```

### 3. Iterative Development
```bash
# Automatically assess quality
make loop MAX_LOOPS=10

# With intelligent force-approval (only critical P1/P0)
ARCHITECT_INTERVENTION=1 make loop

# Development-only mode (no QA)
LOOP_MODE=dev_only make dev-loop
```

### 4. Product Iteration Loop
```bash
make iteration CONCEPT="Login MVP" LOOPS=2
# Optional flags:
#   ALLOW_NO_TESTS=1   -> Permite QA laxo durante exploración
#   SKIP_BA=1          -> Reutiliza requirements existentes
#   SKIP_PLAN=1        -> Reutiliza stories vigentes
```
- Ejecuta BA → Architect → Dev→QA en cadena para cada iteración solicitada.
- Al finalizar, genera un snapshot en `artifacts/iterations/<nombre>` con planning, proyecto y `summary.json` para trazabilidad.
- Usa `ITERATION_NAME="beta-2025Q1"` para etiquetar explícitamente la entrega.

## 🚛 Loop Release Workflow
- Un “release loop” corresponde a una iteración completa desde el concepto hasta QA aprobado.
- `scripts/run_iteration.py` orquesta el flujo y asegura que cualquier estructura faltante en `project/` se restaure desde `project-defaults/`.
- `make iteration` acepta los siguientes parámetros clave:
  - `CONCEPT="..."` → requisito de negocio para BA/Architect.
  - `LOOPS=n` → cuántas pasadas Dev→QA ejecutar para depurar historias pendientes.
  - `ALLOW_NO_TESTS=0/1` → ejecuta QA en modo estricto o permisivo.
  - `ITERATION_NAME="release-X"` → etiqueta la entrega y su snapshot.
- Cada release deja evidencia auditable:
  - `planning/` y `project/` guardados en `artifacts/iterations/<iteration>/`.
  - `summary.json` con métricas de historias (`done`, `blocked`, `pending`) y configuración usada.
- Para reintentar historias bloqueadas tras una iteración, ejecuta `make loop MAX_LOOPS=1` con el mismo concepto; `ARCHITECT_INTERVENTION=1` (por defecto) re-planifica automáticamente cuando QA falla.

### Project Defaults
- El repositorio incluye `project-defaults/`, que contiene la estructura mínima para backend y frontend.
- Cada vez que un flujo llama a `common.ensure_dirs()`, cualquier archivo ausente en `project/` se replica desde este esqueleto sin sobrescribir cambios existentes.
- Útil tras limpiar `project/` o al iniciar un nuevo concepto: garantiza que existan paquetes (`app/__init__.py`), carpetas de tests y placeholders básicos.

## 🏗️ Supported Architectures

### Full-Stack Web Application
```
Frontend: Express.js + Node.js
Backend: FastAPI + Python
Database: ORM (SQLAlchemy/SQLite)
Testing: pytest + Jest
```

### Enterprise E-commerce (Demonstrated)
- ✅ **Authentication**: User registration/login with 2FA
- ✅ **Catalog**: Product listing with search/filter
- ✅ **Shopping Cart**: Add/remove/update with totals
- ✅ **Checkout**: Simulated payment processing
- ✅ **Testing**: >200 automated tests

## 🔧 Advanced Features

### TDD Enforcement (Mandatory Test-Driven Development)
```yaml
# All stories REQUIRE integral tests:
- id: S1
  description: User registration with email verification
  acceptance:
    - User enters details and receives confirmation email
    - Verification redirects to login
  tests_required: true  # AUTOMATIC - not optional
```

### Intelligent QA Severity Analysis
```
❌ CRITICAL ERRORS (NEVER force-approve):
   - SyntaxError, ImportError, environment_fail

✅ FORCE-APPLICABLE (P1/P0 ≥3 iterations):
   - Coverage issues, timeout, temporary issues

🔧 TEST-ONLY (Code OK, tests fail):
   - Assertion failures, separate test stories
```

### Dependency Management System
```
✅ DEPENDENT STORY RELEASED:
   - Parent story ← quality_gate_waiting
   - Test story completes → parent ← todo automatically
   - Intelligent dependency system
```

### Advanced Quality Gates
```yaml
status: done                    # Successfully completed
status: blocked_fatal          # Critical errors - permanently blocked
status: done_force_architect    # Force-approved P1/P0 by architect
status: code_done_tests_pending # Code OK, tests separated
status: quality_gate_waiting   # Waiting for test validation
status: debug_only             # Debugging mode
```

## 📊 System Architectures

### Intelligent Pipeline Flow
```
BA (Business Analysis)
  ↓
Architect (Technical Planning + Test Integration)
  ↓
Dev (Code + Tests Generation)
  ↓
QA (TDD Validation + Severity Analysis)
  ↓
[I/F Loop] Architect Intervention (Intelligent force-approval)
  ↓
[NEXT CYCLE] Re-evaluation when ALL STORIES COMPLETE
```

### Quality Assurance Intelligence
```
❌ FAIL → SEVERITY ANALYSIS → APPROPRIATE PLACEMENT
✅ PASS → DEPENDENCY RESOLUTION → WAITING STORIES RELEASED
🔄 PERSISTENT → ESCALATION → ARCHITECT INTERVENTION
```

## 🔍 Common Commands

### Complete Command Interface
```bash
# Configuration
make setup                           # Install dependencies
make set-role role=<ba|architect|dev|qa> provider=ollama model=<model>
make set-quality profile=<low|normal|high>

# Pipeline Stages
make ba                              # Business analysis → requirements.yaml
make plan                            # Architect → planning/{epics,stories,tasks}
make dev STORY=S1                    # Developer → code in project/
make qa QA_RUN_TESTS=1               # QA validation

# Integration Cycles
make loop MAX_LOOPS=10               # Dev→QA automatic loop
make loop-dev                        # Development-only cycles
make iteration CONCEPT="Login MVP" LOOPS=2  # BA→Architect→Dev→QA + snapshot in artifacts/iterations/

# Quality Intelligence
ARCHITECT_INTERVENTION=1 make loop  # Intelligent force-approval
ALLOW_NO_TESTS=1 make loop          # Permissive for bootstrap
STRICT_TDD=1 make plan              # Enforce TDD from architect

# Utilities
./.venv/bin/python scripts/fix_stories.py     # Normalize stories
./.venv/bin/python scripts/reopen_stories.py  # Reset stories to todo
make show-config                     # Display current settings
```

## ⚡ Optimized Configuration (2025)

### Recommended Models - Performance/Quality Balance
```yaml
roles:
  ba:
    provider: ollama
    model: granite4:latest                  # ⚡ Fast BA analysis
    temperature: 0.4
  architect:
    provider: ollama
    model: qwen2.5-coder:32b-instruct-q8_0   # 📐 Precision planning + TDD
    temperature: 0.2
  dev:
    provider: ollama
    model: mistral:7b-instruct-v0.1          # 🛠️ Proven code+tests generation
    temperature: 0.2
  qa:
    provider: ollama
    model: qwen2.5-coder:7b                  # 🔍 Quality analysis
    temperature: 0.2
```

### Local Codex CLI Provider (Alternative)
```yaml
# For using local CLI instead of Ollama/OpenAI
providers:
  codex_cli:
    type: codex_cli
    command: ["codex", "exec"]  # Usar 'exec' para modo no-interactivo
    cwd: "."
    timeout: 300
    input_format: flags         # 'flags' para --model + prompt directo
    output_clean: true          # Limpieza ANSI codes automática
    extra_args: []              # Argumentos adicionales opcionales

roles:
  architect:                   # ✅ Cualquier rol puede usar CLI
    provider: codex_cli
    model: gpt-5-codex        # Modelo específico para el CLI
    temperature: 0.2
    max_tokens: 4096
  dev:
    provider: codex_cli        # Cambiar provider por rol
    model: codex-local         # Distintos modelos por rol posible
    temperature: 0.2
```

**✅ Proven Working Configuration:**
- Architect role tested with `gpt-5-codex` via `make plan`
- Generates complete user stories and epics
- Logging in `artifacts/architect/last_raw.txt`
- Zero API keys required

### Demonstrated Enterprise Application
```bash
Result: 15 stories → complete e-commerce → >200 passing tests
Architecture: Fully-tested FastAPI + Express.js application
Capabilities: Auth, Product catalog, Shopping cart, Simulated checkout
Quality: 100% success rate in end-to-end pipeline
```

## 🌟 Conclusion

**This is not a development tool - it is an AI pipeline for AUTOMATED GENERATION OF COMMERCIAL APPLICATIONS.**

Generates professional code with mandatory integrated tests, intelligent QA, and automatic quality cycles. Completely demonstrated capable of creating enterprise-scale applications.

**Production-ready - generates real software with guaranteed quality.** 🚀
