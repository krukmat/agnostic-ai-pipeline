# Orchestrator V2 - Phase 3 Implementation Plan

**Status**: 📋 Planning (Pre-implementation)
**Target**: Enhanced learning, domain-specific rules, advanced analytics
**Estimated Scope**: 10 major tasks, ~2000 lines of code
**Timeline**: 4-5 weeks

---

## Executive Summary

Phase 3 builds on Phase 2's foundation by adding:
1. **Advanced Learning**: ML-based performance prediction
2. **Domain-Specific Rules**: Customizable coherence checks per domain
3. **Advanced Analytics**: Detailed execution profiling and reporting
4. **Performance Optimization**: Intelligent caching and parallel execution
5. **Agent Feedback Loop**: Continuous improvement from execution results

---

## Phase Progression

```
Phase 1 (COMPLETE): Core orchestration ✅
  - State machine, DAG, policies
  - Deterministic planning
  - Basic execution

Phase 2 (COMPLETE): Intelligence layer ✅
  - Coherence validation
  - Decision reasoning (CoT)
  - Execution learning
  - 34 tests, 92%+ coverage

Phase 3 (PLANNED): Advanced features
  - ML-based prediction
  - Domain-specific rules
  - Advanced analytics
  - Optimization engine
  - Feedback loops
```

---

## Phase 3 Tasks

### Task 1: Performance Predictor (200 lines)

**Purpose**: Predict execution time and resource usage based on story characteristics

**Components**:
- `scripts/orchestrator/performance_predictor.py` (NEW)

**Methods**:
1. `predict_duration(story_id, story_metadata)` → float (seconds)
   - Analyzes story complexity (lines of code, dependencies, test count)
   - Returns predicted duration in seconds
   - Default: 60s if no history

2. `predict_resource_usage(story_id)` → Dict
   - Predicts memory, CPU requirements
   - Returns: {memory_mb: int, cpu_percent: int, parallel_safe: bool}

3. `train_on_execution(story_id, actual_duration, actual_resources)`
   - Updates model with actual execution data
   - Enables online learning

4. `get_confidence_score(prediction)`
   - Returns confidence (0.0-1.0) based on data points used
   - <5 samples: low (0.3)
   - 5-20 samples: medium (0.6)
   - 20+ samples: high (0.9)

**Tests**: 8 test cases
- `test_predict_duration_default`
- `test_predict_duration_from_history`
- `test_predict_resources`
- `test_training_improves_prediction`
- `test_confidence_score_increases`
- etc.

**Acceptance Criteria**:
- Predictions within ±20% for stories with 10+ samples
- Confidence scores reflect data availability
- Online learning working
- Coverage: 85%+

---

### Task 2: Domain-Specific Rules Engine (300 lines)

**Purpose**: Allow custom coherence checks and validation rules per domain

**Components**:
- `scripts/orchestrator/domain_rules.py` (NEW)

**Methods**:
1. `DomainRulesEngine.__init__(domain_name, rules_config)`
   - Load rules from config YAML
   - Support multiple domains (backend, frontend, data, etc.)

2. `register_check(name, check_function, severity)`
   - Register custom coherence check
   - Severity: ok, medium, high, critical

3. `validate_output(tool_name, output)` → Dict
   - Run domain-specific validation
   - Example: Check API endpoints follow naming conventions
   - Example: Verify database migrations are reversible

4. `get_applicable_rules(context)` → List[Rule]
   - Context: {domain, role, phase, story_type}
   - Return rules matching context

**Rule Format**:
```yaml
domains:
  backend:
    name: Backend Domain Rules
    rules:
      - name: api_endpoint_naming
        description: Endpoints follow /api/v1/resource pattern
        severity: high
        check_function: validate_api_endpoints
        applies_to: [RUN_ARCHITECT, RUN_DEV]

      - name: database_migrations
        description: Migrations include up/down steps
        severity: high
        check_function: validate_migrations
        applies_to: [RUN_DEV]

      - name: test_coverage_backend
        description: Backend tests >=80% coverage
        severity: medium
        check_function: validate_test_coverage
        applies_to: [RUN_QA]
```

**Tests**: 10 test cases
- `test_load_domain_rules`
- `test_register_custom_check`
- `test_validate_api_endpoints`
- `test_validate_migrations`
- `test_context_filtering`
- etc.

**Acceptance Criteria**:
- Custom rules loadable from config
- Multiple domains supported
- Context-aware rule selection
- Domain validation working
- Coverage: 88%+

---

### Task 3: Execution Analytics Engine (350 lines)

**Purpose**: Detailed analysis and reporting of execution patterns

**Components**:
- `scripts/orchestrator/analytics_engine.py` (NEW)

**Methods**:
1. `AnalyticsEngine.__init__(execution_history_dir)`
   - Load all past executions
   - Build aggregated statistics

2. `get_story_patterns()` → Dict
   - Analyze success/failure patterns per story type
   - Return: {story_type: {success_rate, avg_duration, common_errors}}

3. `get_bottleneck_analysis()` → List[Dict]
   - Identify slowest phases
   - Identify most-failing story types
   - Return: [{phase, bottleneck_metric, impact_percent}]

4. `get_role_performance(role)` → Dict
   - Success rate, avg duration, error distribution
   - Recommendations for improvement

5. `get_execution_timeline()` → List[Dict]
   - Chronological view of all executions
   - Duration, success/failure, key metrics

6. `export_report(format='html')` → bytes
   - Generate HTML/PDF report
   - Include charts, tables, recommendations

7. `predict_success_probability(story_metadata)` → float (0.0-1.0)
   - Based on similar past stories
   - Returns success probability

**Report Includes**:
- Success rate by story type
- Duration distributions
- Common failure modes
- Phase bottlenecks
- Recommendations for optimization
- Trend analysis (improving/degrading)

**Tests**: 12 test cases
- `test_story_pattern_analysis`
- `test_bottleneck_detection`
- `test_role_performance`
- `test_timeline_generation`
- `test_report_export`
- `test_success_probability`
- etc.

**Acceptance Criteria**:
- Accurate pattern detection
- Bottleneck analysis useful
- Success probability >70% accuracy
- HTML reports readable
- Coverage: 85%+

---

### Task 4: Intelligent Parallelism Scheduler (250 lines)

**Purpose**: Dynamic parallelism based on real-time resource availability

**Components**:
- `scripts/orchestrator/parallelism_scheduler.py` (NEW)

**Methods**:
1. `ParallelismScheduler.__init__(system_monitor)`
   - Initialize with resource monitor
   - Track available CPU, memory

2. `get_safe_parallelism()` → int
   - Check current resource usage
   - Return max safe parallel stories
   - Consider: available CPU, memory, I/O

3. `should_throttle()` → bool
   - Return True if system under stress
   - CPU >80%, Memory >85%, I/O >75%

4. `estimate_parallelism_for_batch(story_ids)` → int
   - Consider specific story resource requirements
   - Return safe parallelism for this batch

5. `adaptive_parallelism_step()` → int
   - Gradually increase parallelism if stable
   - Decrease if errors spike
   - Returns recommended parallelism

**Monitoring**:
- CPU usage
- Memory available
- Disk I/O
- Network bandwidth (if applicable)
- Error rates

**Tests**: 8 test cases
- `test_safe_parallelism_calculation`
- `test_throttling_under_stress`
- `test_adaptive_increase`
- `test_adaptive_decrease`
- etc.

**Acceptance Criteria**:
- Safe parallelism within 10% of actual capacity
- No OOM errors with adaptive scheduler
- Performance improved 15%+
- Coverage: 80%+

---

### Task 5: Caching Layer (200 lines)

**Purpose**: Intelligent caching to reduce redundant computation

**Components**:
- `scripts/orchestrator/cache_manager.py` (NEW)

**Methods**:
1. `CacheManager.__init__(cache_dir, ttl_seconds)`
   - Initialize with cache location
   - Set time-to-live for entries

2. `cache_coherence_check(ba_output, po_output)` → Dict
   - Cache coherence check results
   - Return cached result if inputs unchanged
   - TTL: 1 hour

3. `cache_story_predictions(story_id, predictions)` → None
   - Cache duration/resource predictions
   - Invalidate on story update

4. `invalidate_cache(pattern)` → None
   - Selective cache invalidation
   - Pattern: "coherence:*", "predict:story_123"

5. `get_cache_stats()` → Dict
   - Hit rate, miss rate, avg overhead
   - Return: {hits, misses, hit_rate, avg_lookup_ms}

**Cache Keys**:
- `coherence:{ba_hash}:{po_hash}` → alignment result
- `predict:story:{id}` → duration/resource prediction
- `optimize:role:{name}` → backoff strategy
- `analytics:pattern:{type}` → pattern analysis

**Tests**: 8 test cases
- `test_cache_coherence_hit`
- `test_cache_coherence_miss`
- `test_invalidation`
- `test_ttl_expiration`
- `test_cache_stats`
- etc.

**Acceptance Criteria**:
- Cache hit rate >60%
- Lookup time <1ms
- Memory efficient (LRU eviction)
- Coverage: 82%+

---

### Task 6: Feedback Loop Integration (200 lines)

**Purpose**: Collect feedback from agents and improve future decisions

**Components**:
- `scripts/orchestrator/feedback_loop.py` (NEW)

**Methods**:
1. `FeedbackCollector.__init__()`
   - Initialize feedback storage

2. `record_agent_feedback(role, story_id, feedback_dict)`
   - Record feedback from agents
   - feedback: {helpful: bool, suggestions: str, errors: []}

3. `record_user_feedback(story_id, rating, comment)`
   - Manual feedback from users/reviewers
   - rating: 1-5 stars

4. `analyze_feedback_patterns()` → Dict
   - Find common issues
   - Return: {issue: count, suggestions: []}

5. `suggest_improvements(context)` → List[str]
   - Based on feedback patterns
   - Return actionable improvement suggestions

6. `apply_learned_rules()`
   - Update policies based on feedback
   - Adjust parallelism, retry strategies, etc.

**Feedback Types**:
- Agent feedback: "This story requirement was unclear"
- User feedback: "Implementation doesn't match requirements"
- Execution feedback: "Story failed due to resource limits"
- Performance feedback: "This phase is too slow"

**Tests**: 8 test cases
- `test_record_feedback`
- `test_pattern_detection`
- `test_improvement_suggestions`
- `test_apply_learned_rules`
- etc.

**Acceptance Criteria**:
- Feedback collection working
- Patterns accurately detected
- Suggestions actionable
- Coverage: 80%+

---

### Task 7: Advanced CoT Logging (200 lines)

**Purpose**: Enhanced chain-of-thought with hierarchical reasoning

**Components**:
- Enhance `scripts/orchestrator/cot_logger.py` (add 200 lines)

**New Methods**:
1. `start_sub_chain(parent_id, name)` → str (chain_id)
   - Start nested chain within phase
   - Return unique chain ID

2. `log_alternative_analysis(alternatives, scores, chosen)`
   - Log analysis of multiple options
   - Why one was chosen over others

3. `log_constraint_check(constraint_name, satisfied, reason)`
   - Log constraint evaluations
   - Track which constraints were satisfied/violated

4. `export_decision_tree(format='json')` → Dict
   - Export complete decision tree
   - Show decision hierarchy
   - Include confidence scores

5. `generate_reasoning_summary()` → str
   - Generate natural language summary
   - "Selected S1 because: ready (deps satisfied), escalation OK, retries available"

**Hierarchical CoT Structure**:
```json
{
  "step": 5,
  "phase": "DEVELOPMENT",
  "reasoning": [
    {
      "decision": "Batch selection",
      "alternatives": {
        "option_a": {
          "stories": ["S1", "S2"],
          "score": 0.85,
          "reason": "Good parallelism"
        },
        "option_b": {
          "stories": ["S1"],
          "score": 0.60,
          "reason": "Conservative"
        }
      },
      "chosen": "option_a"
    }
  ],
  "sub_chains": [
    {"id": "ready_check", "decisions": 2},
    {"id": "escalation_check", "decisions": 1}
  ]
}
```

**Tests**: 8 test cases
- `test_sub_chain_creation`
- `test_alternative_analysis`
- `test_constraint_logging`
- `test_hierarchical_export`
- `test_reasoning_summary`
- etc.

**Acceptance Criteria**:
- Hierarchical structure working
- Alternative analysis clear
- Summary generation accurate
- Coverage: 85%+

---

### Task 8: Adaptive Policy Engine Enhancement (200 lines)

**Purpose**: Policies that adapt based on execution patterns

**Components**:
- Enhance `scripts/orchestrator/policy_engine.py` (add 200 lines)

**New Methods**:
1. `evaluate_dynamic_escalation(story_id, context)` → Optional[str]
   - Escalation threshold adapts based on success rate
   - If role success rate <50%: lower escalation threshold
   - If success rate >90%: higher threshold

2. `learn_optimal_retry_limit(role, story_type)` → int
   - Analyze when retries stop being useful
   - Return optimal retry count
   - Dev stories: typically 2-3
   - QA stories: typically 1-2

3. `adjust_parallelism_factor(phase)` → float
   - Adjust max parallelism multiplier
   - Based on current system state
   - 0.5x during system stress
   - 2.0x when resources abundant

4. `should_escalate_immediately(story_id, attempt)` → bool
   - Some stories should escalate immediately
   - Based on historical failure patterns

**Dynamic Policies**:
- Escalation threshold adapts (attempts 2→3→2 based on success)
- Retry limits per role (dev: 3, qa: 2, architect: 1)
- Parallelism factors (min 1, max 10, adaptive)
- Backoff strategies (exponential/linear based on role)

**Tests**: 10 test cases
- `test_dynamic_escalation_threshold`
- `test_learn_optimal_retry`
- `test_parallelism_adjustment`
- `test_immediate_escalation`
- etc.

**Acceptance Criteria**:
- Policies adapt to actual performance
- Escalation fairer and more effective
- Retry optimization working
- Coverage: 85%+

---

### Task 9: Integration & Configuration (150 lines)

**Purpose**: Integrate Phase 3 components into orchestration pipeline

**Components**:
- Update `scripts/orchestrator/v2_runtime.py` (add integration)
- Update `scripts/orchestrator/__init__.py` (export Phase 3 classes)
- Update `config.yaml` (Phase 3 configuration)

**Integration Points**:
1. Initialize Phase 3 components in `run_orchestrator_v2()`
   ```python
   performance_predictor = PerformancePredictor()
   domain_rules = DomainRulesEngine(domain)
   analytics = AnalyticsEngine()
   scheduler = ParallelismScheduler()
   ```

2. Use predictions in planning
   ```python
   predicted_duration = performance_predictor.predict_duration(story_id)
   safe_parallelism = scheduler.get_safe_parallelism()
   ```

3. Apply domain rules in coherence
   ```python
   domain_issues = domain_rules.validate_output(tool, output)
   coherence_issues.extend(domain_issues)
   ```

4. Collect feedback
   ```python
   feedback.record_agent_feedback(role, story_id, feedback)
   ```

**Config.yaml additions**:
```yaml
orchestrator_v2:
  phase3_features:
    performance_prediction: true
    domain_rules: true
    analytics: true
    intelligent_scheduling: true
    caching: true
    feedback_loops: true

performance:
  predictor_enabled: true
  min_samples_for_prediction: 5

domain_rules:
  enabled: true
  domain: backend  # or frontend, data, etc.

analytics:
  enabled: true
  report_format: html

parallelism:
  adaptive: true
  min: 1
  max: 10
  stress_threshold: 0.8

cache:
  enabled: true
  ttl_seconds: 3600
  max_size_mb: 500
```

**Tests**: 5 test cases
- `test_phase3_initialization`
- `test_all_components_working`
- `test_config_loading`
- `test_backward_compatibility`
- `test_phase2_compatibility`

**Acceptance Criteria**:
- All Phase 3 components integrated
- Config working
- Phase 2 still functional
- No breaking changes
- Coverage: 85%+

---

### Task 10: Advanced E2E Tests & Documentation (400 lines)

**Purpose**: Comprehensive testing and documentation for Phase 3

**Components**:
- `tests/test_orchestrator_v2_phase3_e2e.py` (NEW, 400 lines)
- `docs/ORCHESTRATOR_V2_PHASE3_COMPLETION.md` (NEW)

**Test Suites**:
1. **TestPerformancePredictor** (10 tests)
   - `test_predict_duration_default`
   - `test_predict_duration_accurate`
   - `test_predict_resources`
   - `test_confidence_increases`
   - etc.

2. **TestDomainRulesEngine** (12 tests)
   - `test_load_domain_rules`
   - `test_api_endpoint_validation`
   - `test_migration_validation`
   - `test_context_filtering`
   - etc.

3. **TestAnalyticsEngine** (10 tests)
   - `test_pattern_analysis`
   - `test_bottleneck_detection`
   - `test_success_probability`
   - `test_report_generation`
   - etc.

4. **TestParallelismScheduler** (8 tests)
   - `test_safe_parallelism`
   - `test_throttling`
   - `test_adaptive_scheduling`
   - etc.

5. **TestCacheManager** (8 tests)
   - `test_cache_hit`
   - `test_cache_miss`
   - `test_invalidation`
   - `test_stats`
   - etc.

6. **TestFeedbackLoop** (8 tests)
   - `test_record_feedback`
   - `test_pattern_analysis`
   - `test_apply_improvements`
   - etc.

7. **TestAdvancedCoT** (8 tests)
   - `test_hierarchical_chains`
   - `test_alternative_analysis`
   - `test_summary_generation`
   - etc.

8. **TestAdaptivePolicy** (10 tests)
   - `test_dynamic_escalation`
   - `test_retry_optimization`
   - `test_parallelism_adaptation`
   - etc.

9. **TestIntegration** (6 tests)
   - `test_all_phase3_features`
   - `test_with_phase2`
   - `test_phase1_compatibility`
   - `test_performance_improvement`
   - etc.

**Target**: 80+ tests, 90%+ coverage

**Documentation**:
- Usage guide for each component
- Configuration examples
- Best practices
- Migration guide from Phase 2
- Performance benchmarks
- Troubleshooting guide

**Acceptance Criteria**:
- 80+ tests, all passing
- 90%+ coverage across Phase 3
- Zero regressions to Phase 1/2
- Documentation complete
- Performance benchmarked

---

## Implementation Timeline

### Week 1: Foundation
- Task 1: Performance Predictor
- Task 5: Caching Layer
- Task 9: Integration setup (partial)

### Week 2: Intelligence
- Task 2: Domain Rules Engine
- Task 3: Analytics Engine
- Task 9: Integration (continue)

### Week 3: Optimization & Feedback
- Task 4: Intelligent Scheduler
- Task 6: Feedback Loops
- Task 7: Advanced CoT

### Week 4-5: Polish & Release
- Task 8: Adaptive Policies
- Task 10: E2E Tests & Docs
- Integration testing
- Performance benchmarking
- Production rollout

---

## Success Criteria Phase 3

### Functional
- [ ] All 10 tasks completed
- [ ] Performance predictor accurate (±20%)
- [ ] Domain rules customizable
- [ ] Analytics reports useful
- [ ] Feedback loops operational
- [ ] Adaptive policies effective

### Quality
- [ ] 80+ tests, all passing
- [ ] 90%+ coverage (Phase 3 modules)
- [ ] Zero regressions (Phase 1/2)
- [ ] Documentation complete
- [ ] Performance improved 20%+

### Performance
- [ ] Predictions <100ms
- [ ] Domain rule checks <50ms
- [ ] Analytics queries <500ms
- [ ] Overall overhead <300ms per step

### Integration
- [ ] Phase 1/2 fully compatible
- [ ] Config-driven toggles
- [ ] Seamless upgrades
- [ ] Production-ready

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| ML predictions inaccurate | High | Use conservative defaults, wide confidence intervals |
| Domain rules too strict | Medium | Customizable severity, non-blocking checks |
| Caching invalidation bugs | High | Comprehensive cache tests, audit trails |
| Adaptive policies oscillate | Medium | Gradual adaptation, hysteresis |
| Performance regression | High | Continuous profiling, benchmarks |

---

## Dependencies

### On Phase 2
- ✅ Coherence Checker (extend with domain rules)
- ✅ CoT Logger (enhance with hierarchy)
- ✅ Optimizer (base for adaptive policies)

### External
- Python 3.11+
- pytest >= 8.0
- Additional: scikit-learn (optional, for ML predictions)

---

## Estimated Effort

| Task | Lines | Complexity | Hours |
|------|-------|-----------|-------|
| 1. Performance Predictor | 200 | High | 20 |
| 2. Domain Rules | 300 | High | 24 |
| 3. Analytics | 350 | High | 28 |
| 4. Parallelism Scheduler | 250 | High | 20 |
| 5. Caching | 200 | Medium | 16 |
| 6. Feedback Loops | 200 | Medium | 16 |
| 7. Advanced CoT | 200 | Medium | 16 |
| 8. Adaptive Policies | 200 | Medium | 16 |
| 9. Integration | 150 | Medium | 12 |
| 10. E2E Tests & Docs | 400 | Medium | 32 |

**Total**: ~2,450 lines, ~200 hours, 4-5 weeks

---

## Next Steps

1. **Review & Approve** this Phase 3 plan
2. **Identify domain-specific rules** for your use cases
3. **Prepare test data** for analytics engine
4. **Start Phase 3a** (Performance Predictor + Caching)
5. **Iterate** based on real-world usage patterns

---

**Phase 3 Plan Status**: ✅ **READY FOR REVIEW**

All tasks documented, scoped, and ready to begin upon approval.

---

*Phase 3 Plan: December 10, 2025*
*Generated by: Claude Code*
*Status: 📋 PLANNING*
