#!/usr/bin/env bash
set -euo pipefail

# Phase 2A helper for future GPU sessions (Phase 2B).
# In 2A/local this script is documentation-as-code and optional.

ROLE="${ROLE:-ba}"
NUM_SAMPLES="${NUM_SAMPLES:-100}"
BATCH_SIZE="${BATCH_SIZE:-10}"
MODE="${MODE:-gpu}"

echo "[gpu_session] role=${ROLE} mode=${MODE} num_samples=${NUM_SAMPLES} batch_size=${BATCH_SIZE}"
echo "[gpu_session] Installing training profile dependencies..."
python -m pip install -r requirements-training.txt

echo "[gpu_session] Running synthetic pipeline"
PYTHONPATH=. ./.venv/bin/python -m training.scripts.run_synthetic_pipeline \
  --role "${ROLE}" \
  --mode "${MODE}" \
  --num-samples "${NUM_SAMPLES}" \
  --batch-size "${BATCH_SIZE}"

echo "[gpu_session] Validating generated dataset"
PYTHONPATH=. ./.venv/bin/python -m training.scripts.validate_datasets --role "${ROLE}"

echo "[gpu_session] Done"
