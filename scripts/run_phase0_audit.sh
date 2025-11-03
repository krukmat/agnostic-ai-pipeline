#!/bin/bash
# scripts/run_phase0_audit.sh
# Ejecuta auditoría completa Python 3.11 migration
#
# Usage:
#   bash scripts/run_phase0_audit.sh

set -e

AUDIT_DIR="/tmp/py311_audit"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "🔍 Starting Phase 0 Audit..."
echo "Target: Python 3.9.10 → 3.11.9"
echo "Project: $PROJECT_ROOT"
echo ""

# Setup
mkdir -p "$AUDIT_DIR"
cd "$PROJECT_ROOT"

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command -v python &> /dev/null; then
    echo "❌ python not found"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "  Python version: $PYTHON_VERSION"

if [[ ! -f requirements.txt ]]; then
    echo "❌ requirements.txt not found"
    exit 1
fi
echo "  requirements.txt: ✅"

if [[ ! -d .venv ]]; then
    echo "⚠️  .venv not found (some tests will be skipped)"
fi
echo ""

# 1. Dependencies
echo "📦 [1/7] Analyzing dependencies..."
python scripts/check_py311_compat.py || echo "⚠️  Some dependencies have issues (non-fatal)"
echo ""

# 2. Code analysis - collections.abc
echo "🔍 [2/7] Analyzing code for deprecated collections imports..."
python scripts/check_collections_abc.py > "$AUDIT_DIR/collections_abc_issues.txt" || {
    echo "⚠️  Found deprecated imports (see report)"
}
echo ""

# 3. Code analysis - distutils
echo "🔍 [3/7] Checking for distutils usage..."
if grep -rn "import distutils" scripts/ a2a/ src/ tests/ 2>/dev/null > "$AUDIT_DIR/distutils_usage.txt"; then
    distutils_count=$(wc -l < "$AUDIT_DIR/distutils_usage.txt")
    echo "  ⚠️  Found $distutils_count distutils imports (deprecated)"
else
    echo "None" > "$AUDIT_DIR/distutils_usage.txt"
    echo "  ✅ No distutils usage"
fi
echo ""

# 4. Code analysis - asyncio
echo "🔍 [4/7] Checking for deprecated asyncio patterns..."
if grep -rn "@asyncio.coroutine" scripts/ a2a/ src/ 2>/dev/null > "$AUDIT_DIR/asyncio_decorator.txt"; then
    asyncio_count=$(wc -l < "$AUDIT_DIR/asyncio_decorator.txt")
    echo "  ⚠️  Found $asyncio_count asyncio.coroutine decorators (removed in 3.11)"
else
    echo "None" > "$AUDIT_DIR/asyncio_decorator.txt"
    echo "  ✅ No deprecated asyncio patterns"
fi
echo ""

# 5. Tests baseline
echo "🧪 [5/7] Running test baseline..."
if [[ -d .venv && -f .venv/bin/pytest ]]; then
    source .venv/bin/activate
    .venv/bin/pytest tests/ -v --tb=short --maxfail=5 > "$AUDIT_DIR/py39_test_results.txt" 2>&1 || true
    TEST_EXIT=$?
    echo $TEST_EXIT > "$AUDIT_DIR/py39_test_exitcode.txt"

    # Extract summary
    grep -E "passed|failed|error" "$AUDIT_DIR/py39_test_results.txt" | tail -1 > "$AUDIT_DIR/py39_test_summary.txt" || echo "No summary" > "$AUDIT_DIR/py39_test_summary.txt"

    echo "  Test summary: $(cat "$AUDIT_DIR/py39_test_summary.txt")"
else
    echo "  ⚠️  Skipped (no .venv/bin/pytest)"
    echo "No tests run" > "$AUDIT_DIR/py39_test_summary.txt"
fi
echo ""

# 6. Configuration files
echo "⚙️  [6/7] Scanning configuration files..."
find . -name ".python-version" -o -name "Dockerfile" -o -name "*.yml" -o -name "*.yaml" 2>/dev/null | \
    grep -v ".venv" | \
    grep -v "node_modules" | \
    sort > "$AUDIT_DIR/runtime_files.txt" || echo "" > "$AUDIT_DIR/runtime_files.txt"

runtime_count=$(grep -c . "$AUDIT_DIR/runtime_files.txt" 2>/dev/null || echo 0)
echo "  Found $runtime_count configuration files"
echo ""

# 7. Generate report
echo "📄 [7/7] Generating audit report..."
python scripts/generate_phase0_report.py
REPORT_EXIT=$?
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Phase 0 Audit Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📄 Reports generated:"
echo "  - Main report:  docs/python310_migration_audit.md"
echo "  - Raw data:     $AUDIT_DIR"
echo ""
echo "📁 Audit files:"
ls -lh "$AUDIT_DIR" | tail -n +2 | awk '{print "  - " $9 " (" $5 ")"}'
echo ""

if [[ $REPORT_EXIT -eq 0 ]]; then
    echo "✅ Decision: GO (proceed to Phase 1)"
    echo ""
    echo "Next steps:"
    echo "  1. Review: cat docs/python310_migration_audit.md"
    echo "  2. Fix any warnings (if needed)"
    echo "  3. Execute: # Start Phase 1 setup"
else
    echo "⛔ Decision: NO-GO (blockers found)"
    echo ""
    echo "Next steps:"
    echo "  1. Review blockers: cat docs/python310_migration_audit.md"
    echo "  2. Resolve issues"
    echo "  3. Re-run this audit"
fi

exit $REPORT_EXIT
