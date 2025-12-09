#!/bin/bash
# Script auxiliar para ejecutar smoke tests del orquestador agentic
# Uso: ./scripts/run_orchestrator_smoke_tests.sh [test_name]
#
# Sin argumentos: ejecuta todos los tests
# Con argumento: ejecuta solo el test especificado
#   - trivial
#   - simple
#   - moderate
#   - full
#   - cleanup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==> Orchestrator Agentic Smoke Tests${NC}"
echo ""

# Función para ejecutar un test específico
run_test() {
    local test_name=$1
    local test_function=$2

    echo -e "${YELLOW}Running: $test_name${NC}"
    .venv/bin/pytest tests/smoke/test_agentic_orchestrator.py::$test_function -v -s
    echo ""
}

# Si se proporciona un argumento, ejecutar solo ese test
if [ $# -eq 1 ]; then
    case $1 in
        trivial)
            run_test "Test 1: Trivial Concept" "test_orchestrator_trivial_concept"
            ;;
        simple)
            run_test "Test 2: Simple Concept" "test_orchestrator_simple_concept"
            ;;
        moderate)
            run_test "Test 3: Moderate Concept" "test_orchestrator_moderate_concept"
            ;;
        full)
            run_test "Test 4: Full Pipeline (BA→PO→Arch→Dev→QA)" "test_orchestrator_full_pipeline"
            ;;
        cleanup)
            run_test "Test 5: Cleanup" "test_orchestrator_cleanup"
            ;;
        *)
            echo "Error: Unknown test '$1'"
            echo "Available tests: trivial, simple, moderate, full, cleanup"
            exit 1
            ;;
    esac
else
    # Ejecutar todos los tests en orden
    echo -e "${GREEN}Running all smoke tests in sequence...${NC}"
    echo ""

    run_test "Test 1: Trivial Concept" "test_orchestrator_trivial_concept"
    run_test "Test 2: Simple Concept" "test_orchestrator_simple_concept"
    run_test "Test 3: Moderate Concept" "test_orchestrator_moderate_concept"
    run_test "Test 4: Full Pipeline (BA→PO→Arch→Dev→QA)" "test_orchestrator_full_pipeline"
    run_test "Test 5: Cleanup" "test_orchestrator_cleanup"

    echo -e "${GREEN}==> All smoke tests completed!${NC}"
fi

# Mostrar resumen del último summary generado
if [ -f "artifacts/iterations/latest_orchestrator_summary.json" ]; then
    echo ""
    echo -e "${BLUE}==> Latest Orchestrator Summary:${NC}"
    cat artifacts/iterations/latest_orchestrator_summary.json | head -50
fi
