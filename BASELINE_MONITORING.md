# Baseline Monitoring & Results

## Status: ⏳ RUNNING

**Started**: 2025-12-25 15:23 (UTC-3)
**Expected duration**: 20-30 hours
**Estimated completion**: 2025-12-26 11:23 to 19:23

---

## How to Monitor (Low-Overhead)

### Check if still running
```bash
ps aux | grep posttrain_collect_rollouts | grep -v grep
# If output appears, it's running
```

### View live progress (tail last 50 lines)
```bash
tail -50 post_training/logs/baseline/baseline_*.log
```

### Check rollouts accumulated so far
```bash
wc -l inference_results/posttrain_rollouts/2025-*/rollouts.jsonl
```

---

## What to Expect

### During execution:
- Logs in: `post_training/logs/baseline/baseline_*.log`
- Rollouts in: `inference_results/posttrain_rollouts/2025-*/rollouts.jsonl`
- Each concept ×8 attempts = output directory created

### When complete:
- `post_training/logs/baseline/baseline_results_*.json` will appear
- Contains: pass@1, pass@8, retry_efficiency

---

## Decision Tree (After Completion)

### Get results:
```bash
cat post_training/logs/baseline/baseline_results_*.json | jq .
```

### Interpret pass@8:

**IF pass@8 >= 0.20 (20%)**
```
✓ PROCEED to Phase 1-4
- Collect full dataset ✓ (done)
- Build preferences (Phase 2)
- Train LoRA (Phase 3, needs GPU)
- Evaluate (Phase 4)
```

**IF pass@8 < 0.20 (20%)**
```
⚠️ STOP
- Model base insufficient
- Upgrade: deepseek-coder-v2:lite → deepseek-coder-v2:full (or 33B+)
- Retry baseline with better model
```

**IF 0.20 <= pass@8 <= 0.30**
```
⚠️ MARGINAL
- Model has minimal capacity
- RL gains will be small (~5-10% improvement)
- Consider upgrade OR accept limited ROI
```

---

## Failure Patterns to Watch For

### If logs show repeated failures:

**"YAML invalid"**
- Prompts are vague
- Fix: Improve architecture prompts

**"tests_fail"**
- Developer generates code, but tests fail
- Fix: Relax test constraints or improve prompts

**"timeout"**
- Pipeline > 10min per attempt
- Fix: Increase timeout or reduce complexity concepts

**"compile_fail"**
- Code doesn't compile
- Fix: Add language-specific validation to prompts

---

## After Baseline - Quick Actions

### If pass@8 >= 20%:
```bash
# 1. Build preferences from rollouts
PYTHONPATH=./post_training:$PYTHONPATH python post_training/scripts/posttrain_build_preferences.py \
  --rollouts_dir inference_results/posttrain_rollouts/2025-* \
  --role developer

# 2. (When you have GPU access) Train LoRA
# See post_training/EXECUTION_GUIDE.md for details
```

### If pass@8 < 20%:
```bash
# 1. Check failure patterns
jq '.per_concept_success_attempt | map(select(.==null)) | length' post_training/logs/baseline/baseline_results_*.json

# 2. Decide: Upgrade model or redesign pipeline
# 3. Update config.yaml with new model
# 4. Re-run baseline with new model
```

---

## No Further Action Needed Until Results

You can:
- Close this terminal
- Check results later
- No token waste on monitoring

**I will NOT report until baseline completes.**
