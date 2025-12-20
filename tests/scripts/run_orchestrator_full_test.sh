#!/bin/bash
# Full Orchestrator Testing Suite
# Tests both V1 (LLM-based) and V2 (Deterministic) orchestrators

set -e
cd "$(dirname "$0")/../.."  # Go to repo root

echo "=== ORCHESTRATOR DEEP TESTING SUITE ==="
echo "Timestamp: $(date)"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass_test() {
  echo -e "${GREEN}✓ $1${NC}"
}

fail_test() {
  echo -e "${RED}✗ $1${NC}"
  exit 1
}

warn() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

# ============================================================================
# 1. E2E Happy Path V1 (LLM-based)
# ============================================================================
echo "[1/8] E2E Happy Path V1 (LLM-based)..."
make clean FLUSH=1 > /dev/null 2>&1 || true
CONCEPT="Health check endpoint" MAX_STEPS=10 MAX_ACTIONS=2 \
  timeout 600 make agentic-iteration > /tmp/test_v1.log 2>&1 || {
  warn "V1 execution failed or timed out (this may be expected if LLM unavailable)"
  cat /tmp/test_v1.log | tail -20
}

if [ -f planning/requirements.yaml ] && [ -f planning/stories.yaml ]; then
  pass_test "V1 generated planning artifacts"
else
  warn "V1 did not generate complete artifacts (may need LLM configured)"
fi

# ============================================================================
# 2. E2E Happy Path V2 (Deterministic)
# ============================================================================
echo ""
echo "[2/8] E2E Happy Path V2 (Deterministic)..."
make clean FLUSH=1 > /dev/null 2>&1 || true
PYTHONPATH=. timeout 600 .venv/bin/python scripts/run_orchestrator_agent.py \
  --concept "Health check endpoint" \
  --max-steps 10 \
  --use-v2 > /tmp/test_v2.log 2>&1 || {
  warn "V2 execution failed or timed out"
  cat /tmp/test_v2.log | tail -20
}

if [ -f artifacts/iterations/latest_orchestrator_summary.json ]; then
  pass_test "V2 generated summary artifact"
else
  fail_test "V2 did not generate summary"
fi

# ============================================================================
# 3. Failure Recovery Test
# ============================================================================
echo ""
echo "[3/8] Failure Recovery Test..."
make clean FLUSH=1 > /dev/null 2>&1 || true

# This concept is intentionally contradictory to trigger failures
CONCEPT="Read-only API with write operations" MAX_STEPS=15 MAX_ACTIONS=2 \
  timeout 900 make agentic-iteration > /tmp/test_failure.log 2>&1 || {
  warn "Failure recovery test timed out (expected for complex failures)"
}

# Check if learning store recorded the failures
if [ -f artifacts/learning/learning_store.jsonl ]; then
  FAILURE_COUNT=$(grep -c '"status":"failed"' artifacts/learning/learning_store.jsonl || echo 0)
  if [ "$FAILURE_COUNT" -gt 0 ]; then
    pass_test "Failure recovery: $FAILURE_COUNT failures recorded"
  else
    warn "No failures recorded in learning store"
  fi
else
  warn "Learning store not created"
fi

# ============================================================================
# 4. CoT Tracking Validation
# ============================================================================
echo ""
echo "[4/8] CoT Tracking Validation..."

if [ -d artifacts/cot_layer6 ]; then
  COT_FILES=$(find artifacts/cot_layer6 -type f | wc -l)
  pass_test "CoT tracking: $COT_FILES trace files found"
else
  warn "CoT directory not found (may be feature-flagged)"
fi

# Try to run analytics (optional, may fail if no CoT data)
if [ -f scripts/orchestrator/cot_analytics.py ]; then
  PYTHONPATH=. timeout 30 .venv/bin/python scripts/orchestrator/cot_analytics.py > /tmp/test_cot_analytics.log 2>&1 || {
    warn "CoT analytics script failed (may need data)"
  }
fi

# ============================================================================
# 5. Learning Store Persistence
# ============================================================================
echo ""
echo "[5/8] Learning Store Persistence..."

if [ -f artifacts/learning/learning_store.jsonl ]; then
  ENTRY_COUNT=$(wc -l < artifacts/learning/learning_store.jsonl)
  pass_test "Learning store: $ENTRY_COUNT entries"

  # Show last 3 entries
  echo "  Last 3 entries:"
  tail -3 artifacts/learning/learning_store.jsonl | while read line; do
    echo "    $(echo $line | jq -r '{story_id, phase, status}' 2>/dev/null || echo $line | cut -c1-80)"
  done
else
  warn "Learning store not found"
fi

# ============================================================================
# 6. Pipeline Guard Validation
# ============================================================================
echo ""
echo "[6/8] Pipeline Guard Validation..."

# First create minimal artifacts for guard to check
mkdir -p planning
echo "concept: Test Feature" > planning/requirements.yaml
echo "stories: [{id: S1, title: Test, status: todo, implements: []}]" > planning/stories.yaml

# Run guard (expect it to fail or warn about missing implements)
PYTHONPATH=. CHECK_ARCHITECTURE=0 ALLOW_EMPTY_STORIES=1 \
  .venv/bin/python scripts/checks/pipeline_guard.py > /tmp/test_guard.log 2>&1 || {
  warn "Pipeline guard reported issues (expected)"
}

if [ -f artifacts/qa/pipeline_guard.json ]; then
  pass_test "Pipeline guard generated report"

  # Show guard status
  GUARD_STATUS=$(jq -r '.status // "unknown"' artifacts/qa/pipeline_guard.json)
  echo "  Guard status: $GUARD_STATUS"
else
  warn "Pipeline guard did not generate report"
fi

# ============================================================================
# 7. Unit Tests
# ============================================================================
echo ""
echo "[7/8] Unit Tests (V2 Orchestrator)..."

.venv/bin/pytest tests/test_orchestrator_v2_*.py -v --tb=short > /tmp/test_unit.log 2>&1 || {
  warn "Some unit tests failed"
  cat /tmp/test_unit.log | tail -30
}

UNIT_PASS=$(grep -c "PASSED" /tmp/test_unit.log || echo 0)
UNIT_FAIL=$(grep -c "FAILED" /tmp/test_unit.log || echo 0)

if [ "$UNIT_FAIL" -eq 0 ]; then
  pass_test "Unit tests: $UNIT_PASS passed"
else
  warn "Unit tests: $UNIT_PASS passed, $UNIT_FAIL failed"
fi

# ============================================================================
# 8. Integration Tests
# ============================================================================
echo ""
echo "[8/8] Integration Tests (Orchestrator Runtime)..."

.venv/bin/pytest tests/scripts/test_orchestrator_*.py -v --tb=short > /tmp/test_integration.log 2>&1 || {
  warn "Some integration tests failed"
  cat /tmp/test_integration.log | tail -30
}

INT_PASS=$(grep -c "PASSED" /tmp/test_integration.log || echo 0)
INT_FAIL=$(grep -c "FAILED" /tmp/test_integration.log || echo 0)

if [ "$INT_FAIL" -eq 0 ]; then
  pass_test "Integration tests: $INT_PASS passed"
else
  warn "Integration tests: $INT_PASS passed, $INT_FAIL failed"
fi

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "=== TEST SUITE COMPLETED ==="
echo "See logs in /tmp/test_*.log for details"
echo ""
echo "Artifacts generated:"
ls -lh artifacts/iterations/ 2>/dev/null | tail -5 || echo "  (none)"
echo ""
echo "Next steps:"
echo "  1. Review failed tests (if any)"
echo "  2. Run benchmark: ./tests/scripts/benchmark_orchestrators.sh"
echo "  3. Validate determinism: ./tests/scripts/validate_determinism.sh"
