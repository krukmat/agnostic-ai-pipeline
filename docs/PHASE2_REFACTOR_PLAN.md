# Phase 2 — Role Refactor Plan (Architect, PO, BA)

Status: Proposed (depends on Phase 1 completion)
Scope: Refactor architecture and code quality in Architect, Product Owner, and Business Analyst roles, applying SRP/SoC, DIP, DRY patterns learned from Phase 1.

## 0) Executive Summary

- **Context**: Phase 1 refactored driver layer + Dev/QA roles. Phase 2 applies lessons learned to remaining roles.
- **Issues** (high level)
  - Monolithic flows in `scripts/run_architect.py` (**926 lines** - largest role)
  - YAML sanitization duplicated between Architect and PO (~88 lines each)
  - Story management scattered across Architect and orchestrator
  - Complexity classification tightly coupled to Architect main flow
  - Config loading patterns repeated across all roles
  - Product Owner (371 lines) and BA (112 lines) also have refactor opportunities
- **Goal**
  - Apply Phase 1 patterns (SRP/SoC/DIP/DRY) to Architect, PO, BA
  - Extract shared utilities: YAML sanitizer, story manager, config helpers
  - Improve testability for DSPy module integration
  - Target: Architect 926→~400 lines, PO 371→~200 lines
- **Scope**: Refactor run_architect.py, run_product_owner.py, run_ba.py; extract shared utilities

## 1) Principles, Scope, Non‑Goals

- **Principles**: Same as Phase 1 — SRP/SoC, DIP/testability, DRY/Clean, Defensive/Security, KISS/YAGNI
- **Scope** (Phase 2 - primary refactor targets):
  - `scripts/run_architect.py` (926 lines - **P0 critical**)
  - `scripts/run_product_owner.py` (371 lines - **P1 high**)
  - `scripts/run_ba.py` (112 lines - **P2 medium**)
  - `scripts/utils/*` (new shared utilities: yaml_sanitizer.py, story_manager.py, config_loader.py)
  - `scripts/architect/*` (new modules: complexity_classifier.py, dataset_generator.py)
  - `tests/*` (architect/, product_owner/, ba/, utils/)
- **Dependencies**:
  - Phase 1 must be completed and merged
  - Shared patterns from Phase 1 (runner.py, logging format, DIP patterns) must be stable
- **Non‑Goals**:
  - New features or DSPy/MiPRO algorithm changes
  - Changing LLM prompt content (only refactor how prompts are loaded/used)
  - Breaking existing DSPy integration (preserve module signatures)

## 2) Deferred Role Scripts (detailed analysis)

### Priority Matrix

| Script | Lines | Functions | Complexity | Priority | Estimated Effort |
|--------|-------|-----------|------------|----------|------------------|
| **run_architect.py** | 926 | 28+ | High | **P0** | 3 weeks |
| **run_product_owner.py** | 371 | 15+ | Medium | **P1** | 1 week |
| **run_ba.py** | 112 | 8+ | Low | **P2** | 0.5 weeks |
| **run_orchestrator.py** | 34 | 3 | Minimal | **P3** | No refactor needed |

### Architect Role Issues (run_architect.py - 926 lines)

**Current responsibilities** (violations of SRP):
1. **Config management** (`_load_config()`, `_normalize_bool()`, `_use_dspy_architect()`)
2. **Complexity classification** with LLM + caching (`classify_complexity_with_llm()`, `_complexity_cache_key()`, `parse_complexity_response()`, `fallback_complexity()`)
3. **DSPy pipeline orchestration** (`_run_dspy_pipeline()` - stories → architecture → PRD)
4. **YAML sanitization** (`_sanitize_yaml_block()`, `sanitize_yaml()`, `_normalize_inline_json()`, `_strip_markdown_emphasis()`)
5. **Story lifecycle management** (`load_stories()`, `save_stories()`, `mark_story_todo()`)
6. **QA failure context** (`extract_qa_failure_context()`, `try_programmatic_adjustment()`)
7. **Dataset generation** (`cli_dataset()`, `cli_ba_normalize()`, `cli_ba_remaining()`)
8. **Prompt template loading** (`get_architect_prompt()` with tier selection)
9. **Main execution flow** (`run_architect_job()` - 200+ lines)

**Key problems**:
- Hard to test DSPy integration (no DIP)
- YAML sanitization duplicated with PO (~88 lines each)
- Complexity classifier has hardcoded cache, not injectable
- Story management should be shared utility (orchestrator also needs it)
- Dataset generation mixed with main role logic

**Line-by-line breakdown** (approximate):
- Config/complexity: ~120 lines
- YAML sanitization: ~150 lines
- Story management: ~80 lines
- QA failure handling: ~100 lines
- Dataset generation: ~120 lines
- DSPy pipeline: ~80 lines
- Main flow: ~200 lines
- Helpers/utils: ~76 lines

### Product Owner Role Issues (run_product_owner.py - 371 lines)

**Current responsibilities**:
1. **YAML normalization** (`_normalize_po_yaml()` - 88 lines, similar to Architect's sanitization)
2. **Concept extraction** (`extract_original_concept()`)
3. **Vision validation** (main flow with DSPy module)
4. **Review generation** (product_owner_review.yaml output)

**Key problems**:
- `_normalize_po_yaml()` overlaps 70% with Architect's `sanitize_yaml()`
- Should use shared `scripts/utils/yaml_sanitizer.py`
- DSPy module not injected (DIP violation)

**DRY opportunity**: Extract YAML normalization to shared utility saves ~150 lines total (88 PO + ~80 Architect)

### BA Role Issues (run_ba.py - 112 lines)

**Current responsibilities**:
1. Config loading (pattern similar to other roles)
2. LLM interaction (concept → requirements.yaml)
3. Requirements generation

**Key problems**:
- Config loading duplicated
- LLM client instantiation pattern repeated
- Simpler than others, but inconsistent with Phase 1 patterns

## 3) Work Plan (Phase 2.x)

### 2.1 — Extract shared utilities (DRY foundation)

**Status**: 🔍 IN REVIEW (external validation pending)

**Changes**:
- `config_loader.py` (complejidad: baja). Helpers defensivos (`load_config_base`, `load_config_with_drivers`, `load_qa_config`, `normalize_bool`) y tests en `tests/utils/test_config_loader.py`.
- `story_manager.py` (complejidad: media). `load_stories(recover_comments)`, `save_stories`, `mark_story_status/mark_story_todo`; tests en `tests/utils/test_story_manager.py`.
- `yaml_sanitizer.py` (complejidad: alta). `sanitize_yaml_block` (fences + dump), `sanitize_po_yaml` (backticks cleanup), `normalize_po_yaml` (Gemini quirks); tests en `tests/utils/test_yaml_sanitizer.py`.

**Deliverables**:
- `scripts/utils/yaml_sanitizer.py` (~120 lines, extracted from Architect/PO)
- `scripts/utils/story_manager.py` (~100 lines, extracted from Architect)
- `scripts/utils/config_loader.py` (~80 lines, consolidated from all roles)
- Tests: `tests/utils/test_yaml_sanitizer.py`, `test_story_manager.py`, `test_config_loader.py`

**Acceptance**:
- All existing YAML normalization tests pass with new shared utility
- Story operations work identically through new manager
- Config loading consistent across all roles

### 2.2 — Refactor Architect: extract complexity classifier

**Changes**:
- **Status**: 🔍 IN REVIEW (complejidad: alta). Nuevos módulos `scripts/architect/complexity_classifier.py` (cache inyectable, parse/fallback) y `scripts/architect/cache.py`; `run_architect.py` ahora importa el classifier desde utils; tests en `tests/architect/test_complexity_classifier.py`.
- **Create `scripts/architect/complexity_classifier.py`**:
  - Extract: `classify_complexity_with_llm()`, `parse_complexity_response()`, `fallback_complexity()`
  - Add caching interface: `ComplexityCache` protocol (injectable)
  - Default implementation: `InMemoryComplexityCache` with TTL
  - Extract prompt: `prompts/architect_complexity_classifier.md` (already exists)

**Deliverables**:
- `scripts/architect/complexity_classifier.py` (~150 lines)
- `scripts/architect/cache.py` (cache implementations)
- Tests: `tests/architect/test_complexity_classifier.py` (mock LLM, test cache)

**Acceptance**:
- Complexity classification works identically
- Cache injectable for testing (DIP)
- 90%+ coverage on classifier logic

### 2.3 — Refactor Architect: extract dataset generator

**Changes**:
- **Status**: 🔍 IN REVIEW (complejidad: media). Dataset CLI extraído a `scripts/architect/dataset_cli.py`; `run_architect.py` reducido a CLI DSPy puro (imports de dataset removidos).
- **Consolidate dataset generation** (already has separate files):
  - Move CLI commands from `run_architect.py` → `scripts/architect/dataset_cli.py`
  - Extract: `cli_dataset()`, `cli_ba_normalize()`, `cli_ba_remaining()`
  - Keep imports: `generate_architect_dataset.py`, `normalize_ba_jsonl.py` (already exist)

**Deliverables**:
- `scripts/architect/dataset_cli.py` (~100 lines, extracted from run_architect.py)
- Updated imports in run_architect.py

**Acceptance**:
- Dataset generation commands work identically
- `run_architect.py` reduced by ~120 lines

### 2.4 — Refactor Architect: main flow (SRP/SoC)

**Changes**:
- **Simplify `run_architect_job()`**:
  - Use shared `story_manager` for load/save/mark operations
  - Use shared `config_loader` for settings
  - Use shared `yaml_sanitizer` for output
  - Use injected `complexity_classifier`
  - Extract: `_build_architect_context()` (gather requirements/vision/qa-context)
  - Extract: `_select_prompt_tier()` (complexity → prompt selection)
  - Extract: `_parse_architect_response()` (LLM response → structured output)
- **Apply DIP**: Inject DSPy modules, complexity classifier, cache

**Deliverables**:
- Refactored `run_architect.py` (~400 lines, down from 926)
- Helper functions extracted to same file (following Phase 1 pattern)
- Minimal unit tests with mocked dependencies

**Acceptance**:
- `make architect` / `make plan` unchanged behavior
- All stories.yaml / epics.yaml / architecture.yaml outputs identical
- Logging follows Phase 1 format: `[ARCHITECT][complexity|stories|architecture] STATUS`

### 2.5 — Refactor Product Owner (DRY with Architect)

**Changes**:
- **Use shared `yaml_sanitizer.py`**:
  - Replace `_normalize_po_yaml()` with `sanitize_yaml_block()` from shared utility
  - Test with existing PO outputs to ensure compatibility
- **Use shared `config_loader.py`**:
  - Replace local config loading
- **Apply DIP**: Inject DSPy `ProductOwnerModule`

**Deliverables**:
- Refactored `run_product_owner.py` (~200 lines, down from 371)
- Tests: `tests/product_owner/test_po_refactored.py` (mock DSPy module)

**Acceptance**:
- `make po` unchanged behavior
- product_vision.yaml and product_owner_review.yaml outputs identical
- Logging: `[PO][vision|review] STATUS`

### 2.6 — Refactor BA (consistency with other roles)

**Changes**:
- **Use shared `config_loader.py`** for consistency
- **Apply logging format** from Phase 1: `[BA][requirements] STATUS`
- **Extract helpers** (if any) to match Dev/QA/Architect patterns
- **Apply DIP** for LLM client (if using DSPy)

**Deliverables**:
- Refactored `run_ba.py` (~100 lines, minimal changes)
- Consistent with other roles' patterns

**Acceptance**:
- `make ba` unchanged behavior
- requirements.yaml output identical
- Logging consistent with other roles

### 2.7 — Integration & testing

**Changes**:
- Full pipeline regression: `make iteration CONCEPT="test"` with all refactored roles
- Update documentation: ARCHITECTURE_PRINCIPLES.md, README.md
- Verify no behavior changes in outputs (diff against pre-refactor artifacts)

**Deliverables**:
- Integration tests: `tests/test_orchestrator_e2e.py` (full BA→PO→Architect→Dev→QA cycle)
- Updated docs

**Acceptance**:
- All pipeline commands work unchanged
- No regressions in artifact outputs (YAML diffs)
- All tests pass (Phase 1 + Phase 2)

## 4) Metrics & Acceptance Criteria

### Code Reduction Targets

| File | Before (lines) | After (lines) | Reduction | Modules Extracted |
|------|----------------|---------------|-----------|-------------------|
| run_architect.py | 926 | ~400 | 57% | complexity_classifier, dataset_cli, yaml_sanitizer, story_manager |
| run_product_owner.py | 371 | ~200 | 46% | yaml_sanitizer, config_loader |
| run_ba.py | 112 | ~100 | 11% | config_loader |
| **Total** | **1,409** | **~700** | **50%** | +5 shared/specialized modules |

### Coverage Targets

- **Shared utilities**: ≥90% (yaml_sanitizer, story_manager, config_loader)
- **Architect modules**: ≥80% (complexity_classifier, dataset_cli)
- **Role scripts**: ≥70% (run_architect, run_product_owner, run_ba with mocks)

### Logging Format (standardized with Phase 1)

- **Pattern**: `[{ROLE}][{context}] {STATUS} {details}`
- **Examples**:
  ```
  [ARCHITECT][complexity] RUN Classifying requirements complexity
  [ARCHITECT][complexity] DONE tier=medium (llm_confidence=0.85)
  [ARCHITECT][stories] RUN Generating stories and epics
  [ARCHITECT][stories] DONE 5 stories, 2 epics written to planning/stories.yaml
  [PO][vision] RUN Validating product vision
  [PO][review] DONE Alignment score: 0.92
  [BA][requirements] RUN Generating requirements from concept
  [BA][requirements] DONE requirements.yaml written
  ```

### Security & Quality

- No new shell execution patterns (already handled by Phase 1)
- Config loading centralized with validation
- YAML sanitization prevents injection attacks
- All shared utilities have defensive error handling

## 5) Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Breaking DSPy integration** | High | Preserve module signatures; add integration tests with mocked modules; test with real DSPy before merging |
| **YAML sanitization edge cases** | Medium | Comprehensive test suite with PO/Architect outputs from prod; regression tests with known-good YAMLs |
| **Story manager state corruption** | High | Atomic file writes; validation on load; backup planning/ before tests; add story schema validation |
| **Config loading changes behavior** | Medium | Validate all existing config.yaml patterns; backward compatibility tests; document any breaking changes |
| **Architect complexity (926 lines)** | High | Break into 2.2-2.4 subtasks; incremental refactor with tests at each step; allocate 3 weeks buffer |
| **Phase 1 patterns not mature** | Low | Wait for Phase 1 merge + 1-2 weeks production use before starting Phase 2; incorporate lessons learned |

## 6) Suggested Timeline (conservative estimates)

**Pre-requisites** (before starting):
- Phase 1 merged to main
- 1-2 weeks production validation of Phase 1 patterns
- Lessons learned doc from Phase 1 reviewed

**Week 1-2**: Shared utilities (2.1)
- Days 1-3: Extract yaml_sanitizer.py + tests (PO/Architect outputs)
- Days 4-6: Extract story_manager.py + tests (integration with orchestrator)
- Days 7-8: Extract config_loader.py + tests (all roles)
- Day 9-10: Buffer + integration testing

**Week 3-5**: Architect refactor (2.2-2.4) — **high complexity**
- Week 3: Complexity classifier extraction (2.2)
- Week 4: Dataset generator consolidation (2.3) + main flow refactor start (2.4)
- Week 5: Main flow refactor completion (2.4) + Architect tests
- **Risk**: May slip to Week 6

**Week 6**: Product Owner refactor (2.5)
- Days 1-3: Use shared yaml_sanitizer, refactor main flow
- Days 4-5: Tests + validation

**Week 7**: BA refactor (2.6) + Integration (2.7)
- Days 1-2: BA refactor (lightweight)
- Days 3-5: Full pipeline integration tests, regression validation, docs update

**Week 8** (buffer): Final validation & review
- Production-like testing (full iterations)
- Code review and adjustments
- Documentation finalization
- Prepare for merge

**Total**: 8 weeks (vs. Phase 1's 4 weeks)

**Dependencies**:
- 2.2-2.4 depend on 2.1 (shared utilities must be stable)
- 2.5 depends on 2.1 (yaml_sanitizer)
- 2.6 can start after 2.1 (independent of Architect/PO)
- 2.7 depends on all (2.1-2.6 complete)

## 7) Branch & PR Instructions (to execute)

- **Branch for Phase 2 implementation**:
  - Wait for Phase 1 PR to be merged to `main`
  - `git checkout main && git pull --ff-only`
  - `git checkout -b refactor-roles`  # General branch covering all phases
  - Work on Phase 2 tasks (2.1-2.7)
  - `git add -A && git commit -m "refactor(phase2): apply SRP/DIP/DRY to Architect, PO, BA roles"`
  - `git push -u origin refactor-roles`

- **Create PR to main** (GH CLI):
  ```bash
  gh pr create -B main -H refactor-roles \
    -t "Phase 2 Refactor: Architect, PO, BA roles (SRP/DIP/DRY)" \
    -b "Details in docs/PHASE2_REFACTOR_PLAN.md

  ## Summary
  - Refactored run_architect.py (926→400 lines)
  - Refactored run_product_owner.py (371→200 lines)
  - Refactored run_ba.py (112→100 lines)
  - Extracted shared utilities: yaml_sanitizer, story_manager, config_loader
  - Extracted Architect modules: complexity_classifier, dataset_cli

  ## Testing
  - All Phase 1 + Phase 2 tests pass
  - Full pipeline regression validated
  - No behavior changes in artifacts

  See: docs/PHASE2_REFACTOR_PLAN.md"
  ```

- **After merge**:
  - `git checkout main && git pull --ff-only`
  - `git branch -d refactor-roles`

## 8) Success Metrics (post-merge validation)

- ✅ **Code reduction**: 1,409 → ~700 lines (50% reduction)
- ✅ **Modules extracted**: 5 shared/specialized modules created
- ✅ **Coverage**: Shared utilities ≥90%, Architect modules ≥80%, role scripts ≥70%
- ✅ **No regressions**: All `make iteration` outputs identical (YAML diffs)
- ✅ **Logging consistent**: All roles use `[ROLE][context] STATUS` format
- ✅ **Tests pass**: Phase 1 (12+) + Phase 2 (30+) = 42+ tests
- ✅ **Production validation**: 2 weeks post-merge monitoring, no issues reported
- ✅ **Documentation**: ARCHITECTURE_PRINCIPLES.md updated, ADRs written

---

**Note**: This plan depends on Phase 1 completion. Review and update based on lessons learned from Phase 1 execution.
