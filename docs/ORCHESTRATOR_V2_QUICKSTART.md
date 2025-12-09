# Orchestrator V2 - Quick Start Guide

## TL;DR

**Orchestrator V2** is a deterministic rule-based orchestration system that replaces LLM-based decisions with 90%+ rule-based autonomy.

### Run V2 (opt-in)

```bash
# Use V2 instead of default V1
python scripts/run_orchestrator_agent.py \
  --concept "My feature description" \
  --use-v2 \
  --max-steps 20
```

### Run Tests

```bash
# All V2 tests (41 passing)
.venv/bin/pytest tests/test_orchestrator_v2* -v

# With coverage report
.venv/bin/pytest tests/test_orchestrator_v2* \
  --cov=scripts/orchestrator \
  --cov-report=term-missing
```

---

## What's New in V2

### 1. Deterministic State Machine

Replaces LLM orchestration with 7-phase state machine:
```
INIT → REQUIREMENTS → PLANNING → DEVELOPMENT → INTEGRATION → DONE
```

Each phase has explicit transition rules.

### 2. Story Dependency Graph (DAG)

Stories can depend on other stories:
```yaml
- id: S1
  title: "Setup database schema"
  depends_on: []

- id: S2
  title: "Implement REST API"
  depends_on: [S1]  # Waits for S1 to complete

- id: S3
  title: "Write tests"
  depends_on: [S2]  # Waits for S2
```

**Automatic blocking**: If S1 fails, S2 and S3 are automatically blocked.

### 3. YAML-Driven Policies

Configure retry, escalation, and resource policies in `config.yaml`:

```yaml
pipeline:
  retry_policies:
    dev:
      max_attempts: 3
      backoff: exponential  # 60s → 120s → 240s

  escalation_policies:
    - condition: "dev_attempts >= 3 AND same_error_pattern"
      action: "architect_refine"
      reason: "Repeated failures suggest architectural issue"

  resource_policies:
    max_parallel_stories: 3
    dev_timeout: 600
```

### 4. Rule-Based Planning

No LLM calls for orchestration decisions. Pure rules:
- Is story ready? (dependencies satisfied)
- Should we retry? (max attempts exceeded)
- Should we escalate? (condition met)

### 5. Parallel Execution

Independent stories run in parallel (grouped by epic):
```
S1 (epic: auth)  \
S2 (epic: api)    } Run in parallel (max 3)
S3 (epic: db)    /
```

---

## Architecture Overview

```
V2 Runtime Loop
│
├─ State Machine (current phase, story states)
│  └─ Get phase, ready stories, blocked stories
│
├─ Story DAG (dependency graph)
│  └─ Topological sort, parallel batching
│
├─ Policy Engine (retry, escalation, resources)
│  └─ Should retry? Should escalate? Resource limits?
│
├─ Rule-Based Planner (deterministic decisions)
│  └─ Plan next actions (no LLM)
│
└─ Action Executor (async dispatch)
   └─ Run role handlers (BA, PO, Architect, Dev, QA)
```

---

## Configuration

### Enable V2 (optional)

In `config.yaml`:
```yaml
pipeline:
  use_v2_orchestrator: false  # Set to true to default to V2
  v2_max_steps: 20
```

Or use CLI flag:
```bash
python scripts/run_orchestrator_agent.py --concept "..." --use-v2
```

### Customize Policies

Modify retry/escalation/resource policies in `config.yaml`:

```yaml
pipeline:
  retry_policies:
    architect:
      max_attempts: 2
      backoff: linear  # 60s → 120s

  escalation_policies:
    - condition: "qa_coverage < 0.8 AND tests_failed > 0"
      action: "architect_review_tests"
      reason: "Low test coverage with failures"

  resource_policies:
    max_parallel_stories: 5  # Increase parallelism
    dev_timeout: 1200  # Longer timeout for complex stories
```

---

## How It Works

### Phase 1: INIT → REQUIREMENTS
- BA generates requirements.yaml
- Planner transitions to next phase

### Phase 2: REQUIREMENTS → PLANNING
- PO validates requirements
- Architect generates stories.yaml with dependencies
- Planner loads stories into DAG

### Phase 3: PLANNING → DEVELOPMENT
- Planner gets ready stories (no blocking dependencies)
- Selects N stories for parallel execution
- Dispatches RUN_DEV_STORY actions

### Phase 4: DEVELOPMENT → INTEGRATION
- All stories done or blocked
- Planner transitions to INTEGRATION
- Dispatches RUN_QA_FULL

### Phase 5: INTEGRATION → DONE
- QA complete
- Mark as DONE (or FAILED if blocker)

---

## Example: Story with Dependencies

```yaml
stories:
  - id: S1
    title: Create database schema
    depends_on: []

  - id: S2
    title: Implement user API endpoint
    depends_on: [S1]

  - id: S3
    title: Implement auth middleware
    depends_on: [S2]

  - id: S4
    title: Write integration tests
    depends_on: [S2, S3]
```

**Execution order**:
1. S1 runs (no deps)
2. After S1 done → S2 runs
3. After S2 done → S3 runs
4. After S2 and S3 done → S4 runs

**If S1 fails**:
- S2, S3, S4 are all blocked
- Pipeline terminates (blocker)

---

## Debugging

### Check V2 Logs

```bash
# Run with verbose logging
python scripts/run_orchestrator_agent.py \
  --concept "..." --use-v2 --max-steps 5 2>&1 | grep "\[v2_orchestrator\]"
```

### View Summary

```bash
# Check what actions were taken
cat artifacts/iterations/latest_orchestrator_summary.json | jq '.steps'
```

### Run Tests with Coverage

```bash
.venv/bin/pytest tests/test_orchestrator_v2_e2e.py -v -s \
  --cov=scripts/orchestrator \
  --cov-report=html
```

---

## Key Differences: V1 vs V2

| Aspect | V1 (LLM-based) | V2 (Deterministic) |
|--------|---|---|
| **Orchestration** | LLM makes decisions | Rules engine |
| **Cost** | High (many LLM calls) | Low (minimal LLM) |
| **Reproducibility** | Non-deterministic | Fully deterministic |
| **Latency** | Higher | Lower |
| **Dependencies** | Manual management | Automatic DAG scheduling |
| **Retry logic** | LLM decides | Policy-driven |
| **Resource limits** | None | Configurable |
| **Auditability** | Hard to trace | All decisions logged |

---

## Troubleshooting

### V2 Not Running
Check that `--use-v2` flag is set:
```bash
python scripts/run_orchestrator_agent.py --concept "..." --use-v2
```

### Story Stuck in Blocked
Check dependencies in `planning/stories.yaml`:
```bash
# Find blocked story
grep "id: S2" planning/stories.yaml
# Check its depends_on
grep -A 2 "id: S2" planning/stories.yaml | grep depends_on
```

If S2 depends on S1 and S1 failed, S2 won't run. Check S1 in artifacts.

### Tests Failing
Run with verbose output:
```bash
.venv/bin/pytest tests/test_orchestrator_v2_e2e.py -vvs
```

---

## Files to Know

| File | Purpose |
|------|---------|
| `scripts/orchestrator/state_machine.py` | 7-phase pipeline state |
| `scripts/orchestrator/story_dag.py` | Dependency graph & scheduling |
| `scripts/orchestrator/policy_engine.py` | Retry/escalation policies |
| `scripts/orchestrator/planner.py` | Deterministic planning |
| `scripts/orchestrator/executor.py` | Async action dispatch |
| `scripts/orchestrator/v2_runtime.py` | Main orchestration loop |
| `config.yaml` | V2 configuration |
| `tests/test_orchestrator_v2*.py` | Test suite (41 tests) |

---

## Next Steps

- **Phase 2**: Coherence Checker (detect agent inconsistencies)
- **Phase 3**: Chain-of-Thought logging
- **Phase 4**: Learning from execution history

---

## Resources

- [Detailed Summary](./ORCHESTRATOR_V2_PHASE1_SUMMARY.md)
- [Design Document](./ORCHESTRATOR_V2_DESIGN.md)
- [Execution Example](./ORCHESTRATOR_V2_EXECUTION_EXAMPLE.md)
- [Implementation Plan](./ORCHESTRATOR_V2_PHASE1_PLAN.md)

---

**Status**: Production-ready, 41/41 tests passing, 75% coverage

**Questions?** Check logs in artifacts/iterations/ or run tests with `-vvs`
