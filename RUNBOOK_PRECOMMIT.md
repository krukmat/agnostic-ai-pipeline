# Pre-Commit Validation Runbook — Graph RAG Phase 1+

**Propósito**: Checklist para asegurar calidad ANTES de realizar commit
**Audiencia**: Developers trabajando en Graph RAG y módulos relacionados
**Actualizado**: 2026-02-06 (Post-remediación AP-1, AP-2, AP-3)

---

## Quick Start (5 minutos)

```bash
# 1. Run all tests
.venv/bin/pytest tests/ -v

# 2. Check complexity
pip install radon  # if not installed
radon cc graph_rag/ --min B

# 3. Run linting (if configured)
ruff check graph_rag/
black graph_rag/ --check

# If all ✅ pass → Ready to commit
```

---

## Full Validation Checklist

Use this for any commit affecting Graph RAG modules or tests.

### Phase 0: Pre-Development Setup
- [ ] Create feature branch: `git checkout -b feature/<name>`
- [ ] No uncommitted changes from previous work
- [ ] `.venv` is activated: `source .venv/bin/activate`

### Phase 1: Tests (Unit + Integration)
```bash
.venv/bin/pytest tests/ -v
```

Validate:
- [ ] **All unit tests pass**: `tests/test_graph_rag_*.py` (marked with `@pytest.mark.unit`)
- [ ] **No new test failures**: Compare with baseline (should be same or more)
- [ ] **Integration tests pass** (if modified integration logic): `@pytest.mark.integration`
- [ ] **No `assert True` statements**: Tests must verify real behavior
- [ ] **No mocks of internal logic**:
  - ❌ `mock_engine.query`  (engine is internal to test)
  - ✅ `mock_ollama_api`    (external dependency)

**Common failures to check**:
- `AttributeError: 'PipelineIngestion' has no attribute '_should_ingest_file'`
  → Helper not extracted properly
- `AssertionError: Should have 1 hash after first ingest`
  → State not persisted correctly
- `TypeError: object NoneType has no len()`
  → Missing validation or default

### Phase 2: Complexity Metrics

```bash
# Install if needed:
pip install radon

# Check cyclomatic complexity
radon cc graph_rag/ --min B
```

Validate for files in `graph_rag/`:
- [ ] **No CC > 10**: If function has CC > 10, requires refactor
- [ ] **Target CC ≤ 5 for new functions**:
  - Example: `_should_ingest_file()` should be CC ≤ 3
  - Example: `_resolve_policy()` should be CC ≤ 3
- [ ] **Document if CC 6-10**: Add comment explaining complexity

**Sample output interpretation**:
```
graph_rag/ingestion.py
    _ingest_directory 5     ✅ Acceptable
    _should_ingest_file 1   ✅ Good
    _build_file_metadata 1  ✅ Good

graph_rag/retrieval.py
    retrieve_for_role 4     ✅ Acceptable
    _resolve_policy 2       ✅ Good

graph_rag/engine.py
    query 5                 ✅ Acceptable
```

### Phase 3: Configuration Validation

If you modified `config.yaml`, `GraphRAGConfig`, or config-dependent code:

```python
# Run this in Python REPL or test:
from graph_rag.config import GraphRAGConfig
import yaml

# Load your config
with open("config.yaml") as f:
    config_dict = yaml.safe_load(f)

# Initialize and validate
cfg = GraphRAGConfig(config_dict.get("graph_rag", {}))
cfg.validate_schema()  # Must not raise ValueError

print(f"✓ Config validated: model={cfg.llm_model}, top_k={cfg.top_k}")
```

Validate:
- [ ] **Single source of truth**: No defaults duplicated in 3 places
  - [ ] Default in `GraphRAGConfig.DEFAULT_CONFIG`
  - [ ] NOT hardcoded in `engine.py`
  - [ ] NOT hardcoded in `retrieval.py`
- [ ] **Property accessors used**: `cfg.llm_model` not `cfg["llm_model"]`
- [ ] **`validate_schema()` passes**: No ValueError on startup
- [ ] **Valid ranges**:
  - [ ] `top_k` is between 1-100
  - [ ] `embedding_dim` is positive integer
  - [ ] `default_mode` is one of [naive, local, global, hybrid, mix]
  - [ ] `context_budget_chars` is positive integer
  - [ ] `context_truncation_strategy` is one of [hierarchical, truncate]

### Phase 4: Code Quality Checks

```bash
# Optional: Run if configured
ruff check graph_rag/
black graph_rag/ --check
mypy graph_rag/ --strict  # If type hints enabled
```

Validate:
- [ ] **No undefined variables**: Ruff reports 0 errors
- [ ] **Imports organized**: Black formatting correct
- [ ] **Type hints added to new functions** (optional, but recommended)

### Phase 5: Feature Promises (Important!)

If you added a new feature or modified config:

- [ ] **Feature is 100% implemented**:
  - ❌ `auto_ingest: true` without hooks → Don't commit
  - ✅ `auto_ingest: false` with comment "manual indexing" → OK
- [ ] **Feature is tested**: E2E test exists for critical features
- [ ] **Feature is documented**:
  - Docstring in function
  - Comment in config.yaml explaining what it does
  - Entry in MEMORY.md or LESSONS_LEARNED_PHASE1.md if relevant

### Phase 6: Documentation

If code is non-obvious:

Validate:
- [ ] **High CC functions have comments**:
  ```python
  # Extract _should_ingest_file to reduce CC
  # Main loop: 1. Check file validity 2. Build metadata 3. Ingest
  if not self._should_ingest_file(file):
      continue
  ```
- [ ] **Tech debt documented** (if applicable):
  ```python
  # TECH DEBT: High CC in __init__ (CC=61)
  # Cause: Multiple provider handling
  # Priority: Medium (not blocking Phase 1)
  ```
- [ ] **Policy decisions explained**:
  ```python
  # Design choice: preserve source diversity in dedup
  # Because: helps identify code reuse patterns
  # Tradeoff: slightly larger ingestion state file
  ```

### Phase 7: Makefile Targets (if modified)

If you modified Makefile graph_rag targets:

```bash
make rag-index
make rag-query QUERY="test"
make rag-visualize
```

Validate:
- [ ] `make rag-index` runs without errors
- [ ] `make rag-query` respects MODE parameter
- [ ] `make rag-visualize` produces output

---

## Pre-Commit Script (Optional Automation)

Save as `.git/hooks/pre-commit`:

```bash
#!/bin/bash
set -e

echo "🔍 Running pre-commit checks..."

# 1. Tests
echo "📋 Running tests..."
.venv/bin/pytest tests/ -q || exit 1

# 2. Complexity
echo "⚙️ Checking complexity..."
python -m radon cc graph_rag/ --min B --fail-under=11 || exit 1

# 3. Config validation
echo "⚙️ Validating config..."
python -c "
from graph_rag.config import GraphRAGConfig
import yaml
with open('config.yaml') as f:
    cfg = GraphRAGConfig(yaml.safe_load(f).get('graph_rag', {}))
    cfg.validate_schema()
" || exit 1

echo "✅ All pre-commit checks passed!"
exit 0
```

Enable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Troubleshooting

### "AssertionError: tests are failing"
1. Run single test: `.venv/bin/pytest tests/test_graph_rag_ingestion.py::test_deduplication_skips_same_hash -v`
2. Check error message for specific assertion
3. If integration test: ensure Ollama is running
4. Compare with upstream: `git diff main...HEAD`

### "radon cc reports CC > 10"
1. Identify high-CC function
2. Extract helpers (see `_should_ingest_file` pattern)
3. Add TDD test first
4. Implement extraction
5. Rerun radon

### "Config validation fails"
1. Check exact error: `GraphRAGConfig(config_dict).validate_schema()`
2. Fix config value (e.g., `top_k: 150` → `top_k: 60`)
3. Or update validation logic if legitimate change
4. Document rationale if extending allowed ranges

### "Mock test failure"
1. Check if you're mocking internal logic
2. Replace with `LocalEngine*` pattern from integration tests
3. Verify test validates actual behavior, not mock behavior

---

## Success Criteria

✅ Ready to commit when:

```
✅ 44/44+ tests pass (no failures or skips without reason)
✅ All modified graph_rag/ files: CC ≤ 10 (target ≤ 5)
✅ No `assert True` in tests
✅ No mock of internal components (retrieval, ingestion)
✅ Config validates without error
✅ Single source of truth for defaults
✅ Feature is 100% implemented (not "pending")
✅ Code has necessary comments for clarity
✅ Makefile targets (if modified) work
```

---

## Quick Reference

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| Unit Tests | `pytest tests/ -k unit -v` | All pass ✅ |
| Integration Tests | `pytest tests/ -k integration -v` | All pass ✅ |
| Full Tests | `pytest tests/ -v` | All pass ✅ |
| Complexity | `radon cc graph_rag/ --min B` | CC ≤ 10 |
| Config | `python -c "GraphRAGConfig(...).validate_schema()"` | No error |
| Linting | `ruff check graph_rag/` | 0 errors |
| Format | `black graph_rag/ --check` | Correct format |

---

## Related Documents

- **MEMORY.md**: Coding standards for Graph RAG
- **LESSONS_LEARNED_PHASE1.md**: Anti-patterns and how to avoid them
- **PLAN_ANTIPATTERNS_REMEDIATION.md**: Detailed remediation plan
- **AUDIT_PHASE1_GRAPH_RAG_EXTERNAL_FINDINGS.md**: External audit (source of truth)

---

## Version History

| Date | Author | Changes |
|------|--------|---------|
| 2026-02-06 | Claude Code (AP-3-T3) | Initial runbook from remediation lessons |

**Contact**: For questions on standards or runbook updates, refer to MEMORY.md
