#!/bin/bash
# Monitor architect dataset batch generation progress

echo "=== Architect Dataset Generation Monitor ==="
echo ""

# Check if process is still running
PID=$(ps aux | grep "[g]enerate_architect_batch.sh" | awk '{print $2}')
if [ -n "$PID" ]; then
  echo "✅ Batch generation process running (PID: $PID)"
else
  echo "⚠️  Batch generation process not found (may have finished or not started)"
fi

echo ""
echo "--- Current Dataset Status ---"
TRAIN_COUNT=$(wc -l < /Users/matiasleandrokruk/Documents/agnostic-ai-pipeline/dspy_baseline/data/production/architect_train.jsonl 2>/dev/null || echo 0)
VAL_COUNT=$(wc -l < /Users/matiasleandrokruk/Documents/agnostic-ai-pipeline/dspy_baseline/data/production/architect_val.jsonl 2>/dev/null || echo 0)
TOTAL=$((TRAIN_COUNT + VAL_COUNT))

echo "Train samples: $TRAIN_COUNT"
echo "Val samples:   $VAL_COUNT"
echo "Total:         $TOTAL / 50 target"

# Progress bar
PROGRESS=$((TOTAL * 100 / 50))
if [ $PROGRESS -gt 100 ]; then
  PROGRESS=100
fi
echo "Progress:      $PROGRESS%"

echo ""
echo "--- Latest Activity (last 10 lines of batch log) ---"
tail -10 architect_batch_generation.log 2>/dev/null || echo "No log output yet"

echo ""
echo "--- Full logs available at: ---"
echo "architect_batch_run.log (main batch log)"
echo "architect_batch_generation.log (detailed generation log)"
