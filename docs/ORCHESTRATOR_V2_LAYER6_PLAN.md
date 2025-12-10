# Orchestrator V2 - Layer 6 Implementation Plan

**Status**: 📋 PLANNING
**Gap Identified**: Layer 6 (Chain-of-Thought Tracker) mentioned in ORCHESTRATOR_V2_DESIGN.md but not implemented
**Date**: December 10, 2025

---

## Executive Summary

Layer 6 (Chain-of-Thought Tracker) bridges the gap between Phase 2/3 CoT modules and the core orchestration layers. It captures reasoning at **every architectural layer** (state machine, DAG, policy, planner, LLM) with structured logging and export capabilities.

**Current Status**:
- ✅ Phase 2 CoT Logger exists: `cot_logger.py`
- ✅ Phase 3 Advanced CoT exists: `advanced_cot.py`
- ❌ **Layer 6 CoT Tracker MISSING**: Design exists but no implementation
- ❌ **Planner Integration MISSING**: Planner doesn't call CoT tracker methods

**Scope**: 2 implementation tasks

---

## Identified Gap Analysis

### What's Described in Design Doc

**File**: `docs/ORCHESTRATOR_V2_DESIGN.md` (lines 482-604)

**Components**:
1. `ThoughtEntry` dataclass - Captures a single reasoning step
2. `ChainOfThoughtTracker` class - Collects and manages thoughts
3. Methods to log at each layer:
   - `log_state_transition()` - State machine decisions
   - `log_dag_decision()` - DAG-based story selection
   - `log_policy_evaluation()` - Policy engine results
   - `log_llm_decision()` - LLM-based decisions
4. Export methods:
   - `export_jsonl()` - Machine-readable format
   - `export_markdown()` - Human-readable format

**Why It's Needed**:
- CoT Logger (Phase 2) captures decisions but not layer-by-layer reasoning
- Advanced CoT (Phase 3) focuses on hierarchical chains, not integration
- No module exists to capture reasoning across **all 5 layers** (state, DAG, policy, planner, LLM)
- Design doc shows intent but no code exists

### Difference from Existing CoT Modules

| Aspect | Phase 2 CoT Logger | Phase 3 Advanced CoT | **Layer 6 Tracker (MISSING)** |
|--------|-------------------|---------------------|------------------------------|
| Scope | Decision logging | Hierarchical reasoning | All architectural layers |
| Input | Decisions + confidence | Sub-chains + alternatives | Every layer's output |
| Output | step_NNN.json | cot_advanced/ | jsonl + markdown |
| Layer awareness | ❌ No | ❌ No | ✅ **Yes** |
| State transitions | ❌ No | ❌ No | ✅ **Yes** |
| DAG decisions | ❌ No | ❌ No | ✅ **Yes** |
| Policy evals | ❌ No | ❌ No | ✅ **Yes** |
| LLM decisions | Basic | No | ✅ **Yes** |

---

## Task Breakdown

### Task 1: Implement Layer 6 CoT Tracker Module

**File**: `scripts/orchestrator/cot_tracker.py` (NEW)

**Purpose**: Unified thought tracking across all orchestration layers

**Components to Implement**:

#### 1.1 ThoughtEntry Dataclass
```python
@dataclass
class ThoughtEntry:
    """Single reasoning step in the orchestration pipeline."""
    timestamp: str              # ISO format timestamp
    phase: str                  # Pipeline phase (INIT, REQUIREMENTS, etc.)
    layer: str                  # Which layer made decision (state_machine, dag, policy, planner, llm)
    kind: str                   # Type of thought (transition, decision, policy_eval, escalation)
    message: str                # Human-readable summary
    details: Dict[str, Any]     # Extra context specific to this thought

    # Reasoning trace
    inputs: Dict[str, Any]      # What went in
    reasoning_steps: List[str]  # How we got to output
    output: Any                 # What was decided
    confidence: float           # 1.0 for deterministic, <1.0 for LLM
```

#### 1.2 ChainOfThoughtTracker Class
```python
class ChainOfThoughtTracker:
    """Tracks reasoning at every layer."""

    def __init__(self, output_dir: Optional[Path] = None)
    def log_state_transition(from_phase, to_phase, reason)
    def log_dag_decision(ready_stories, batch, reason)
    def log_policy_evaluation(policy_name, condition, matched, context)
    def log_llm_decision(prompt, response, parsed)
    def log_escalation_decision(story_id, action, reason)
    def log_planner_decision(decision_type, alternatives, chosen, confidence)

    # Export methods
    def export_jsonl(path: Path) -> None
    def export_markdown(path: Path) -> None
    def get_thought_count() -> int
    def get_thoughts_by_layer() -> Dict[str, int]
    def get_thoughts_by_phase() -> Dict[str, List[ThoughtEntry]]
```

**Estimated Lines**: 250-300 lines
- ThoughtEntry: 20 lines
- ChainOfThoughtTracker.__init__: 10 lines
- log_* methods (7 methods × 15 lines): 105 lines
- export_jsonl: 15 lines
- export_markdown: 80 lines
- Helper methods: 30 lines

**Output Artifacts**:
- `artifacts/cot_layer6/thoughts.jsonl` - Streaming JSON (one thought per line)
- `artifacts/cot_layer6/reasoning_chain.md` - Human-readable report
- `artifacts/cot_layer6/summary.json` - Statistics and metadata

**Tests Required** (8-10 tests):
1. `test_create_tracker`
2. `test_log_state_transition`
3. `test_log_dag_decision`
4. `test_log_policy_evaluation`
5. `test_log_llm_decision`
6. `test_log_escalation_decision`
7. `test_export_jsonl`
8. `test_export_markdown`
9. `test_thought_counts`
10. `test_integration_with_planner` (?)

---

### Task 2: Integrate Layer 6 into Planner

**File**: `scripts/orchestrator/planner.py` (MODIFY)

**Current Status**:
- Planner has `_plan_*` methods
- No CoT tracker integration
- No layer-aware reasoning capture

**Changes Required**:

#### 2.1 Add CoT Tracker Initialization
```python
class OrchestratorPlanner:
    def __init__(self, config: Dict):
        # ... existing code ...
        self.cot_tracker = ChainOfThoughtTracker()  # NEW
```

#### 2.2 Update _plan_init()
```python
def _plan_init(self, state: PipelineState) -> List[Dict]:
    # NEW: Log state transition
    self.cot_tracker.log_state_transition(
        from_phase=state.phase.value,
        to_phase=PipelinePhase.REQUIREMENTS.value,
        reason="Start BA phase"
    )
    # ... existing logic ...
```

#### 2.3 Update _plan_development()
```python
async def _plan_development(self, state: PipelineState) -> List[Dict]:
    # NEW: Log DAG decision
    self.cot_tracker.log_dag_decision(
        ready_stories=ready_stories,
        batch=batch,
        reason=f"Selected {len(batch)} stories respecting resource limits"
    )

    # NEW: Log policy evaluations
    for story_id in batch:
        escalation_action = self.policy_engine.evaluate_escalation(state, story_id)
        self.cot_tracker.log_policy_evaluation(
            policy_name="escalation_policy",
            condition=f"story_id={story_id}",
            matched=escalation_action is not None,
            context={"story_id": story_id, "attempts": state.stories_running.get(story_id, 0)}
        )

    # ... existing logic ...
```

#### 2.4 Add Method to Export CoT
```python
def export_cot_reasoning(self, output_dir: Optional[Path] = None) -> Dict:
    """Export chain-of-thought reasoning."""
    output_dir = output_dir or Path("artifacts/cot_layer6")
    self.cot_tracker.export_jsonl(output_dir / "thoughts.jsonl")
    self.cot_tracker.export_markdown(output_dir / "reasoning_chain.md")
    return {
        "jsonl": str(output_dir / "thoughts.jsonl"),
        "markdown": str(output_dir / "reasoning_chain.md"),
        "thought_count": self.cot_tracker.get_thought_count()
    }
```

**Estimated Changes**: 80-100 lines
- Import ChainOfThoughtTracker: 1 line
- Initialize in __init__: 1 line
- Add logging in _plan_init: 5 lines
- Add logging in _plan_requirements: 10 lines
- Add logging in _plan_planning: 10 lines
- Add logging in _plan_development: 30 lines
- Add logging in _plan_integration: 10 lines
- Add export_cot_reasoning method: 15 lines
- Update docstrings: 8 lines

**Tests Required** (5-6 tests):
1. `test_planner_initializes_cot_tracker`
2. `test_plan_init_logs_transition`
3. `test_plan_development_logs_dag_decisions`
4. `test_plan_development_logs_policy_evaluations`
5. `test_export_cot_reasoning`
6. `test_cot_integration_with_state_changes`

---

## Integration Points

### With Existing Modules

```
Phase 2 CoT Logger (cot_logger.py)
    ↓ (complements with layer awareness)
Layer 6 CoT Tracker (cot_tracker.py) ← NEW
    ↓ (used by)
Planner (planner.py) → adds logging calls
    ↓ (integrates with)
Policy Engine (policy_engine.py) → evaluations logged
State Machine (state_machine.py) → transitions logged
Story DAG (story_dag.py) → decisions logged
```

### Backward Compatibility
- ✅ ChainOfThoughtTracker is optional (can be disabled)
- ✅ Planner works with or without tracker
- ✅ No changes to existing APIs
- ✅ Phase 2 CoT Logger unaffected

---

## Acceptance Criteria

### Task 1: CoT Tracker Implementation
- [ ] `cot_tracker.py` created with 250+ lines
- [ ] `ThoughtEntry` dataclass complete
- [ ] `ChainOfThoughtTracker` class with 7+ logging methods
- [ ] `export_jsonl()` produces valid JSONL
- [ ] `export_markdown()` produces readable report
- [ ] 8-10 unit tests all passing
- [ ] 80%+ code coverage
- [ ] Documentation complete
- [ ] Zero regressions to Phase 2/3 modules

### Task 2: Planner Integration
- [ ] `planner.py` updated with CoT tracking
- [ ] All 5 plan_* methods log appropriately
- [ ] `export_cot_reasoning()` method works
- [ ] 5-6 integration tests passing
- [ ] No performance regression (<50ms overhead)
- [ ] Documentation updated
- [ ] Phase 1/2/3 compatibility maintained

---

## Testing Strategy

### Unit Tests (Task 1)
```python
# tests/test_orchestrator_cot_tracker.py
class TestChainOfThoughtTracker:
    - test_create_tracker()
    - test_log_state_transition()
    - test_log_dag_decision()
    - test_log_policy_evaluation()
    - test_log_llm_decision()
    - test_log_escalation_decision()
    - test_log_planner_decision()
    - test_export_jsonl()
    - test_export_markdown()
    - test_thought_statistics()
```

### Integration Tests (Task 2)
```python
# tests/test_planner_cot_integration.py
class TestPlannerCOTIntegration:
    - test_planner_initializes_tracker()
    - test_plan_init_logs_transition()
    - test_plan_development_logs_decisions()
    - test_plan_integration_logs_escalations()
    - test_export_cot_from_planner()
    - test_cot_with_multiple_phases()
```

### E2E Test (Optional)
```python
# Full orchestration run with CoT tracking
# Verify artifacts/ contains:
#   - artifacts/cot_layer6/thoughts.jsonl
#   - artifacts/cot_layer6/reasoning_chain.md
#   - artifacts/cot_layer6/summary.json
```

---

## Implementation Order

1. **Task 1 First**: Implement CoT Tracker (standalone, testable)
2. **Task 2 Second**: Integrate into Planner (depends on Task 1)
3. **Verify**: Run full test suite (Phase 1/2/3 + Layer 6)
4. **Document**: Update ORCHESTRATOR_V2_DESIGN.md status

---

## Files to Create/Modify

### New Files
- `scripts/orchestrator/cot_tracker.py` (250-300 lines)
- `tests/test_orchestrator_cot_tracker.py` (150-200 lines)
- `tests/test_planner_cot_integration.py` (120-150 lines)

### Modified Files
- `scripts/orchestrator/planner.py` (+80-100 lines)
- `scripts/orchestrator/__init__.py` (+2 lines for export)
- `docs/ORCHESTRATOR_V2_DESIGN.md` (update status section)

### Total Scope
- New code: ~250-300 lines (cot_tracker)
- Modified code: ~80-100 lines (planner integration)
- Test code: ~270-350 lines
- **Total: ~600-750 lines**

---

## Success Metrics

| Metric | Target | Check |
|--------|--------|-------|
| Code Coverage | 85%+ | pytest --cov |
| Test Pass Rate | 100% | 13+ tests all passing |
| Performance | <50ms overhead | Profiling |
| Compatibility | Zero regressions | Full test suite passes |
| Documentation | Complete | Design doc updated |
| Export Quality | Valid JSONL + readable MD | Manual verification |

---

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Planner performance impact | Low | Medium | Lazy initialize tracker, benchmark first |
| CoT file size explosion | Low | Low | Rolling logs, size limits |
| Integration complexity | Low | Medium | Phase Task 1 independently, simple integration |
| Circular imports | Low | High | Careful import order, type hints |

---

## Effort Estimate

| Task | Effort | Duration |
|------|--------|----------|
| Task 1: CoT Tracker | ~3-4 hours | 1 session |
| Task 2: Planner Integration | ~2-3 hours | 1 session |
| Testing & Verification | ~2 hours | 1 session |
| Documentation | ~1 hour | Parallel |
| **Total** | **~8-10 hours** | **~3 sessions** |

---

## Next Steps

1. ✅ **[DONE]** Document gap analysis
2. ✅ **[DONE]** Create implementation plan
3. ⏳ **[PENDING]** Implement Task 1: CoT Tracker
4. ⏳ **[PENDING]** Implement Task 2: Planner Integration
5. ⏳ **[PENDING]** Run full test suite
6. ⏳ **[PENDING]** Update documentation
7. ⏳ **[PENDING]** Commit and push to origin

---

## Questions for User

1. Should we implement Layer 6 CoT Tracker now, or defer to future phase?
2. Any preferences on export formats (JSONL, Markdown, JSON, CSV)?
3. Should CoT tracking be enabled by default or optional config?
4. How verbose should reasoning steps be (basic, detailed, very detailed)?

---

**Plan Status**: ✅ **COMPLETE & READY FOR IMPLEMENTATION**

*Generated*: December 10, 2025
*Plan Document*: `docs/ORCHESTRATOR_V2_LAYER6_PLAN.md`
