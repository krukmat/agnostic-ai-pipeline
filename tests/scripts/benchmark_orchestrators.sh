#!/bin/bash
# Benchmark V1 (LLM-based) vs V2 (Deterministic) Orchestrator
# Measures: execution time, LLM calls, throughput

set -e
cd "$(dirname "$0")/../.."  # Go to repo root

CONCEPT="${1:-User authentication REST API with JWT}"
MAX_STEPS="${2:-15}"

echo "=== ORCHESTRATOR BENCHMARK: V1 vs V2 ==="
echo "Concept: $CONCEPT"
echo "Max steps: $MAX_STEPS"
echo "Timestamp: $(date)"
echo ""

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# V1: LLM-Based Orchestrator
# ============================================================================
echo -e "${CYAN}[V1] Running LLM-based orchestrator...${NC}"
make clean FLUSH=1 > /dev/null 2>&1 || true

START_V1=$(date +%s)
CONCEPT="$CONCEPT" MAX_STEPS=$MAX_STEPS MAX_ACTIONS=3 \
  timeout 1200 make agentic-iteration > /tmp/bench_v1.log 2>&1 || {
  echo "V1 timed out or failed"
  V1_FAILED=1
}
END_V1=$(date +%s)
V1_TIME=$((END_V1 - START_V1))

# Count LLM calls from orchestrator (not roles)
V1_ORCHESTRATOR_LLM=$(grep -c "\[orchestrator\].*chat" /tmp/bench_v1.log 2>/dev/null || echo 0)
V1_TOTAL_LLM=$(grep -c "chat.*request" /tmp/bench_v1.log 2>/dev/null || echo "N/A")

# Count stories completed
V1_STORIES_DONE=0
if [ -f planning/stories.yaml ]; then
  V1_STORIES_DONE=$(grep -c 'status: done' planning/stories.yaml 2>/dev/null || echo 0)
fi

# Check artifacts
V1_ARTIFACTS=$(find artifacts/iterations -name "latest_orchestrator_summary.json" 2>/dev/null | wc -l)

echo -e "${GREEN}V1 Completed in ${V1_TIME}s${NC}"
echo "  Orchestrator LLM calls: $V1_ORCHESTRATOR_LLM"
echo "  Total LLM calls: $V1_TOTAL_LLM"
echo "  Stories completed: $V1_STORIES_DONE"
echo "  Artifacts: $V1_ARTIFACTS"
echo ""

# ============================================================================
# V2: Deterministic Orchestrator
# ============================================================================
echo -e "${CYAN}[V2] Running deterministic orchestrator...${NC}"
make clean FLUSH=1 > /dev/null 2>&1 || true

START_V2=$(date +%s)
PYTHONPATH=. timeout 1200 .venv/bin/python scripts/run_orchestrator_agent.py \
  --concept "$CONCEPT" \
  --max-steps $MAX_STEPS \
  --use-v2 > /tmp/bench_v2.log 2>&1 || {
  echo "V2 timed out or failed"
  V2_FAILED=1
}
END_V2=$(date +%s)
V2_TIME=$((END_V2 - START_V2))

# V2 should have 0 orchestrator LLM calls (only roles call LLM)
V2_ORCHESTRATOR_LLM=$(grep -c "\[v2_orchestrator\].*chat" /tmp/bench_v2.log 2>/dev/null || echo 0)
V2_TOTAL_LLM=$(grep -c "chat.*request" /tmp/bench_v2.log 2>/dev/null || echo "N/A")

# Count stories completed
V2_STORIES_DONE=0
if [ -f planning/stories.yaml ]; then
  V2_STORIES_DONE=$(grep -c 'status: done' planning/stories.yaml 2>/dev/null || echo 0)
fi

# Check artifacts
V2_ARTIFACTS=$(find artifacts/iterations -name "latest_orchestrator_summary.json" 2>/dev/null | wc -l)

echo -e "${GREEN}V2 Completed in ${V2_TIME}s${NC}"
echo "  Orchestrator LLM calls: $V2_ORCHESTRATOR_LLM"
echo "  Total LLM calls: $V2_TOTAL_LLM"
echo "  Stories completed: $V2_STORIES_DONE"
echo "  Artifacts: $V2_ARTIFACTS"
echo ""

# ============================================================================
# COMPARISON
# ============================================================================
echo "=== BENCHMARK RESULTS ==="
echo ""
printf "%-30s %10s %10s %10s\n" "Metric" "V1 (LLM)" "V2 (Det)" "Difference"
echo "--------------------------------------------------------------------"

# Time comparison
if [ $V2_TIME -gt 0 ]; then
  TIME_DIFF=$((V1_TIME - V2_TIME))
  TIME_PCT=$((TIME_DIFF * 100 / V2_TIME))
  printf "%-30s %10ss %10ss %10s%%\n" "Execution Time" "$V1_TIME" "$V2_TIME" "$TIME_PCT"
else
  printf "%-30s %10ss %10ss %10s\n" "Execution Time" "$V1_TIME" "$V2_TIME" "N/A"
fi

# LLM calls comparison
printf "%-30s %10s %10s %10s\n" "Orchestrator LLM Calls" "$V1_ORCHESTRATOR_LLM" "$V2_ORCHESTRATOR_LLM" "$(($V1_ORCHESTRATOR_LLM - $V2_ORCHESTRATOR_LLM))"

# Throughput (stories/min)
if [ $V1_TIME -gt 0 ] && [ $V1_STORIES_DONE -gt 0 ]; then
  V1_THROUGHPUT=$(echo "scale=2; $V1_STORIES_DONE * 60 / $V1_TIME" | bc)
else
  V1_THROUGHPUT="N/A"
fi

if [ $V2_TIME -gt 0 ] && [ $V2_STORIES_DONE -gt 0 ]; then
  V2_THROUGHPUT=$(echo "scale=2; $V2_STORIES_DONE * 60 / $V2_TIME" | bc)
else
  V2_THROUGHPUT="N/A"
fi

printf "%-30s %10s %10s %10s\n" "Throughput (stories/min)" "$V1_THROUGHPUT" "$V2_THROUGHPUT" "-"

# Stories completed
printf "%-30s %10s %10s %10s\n" "Stories Completed" "$V1_STORIES_DONE" "$V2_STORIES_DONE" "$(($V2_STORIES_DONE - $V1_STORIES_DONE))"

echo ""

# ============================================================================
# COST ESTIMATION (rough)
# ============================================================================
echo "=== COST ESTIMATION (Rough) ==="
echo ""

# Assume avg 500 tokens per orchestrator LLM call @ $0.003 per 1K tokens (GPT-4 pricing)
COST_PER_CALL=0.0015
V1_ORCHESTRATOR_COST=$(echo "scale=4; $V1_ORCHESTRATOR_LLM * $COST_PER_CALL" | bc)
V2_ORCHESTRATOR_COST=$(echo "scale=4; $V2_ORCHESTRATOR_LLM * $COST_PER_CALL" | bc)

echo "Orchestrator-only cost (estimated):"
echo "  V1: \$$V1_ORCHESTRATOR_COST ($V1_ORCHESTRATOR_LLM calls @ \$0.0015/call)"
echo "  V2: \$$V2_ORCHESTRATOR_COST ($V2_ORCHESTRATOR_LLM calls @ \$0.0015/call)"

if [ "$V1_ORCHESTRATOR_COST" != "0" ] && [ "$V2_ORCHESTRATOR_COST" != "0" ]; then
  COST_SAVINGS=$(echo "scale=2; ($V1_ORCHESTRATOR_COST - $V2_ORCHESTRATOR_COST) * 100 / $V1_ORCHESTRATOR_COST" | bc)
  echo "  Savings: ${COST_SAVINGS}% (orchestration only)"
fi

echo ""
echo -e "${YELLOW}Note: Role execution costs (BA, PO, Arch, Dev, QA) are identical for both.${NC}"
echo -e "${YELLOW}V2 saves cost ONLY on orchestration decisions.${NC}"

# ============================================================================
# WINNER
# ============================================================================
echo ""
if [ $V2_TIME -lt $V1_TIME ] && [ $V2_ORCHESTRATOR_LLM -le $V1_ORCHESTRATOR_LLM ]; then
  echo -e "${GREEN}✓ V2 (Deterministic) is FASTER and CHEAPER for orchestration${NC}"
elif [ $V1_STORIES_DONE -gt $V2_STORIES_DONE ]; then
  echo -e "${YELLOW}⚠ V1 (LLM-based) completed more stories (may be more flexible)${NC}"
else
  echo -e "${CYAN}→ Results are mixed, review logs for details${NC}"
fi

echo ""
echo "Logs:"
echo "  V1: /tmp/bench_v1.log"
echo "  V2: /tmp/bench_v2.log"
