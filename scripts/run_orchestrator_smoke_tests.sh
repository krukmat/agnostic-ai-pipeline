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

run_guard_scenario() {
    echo -e "${YELLOW}Running: Guarded Multi-epic Concept (direct orchestrator run)${NC}"
    local concept="Federated subtitle orchestration for global cinema premieres"
    CONCEPT="$concept" .venv/bin/python scripts/run_orchestrator_agent.py \
        --concept "$concept" \
        --use-v2 \
        --max-steps 4 \
        --max-actions-per-step 2

    python - <<'PY'
from pathlib import Path
import yaml

stories_path = Path("planning/stories.yaml")
if not stories_path.exists():
    raise SystemExit("stories.yaml missing after guard scenario")
stories = yaml.safe_load(stories_path.read_text(encoding="utf-8")) or []
assert isinstance(stories, list) and stories, "stories.yaml must contain stories"
for story in stories:
    if isinstance(story, dict):
        implements = story.get("implements")
        if not isinstance(implements, list):
            raise SystemExit(f"Story {story.get('id')} missing implements list")
print("✓ Guard scenario verified: all stories include implements lists")
PY
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
        guard)
            run_guard_scenario
            ;;
        cleanup)
            run_test "Test 5: Cleanup" "test_orchestrator_cleanup"
            ;;
        *)
            echo "Error: Unknown test '$1'"
            echo "Available tests: trivial, simple, moderate, full, guard, cleanup"
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
    run_guard_scenario
    run_test "Test 5: Cleanup" "test_orchestrator_cleanup"

    echo -e "${GREEN}==> All smoke tests completed!${NC}"
fi

# Mostrar resumen del último summary generado
if [ -f "artifacts/iterations/latest_orchestrator_summary.json" ]; then
    echo ""
    echo -e "${BLUE}==> Latest Orchestrator Summary:${NC}"
    cat artifacts/iterations/latest_orchestrator_summary.json | head -50
fi

echo ""
echo -e "${BLUE}==> Running coverage guard for Phase 5 modules${NC}"
.venv/bin/pytest --maxfail=1 --disable-warnings \
  --cov=scripts/orchestrator/cot_analytics.py \
  --cov=scripts/tools/generate_implements.py \
  --cov-report=term \
  --cov-fail-under=80 \
  tests/scripts/test_cot_analytics.py \
  tests/scripts/test_generate_implements.py
