#!/bin/bash
# Master test runner for deep orchestrator validation
# Runs all test suites in sequence

set -e
cd "$(dirname "$0")/../.."  # Go to repo root

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                                                                    ║"
echo "║     ORCHESTRATOR DEEP TESTING - COMPLETE VALIDATION SUITE         ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "This will run:"
echo "  1. Full functional test suite (both V1 and V2)"
echo "  2. Performance benchmark (V1 vs V2)"
echo "  3. Determinism validation (V2)"
echo ""
echo "Estimated time: 30-60 minutes (depending on LLM speed)"
echo ""

# Ask for confirmation
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 1
fi

START_TIME=$(date +%s)

# ============================================================================
# 1. Full Test Suite
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHASE 1: FULL FUNCTIONAL TEST SUITE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

./tests/scripts/run_orchestrator_full_test.sh 2>&1 | tee /tmp/deep_test_phase1.log

PHASE1_EXIT=${PIPESTATUS[0]}
if [ $PHASE1_EXIT -ne 0 ]; then
  echo ""
  echo "⚠ Phase 1 had warnings (see /tmp/deep_test_phase1.log)"
fi

# ============================================================================
# 2. Performance Benchmark
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHASE 2: PERFORMANCE BENCHMARK (V1 vs V2)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

./tests/scripts/benchmark_orchestrators.sh "Simple todo list API" 12 2>&1 | tee /tmp/deep_test_phase2.log

PHASE2_EXIT=${PIPESTATUS[0]}
if [ $PHASE2_EXIT -ne 0 ]; then
  echo ""
  echo "⚠ Phase 2 had warnings (see /tmp/deep_test_phase2.log)"
fi

# ============================================================================
# 3. Determinism Validation
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHASE 3: DETERMINISM VALIDATION (V2)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

./tests/scripts/validate_determinism.sh "Calculator API" 8 2>&1 | tee /tmp/deep_test_phase3.log

PHASE3_EXIT=${PIPESTATUS[0]}
if [ $PHASE3_EXIT -ne 0 ]; then
  echo ""
  echo "⚠ Phase 3 FAILED - V2 is not deterministic (see /tmp/deep_test_phase3.log)"
fi

# ============================================================================
# FINAL SUMMARY
# ============================================================================
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

echo ""
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                                                                    ║"
echo "║                    DEEP TESTING COMPLETE                           ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Total time: ${ELAPSED_MIN}m ${ELAPSED_SEC}s"
echo ""
echo "Results:"
echo "  Phase 1 (Functional):   $([ $PHASE1_EXIT -eq 0 ] && echo '✓ PASS' || echo '⚠ WARNINGS')"
echo "  Phase 2 (Performance):  $([ $PHASE2_EXIT -eq 0 ] && echo '✓ PASS' || echo '⚠ WARNINGS')"
echo "  Phase 3 (Determinism):  $([ $PHASE3_EXIT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo ""
echo "Detailed logs:"
echo "  /tmp/deep_test_phase1.log"
echo "  /tmp/deep_test_phase2.log"
echo "  /tmp/deep_test_phase3.log"
echo ""

# Generate summary report
REPORT_FILE="/tmp/orchestrator_deep_test_report.txt"
cat > $REPORT_FILE <<EOF
ORCHESTRATOR DEEP TESTING REPORT
Generated: $(date)
Duration: ${ELAPSED_MIN}m ${ELAPSED_SEC}s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESULTS:

Phase 1: Functional Test Suite
  Status: $([ $PHASE1_EXIT -eq 0 ] && echo 'PASS' || echo 'WARNINGS')
  Log: /tmp/deep_test_phase1.log

Phase 2: Performance Benchmark (V1 vs V2)
  Status: $([ $PHASE2_EXIT -eq 0 ] && echo 'PASS' || echo 'WARNINGS')
  Log: /tmp/deep_test_phase2.log

Phase 3: Determinism Validation (V2)
  Status: $([ $PHASE3_EXIT -eq 0 ] && echo 'PASS' || echo 'FAIL')
  Log: /tmp/deep_test_phase3.log

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ARTIFACTS:

Planning artifacts:
$(ls -lh planning/ 2>/dev/null | tail -5 || echo "  (none)")

Iteration artifacts:
$(ls -lh artifacts/iterations/ 2>/dev/null | tail -3 || echo "  (none)")

Learning store:
$([ -f artifacts/learning/learning_store.jsonl ] && echo "  $(wc -l < artifacts/learning/learning_store.jsonl) entries" || echo "  (none)")

CoT traces:
$([ -d artifacts/cot_layer6 ] && echo "  $(find artifacts/cot_layer6 -type f | wc -l) files" || echo "  (none)")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDATIONS:

$(if [ $PHASE3_EXIT -ne 0 ]; then
  echo "  ✗ V2 Determinism FAILED"
  echo "    → Review state machine transitions in scripts/orchestrator/state_machine.py"
  echo "    → Check for non-deterministic operations (timestamps, random, etc.)"
  echo "    → Inspect diffs in /tmp/determinism_diff_*.txt"
fi)

$(if [ $PHASE1_EXIT -ne 0 ]; then
  echo "  ⚠ Functional tests had warnings"
  echo "    → Review /tmp/deep_test_phase1.log for details"
  echo "    → Check LLM provider configuration in config.yaml"
fi)

$(if [ $PHASE2_EXIT -ne 0 ]; then
  echo "  ⚠ Performance benchmark had warnings"
  echo "    → Review /tmp/deep_test_phase2.log for details"
fi)

$(if [ $PHASE1_EXIT -eq 0 ] && [ $PHASE2_EXIT -eq 0 ] && [ $PHASE3_EXIT -eq 0 ]; then
  echo "  ✓ All tests PASSED"
  echo "    → Orchestrator is production-ready"
  echo "    → Consider running stress tests with higher story counts"
fi)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS:

1. Review this report and phase logs
2. Run unit tests: .venv/bin/pytest tests/test_orchestrator_v2_*.py -v
3. Check coverage: .venv/bin/pytest --cov=scripts/orchestrator --cov-report=html
4. Review config.yaml and adjust policies if needed
5. Run stress test with complex concepts (10+ stories)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

echo "Summary report saved to: $REPORT_FILE"
echo ""
cat $REPORT_FILE
echo ""

# Exit with appropriate code
if [ $PHASE3_EXIT -ne 0 ]; then
  exit 1  # Determinism is critical
elif [ $PHASE1_EXIT -ne 0 ] || [ $PHASE2_EXIT -ne 0 ]; then
  exit 2  # Warnings
else
  exit 0  # All good
fi
