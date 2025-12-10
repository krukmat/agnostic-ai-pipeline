# Orchestrator V2 - Phase 2 Implementation Plan

**Status**: 📋 Planning (Ready for execution)
**Target**: Complete Planner module + Coherence Checker
**Estimated Scope**: 8 major tasks, ~1500 lines of code

---

## Executive Summary

Phase 2 completes Orchestrator V2 by:
1. **Implementing full Planner logic** (currently stubs)
2. **Adding Coherence Checker** for agent consistency validation
3. **Implementing Chain-of-Thought logging**
4. **Reaching 95%+ code coverage** across all modules

---

## Phase 2 Tasks

### **Task 1: Implement Planner Phase Methods (250 lines)**

**Current Status**: Stubs only (25% coverage)

#### 1.1 `_plan_init()`
- **Lines**: ~15
- **Current**: Returns hardcoded RUN_BA action
- **To Implement**:
  - Check if requirements.yaml exists
  - If missing: return RUN_BA
  - If exists: transition logic instead

**Test**: test_planner_init_existing_requirements

#### 1.2 `_plan_requirements()`
- **Lines**: ~30
- **Current**: Empty
- **To Implement**:
  - Sequence: RUN_BA → RUN_PO → RUN_ARCHITECT
  - Check completion of each phase
  - Return appropriate next action
  - Handle PO validation feedback

**Test**: test_planner_requirements_sequence, test_planner_po_rejection

#### 1.3 `_plan_planning()`
- **Lines**: ~20
- **Current**: Empty
- **To Implement**:
  - Load stories.yaml into DAG
  - Validate story dependencies (no cycles)
  - Transition to DEVELOPMENT phase
  - Log loaded stories

**Test**: test_planner_planning_loads_dag, test_planner_invalid_dependencies

#### 1.4 `_plan_development()`
- **Lines**: ~100 (largest, most complex)
- **Current**: Returns empty list
- **To Implement**:
  ```python
  def _plan_development(self) -> List[Dict]:
      # 1. Get ready stories from DAG
      ready = self.dag.get_ready_stories(
          self.state.stories_done,
          self.state.stories_doing,
          self.state.stories_failed
      )

      if not ready:
          return []  # No action, wait for completion

      # 2. Check escalation for each ready story
      actions = []
      for story_id in ready:
          attempts = self.state.story_attempts.get(story_id, 0)
          errors = self.state.story_errors.get(story_id, [])

          escalation = self.policy_engine.evaluate_escalation(
              story_id, attempts, errors, {}
          )
          if escalation:
              actions.append({
                  "tool": "ESCALATE_ARCHITECT",
                  "arguments": {"story_id": story_id},
                  "reason": f"Escalation: {escalation}",
              })
              continue

          # 3. Check if should retry
          if not self.policy_engine.should_retry("dev", attempts):
              # Max attempts exceeded, mark as failed
              self.state.stories_failed.add(story_id)
              self.state.stories_todo.remove(story_id)
              continue

      # 4. Select parallel batch
      batch = self.dag.get_parallel_batch(
          ready,
          self.policy_engine.get_max_parallel_stories()
      )

      # 5. Create dev actions for batch
      for story_id in batch:
          actions.append({
              "tool": "RUN_DEV_STORY",
              "arguments": {"story_id": story_id},
              "reason": f"Ready story: {story_id}",
              "rule": "dag_ready_check",
          })

      return actions
  ```

**Tests**:
- test_planner_dev_ready_stories
- test_planner_dev_escalation
- test_planner_dev_max_attempts
- test_planner_dev_parallel_batch
- test_planner_dev_no_ready_stories

#### 1.5 `_plan_integration()`
- **Lines**: ~20
- **Current**: Empty
- **To Implement**:
  - Check if all stories are done or blocked
  - If done: return RUN_QA_FULL action
  - If still todo: return empty (wait)
  - Track QA start time

**Test**: test_planner_integration_all_done, test_planner_integration_waiting

#### 1.6 `_plan_done()`
- **Lines**: ~15
- **Current**: Empty
- **To Implement**:
  - Verify all stories marked as done or blocked
  - Calculate success metrics (coverage, time)
  - Return empty list (terminal state)

**Test**: test_planner_done_state

---

### **Task 2: Add Story Attempt Tracking (100 lines)**

**Purpose**: Track retries and errors per story

**Location**: `state_machine.py` - PipelineState class

#### 2.1 Add state fields
```python
@dataclass
class PipelineState:
    # ... existing fields ...

    # NEW: Track attempts and errors per story
    story_attempts: Dict[str, int] = field(default_factory=dict)
    story_errors: Dict[str, List[str]] = field(default_factory=dict)
    story_start_times: Dict[str, float] = field(default_factory=dict)
    story_durations: Dict[str, float] = field(default_factory=dict)
```

#### 2.2 Update `update_from_results()`
```python
# When RUN_DEV_STORY fails:
story_id = result.get("story_id")
attempts = self.story_attempts.get(story_id, 0) + 1
self.story_attempts[story_id] = attempts

# Record error
error = result.get("error", "Unknown")
if story_id not in self.story_errors:
    self.story_errors[story_id] = []
self.story_errors[story_id].append(error)

# Track duration
elapsed = result.get("elapsed", 0)
self.story_durations[story_id] = elapsed
```

**Tests**:
- test_state_tracks_attempts
- test_state_tracks_errors
- test_state_tracks_durations

---

### **Task 3: Implement Coherence Checker (400 lines)**

**Purpose**: Detect and flag inconsistencies between agent outputs

**New File**: `scripts/orchestrator/coherence_checker.py`

#### 3.1 CoherenceChecker Class
```python
class CoherenceChecker:
    """Validates consistency between BA, PO, Architect, Dev outputs."""

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logger

    def check_ba_po_alignment(
        self,
        requirements: Dict,
        po_review: Dict
    ) -> Dict:
        """Check if PO review aligns with BA requirements."""
        issues = []

        # 1. Check required fields
        if "requirements" not in requirements:
            issues.append("BA missing requirements list")
        if "approved" not in po_review:
            issues.append("PO missing approval status")

        # 2. Check scope consistency
        ba_req_count = len(requirements.get("requirements", []))
        po_req_count = len(po_review.get("reviewed_requirements", []))
        if po_req_count != ba_req_count:
            issues.append(
                f"Requirement count mismatch: BA={ba_req_count}, PO={po_req_count}"
            )

        # 3. Check for conflicts
        ba_constraints = set(requirements.get("constraints", []))
        po_constraints = set(po_review.get("constraints", []))
        conflicts = ba_constraints ^ po_constraints
        if conflicts:
            issues.append(f"Constraint conflicts: {conflicts}")

        return {
            "aligned": len(issues) == 0,
            "issues": issues,
            "severity": "high" if issues else "ok",
        }

    def check_arch_stories_alignment(
        self,
        architecture: Dict,
        stories: List[Dict]
    ) -> Dict:
        """Check if stories implement architecture."""
        issues = []

        # 1. Check architecture components in stories
        arch_components = set(architecture.get("components", []))
        story_components = set()
        for story in stories:
            story_components.update(story.get("components", []))

        missing = arch_components - story_components
        if missing:
            issues.append(f"Architecture components not in stories: {missing}")

        # 2. Check dependencies are consistent
        for story in stories:
            deps = story.get("depends_on", [])
            for dep in deps:
                if not self._story_exists(dep, stories):
                    issues.append(f"Story {story['id']}: dependency {dep} not found")

        # 3. Check layers/tiers respected
        arch_layers = architecture.get("layers", [])
        for story in stories:
            story_layer = story.get("layer")
            if story_layer and story_layer not in arch_layers:
                issues.append(
                    f"Story {story['id']}: layer {story_layer} not in architecture"
                )

        return {
            "aligned": len(issues) == 0,
            "issues": issues,
            "severity": "high" if len(issues) > 2 else "medium" if issues else "ok",
        }

    def check_dev_tests_alignment(
        self,
        implementation: Dict,
        tests: Dict
    ) -> Dict:
        """Check if tests cover implementation."""
        issues = []

        # 1. Check test coverage
        coverage = tests.get("coverage", 0.0)
        if coverage < 0.7:
            issues.append(f"Low test coverage: {coverage*100:.1f}%")

        # 2. Check test types
        test_types = set(tests.get("test_types", []))
        required_types = {"unit", "integration"}
        missing_types = required_types - test_types
        if missing_types:
            issues.append(f"Missing test types: {missing_types}")

        # 3. Check edge cases tested
        impl_functions = set(implementation.get("functions", []))
        tested_functions = set(tests.get("tested_functions", []))
        untested = impl_functions - tested_functions
        if len(untested) > len(impl_functions) * 0.2:
            issues.append(f"Many untested functions: {len(untested)}")

        return {
            "aligned": len(issues) == 0,
            "issues": issues,
            "severity": "high" if coverage < 0.5 else "medium" if issues else "ok",
        }

    def check_qa_artifacts(self, qa_report: Dict) -> Dict:
        """Validate QA report completeness."""
        issues = []

        required_fields = [
            "test_results",
            "coverage",
            "failures",
            "duration",
        ]

        for field in required_fields:
            if field not in qa_report:
                issues.append(f"QA report missing: {field}")

        if qa_report.get("failures", {}).get("critical"):
            issues.append("Critical test failures detected")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "severity": "critical" if "Critical" in str(issues) else "high" if issues else "ok",
        }
```

**Tests**:
- test_coherence_ba_po_alignment
- test_coherence_arch_stories_alignment
- test_coherence_dev_tests_alignment
- test_coherence_qa_artifacts
- test_coherence_detects_misalignment
- test_coherence_severity_levels

---

### **Task 4: Integrate Coherence Checker (150 lines)**

**Location**: `scripts/orchestrator/planner.py`

#### 4.1 Add to Planner
```python
class OrchestratorPlanner:
    def __init__(self, sm, dag, policy_engine, config):
        # ... existing init ...
        self.coherence_checker = CoherenceChecker(config)

    def plan_next_actions(self, state: PipelineState) -> List[Dict]:
        """Plan next actions with coherence validation."""

        # Get base actions
        actions = super().plan_next_actions(state)

        # Check coherence before transitioning phases
        if state.phase == PipelinePhase.REQUIREMENTS:
            self._check_and_log_coherence(state)

        return actions

    def _check_and_log_coherence(self, state: PipelineState):
        """Log coherence issues without blocking."""

        # Check BA→PO alignment
        ba_output = self._load_artifact("requirements.yaml")
        po_output = self._load_artifact("product_owner_review.yaml")
        if ba_output and po_output:
            alignment = self.coherence_checker.check_ba_po_alignment(
                ba_output, po_output
            )
            if not alignment["aligned"]:
                logger.warning(
                    f"[coherence] BA→PO misalignment: {alignment['issues']}"
                )
                state.coherence_issues.append(alignment)
```

**Tests**:
- test_planner_checks_coherence
- test_planner_logs_issues_non_blocking
- test_planner_coherence_per_phase

---

### **Task 5: Implement Chain-of-Thought Logging (200 lines)**

**Purpose**: Structured logging of decision reasoning

**New File**: `scripts/orchestrator/cot_logger.py`

#### 5.1 ChainOfThoughtLogger Class
```python
class ChainOfThoughtLogger:
    """Logs structured reasoning for orchestrator decisions."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("artifacts/cot")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_chain = []
        self.all_chains = []

    def start_chain(self, step: int, phase: str):
        """Start a new chain of thought."""
        self.current_chain = {
            "step": step,
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "reasoning": [],
        }

    def log_decision(
        self,
        decision: str,
        rule: str,
        confidence: float,
        alternatives: List[str] = None,
    ):
        """Log a decision point in the chain."""
        self.current_chain["reasoning"].append({
            "decision": decision,
            "rule": rule,
            "confidence": confidence,
            "alternatives": alternatives or [],
            "timestamp": datetime.now().isoformat(),
        })

    def log_evaluation(self, condition: str, result: bool, reason: str):
        """Log condition evaluation."""
        self.current_chain["reasoning"].append({
            "type": "evaluation",
            "condition": condition,
            "result": result,
            "reason": reason,
        })

    def end_chain(self) -> Dict:
        """End current chain and save."""
        if self.current_chain:
            self.all_chains.append(self.current_chain)
            self._save_chain(self.current_chain)
        chain = self.current_chain
        self.current_chain = []
        return chain

    def _save_chain(self, chain: Dict):
        """Save chain to file."""
        step = chain["step"]
        path = self.output_dir / f"step_{step:03d}.json"
        path.write_text(json.dumps(chain, indent=2))

    def export_summary(self) -> Dict:
        """Export summary of all chains."""
        return {
            "total_steps": len(self.all_chains),
            "chains": self.all_chains,
            "decision_tree": self._build_tree(),
        }

    def _build_tree(self) -> Dict:
        """Build decision tree from chains."""
        tree = {}
        for chain in self.all_chains:
            phase = chain["phase"]
            if phase not in tree:
                tree[phase] = []
            tree[phase].append({
                "step": chain["step"],
                "decisions": len(chain["reasoning"]),
            })
        return tree
```

**Tests**:
- test_cot_logger_chain_creation
- test_cot_logger_decision_logging
- test_cot_logger_evaluation_logging
- test_cot_logger_chain_export
- test_cot_logger_decision_tree

---

### **Task 6: Implement Learning & Optimization (250 lines)**

**Purpose**: Learn from execution history to improve decisions

**New File**: `scripts/orchestrator/optimizer.py`

#### 6.1 ExecutionOptimizer Class
```python
class ExecutionOptimizer:
    """Learns from past executions to optimize future decisions."""

    def __init__(self, history_dir: Path = None):
        self.history_dir = history_dir or Path("artifacts/iterations")
        self.execution_history = []
        self._load_history()

    def _load_history(self):
        """Load past execution summaries."""
        for iteration_dir in self.history_dir.iterdir():
            summary_file = iteration_dir / "latest_orchestrator_summary.json"
            if summary_file.exists():
                data = json.loads(summary_file.read_text())
                self.execution_history.append(data)

    def get_optimal_parallelism(self) -> int:
        """Learn optimal number of parallel stories."""
        # Analyze past executions
        successful_parallelism = []
        for execution in self.execution_history:
            if execution.get("status") == "success":
                parallelism = execution.get("max_parallel", 3)
                duration = execution.get("duration")
                successful_parallelism.append({
                    "parallelism": parallelism,
                    "duration": duration,
                    "efficiency": duration / parallelism,
                })

        if not successful_parallelism:
            return 3  # default

        # Return parallelism with best efficiency
        best = min(successful_parallelism, key=lambda x: x["efficiency"])
        return best["parallelism"]

    def get_optimal_backoff(self, role: str) -> Dict:
        """Learn optimal retry backoff for role."""
        role_failures = []
        for execution in self.execution_history:
            if f"{role}_failures" in execution:
                role_failures.extend(execution[f"{role}_failures"])

        if not role_failures:
            return {"type": "exponential", "base": 60}

        # Analyze failure patterns
        retry_effectiveness = {}
        for failure in role_failures:
            retries = failure.get("retries", 0)
            succeeded = failure.get("succeeded", False)

            if retries not in retry_effectiveness:
                retry_effectiveness[retries] = {"success": 0, "total": 0}

            retry_effectiveness[retries]["total"] += 1
            if succeeded:
                retry_effectiveness[retries]["success"] += 1

        # Calculate success rate by retry count
        success_rates = {
            retries: data["success"] / data["total"]
            for retries, data in retry_effectiveness.items()
        }

        # Return optimal strategy
        if max(success_rates.values()) > 0.7:
            return {"type": "exponential", "base": 60}
        else:
            return {"type": "linear", "base": 120}
```

**Tests**:
- test_optimizer_loads_history
- test_optimizer_optimal_parallelism
- test_optimizer_optimal_backoff
- test_optimizer_learns_from_failures

---

### **Task 7: Add E2E Tests with Coherence (300 lines)**

**File**: `tests/test_orchestrator_v2_phase2_e2e.py`

#### 7.1 Test Planner Implementation
```python
class TestPlannerImplementation:
    @pytest.mark.asyncio
    async def test_planner_full_pipeline(self):
        """Full pipeline execution through all phases."""
        # Setup
        planning_dir = Path("planning")
        planning_dir.mkdir(exist_ok=True)

        # Create artifacts for each phase
        requirements = {"concept": "test", "requirements": []}
        (planning_dir / "requirements.yaml").write_text(
            json.dumps(requirements)
        )

        po_review = {"approved": True}
        (planning_dir / "product_owner_review.yaml").write_text(
            json.dumps(po_review)
        )

        stories = [
            {"id": "S1", "title": "Test", "status": "todo", "depends_on": []}
        ]
        (planning_dir / "stories.yaml").write_text(json.dumps(stories))

        # Run orchestrator
        result = await run_orchestrator_v2(
            "test concept", max_steps=20, role_handlers={...}
        )

        # Verify full execution
        assert result["final_state"] == "done"
        assert all(step["status"] == "ok" for step in result["steps"])
```

#### 7.2 Test Coherence Checker
```python
class TestCoherenceChecker:
    def test_coherence_detects_misalignment(self):
        """Coherence checker detects inconsistencies."""
        checker = CoherenceChecker({})

        ba_output = {
            "requirements": ["Feature 1", "Feature 2"],
            "constraints": ["Performance"],
        }

        po_review = {
            "reviewed_requirements": ["Feature 1"],  # Mismatch!
            "constraints": ["Performance", "Security"],  # Extra!
        }

        result = checker.check_ba_po_alignment(ba_output, po_review)
        assert not result["aligned"]
        assert "count mismatch" in str(result["issues"]).lower()
```

#### 7.3 Test Learning & Optimization
```python
class TestOptimizer:
    def test_optimizer_learns_parallelism(self):
        """Optimizer learns optimal parallelism."""
        optimizer = ExecutionOptimizer()

        # Should return learned value or default
        parallelism = optimizer.get_optimal_parallelism()
        assert parallelism > 0
        assert parallelism <= 10
```

**Tests**: ~30 test cases covering all Phase 2 components

---

### **Task 8: Integration & Documentation (200 lines)**

#### 8.1 Update run_orchestrator_v2()
```python
async def run_orchestrator_v2(
    concept: str,
    max_steps: int = 10,
    role_handlers: Dict = None,
    enable_coherence: bool = True,
    enable_cot: bool = True,
) -> Dict:
    """Run V2 orchestrator with Phase 2 features."""

    # ... existing code ...

    # Add coherence checker
    if enable_coherence:
        planner.coherence_checker = CoherenceChecker(config)

    # Add chain-of-thought logger
    cot_logger = None
    if enable_cot:
        cot_logger = ChainOfThoughtLogger()

    # Add optimizer
    optimizer = ExecutionOptimizer()

    for step_num in range(max_steps):
        if cot_logger:
            cot_logger.start_chain(step_num, state.phase.value)

        # Plan actions
        actions = planner.plan_next_actions(state)

        # Log reasoning
        if cot_logger:
            cot_logger.log_decision(
                f"Planned {len(actions)} actions",
                "phase_transition_rules",
                1.0,
            )

        # Execute
        results = await executor.execute_actions(actions)

        # Learn
        optimizer.record_execution(results)

        # End chain
        if cot_logger:
            cot_logger.end_chain()

        # ... rest of loop ...

    # Export results
    return {
        "concept": concept,
        "steps": steps,
        "final_state": state.phase.value,
        "coherence_issues": planner.state.coherence_issues,
        "cot_chains": cot_logger.export_summary() if cot_logger else None,
    }
```

#### 8.2 Update Documentation
- Update PHASE1_SUMMARY.md with Phase 2 preview
- Create PHASE2_COMPLETION_GUIDE.md
- Update README with new features

#### 8.3 Update config.yaml
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
  history_window: 10  # Learn from last 10 executions
```

---

## Coverage Targets Phase 2

### Current (Phase 1 + Stubs)
```
Total: 75% (430 statements, 108 missed)
Without planner stubs: 88%
```

### Target (Phase 2 Complete)
```
planner.py:              95% (full implementation)
coherence_checker.py:    90% (new module)
cot_logger.py:           92% (new module)
optimizer.py:            88% (new module)

Overall: 92%+ (exceeding >85% target by large margin)
```

---

## Task Breakdown by Effort

| Task | Lines | Complexity | Priority | Est. Hours |
|------|-------|-----------|----------|-----------|
| 1. Planner Methods | 250 | High | 🔴 P0 | 16 |
| 2. Attempt Tracking | 100 | Medium | 🔴 P0 | 4 |
| 3. Coherence Checker | 400 | High | 🟡 P1 | 20 |
| 4. Coherence Integration | 150 | Medium | 🟡 P1 | 8 |
| 5. CoT Logging | 200 | Medium | 🟢 P2 | 12 |
| 6. Learning Optimizer | 250 | High | 🟢 P2 | 16 |
| 7. E2E Tests | 300 | High | 🔴 P0 | 20 |
| 8. Integration & Docs | 200 | Low | 🔴 P0 | 10 |

**Total Estimated**: ~1850 lines, 106 hours, 3-4 weeks

---

## Success Criteria Phase 2

✅ **Functional**
- [ ] All planner methods fully implemented (not stubs)
- [ ] Coherence checker detects real inconsistencies
- [ ] CoT logging captures decision reasoning
- [ ] Optimizer learns from execution history

✅ **Quality**
- [ ] 92%+ code coverage (all modules >85%)
- [ ] 50+ new test cases (all passing)
- [ ] Zero regressions to Phase 1
- [ ] Documentation complete

✅ **Performance**
- [ ] Planner runs in <1s per step
- [ ] Coherence check in <500ms
- [ ] CoT logging adds <100ms overhead
- [ ] Optimizer learns in <100ms

✅ **Integration**
- [ ] All Phase 2 features optional (backward compatible)
- [ ] Config-driven feature toggles
- [ ] Seamless V1 compatibility

---

## Dependencies

### On Phase 1
- ✅ State Machine (completed)
- ✅ Story DAG (completed)
- ✅ Policy Engine (completed)
- ✅ V2 Runtime (completed)

### External
- Python 3.11+
- pytest >= 8.0
- async/await support

---

## Rollout Strategy

### Phase 2a (Weeks 1-2)
- [ ] Task 1: Implement Planner methods
- [ ] Task 2: Add attempt tracking
- [ ] Task 7: Write E2E tests

### Phase 2b (Weeks 2-3)
- [ ] Task 3: Implement Coherence Checker
- [ ] Task 4: Integrate with Planner
- [ ] Task 7: Coherence tests

### Phase 2c (Week 3-4)
- [ ] Task 5: Chain-of-Thought logging
- [ ] Task 6: Learning Optimizer
- [ ] Task 8: Integration & Documentation

### Phase 2 Completion
- [ ] All 92%+ coverage
- [ ] All 50+ tests passing
- [ ] Full documentation
- [ ] Production ready

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Planner logic complex | High | Design step-by-step, test each phase |
| Coherence false positives | Medium | Adjust thresholds, log non-blocking |
| Performance overhead | Medium | Profile, optimize hot paths |
| Integration complexity | Medium | Comprehensive integration tests |

---

## Next Steps

1. **Review & Approve** this Phase 2 plan
2. **Create issues** for each task
3. **Start Phase 2a** (Planner implementation)
4. **Track progress** in GitHub/todo

---

**Phase 2 Plan Status**: ✅ **READY FOR EXECUTION**

All tasks documented, estimated, and prioritized. Ready to begin implementation upon approval.
