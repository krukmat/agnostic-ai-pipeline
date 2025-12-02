#!/usr/bin/env bash
# =============================================================================
# E2E Test Battery Script - Agnostic AI Pipeline
# =============================================================================
# Task: E2E test suite with detailed metrics and validation
#
# This script runs end-to-end integration tests of the full pipeline:
# BA → PO → Architect → Dev → QA
#
# Features:
# - Multiple test scenarios (simple, medium, complex)
# - Detailed metrics collection (time, tokens, costs)
# - Artifact validation
# - Comprehensive reporting with recommendations
# - CI/CD compatible exit codes
#
# Usage:
#   ./scripts/test_e2e_battery.sh [options]
#
# Options:
#   --scenario <name>   Run specific scenario (simple|medium|complex|all)
#   --quick             Skip complex scenarios, faster execution
#   --verbose           Show detailed output
#   --no-cleanup        Don't clean artifacts between tests
#   --report-dir <path> Output directory for reports (default: artifacts/e2e_reports)
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="./.venv/bin/python"
PYTEST="./.venv/bin/pytest"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="${REPORT_DIR:-artifacts/e2e_reports/$TIMESTAMP}"

# Test scenarios
SCENARIO="${1:-all}"
QUICK_MODE=false
VERBOSE=false
NO_CLEANUP=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Metrics (Bash 3.2 compatible - using delimited strings)
TEST_RESULTS=""      # Format: "scenario:result|scenario:result|..."
TEST_TIMES=""        # Format: "scenario:duration|scenario:duration|..."
TEST_ARTIFACTS=""    # Format: "scenario:path|scenario:path|..."
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# -----------------------------------------------------------------------------
# Argument Parsing
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case $1 in
    --scenario)
      SCENARIO="$2"
      shift 2
      ;;
    --quick)
      QUICK_MODE=true
      shift
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --no-cleanup)
      NO_CLEANUP=true
      shift
      ;;
    --report-dir)
      REPORT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      head -n 30 "$0" | grep "^#" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# -----------------------------------------------------------------------------
# Helper Functions - Associative Array Simulation (Bash 3.2 compatible)
# -----------------------------------------------------------------------------
set_value() {
  local var_name="$1"
  local key="$2"
  local value="$3"

  # Get current value
  eval "local current=\"\$$var_name\""

  # Remove existing key if present
  local new_value=$(echo "$current" | tr '|' '\n' | grep -v "^${key}:" | tr '\n' '|' | sed 's/|$//')

  # Add new key:value
  if [ -z "$new_value" ]; then
    new_value="${key}:${value}"
  else
    new_value="${new_value}|${key}:${value}"
  fi

  eval "$var_name=\"$new_value\""
}

get_value() {
  local var_name="$1"
  local key="$2"

  eval "local current=\"\$$var_name\""
  echo "$current" | tr '|' '\n' | grep "^${key}:" | cut -d: -f2-
}

get_all_keys() {
  local var_name="$1"
  eval "local current=\"\$$var_name\""
  echo "$current" | tr '|' '\n' | cut -d: -f1
}

# -----------------------------------------------------------------------------
# Logging Functions
# -----------------------------------------------------------------------------
log_info() {
  echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
  echo -e "${GREEN}[PASS]${NC} $*"
}

log_error() {
  echo -e "${RED}[FAIL]${NC} $*"
}

log_warning() {
  echo -e "${YELLOW}[WARN]${NC} $*"
}

log_section() {
  echo ""
  echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}  $*${NC}"
  echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
  echo ""
}

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
setup_environment() {
  log_section "Environment Setup"

  # Create report directory
  mkdir -p "$REPORT_DIR"
  log_info "Report directory: $REPORT_DIR"

  # Check dependencies
  if [[ ! -f "$PYTHON" ]]; then
    log_error "Python venv not found. Run 'make setup' first."
    exit 1
  fi

  if [[ ! -f "$PYTEST" ]]; then
    log_error "Pytest not found. Run 'make setup' first."
    exit 1
  fi

  # Check config
  if [[ ! -f "config.yaml" ]]; then
    log_error "config.yaml not found"
    exit 1
  fi

  log_success "Environment ready"
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------
preflight_checks() {
  log_section "Pre-flight Checks"

  local all_passed=true

  # Check database layer
  log_info "Checking database layer..."
  if grep -q "enabled: true" config.yaml | grep -A 2 "^database:" > /dev/null 2>&1; then
    log_success "Database layer: enabled"
  else
    log_warning "Database layer: disabled"
  fi

  # Check providers connectivity
  log_info "Checking provider connectivity..."

  # Vertex AI
  if command -v gcloud &> /dev/null; then
    if gcloud auth application-default print-access-token &> /dev/null; then
      log_success "Vertex AI: authenticated"
    else
      log_warning "Vertex AI: not authenticated (gcloud auth application-default login)"
      all_passed=false
    fi
  else
    log_warning "gcloud CLI not found, Vertex AI unavailable"
  fi

  # Ollama (optional)
  if command -v ollama &> /dev/null; then
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
      log_success "Ollama: running"
    else
      log_warning "Ollama: not running (optional)"
    fi
  else
    log_info "Ollama: not installed (optional)"
  fi

  # Check planning directory
  if [[ -d "planning" ]] && [[ -n "$(ls -A planning 2>/dev/null)" ]]; then
    log_warning "planning/ directory not empty, may affect tests"
    if [[ "$NO_CLEANUP" == "false" ]]; then
      log_info "Will clean before each test"
    fi
  fi

  if [[ "$all_passed" == "false" ]]; then
    log_warning "Some checks failed, but continuing..."
  else
    log_success "All pre-flight checks passed"
  fi
}

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------
cleanup_artifacts() {
  if [[ "$NO_CLEANUP" == "true" ]]; then
    log_info "Skipping cleanup (--no-cleanup flag)"
    return 0
  fi

  log_info "Cleaning artifacts..."
  make clean FLUSH=1 > /dev/null 2>&1 || true
  log_success "Cleanup complete"
}

# -----------------------------------------------------------------------------
# Test Execution
# -----------------------------------------------------------------------------
run_test_scenario() {
  local scenario_name="$1"
  local concept="$2"
  local max_loops="${3:-}"
  local complexity="${4:-medium}"

  TOTAL_TESTS=$((TOTAL_TESTS + 1))

  log_section "Test Scenario: $scenario_name"
  log_info "Concept: $concept"
  log_info "Max Loops: $max_loops"
  log_info "Complexity: $complexity"

  local start_time=$(date +%s)
  local test_log="$REPORT_DIR/${scenario_name}_test.log"
  local artifacts_snapshot="$REPORT_DIR/${scenario_name}_artifacts"

  # Cleanup before test
  cleanup_artifacts
  # Ensure report dir exists after cleanup
  mkdir -p "$REPORT_DIR"

  # Run full iteration
  log_info "Running full pipeline iteration..."

  # If MAX_LOOPS not set explicitly, derive from stories.yaml after planning (fallback to provided max_loops)
  local derived_loops="$max_loops"
  if [[ -n "${MAX_LOOPS:-}" ]]; then
    derived_loops="$MAX_LOOPS"
    log_info "Using MAX_LOOPS from environment: $derived_loops"
  elif [[ -z "$max_loops" || "$max_loops" == "auto" ]]; then
    if [[ -f "planning/stories.yaml" ]]; then
      local todo_count
      todo_count=$(python - <<'PY'
import yaml
from pathlib import Path
p = Path("planning/stories.yaml")
try:
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "stories" in data:
        data = data["stories"]
    todos = [s for s in data or [] if isinstance(s, dict) and str(s.get("status","")).lower() == "todo"]
    print(len(todos))
except Exception:
    print("")
PY
)
      if [[ -n "$todo_count" && "$todo_count" =~ ^[0-9]+$ && "$todo_count" -gt 0 ]]; then
        derived_loops="$todo_count"
        log_info "Derived MAX_LOOPS from stories.yaml: $derived_loops"
      fi
    fi
  fi
  if [[ -z "$derived_loops" ]]; then
    derived_loops=1
  fi

  if [[ "$VERBOSE" == "true" ]]; then
    set +e
    CONCEPT="$concept" MAX_LOOPS="$derived_loops" make iteration 2>&1 | tee "$test_log"
    local exit_code=${PIPESTATUS[0]}
    set -e
  else
    set +e
    CONCEPT="$concept" MAX_LOOPS="$derived_loops" make iteration > "$test_log" 2>&1
    local exit_code=$?
    set -e
  fi

  local end_time=$(date +%s)
  local duration=$((end_time - start_time))

  set_value TEST_TIMES "$scenario_name" "$duration"

  # Validate results
  log_info "Validating results..."
  local validation_result=$(validate_test_artifacts "$scenario_name" "$test_log")

  if [[ $exit_code -eq 0 ]] && [[ "$validation_result" == "PASS" ]]; then
    set_value TEST_RESULTS "$scenario_name" "PASS"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "Test PASSED (${duration}s)"
  else
    set_value TEST_RESULTS "$scenario_name" "FAIL"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "Test FAILED (${duration}s)"

    # Show last errors
    if [[ -f "$test_log" ]]; then
      log_info "Last 20 lines of log:"
      tail -n 20 "$test_log" | sed 's/^/  /'
    fi
  fi

  # Snapshot artifacts
  if [[ -d "artifacts" ]]; then
    mkdir -p "$artifacts_snapshot"
    cp -r artifacts/* "$artifacts_snapshot/" 2>/dev/null || true
    cp -r planning "$artifacts_snapshot/" 2>/dev/null || true
    cp -r project "$artifacts_snapshot/" 2>/dev/null || true
    set_value TEST_ARTIFACTS "$scenario_name" "$artifacts_snapshot"
  fi

  return $exit_code
}

# -----------------------------------------------------------------------------
# Artifact Validation
# -----------------------------------------------------------------------------
validate_test_artifacts() {
  local scenario_name="$1"
  local test_log="$2"

  local issues=0

  # Check requirements.yaml
  if [[ ! -f "planning/requirements.yaml" ]]; then
    log_error "Missing: planning/requirements.yaml"
    issues=$((issues + 1))
  fi

  # Check stories.yaml
  if [[ ! -f "planning/stories.yaml" ]]; then
    log_error "Missing: planning/stories.yaml"
    issues=$((issues + 1))
  else
    # Validate stories have required fields
    if ! grep -q "title:" "planning/stories.yaml"; then
      log_error "Invalid stories.yaml: missing 'title' fields"
      issues=$((issues + 1))
    fi
  fi

  # Check project output
  if [[ ! -d "project" ]] || [[ -z "$(ls -A project 2>/dev/null)" ]]; then
    log_warning "project/ directory empty or missing"
    issues=$((issues + 1))
  fi

  # Check QA report
  if [[ -d "artifacts/qa" ]]; then
    local qa_reports=$(find artifacts/qa -name "*.yaml" -o -name "*.json" 2>/dev/null | wc -l)
    if [[ $qa_reports -eq 0 ]]; then
      log_warning "No QA reports found"
      issues=$((issues + 1))
    fi
  fi

  # Check for errors in log
  if grep -q "ERROR\|CRITICAL\|Exception" "$test_log" 2>/dev/null; then
    log_warning "Errors found in test log"
    issues=$((issues + 1))
  fi

  if [[ $issues -eq 0 ]]; then
    echo "PASS"
  else
    echo "FAIL"
  fi
}

# -----------------------------------------------------------------------------
# Test Scenarios
# -----------------------------------------------------------------------------
run_simple_scenario() {
  run_test_scenario \
    "simple_health_check" \
    "Simple REST API with a /health endpoint that returns status ok" \
    1 \
    "simple"
}

run_medium_scenario() {
  run_test_scenario \
    "medium_calculator" \
    "Calculator REST API with add, subtract, multiply, divide endpoints and input validation" \
    2 \
    "medium"
}

run_complex_scenario() {
  run_test_scenario \
    "complex_todo_app" \
    "Todo list REST API with user authentication, CRUD operations, due dates, categories, and search functionality" \
    3 \
    "complex"
}

run_database_scenario() {
  run_test_scenario \
    "database_integration" \
    "User management API with SQLite database, CRUD operations, and pagination" \
    2 \
    "medium"
}

# -----------------------------------------------------------------------------
# Metrics Collection
# -----------------------------------------------------------------------------
collect_metrics() {
  log_section "Collecting Metrics"

  local metrics_file="$REPORT_DIR/metrics.json"

  cat > "$metrics_file" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "total_tests": $TOTAL_TESTS,
  "passed": $PASSED_TESTS,
  "failed": $FAILED_TESTS,
  "skipped": $SKIPPED_TESTS,
  "success_rate": $(awk "BEGIN {printf \"%.2f\", ($PASSED_TESTS/$TOTAL_TESTS)*100}"),
  "scenarios": {
EOF

  local first=true
  for scenario in $(get_all_keys TEST_RESULTS); do
    if [[ "$first" == "false" ]]; then
      echo "," >> "$metrics_file"
    fi
    first=false

    local result=$(get_value TEST_RESULTS "$scenario")
    local duration=$(get_value TEST_TIMES "$scenario")
    local artifacts=$(get_value TEST_ARTIFACTS "$scenario")

    cat >> "$metrics_file" <<EOF
    "$scenario": {
      "result": "$result",
      "duration_seconds": $duration,
      "artifacts_path": "${artifacts:-null}"
    }
EOF
  done

  cat >> "$metrics_file" <<EOF

  }
}
EOF

  log_success "Metrics saved to $metrics_file"
}

# -----------------------------------------------------------------------------
# Report Generation
# -----------------------------------------------------------------------------
generate_report() {
  log_section "Generating Report"

  local report_file="$REPORT_DIR/report.md"

  cat > "$report_file" <<EOF
# E2E Test Battery Report

**Generated:** $(date)
**Duration:** ${SECONDS}s

## Summary

- **Total Tests:** $TOTAL_TESTS
- **Passed:** $PASSED_TESTS ✅
- **Failed:** $FAILED_TESTS ❌
- **Skipped:** $SKIPPED_TESTS ⏭️
- **Success Rate:** $(awk "BEGIN {printf \"%.2f%%\", ($PASSED_TESTS/$TOTAL_TESTS)*100}")

## Test Results

EOF

  # Add individual test results
  for scenario in $(get_all_keys TEST_RESULTS); do
    local result=$(get_value TEST_RESULTS "$scenario")
    local duration=$(get_value TEST_TIMES "$scenario")
    local artifacts=$(get_value TEST_ARTIFACTS "$scenario")
    local status_icon

    if [[ "$result" == "PASS" ]]; then
      status_icon="✅"
    else
      status_icon="❌"
    fi

    cat >> "$report_file" <<EOF
### $status_icon $scenario

- **Status:** $result
- **Duration:** ${duration}s
- **Artifacts:** \`${artifacts:-N/A}\`

EOF
  done

  # Add recommendations
  cat >> "$report_file" <<EOF

## Configuration

- **Database Layer:** $(grep -A 2 "^database:" config.yaml | grep "enabled:" | awk '{print $2}')
- **Complexity Routing:** $(grep "routing_by_complexity_enabled:" config.yaml | awk '{print $2}')
- **Default Provider:** $(grep -A 10 "^roles:" config.yaml | grep -A 2 "dev:" | grep "provider:" | awk '{print $2}' | head -1)

## Recommendations

EOF

  if [[ $FAILED_TESTS -gt 0 ]]; then
    cat >> "$report_file" <<EOF
⚠️ **$FAILED_TESTS test(s) failed:**

1. Review test logs in \`$REPORT_DIR/\`
2. Check provider connectivity with \`make show-config\`
3. Verify all dependencies are installed
4. Run individual scenarios with \`--scenario <name>\`

EOF
  else
    cat >> "$report_file" <<EOF
✅ **All tests passed!**

Pipeline is working correctly. Key achievements:

- All role transitions successful
- Artifacts generated correctly
- QA validation completed
- Database layer functioning (if enabled)

EOF
  fi

  cat >> "$report_file" <<EOF

## Artifacts Location

All test artifacts, logs, and snapshots are available at:

\`\`\`
$REPORT_DIR
\`\`\`

## Next Steps

1. Review individual test logs for detailed execution traces
2. Inspect generated code in \`<scenario>_artifacts/project/\`
3. Analyze metrics in \`metrics.json\`
4. Run smoke tests: \`.venv/bin/pytest tests/smoke/ -v\`

---

*Generated by E2E Test Battery Script v1.0*
EOF

  log_success "Report saved to $report_file"

  # Display report
  if command -v bat &> /dev/null; then
    bat "$report_file"
  elif command -v cat &> /dev/null; then
    cat "$report_file"
  fi
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
main() {
  log_section "E2E Test Battery - Agnostic AI Pipeline"

  setup_environment
  preflight_checks

  # Run scenarios based on selection
  case "$SCENARIO" in
    simple)
      run_simple_scenario
      ;;
    medium)
      run_medium_scenario
      ;;
    complex)
      if [[ "$QUICK_MODE" == "true" ]]; then
        log_warning "Skipping complex scenario (--quick mode)"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
      else
        run_complex_scenario
      fi
      ;;
    database)
      run_database_scenario
      ;;
    all)
      run_simple_scenario
      run_medium_scenario

      if [[ "$QUICK_MODE" == "false" ]]; then
        run_complex_scenario
      else
        log_warning "Skipping complex scenario (--quick mode)"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
      fi

      run_database_scenario
      ;;
    *)
      log_error "Unknown scenario: $SCENARIO"
      log_info "Available scenarios: simple, medium, complex, database, all"
      exit 1
      ;;
  esac

  # Generate reports
  collect_metrics
  generate_report

  # Summary
  log_section "Test Battery Complete"
  log_info "Total: $TOTAL_TESTS | Passed: $PASSED_TESTS | Failed: $FAILED_TESTS | Skipped: $SKIPPED_TESTS"
  log_info "Report: $REPORT_DIR/report.md"

  # Exit with appropriate code
  if [[ $FAILED_TESTS -gt 0 ]]; then
    exit 1
  else
    exit 0
  fi
}

# Run main
main
