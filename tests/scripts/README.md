# Orchestrator Deep Testing Scripts

Scripts automatizados para validación profunda de los orchestrators V1 (LLM-based) y V2 (Deterministic).

## Scripts Disponibles

### 1. `run_all_deep_tests.sh` - Master Test Runner ⭐

**Ejecuta todas las suites de testing en secuencia.**

```bash
./tests/scripts/run_all_deep_tests.sh
```

**Incluye:**
- Functional test suite (8 test cases)
- Performance benchmark (V1 vs V2)
- Determinism validation (V2)

**Tiempo estimado:** 30-60 minutos

**Output:**
- Logs en `/tmp/deep_test_phase*.log`
- Reporte final en `/tmp/orchestrator_deep_test_report.txt`

**Exit codes:**
- `0`: Todos los tests pasaron
- `1`: Determinismo falló (crítico)
- `2`: Tests funcionales con warnings

---

### 2. `run_orchestrator_full_test.sh` - Functional Test Suite

**Ejecuta 8 test cases funcionales:**

1. E2E Happy Path V1 (LLM-based)
2. E2E Happy Path V2 (Deterministic)
3. Failure Recovery & Escalation
4. CoT Tracking Validation
5. Learning Store Persistence
6. Pipeline Guard Integration
7. Unit Tests (V2 modules)
8. Integration Tests (Runtime)

```bash
./tests/scripts/run_orchestrator_full_test.sh
```

**Validaciones:**
- ✓ Planning artifacts generados correctamente
- ✓ Stories completadas con status `done`
- ✓ CoT traces registrados
- ✓ Learning store con entries válidos
- ✓ Pipeline guard detecta errores estructurales
- ✓ Tests unitarios e integración pasando

**Output:**
- Logs en `/tmp/test_*.log`
- Artifacts en `artifacts/`, `planning/`

---

### 3. `benchmark_orchestrators.sh` - Performance Comparison

**Compara V1 vs V2 en métricas de rendimiento.**

```bash
# Uso básico
./tests/scripts/benchmark_orchestrators.sh

# Con concepto y steps personalizados
./tests/scripts/benchmark_orchestrators.sh "User auth API" 15
```

**Métricas medidas:**
- ⏱️ Tiempo de ejecución total
- 🔄 Número de llamadas LLM (orchestrator)
- 📊 Throughput (stories completadas/minuto)
- 💰 Estimación de costos (orchestration only)

**Expected results:**
- V2 debería ser **3-10x más rápido** que V1
- V2 debería tener **0 llamadas LLM de orchestración** (vs muchas en V1)
- V2 debería costar **~80% menos** en orchestration

**Output:**
- `/tmp/bench_v1.log` - Log de V1
- `/tmp/bench_v2.log` - Log de V2
- Tabla comparativa en stdout

---

### 4. `validate_determinism.sh` - Determinism Validator

**Valida que V2 produce resultados idénticos en ejecuciones repetidas.**

```bash
# Uso básico (3 runs)
./tests/scripts/validate_determinism.sh

# Con concepto y steps personalizados
./tests/scripts/validate_determinism.sh "Calculator API" 8
```

**Validaciones:**
1. Secuencias de decisiones idénticas (steps)
2. Estado de stories idéntico (mismo id, status, orden)
3. Fase final idéntica (DONE, FAILED, etc.)

**Output:**
- `/tmp/determinism_run*.log` - Logs de cada run
- `/tmp/determinism_run*_summary.json` - Summaries
- `/tmp/determinism_diff_*.txt` - Diffs si hay diferencias

**Exit codes:**
- `0`: Determinismo validado (3/3 runs idénticos)
- `1`: Runs difieren (requiere investigación)

---

## Flujo de Testing Recomendado

### Opción 1: Quick Start (Todo automático)

```bash
# Ejecutar suite completa
./tests/scripts/run_all_deep_tests.sh

# Revisar reporte
cat /tmp/orchestrator_deep_test_report.txt
```

### Opción 2: Testing Manual (Step-by-step)

```bash
# 1. Tests funcionales
./tests/scripts/run_orchestrator_full_test.sh

# 2. Benchmark
./tests/scripts/benchmark_orchestrators.sh "Simple API" 12

# 3. Determinismo
./tests/scripts/validate_determinism.sh "Calculator" 8

# 4. Unit tests
cd ../..  # repo root
.venv/bin/pytest tests/test_orchestrator_v2_*.py -v

# 5. Coverage
.venv/bin/pytest --cov=scripts/orchestrator --cov-report=html
open htmlcov/index.html
```

### Opción 3: Testing de Regresión (CI/CD)

```bash
# En CI, ejecutar con timeout y capturar exit code
timeout 3600 ./tests/scripts/run_all_deep_tests.sh
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "✓ All tests passed"
elif [ $EXIT_CODE -eq 1 ]; then
  echo "✗ Determinism failed - CRITICAL"
  exit 1
elif [ $EXIT_CODE -eq 2 ]; then
  echo "⚠ Tests passed with warnings"
fi
```

---

## Requisitos

### Setup inicial

```bash
cd /path/to/agnostic-ai-pipeline
make setup
```

### Configuración de providers

Los tests requieren al menos un LLM provider configurado en `config.yaml`:

```yaml
roles:
  orchestrator:
    provider: openai  # o claude_cli, vertex_sdk, ollama
    model: gpt-4o-mini
```

Para tests solo de V2 (determinístico), no se requiere configuración adicional.

### Dependencias

```bash
# Python packages
pip install pytest pytest-asyncio pyyaml httpx

# CLI tools (opcional, solo para algunos providers)
# Claude CLI: brew install anthropics/tap/claude
# Vertex AI: gcloud auth application-default login

# jq (para scripts de comparación)
brew install jq  # macOS
apt-get install jq  # Linux
```

---

## Interpretación de Resultados

### ✓ PASS - Todo funciona correctamente

```
✓ V1 generated planning artifacts
✓ V2 generated summary artifact
✓ Pipeline guard generated report
✓ Unit tests: 45 passed
✓ DETERMINISM VALIDATED: All 3 runs identical
```

**Acción:** Ninguna, orchestrator listo para producción.

---

### ⚠ WARNINGS - Tests funcionales con issues menores

```
⚠ V1 execution failed or timed out (this may be expected if LLM unavailable)
⚠ No failures recorded in learning store
⚠ CoT directory not found (may be feature-flagged)
```

**Posibles causas:**
- LLM provider no configurado o sin API key
- Features opcionales deshabilitadas (CoT, learning store)
- Timeouts por conceptos muy complejos

**Acción:**
1. Revisar logs en `/tmp/test_*.log`
2. Verificar `config.yaml` tiene provider válido
3. Aumentar timeouts si necesario

---

### ✗ FAIL - Determinismo roto (CRÍTICO)

```
✗ Run 1 and Run 2: DIFFER
✗ Stories state: DIFFER
✗ DETERMINISM VALIDATION FAILED
```

**Posibles causas:**
- Timestamps o IDs no normalizados
- Race conditions en state machine
- Operaciones no determinísticas (random, datetime.now())
- Orden de dict keys (Python < 3.7)

**Acción:**
1. Revisar diffs en `/tmp/determinism_diff_*.txt`
2. Inspeccionar `scripts/orchestrator/state_machine.py`
3. Verificar que no hay randomness en decisiones
4. Correr `validate_determinism.sh` nuevamente tras fixes

---

## Troubleshooting

### "V1 execution timed out"

**Solución:**
```bash
# Aumentar timeout en el script
timeout 1800 make agentic-iteration ...  # 30 min
```

### "V2 did not generate summary"

**Solución:**
- Revisar que `--use-v2` está presente
- Verificar que `scripts/orchestrator/v2_runtime.py` existe
- Chequear logs en `/tmp/test_v2.log`

### "Pipeline guard reported issues"

**Solución:**
- Es esperado si stories no tienen `implements`
- Validar que `planning/requirements.yaml` tiene FRs válidos
- Ejecutar: `PYTHONPATH=. python scripts/checks/pipeline_guard.py`

### "Determinism test fails intermittently"

**Solución:**
- Verificar que no hay procesos en background modificando artifacts
- Limpiar estado: `make clean FLUSH=1`
- Revisar si hay dependencias de timestamps
- Correr con conceptos más simples primero

---

## Métricas de Éxito

| Métrica | V1 Target | V2 Target |
|---------|-----------|-----------|
| **E2E Success Rate** | ≥80% | ≥90% |
| **Failure Recovery** | 3 attempts → escalate | 3 attempts → escalate |
| **Determinism** | N/A | 100% (3/3 identical) |
| **Perf (simple)** | <5 min | <2 min |
| **Perf (complex)** | <20 min | <10 min |
| **Test Coverage** | ≥70% | ≥80% |

---

## Referencias

- **Estrategia completa**: `docs/TESTING_STRATEGY_ORCHESTRATOR.md`
- **Project memory**: `docs/PROJECT_MEMORY.md`
- **Orchestrator V2 code**: `scripts/orchestrator/v2_runtime.py`
- **State machine**: `scripts/orchestrator/state_machine.py`
- **Policy engine**: `scripts/orchestrator/policy_engine.py`

---

## Contribuir

Al agregar nuevos features al orchestrator:

1. **Agregar unit test** en `tests/test_orchestrator_v2_*.py`
2. **Validar determinismo** con `validate_determinism.sh`
3. **Actualizar benchmark** si afecta performance
4. **Documentar en** `TESTING_STRATEGY_ORCHESTRATOR.md`

Para agregar nuevos test cases:

```bash
# 1. Crear test en tests/scripts/
vim tests/scripts/test_new_feature.sh

# 2. Hacerlo ejecutable
chmod +x tests/scripts/test_new_feature.sh

# 3. Integrarlo en run_orchestrator_full_test.sh
# o crear suite separada si es independiente

# 4. Actualizar este README
```
