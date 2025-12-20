# Estrategia de Pruebas Profundas - Orchestrator Agentic

## Resumen del Enfoque Implementado

### Arquitectura del Sistema

El proyecto implementa **DOS orchestrators complementarios**:

#### **V1: LLM-Based Orchestrator (Por defecto)**
- **Ubicación**: `scripts/run_orchestrator_agent.py::run_agentic_orchestrator()`
- **Enfoque**: Usa un LLM (GPT/Claude/Gemini) para decisiones dinámicas
- **Ventajas**:
  - Flexible y adaptable a situaciones inesperadas
  - Puede razonar sobre problemas complejos (Chain-of-Thought)
  - Puede tomar decisiones contextuales sofisticadas
- **Desventajas**:
  - Costoso (cada decisión = llamada API)
  - No determinístico (misma entrada puede dar diferentes salidas)
  - Más lento
  - Requiere parsing de respuestas JSON

#### **V2: Deterministic Orchestrator (flag `--use-v2`)**
- **Ubicación**: `scripts/orchestrator/v2_runtime.py::run_orchestrator_v2()`
- **Enfoque**: State machine + Policy engine + Learning statistics
- **Componentes**:
  - **State Machine** (`state_machine.py`): Transiciones fijas de fases
  - **Policy Engine** (`policy_engine.py`): Reglas declarativas en `config.yaml`
  - **Adaptive Policy Engine** (`adaptive_policy_engine.py`): Ajusta thresholds por estadísticas
  - **Learning Store** (`learning_store.py`): Memoria de resultados pasados
  - **Story DAG** (`story_dag.py`): Scheduling por dependencias
- **Ventajas**:
  - Determinístico y reproducible
  - Gratis (no API calls para decisiones)
  - Rápido
  - Más fácil de debuggear
- **Desventajas**:
  - Menos flexible ante situaciones imprevistas
  - Requiere configuración explícita de políticas

### ¿Es Machine Learning o Reglas?

**RESPUESTA: 100% Determinístico con Aprendizaje Estadístico por Reglas**

- **NO hay redes neuronales**
- **NO hay entrenamiento con gradientes**
- **NO hay backpropagation**

El "aprendizaje" es simplemente:
```python
# Ejemplo: Adaptive Policy Engine
success_rate = num_successes / total_attempts
dynamic_threshold = base_threshold * success_rate  # Simple multiplicación
```

Es un sistema de reglas que ajusta parámetros basándose en estadísticas simples de éxito/fallo.

---

## Matriz de Pruebas Profundas

### Dimensiones de Testing

| Dimensión | V1 (LLM) | V2 (Deterministic) | Prioridad |
|-----------|----------|-------------------|-----------|
| **Unit Tests** | Parsing, tool dispatch | State transitions, policy eval | Alta |
| **Integration Tests** | Role execution, LLM integration | DAG scheduling, adaptive policies | Alta |
| **E2E Tests** | Full pipeline CONCEPT→DONE | Full pipeline CONCEPT→DONE | **Crítica** |
| **Stress Tests** | Multiple concepts concurrentes | High story count, deep DAG | Media |
| **Failure Recovery** | Malformed JSON, API errors | Story failures, escalation | Alta |
| **Performance** | Latency, cost tracking | Throughput, determinism | Alta |
| **Consistency** | Repeatability (¿misma decisión?) | Reproducibility (mismos resultados) | Media |
| **Learning Validation** | N/A (stateless) | Learning store correctness | Media |

---

## Escenarios de Prueba Detallados

### 1. E2E: Pipeline Completo (Happy Path)

**Objetivo**: Validar que ambos orchestrators completen el ciclo BA→PO→Arch→Dev→QA

**Conceptos de prueba**:
- Simple: "Health check API endpoint" (1 story)
- Medium: "User CRUD REST API" (3-5 stories)
- Complex: "E-commerce cart with inventory" (8+ stories con dependencias)

**Comandos**:
```bash
# V1 (LLM-based)
make clean FLUSH=1
make agentic-iteration CONCEPT="Aplicativo para generar imagenes del inframundo" MAX_STEPS=10 MAX_ACTIONS=3

# V2 (Deterministic)
c
PYTHONPATH=. .venv/bin/python scripts/run_orchestrator_agent.py \
  --concept "Health check API endpoint" \
  --max-steps 10 \
  --use-v2
```

**Validaciones**:
- ✓ `planning/requirements.yaml` existe y tiene FR válidos
- ✓ `planning/stories.yaml` con status `done` en todas las historias
- ✓ `project/` contiene código generado
- ✓ Tests ejecutados y pasando
- ✓ `artifacts/iterations/latest_orchestrator_summary.json` tiene termination exitosa

### 2. Failure Recovery: Dev Failures + Escalation

**Objetivo**: Validar que el sistema maneja fallos de Dev y escala a Architect

**Setup**:
- Configurar `config.yaml` con retry policies:
```yaml
pipeline:
  retry_policies:
    dev:
      max_attempts: 3
      backoff: exponential
  escalation_policies:
    - condition: "dev_attempts >= 3 AND same_error_pattern"
      action: "architect_refine"
      reason: "Repeated dev failures"
```

**Simulación de fallo**:
- Inyectar un concepto que cause errores consistentes en Dev (ej: requerimientos contradictorios)
- Observar que tras 3 intentos se llama a Architect para refinamiento

**Comandos**:
```bash
make agentic-iteration CONCEPT="API with conflicting requirements: read-only but allow updates" \
  MAX_STEPS=15 MAX_ACTIONS=2
```

**Validaciones**:
- ✓ Dev falla 3 veces (en `learning_store.jsonl`)
- ✓ Architect es llamado para refinar story
- ✓ Dev reintenta con story refinada
- ✓ Pipeline NO aborta prematuramente

### 3. Concurrency & Parallelism (V2 only)

**Objetivo**: Validar que V2 ejecuta stories independientes en paralelo

**Setup**:
- Concepto con 5+ stories sin dependencias entre sí
- Configurar `max_parallel_stories: 3` en `config.yaml`

**Comandos**:
```bash
make agentic-iteration CONCEPT="Microservices suite: auth, products, orders, payments, notifications" \
  MAX_STEPS=20 MAX_ACTIONS=5 --use-v2
```

**Validaciones**:
- ✓ Múltiples stories en status `doing` simultáneamente (max 3)
- ✓ Tiempo total < suma de tiempos individuales (indica paralelismo)
- ✓ No hay race conditions en `stories.yaml`

### 4. CoT Tracking Validation

**Objetivo**: Validar que el sistema de Chain-of-Thought registra decisiones

**Comandos**:
```bash
make agentic-iteration CONCEPT="Simple calculator API" MAX_STEPS=5 MAX_ACTIONS=2

# Inspeccionar CoT artifacts
ls -lh artifacts/cot_layer6/
PYTHONPATH=. .venv/bin/python scripts/orchestrator/cot_analytics.py
```

**Validaciones**:
- ✓ `artifacts/cot_layer6/` contiene traces por step
- ✓ Cada decisión tiene contexto suficiente para reconstruir razonamiento
- ✓ Analytics genera reportes en JSON/Markdown
- ✓ Learning store tiene entries por story

### 5. Determinism Check (V2)

**Objetivo**: Validar que V2 produce resultados idénticos en ejecuciones repetidas

**Comandos**:
```bash
CONCEPT="Todo list REST API"

# Run 1
make clean FLUSH=1
.venv/bin/python scripts/run_orchestrator_agent.py --concept "$CONCEPT" --max-steps 10 --use-v2
cp artifacts/iterations/latest_orchestrator_summary.json /tmp/run1.json

# Run 2
make clean FLUSH=1
.venv/bin/python scripts/run_orchestrator_agent.py --concept "$CONCEPT" --max-steps 10 --use-v2
cp artifacts/iterations/latest_orchestrator_summary.json /tmp/run2.json

# Compare
diff /tmp/run1.json /tmp/run2.json
```

**Validaciones**:
- ✓ Mismas fases ejecutadas en mismo orden
- ✓ Mismas stories generadas (IDs pueden variar, pero títulos y orden deben coincidir)
- ✓ Timestamps diferentes, pero decisiones idénticas

### 6. Performance Benchmark: V1 vs V2

**Objetivo**: Comparar latencia, costo y throughput

**Comandos**:
```bash
# Script de benchmark (crear en tests/benchmark/)
time make agentic-iteration CONCEPT="User authentication system" MAX_STEPS=15  # V1
time .venv/bin/python scripts/run_orchestrator_agent.py --concept "User authentication system" --max-steps 15 --use-v2  # V2
```

**Métricas a capturar**:
- Tiempo total de ejecución
- Número de llamadas LLM (V1 tendrá muchas más)
- Costo estimado (tokens consumidos)
- Throughput (stories completadas / minuto)

**Expected**:
- V2 debería ser 3-10x más rápido
- V2 debería costar ~80% menos (solo usa LLM en roles, no en orquestación)

### 7. Guardrails: Pipeline Guard Integration

**Objetivo**: Validar que guardrails detienen ejecución ante errores estructurales

**Comandos**:
```bash
# Forzar un planning incompleto (sin implements)
make ba CONCEPT="Test feature"
echo "stories: [{id: S1, title: Test, status: todo}]" > planning/stories.yaml

# Ejecutar pipeline guard
PYTHONPATH=. CHECK_ARCHITECTURE=0 python scripts/checks/pipeline_guard.py

# Intentar orchestrator (debería fallar)
make agentic-iteration CONCEPT="Test feature" MAX_STEPS=3
```

**Validaciones**:
- ✓ Pipeline guard detecta missing `implements`
- ✓ Guard escribe reporte en `artifacts/qa/pipeline_guard.json`
- ✓ Orchestrator NO ejecuta Dev si guard falla

### 8. Learning Store Persistence

**Objetivo**: Validar que learning store persiste entre ejecuciones

**Comandos**:
```bash
# Run 1: Primera ejecución con fallos
make agentic-iteration CONCEPT="Buggy feature" MAX_STEPS=5

# Verificar learning store
cat artifacts/learning/learning_store.jsonl | wc -l  # Debe tener entries

# Run 2: Segunda ejecución, debería ajustar thresholds
make agentic-iteration CONCEPT="Buggy feature" MAX_STEPS=5

# Comparar thresholds
cat artifacts/learning/learning_store.jsonl | tail -10
```

**Validaciones**:
- ✓ Learning store es append-only
- ✓ Segunda ejecución usa datos de primera (logs deben mencionar "learning from previous attempts")
- ✓ Adaptive policies ajustan thresholds basándose en success rates

---

## Scripts Automatizados de Testing

### Script 1: Test Suite Completo

**Ubicación**: `tests/scripts/run_orchestrator_full_test.sh`

```bash
#!/bin/bash
set -e

echo "=== ORCHESTRATOR DEEP TESTING SUITE ==="

# 1. Happy path V1
echo "[1/8] E2E Happy Path V1..."
make clean FLUSH=1
make agentic-iteration CONCEPT="Health check endpoint" MAX_STEPS=10 MAX_ACTIONS=2
test -f planning/requirements.yaml || exit 1
test -f planning/stories.yaml || exit 1

# 2. Happy path V2
echo "[2/8] E2E Happy Path V2..."
make clean FLUSH=1
PYTHONPATH=. .venv/bin/python scripts/run_orchestrator_agent.py \
  --concept "Health check endpoint" --max-steps 10 --use-v2
test -f artifacts/iterations/latest_orchestrator_summary.json || exit 1

# 3. Failure recovery
echo "[3/8] Failure Recovery..."
make clean FLUSH=1
make agentic-iteration CONCEPT="Contradictory requirements: read-only with write operations" MAX_STEPS=15

# 4. CoT tracking
echo "[4/8] CoT Tracking..."
test -d artifacts/cot_layer6 || exit 1
PYTHONPATH=. .venv/bin/python scripts/orchestrator/cot_analytics.py

# 5. Learning store
echo "[5/8] Learning Store Persistence..."
test -f artifacts/learning/learning_store.jsonl || exit 1
wc -l artifacts/learning/learning_store.jsonl

# 6. Pipeline guard
echo "[6/8] Pipeline Guard..."
PYTHONPATH=. CHECK_ARCHITECTURE=0 python scripts/checks/pipeline_guard.py
test -f artifacts/qa/pipeline_guard.json || exit 1

# 7. Unit tests
echo "[7/8] Unit Tests..."
.venv/bin/pytest tests/test_orchestrator_v2_*.py -v

# 8. Integration tests
echo "[8/8] Integration Tests..."
.venv/bin/pytest tests/scripts/test_orchestrator_*.py -v

echo "=== ALL TESTS PASSED ==="
```

### Script 2: Benchmark V1 vs V2

**Ubicación**: `tests/scripts/benchmark_orchestrators.sh`

```bash
#!/bin/bash
set -e

CONCEPT="User authentication REST API with JWT"

echo "=== BENCHMARKING V1 vs V2 ==="

# V1
echo "Running V1..."
make clean FLUSH=1 > /dev/null 2>&1
START_V1=$(date +%s)
make agentic-iteration CONCEPT="$CONCEPT" MAX_STEPS=15 MAX_ACTIONS=3 > /tmp/v1.log 2>&1
END_V1=$(date +%s)
V1_TIME=$((END_V1 - START_V1))

# V2
echo "Running V2..."
make clean FLUSH=1 > /dev/null 2>&1
START_V2=$(date +%s)
PYTHONPATH=. .venv/bin/python scripts/run_orchestrator_agent.py \
  --concept "$CONCEPT" --max-steps 15 --use-v2 > /tmp/v2.log 2>&1
END_V2=$(date +%s)
V2_TIME=$((END_V2 - START_V2))

echo ""
echo "=== RESULTS ==="
echo "V1 (LLM-based): ${V1_TIME}s"
echo "V2 (Deterministic): ${V2_TIME}s"
echo "Speedup: $((V1_TIME * 100 / V2_TIME - 100))% faster"

# Count LLM calls (rough estimate from logs)
V1_LLM_CALLS=$(grep -c "client.chat" /tmp/v1.log || echo "N/A")
V2_LLM_CALLS=$(grep -c "client.chat" /tmp/v2.log || echo "N/A")
echo "V1 LLM calls: $V1_LLM_CALLS"
echo "V2 LLM calls: $V2_LLM_CALLS"
```

### Script 3: Determinism Validator

**Ubicación**: `tests/scripts/validate_determinism.sh`

```bash
#!/bin/bash
set -e

CONCEPT="Simple calculator REST API"

echo "=== VALIDATING V2 DETERMINISM ==="

for i in 1 2 3; do
  echo "Run $i..."
  make clean FLUSH=1 > /dev/null 2>&1
  PYTHONPATH=. .venv/bin/python scripts/run_orchestrator_agent.py \
    --concept "$CONCEPT" --max-steps 10 --use-v2 > /dev/null 2>&1
  cp artifacts/iterations/latest_orchestrator_summary.json /tmp/run${i}.json
done

echo "Comparing runs..."
if diff /tmp/run1.json /tmp/run2.json > /dev/null && \
   diff /tmp/run2.json /tmp/run3.json > /dev/null; then
  echo "✓ DETERMINISM VALIDATED: All 3 runs identical"
else
  echo "✗ DETERMINISM FAILED: Runs differ"
  exit 1
fi
```

---

## Métricas de Éxito

### Criterios de Aceptación

| Métrica | V1 Target | V2 Target |
|---------|-----------|-----------|
| **E2E Success Rate** | ≥80% | ≥90% |
| **Failure Recovery** | Escalate after 3 failures | Escalate after 3 failures |
| **Determinism** | N/A | 100% (3/3 runs identical) |
| **Performance (simple concept)** | <5 min | <2 min |
| **Performance (complex concept)** | <20 min | <10 min |
| **Test Coverage** | ≥70% | ≥80% |
| **Learning Store Retention** | N/A | 20 entries/story |

### Comandos de Verificación

```bash
# Coverage
.venv/bin/pytest --cov=scripts/orchestrator --cov-report=html

# Success rate (manual log analysis)
grep "termination.*should_stop.*true" artifacts/iterations/*.json | wc -l

# Determinism
./tests/scripts/validate_determinism.sh

# Performance
./tests/scripts/benchmark_orchestrators.sh
```

---

## Próximos Pasos

1. **Ejecutar suite base**: `./tests/scripts/run_orchestrator_full_test.sh`
2. **Benchmark V1 vs V2**: `./tests/scripts/benchmark_orchestrators.sh`
3. **Validar determinism**: `./tests/scripts/validate_determinism.sh`
4. **Revisar métricas**: Analizar resultados y ajustar thresholds en `config.yaml`
5. **Iterar**: Identificar fallos y refinar políticas

---

## Referencias

- **PROJECT_MEMORY.md**: Resumen del orchestrator agentic y CoT
- **PIPELINE_IMPROVES.md**: Histórico de mejoras de guardrails
- **config.yaml**: Configuración de políticas y providers
- **scripts/orchestrator/**: Módulos del V2 orchestrator
- **tests/test_orchestrator_v2_*.py**: Tests unitarios y E2E existentes
