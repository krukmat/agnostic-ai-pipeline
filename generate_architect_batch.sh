#!/bin/bash
# Batch generation of architect dataset with multiple seeds
# Target: ~50 total samples (from current 23)


echo "=== Architect Dataset Batch Generation Started at $(date) ==="
echo "Current samples: $(wc -l < dspy_baseline/data/production/architect_train.jsonl) train + $(wc -l < dspy_baseline/data/production/architect_val.jsonl) val"

# Run with different seeds to maximize BA dataset coverage
# Each seed shuffles the 25 BA samples differently
SEEDS=(1111 2222 3333 4444 5555)

for SEED in "${SEEDS[@]}"; do
  echo ""
  echo "=========================================="
  echo "SEED $SEED - Starting at $(date)"
  echo "=========================================="

  PYTHONPATH=. ./.venv/bin/python scripts/generate_architect_dataset.py \
    --ba-path dspy_baseline/data/production/ba_train_plus_extra.jsonl \
    --out-train dspy_baseline/data/production/architect_train.jsonl \
    --out-val dspy_baseline/data/production/architect_val.jsonl \
    --min-score 0.45 \
    --max-records 25 \
    --seed $SEED \
    --resume \
    2>&1 | tee -a architect_batch_generation.log

  CURRENT_TOTAL=$(($(wc -l < dspy_baseline/data/production/architect_train.jsonl) + $(wc -l < dspy_baseline/data/production/architect_val.jsonl)))

  echo "After seed $SEED: $CURRENT_TOTAL total samples"

  # Stop if we've reached 50+ samples
  if [ $CURRENT_TOTAL -ge 50 ]; then
    echo "✅ Target of 50 samples reached! Stopping batch."
    break
  fi

  # Brief pause between runs to avoid overwhelming the system
  sleep 10
done

FINAL_TRAIN=$(wc -l < dspy_baseline/data/production/architect_train.jsonl)
FINAL_VAL=$(wc -l < dspy_baseline/data/production/architect_val.jsonl)
FINAL_TOTAL=$((FINAL_TRAIN + FINAL_VAL))

echo ""
echo "=========================================="
echo "=== Batch Generation Complete at $(date) ==="
echo "Final: $FINAL_TRAIN train + $FINAL_VAL val = $FINAL_TOTAL total samples"
echo "=========================================="
