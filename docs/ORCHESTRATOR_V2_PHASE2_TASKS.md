# Orchestrator V2 - Phase 2 Task Checklist

**Status**: 📋 Ready for Execution
**Total Tasks**: 8
**Estimated Duration**: 3-4 weeks
**Target Coverage**: 92%+

---

## Quick Reference

| Task | Name | Lines | Hours | Priority |
|------|------|-------|-------|----------|
| 1 | Implement Planner methods | 250 | 16 | 🔴 P0 |
| 2 | Add attempt tracking | 100 | 4 | 🔴 P0 |
| 3 | Coherence Checker | 400 | 20 | 🟡 P1 |
| 4 | Coherence integration | 150 | 8 | 🟡 P1 |
| 5 | Chain-of-Thought logging | 200 | 12 | 🟢 P2 |
| 6 | Learning Optimizer | 250 | 16 | 🟢 P2 |
| 7 | E2E tests | 300 | 20 | 🔴 P0 |
| 8 | Integration & docs | 200 | 10 | 🔴 P0 |

**Total**: 1850 lines, 106 hours

---

## Task 1: Implement Planner Phase Methods ✓

**Priority**: 🔴 P0 (Critical)
**Lines**: 250
**Hours**: 16
**File**: `scripts/orchestrator/planner.py`

### Subtasks

- [ ] **1.1 `_plan_init()` - 15 lines**
  - Check if requirements.yaml exists
  - If missing: return RUN_BA action
  - If exists: return empty (skip to next)
  - Test: `test_planner_init_has_requirements`

- [ ] **1.2 `_plan_requirements()` - 30 lines**
  - Implement BA → PO → Architect sequence
  - Check completion of each phase
  - Return next action in sequence
  - Handle PO feedback/rejection
  - Tests: `test_planner_requirements_sequence`, `test_planner_po_rejection`

- [ ] **1.3 `_plan_planning()` - 20 lines**
  - Load stories.yaml into DAG
  - Validate no dependency cycles
  - Transition to DEVELOPMENT phase
  - Log loaded stories count
  - Test: `test_planner_planning_loads_dag`

- [ ] **1.4 `_plan_development()` - 100 lines (COMPLEX)**
  ```python
  # 1. Get ready stories from DAG
  # 2. Check escalation policies for each
  # 3. Check retry limits
  # 4. Select parallel batch
  # 5. Create RUN_DEV_STORY actions
  ```
  - Tests: `test_planner_dev_ready`, `test_planner_dev_escalation`,
           `test_planner_dev_max_attempts`, `test_planner_dev_parallel_batch`

- [ ] **1.5 `_plan_integration()` - 20 lines**
  - Check if all stories done or blocked
  - If done: return RUN_QA_FULL
  - If waiting: return empty list
  - Test: `test_planner_integration_ready`

- [ ] **1.6 `_plan_done()` - 15 lines**
  - Verify all stories marked done/blocked
  - Calculate success metrics
  - Return empty (terminal state)
  - Test: `test_planner_done_state`

**Acceptance Criteria**:
- [ ] All 6 methods fully implemented (not stubs)
- [ ] Coverage: 95% (up from 25%)
- [ ] 12 test cases passing
- [ ] No regressions to existing tests

---

## Task 2: Add Story Attempt Tracking ✓

**Priority**: 🔴 P0 (Critical)
**Lines**: 100
**Hours**: 4
**File**: `scripts/orchestrator/state_machine.py`

### Implementation

- [ ] **2.1 Add state fields to PipelineState**
  ```python
  story_attempts: Dict[str, int] = field(default_factory=dict)
  story_errors: Dict[str, List[str]] = field(default_factory=dict)
  story_start_times: Dict[str, float] = field(default_factory=dict)
  story_durations: Dict[str, float] = field(default_factory=dict)
  ```

- [ ] **2.2 Update `update_from_results()` method**
  - Track attempt count on failure
  - Record error type
  - Measure execution duration
  - Handle attempt limit exceeded

- [ ] **2.3 Add helper methods**
  - `increment_attempts(story_id)`
  - `add_error(story_id, error_type)`
  - `record_duration(story_id, elapsed)`

**Acceptance Criteria**:
- [ ] State fields persist across steps
- [ ] Errors recorded in order
- [ ] Durations accurate to 0.1s
- [ ] 5 test cases passing

---

## Task 3: Implement Coherence Checker ✓

**Priority**: 🟡 P1 (Important)
**Lines**: 400
**Hours**: 20
**File**: `scripts/orchestrator/coherence_checker.py` (NEW)

### Implementation

- [ ] **3.1 Create CoherenceChecker class**
  - Init with config
  - Load severity thresholds from config

- [ ] **3.2 Implement `check_ba_po_alignment(requirements, po_review)`**
  - Check required fields
  - Compare requirement counts
  - Detect constraint conflicts
  - Return {aligned: bool, issues: [], severity: str}

- [ ] **3.3 Implement `check_arch_stories_alignment(architecture, stories)`**
  - Verify all arch components in stories
  - Check story dependencies valid
  - Check layers/tiers respected
  - Detect unimplemented components

- [ ] **3.4 Implement `check_dev_tests_alignment(implementation, tests)`**
  - Check test coverage >= 70%
  - Verify required test types
  - Flag untested functions
  - Check edge cases

- [ ] **3.5 Implement `check_qa_artifacts(qa_report)`**
  - Validate required fields
  - Check for critical failures
  - Assess completeness

- [ ] **3.6 Add severity levels**
  - "ok" - No issues
  - "medium" - Minor misalignment
  - "high" - Important issues
  - "critical" - Blocking issues

**Acceptance Criteria**:
- [ ] All 5 check methods implemented
- [ ] Coverage: 90%
- [ ] 8 test cases passing
- [ ] Detects real inconsistencies

---

## Task 4: Integrate Coherence Checker ✓

**Priority**: 🟡 P1 (Important)
**Lines**: 150
**Hours**: 8
**File**: `scripts/orchestrator/planner.py` (modify)

### Implementation

- [ ] **4.1 Add to OrchestratorPlanner**
  - `self.coherence_checker = CoherenceChecker(config)`
  - Add `_check_and_log_coherence()` method

- [ ] **4.2 Integration points**
  - After REQUIREMENTS: check BA→PO
  - After PLANNING: check Arch→Stories
  - During DEVELOPMENT: check Dev→Tests
  - After INTEGRATION: check QA

- [ ] **4.3 Logging & reporting**
  - Log issues non-blocking
  - Store in state.coherence_issues
  - Mark severity for alerts
  - Suggest remediations

- [ ] **4.4 Config integration**
  - Read thresholds from config.yaml
  - Enable/disable per check
  - Configurable severity levels

**Acceptance Criteria**:
- [ ] Coverage: 85%
- [ ] 5 test cases passing
- [ ] No impact on orchestration flow
- [ ] Issues logged but don't block pipeline

---

## Task 5: Chain-of-Thought Logging ✓

**Priority**: 🟢 P2 (Enhancement)
**Lines**: 200
**Hours**: 12
**File**: `scripts/orchestrator/cot_logger.py` (NEW)

### Implementation

- [ ] **5.1 Create ChainOfThoughtLogger class**
  - Init with output_dir
  - Create artifacts/cot directory

- [ ] **5.2 Implement core methods**
  - `start_chain(step, phase)` - Begin recording
  - `log_decision(decision, rule, confidence, alternatives)` - Record choice
  - `log_evaluation(condition, result, reason)` - Record evaluation
  - `end_chain()` - Save and return chain

- [ ] **5.3 Implement export methods**
  - `export_summary()` - All chains
  - `_build_tree()` - Decision tree structure
  - Save chains to JSON files

- [ ] **5.4 Chain structure**
  ```json
  {
    "step": 3,
    "phase": "DEVELOPMENT",
    "timestamp": "2025-12-10T22:00:00",
    "reasoning": [
      {
        "decision": "Selected S1",
        "rule": "dag_ready_check",
        "confidence": 1.0,
        "alternatives": ["S2", "S3"]
      }
    ]
  }
  ```

**Acceptance Criteria**:
- [ ] Coverage: 92%
- [ ] 6 test cases passing
- [ ] Chains saved to artifacts/cot/
- [ ] Decision tree exportable

---

## Task 6: Learning Optimizer ✓

**Priority**: 🟢 P2 (Enhancement)
**Lines**: 250
**Hours**: 16
**File**: `scripts/orchestrator/optimizer.py` (NEW)

### Implementation

- [ ] **6.1 Create ExecutionOptimizer class**
  - Load history from artifacts/iterations/
  - Cache loaded executions

- [ ] **6.2 Implement `get_optimal_parallelism()`**
  - Analyze successful executions
  - Calculate efficiency per level
  - Return best parallelism
  - Default to 3 if no history

- [ ] **6.3 Implement `get_optimal_backoff(role)`**
  - Analyze role failure patterns
  - Calculate success rate by retry
  - Return strategy with best rate
  - Support exponential/linear

- [ ] **6.4 Add learning metrics**
  - Success rate by attempt count
  - Failure pattern distribution
  - Duration trends
  - Resource utilization

- [ ] **6.5 Configuration**
  - History window (last N executions)
  - Fallback to defaults
  - Export learned params

**Acceptance Criteria**:
- [ ] Coverage: 88%
- [ ] 6 test cases passing
- [ ] Learns from history
- [ ] Provides actionable recommendations

---

## Task 7: Add E2E Tests ✓

**Priority**: 🔴 P0 (Critical)
**Lines**: 300
**Hours**: 20
**File**: `tests/test_orchestrator_v2_phase2_e2e.py` (NEW)

### Test Classes

- [ ] **7.1 TestPlannerImplementation (8 tests)**
  - `test_full_pipeline_execution` - All phases
  - `test_planner_phase_transitions` - Each transition
  - `test_planner_ready_stories` - DAG scheduling
  - `test_planner_escalation` - Policy evaluation
  - `test_planner_max_attempts` - Retry limits
  - `test_planner_parallel_batch` - Batching
  - `test_planner_no_ready_stories` - Waiting state
  - `test_planner_blocked_stories` - Dependency blocking

- [ ] **7.2 TestCoherenceChecker (6 tests)**
  - `test_coherence_ba_po_alignment`
  - `test_coherence_arch_stories_alignment`
  - `test_coherence_dev_tests_alignment`
  - `test_coherence_qa_artifacts`
  - `test_coherence_detects_misalignment`
  - `test_coherence_severity_levels`

- [ ] **7.3 TestOptimizer (4 tests)**
  - `test_optimizer_loads_history`
  - `test_optimizer_optimal_parallelism`
  - `test_optimizer_optimal_backoff`
  - `test_optimizer_learns_from_failures`

- [ ] **7.4 TestChainOfThought (6 tests)**
  - `test_cot_chain_creation`
  - `test_cot_decision_logging`
  - `test_cot_evaluation_logging`
  - `test_cot_chain_export`
  - `test_cot_decision_tree`
  - `test_cot_artifacts_saved`

- [ ] **7.5 Integration tests (6 tests)**
  - `test_all_features_together`
  - `test_with_coherence_disabled`
  - `test_with_cot_disabled`
  - `test_backward_compatibility`
  - `test_no_regressions_to_phase1`
  - `test_error_handling`

**Acceptance Criteria**:
- [ ] 30+ test cases total
- [ ] All passing
- [ ] Coverage: 85%+
- [ ] No regressions to Phase 1

---

## Task 8: Integration & Documentation ✓

**Priority**: 🔴 P0 (Critical)
**Lines**: 200
**Hours**: 10
**Files**: Multiple

### Implementation

- [ ] **8.1 Update `run_orchestrator_v2()` function**
  - Add `enable_coherence` parameter
  - Add `enable_cot` parameter
  - Integrate CoherenceChecker
  - Integrate ChainOfThoughtLogger
  - Integrate ExecutionOptimizer
  - Return results with new fields

- [ ] **8.2 Update `config.yaml`**
  ```yaml
  orchestrator_v2:
    phase2_features:
      coherence_checker: true
      chain_of_thought: true
      learning_optimizer: true

  coherence:
    check_ba_po: true
    check_arch_stories: true
    check_dev_tests: true
    fail_on_critical: false

  cot:
    enabled: true
    output_dir: artifacts/cot
    save_chains: true

  optimizer:
    enabled: true
    history_window: 10
  ```

- [ ] **8.3 Update documentation**
  - Update ORCHESTRATOR_V2_PHASE1_SUMMARY.md
  - Create ORCHESTRATOR_V2_PHASE2_COMPLETION_GUIDE.md
  - Update README with Phase 2 features
  - Update QUICKSTART.md

- [ ] **8.4 Update module __init__.py**
  - Export new classes
  - Update imports

- [ ] **8.5 Final validation**
  - Run all tests: `pytest tests/test_orchestrator_v2* -v`
  - Check coverage: `pytest --cov=scripts/orchestrator`
  - Verify no regressions
  - Verify backward compatibility

**Acceptance Criteria**:
- [ ] All features optional (backward compatible)
- [ ] Config-driven toggles working
- [ ] Documentation complete
- [ ] Tests: 90+ total, all passing
- [ ] Coverage: 92%+

---

## Rollout Phases

### Phase 2a: Weeks 1-2 (Core Planner)
- [ ] Task 1: Implement Planner methods
- [ ] Task 2: Add attempt tracking
- [ ] Task 7: Add E2E tests (for Tasks 1-2)
- **Gate**: All P0 tests passing, coverage >85%

### Phase 2b: Weeks 2-3 (Agent Consistency)
- [ ] Task 3: Implement Coherence Checker
- [ ] Task 4: Integrate Coherence
- [ ] Task 7: Add coherence tests
- **Gate**: Coherence tests passing, no false positives

### Phase 2c: Weeks 3-4 (Learning & Release)
- [ ] Task 5: Chain-of-Thought logging
- [ ] Task 6: Learning Optimizer
- [ ] Task 8: Integration & docs
- [ ] Task 7: Final integration tests
- **Gate**: All 92% coverage, all tests passing, ready for production

---

## Success Metrics

### Code Quality
- [ ] 92%+ overall coverage
- [ ] All modules >85% coverage
- [ ] No regressions to Phase 1
- [ ] Code reviews passed

### Functionality
- [ ] All 8 tasks completed
- [ ] 90+ tests passing (100%)
- [ ] Coherence detects real issues
- [ ] Optimizer learns from history
- [ ] CoT logs structured reasoning

### Documentation
- [ ] Phase 2 completion guide
- [ ] API documentation updated
- [ ] README updated
- [ ] Examples provided

### Performance
- [ ] Planner <1s per step
- [ ] Coherence check <500ms
- [ ] CoT logging <100ms overhead
- [ ] Optimizer <100ms

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Planner logic complex | Design step-by-step, test each method |
| Coherence false positives | Adjustable thresholds, non-blocking |
| Performance overhead | Profile hot paths, optimize |
| Integration issues | Comprehensive integration tests |

---

## Implementation Order

**Recommended sequence for parallel execution:**

```
Week 1:
├─ Task 1: Planner methods (16h)
├─ Task 2: Attempt tracking (4h)
└─ Task 7: E2E tests for 1-2 (10h)

Week 2:
├─ Task 3: Coherence Checker (20h)
├─ Task 4: Coherence integration (8h)
├─ Task 7: Coherence tests (5h)
└─ Task 5: CoT logging starts (12h)

Week 3:
├─ Task 5: CoT logging continues (12h)
├─ Task 6: Learning Optimizer (16h)
├─ Task 7: Integration tests (5h)
└─ Task 8: Integration & docs starts (10h)

Week 4:
└─ Task 8: Integration & docs finishes (10h)
```

---

**Status**: ✅ READY FOR IMPLEMENTATION

All tasks documented, scoped, and ready to begin.

---

## Quick Commands (Phase 2)

```bash
# Run all Phase 2 tests
pytest tests/test_orchestrator_v2_phase2_e2e.py -v

# Run with coverage
pytest tests/test_orchestrator_v2* --cov=scripts/orchestrator --cov-report=term-missing

# Run V2 with Phase 2 features
python scripts/run_orchestrator_agent.py \
  --concept "My feature" --use-v2 \
  --max-steps 20

# Check coverage targets
pytest tests/test_orchestrator_v2* --cov=scripts/orchestrator --cov=92
```

---

**Next Action**: Approve and begin Phase 2a (Weeks 1-2)
