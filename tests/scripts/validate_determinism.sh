#!/bin/bash
# Validate V2 Orchestrator Determinism
# Runs V2 orchestrator 3 times with same concept and verifies identical decision sequences

set -e
cd "$(dirname "$0")/../.."  # Go to repo root

CONCEPT="${1:-Simple calculator REST API with add and subtract}"
MAX_STEPS="${2:-10}"
NUM_RUNS=3

echo "=== V2 ORCHESTRATOR DETERMINISM VALIDATION ==="
echo "Concept: $CONCEPT"
echo "Max steps: $MAX_STEPS"
echo "Number of runs: $NUM_RUNS"
echo "Timestamp: $(date)"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# Run V2 orchestrator N times
# ============================================================================
for i in $(seq 1 $NUM_RUNS); do
  echo "[$i/$NUM_RUNS] Running V2 orchestrator (run $i)..."

  # Clean state
  make clean FLUSH=1 > /dev/null 2>&1 || true

  # Run V2
  PYTHONPATH=. timeout 600 .venv/bin/python scripts/run_orchestrator_agent.py \
    --concept "$CONCEPT" \
    --max-steps $MAX_STEPS \
    --use-v2 > /tmp/determinism_run${i}.log 2>&1 || {
    echo -e "${RED}✗ Run $i failed or timed out${NC}"
    cat /tmp/determinism_run${i}.log | tail -20
    exit 1
  }

  # Save summary
  if [ -f artifacts/iterations/latest_orchestrator_summary.json ]; then
    cp artifacts/iterations/latest_orchestrator_summary.json /tmp/determinism_run${i}_summary.json
  else
    echo -e "${RED}✗ Run $i did not generate summary${NC}"
    exit 1
  fi

  # Save stories state
  if [ -f planning/stories.yaml ]; then
    cp planning/stories.yaml /tmp/determinism_run${i}_stories.yaml
  fi

  echo -e "${GREEN}  ✓ Run $i completed${NC}"
done

echo ""
echo "=== COMPARING RUNS ==="

# ============================================================================
# Compare summaries (decision sequences)
# ============================================================================
echo ""
echo "[1/3] Comparing orchestrator decision sequences..."

# Extract just the "steps" array from each summary (ignore timestamps)
for i in $(seq 1 $NUM_RUNS); do
  jq '.steps | map({step, actions: .actions | map({tool, arguments})})' \
    /tmp/determinism_run${i}_summary.json > /tmp/determinism_run${i}_steps.json
done

# Compare run1 vs run2
if diff -u /tmp/determinism_run1_steps.json /tmp/determinism_run2_steps.json > /tmp/determinism_diff_12.txt; then
  echo -e "${GREEN}✓ Run 1 and Run 2: Identical decision sequences${NC}"
  DIFF_12_OK=1
else
  echo -e "${RED}✗ Run 1 and Run 2: DIFFER${NC}"
  echo "  See diff: /tmp/determinism_diff_12.txt"
  head -20 /tmp/determinism_diff_12.txt
  DIFF_12_OK=0
fi

# Compare run2 vs run3
if diff -u /tmp/determinism_run2_steps.json /tmp/determinism_run3_steps.json > /tmp/determinism_diff_23.txt; then
  echo -e "${GREEN}✓ Run 2 and Run 3: Identical decision sequences${NC}"
  DIFF_23_OK=1
else
  echo -e "${RED}✗ Run 2 and Run 3: DIFFER${NC}"
  echo "  See diff: /tmp/determinism_diff_23.txt"
  head -20 /tmp/determinism_diff_23.txt
  DIFF_23_OK=0
fi

# ============================================================================
# Compare stories state
# ============================================================================
echo ""
echo "[2/3] Comparing stories state..."

# Normalize stories (remove timestamps, sort by id)
for i in $(seq 1 $NUM_RUNS); do
  if [ -f /tmp/determinism_run${i}_stories.yaml ]; then
    # Convert YAML to JSON, sort by id, extract relevant fields
    PYTHONPATH=. .venv/bin/python -c "
import sys, yaml, json
stories = yaml.safe_load(open('/tmp/determinism_run${i}_stories.yaml'))
if isinstance(stories, dict) and 'stories' in stories:
    stories = stories['stories']
if not isinstance(stories, list):
    sys.exit(0)
normalized = []
for s in stories:
    normalized.append({
        'id': s.get('id'),
        'title': s.get('title'),
        'status': s.get('status'),
        'depends_on': sorted(s.get('depends_on', [])),
        'implements': sorted(s.get('implements', []))
    })
normalized.sort(key=lambda x: x.get('id', ''))
print(json.dumps(normalized, indent=2, sort_keys=True))
" > /tmp/determinism_run${i}_stories_normalized.json 2>/dev/null || {
      echo "  (Could not normalize stories for run $i)"
    }
  fi
done

# Compare normalized stories
if [ -f /tmp/determinism_run1_stories_normalized.json ] && \
   [ -f /tmp/determinism_run2_stories_normalized.json ] && \
   [ -f /tmp/determinism_run3_stories_normalized.json ]; then

  if diff -u /tmp/determinism_run1_stories_normalized.json \
           /tmp/determinism_run2_stories_normalized.json > /tmp/determinism_stories_diff.txt && \
     diff -u /tmp/determinism_run2_stories_normalized.json \
           /tmp/determinism_run3_stories_normalized.json >> /tmp/determinism_stories_diff.txt; then
    echo -e "${GREEN}✓ Stories state: Identical across all runs${NC}"
    STORIES_OK=1
  else
    echo -e "${RED}✗ Stories state: DIFFER${NC}"
    echo "  See diff: /tmp/determinism_stories_diff.txt"
    head -30 /tmp/determinism_stories_diff.txt
    STORIES_OK=0
  fi
else
  echo -e "${YELLOW}⚠ Could not compare stories (files missing)${NC}"
  STORIES_OK=0
fi

# ============================================================================
# Compare final phase
# ============================================================================
echo ""
echo "[3/3] Comparing final pipeline phase..."

for i in $(seq 1 $NUM_RUNS); do
  PHASE=$(jq -r '.final_state // "unknown"' /tmp/determinism_run${i}_summary.json 2>/dev/null || echo "unknown")
  echo "  Run $i: $PHASE"
  eval "PHASE_$i=$PHASE"
done

if [ "$PHASE_1" == "$PHASE_2" ] && [ "$PHASE_2" == "$PHASE_3" ]; then
  echo -e "${GREEN}✓ Final phase: Consistent${NC}"
  PHASE_OK=1
else
  echo -e "${RED}✗ Final phase: INCONSISTENT${NC}"
  PHASE_OK=0
fi

# ============================================================================
# VERDICT
# ============================================================================
echo ""
echo "=== DETERMINISM VALIDATION RESULTS ==="
echo ""

if [ $DIFF_12_OK -eq 1 ] && [ $DIFF_23_OK -eq 1 ] && \
   [ $STORIES_OK -eq 1 ] && [ $PHASE_OK -eq 1 ]; then
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}  ✓ DETERMINISM VALIDATED${NC}"
  echo -e "${GREEN}  All $NUM_RUNS runs produced identical decision sequences${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  EXIT_CODE=0
else
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${RED}  ✗ DETERMINISM VALIDATION FAILED${NC}"
  echo -e "${RED}  Runs produced different results${NC}"
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "Results:"
  echo "  Decision sequences: $([ $DIFF_12_OK -eq 1 ] && [ $DIFF_23_OK -eq 1 ] && echo '✓ OK' || echo '✗ DIFFER')"
  echo "  Stories state:      $([ $STORIES_OK -eq 1 ] && echo '✓ OK' || echo '✗ DIFFER')"
  echo "  Final phase:        $([ $PHASE_OK -eq 1 ] && echo '✓ OK' || echo '✗ DIFFER')"
  echo ""
  echo "Diff files:"
  echo "  /tmp/determinism_diff_*.txt"
  echo "  /tmp/determinism_stories_diff.txt"
  EXIT_CODE=1
fi

echo ""
echo "Run logs:"
for i in $(seq 1 $NUM_RUNS); do
  echo "  Run $i: /tmp/determinism_run${i}.log"
done

echo ""
echo "Summary artifacts:"
for i in $(seq 1 $NUM_RUNS); do
  echo "  Run $i: /tmp/determinism_run${i}_summary.json"
done

exit $EXIT_CODE
