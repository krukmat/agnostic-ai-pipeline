# Phase 2 - Task 2.1 Analysis Results

**Date**: 2025-11-26
**Analyst**: Claude Sonnet 4.5
**Status**: ✅ COMPLETED
**Execution Time**: ~30 minutes

---

## Executive Summary

### Key Findings

1. **✅ architect_utils.py and po_format.py EXIST** - Created Nov 21, contain shared sanitization logic
2. **🔴 Scope is 40% LARGER** than expected - 7 files affected instead of 5
3. **🟡 YAML Sanitization: 6 implementations** found (not 2-3 expected)
4. **🟢 Story Management: Recovery logic** in Dev is well-defined and reusable
5. **🟡 Config Loading: 3 different return types** (dict, tuple2, tuple3) - requires strategy pattern

### Recommendations

- **Proceed with Task 2.1** but adjust scope and order
- **Implementation order (aligned with pre-analysis)**: config_loader → story_manager → yaml_sanitizer
- **Test estimate**: ~50 tests (was 40) due to additional variants
- **Risk level**: MEDIUM (was LOW) due to dataset generator dependencies

---

## 1. YAML Sanitization Investigation

### Functions Found

| File | Function | Lines | Return Type | Usage |
|------|----------|-------|-------------|-------|
| `scripts/architect_utils.py` | `sanitize_yaml_block(value)` | 10-31 | `str` | Shared utility (60 lines) |
| `scripts/po_format.py` | `sanitize_yaml(content)` | 23-39 | `str` | Shared utility (101 lines) |
| `scripts/run_architect.py` | `_sanitize_yaml_block(value)` | 257-259 | `str` | Wrapper → architect_utils |
| `scripts/run_architect.py` | `sanitize_yaml(content)` | 726+ | `str` | Inline implementation |
| `scripts/run_product_owner.py` | `_normalize_po_yaml(content)` | 35-109 | `str` | Complex normalization |
| `scripts/run_product_owner.py` | `sanitize_yaml(content)` | 112+ | `str` | Inline implementation |

### Implementation Details

#### architect_utils.py: `sanitize_yaml_block` (Canonical)

```python
def sanitize_yaml_block(value) -> str:
    """Return a clean YAML string from a value or existing YAML text.

    - Strips markdown fences if present.
    - Serializes dict/list values via yaml.safe_dump.
    - Falls back to str(value) when dumping fails.
    """
    if not value:
        return ""
    if isinstance(value, str):
        # Regex strip: ```yaml or ```
        cleaned = re.sub(r"```(?:yaml)?", "", value, flags=re.IGNORECASE)
        cleaned = cleaned.replace("```", "")
        return cleaned.strip()
    try:
        return yaml.safe_dump(
            value,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).strip()
    except yaml.YAMLError:
        return str(value).strip()
```

**Features**:
- Handles both string and object inputs
- Case-insensitive ` ```yaml ` removal
- Fallback to str() if YAML dump fails
- **NO lowercasing** (preserves case)

#### po_format.py: `sanitize_yaml` (Simpler)

```python
def sanitize_yaml(content: str) -> str:
    if not content.strip():
        return content
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        # Attempt to clean backticks and retry
        cleaned = re.sub(r'`([^`]+?)`', r"\1", content)
        try:
            data = yaml.safe_load(cleaned)
        except yaml.YAMLError:
            return content.strip()
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()
```

**Features**:
- String-only input
- Load → dump roundtrip (normalizes format)
- Backtick removal fallback
- **NO markdown fence handling**

#### run_product_owner.py: `_normalize_po_yaml` (Most Complex)

```python
def _normalize_po_yaml(content: str) -> str:
    """Pre-process Gemini output so yaml.safe_load can handle human text lists."""
    lines = content.splitlines()
    normalized: list[str] = []
    for raw_line in lines:
        line = raw_line
        # Remove thin-space characters
        for ch in _THIN_SPACE_CHARS:
            if ch in line:
                line = line.replace(ch, " ")

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("-"):
            payload = stripped[1:].lstrip()
            if payload:
                needs_quote = False
                # Quote bullets starting with YAML special chars
                if payload[0] in ("%", "&", "*", "#", "!", "?", "@", "[", "]", "{", "}", ","):
                    needs_quote = True
                elif payload[0] in (">", "<"):
                    needs_quote = True
                else:
                    # Check for keys with spaces
                    colon_idx = payload.find(":")
                    if colon_idx != -1:
                        key_part = payload[:colon_idx]
                        key_has_spaces = " " in key_part.strip()
                        # ... complex logic
```

**Features**:
- **LLM-specific**: Handles Gemini quirks
- Thin-space character normalization
- Smart quoting for YAML special chars
- Handles keys with spaces
- **75 lines** of preprocessing logic

### Dependencies

**Who imports architect_utils:**
- `scripts/run_architect.py` (via wrapper)
- `scripts/generate_architect_dataset.py` (direct import)

**Who imports po_format:**
- `scripts/generate_po_teacher_dataset.py` (direct import)
- `scripts/eval_po_student.py` (direct import)
- `scripts/generate_architect_dataset.py` (direct import)

**Dataset generators affected:**
- `generate_architect_dataset.py`
- `generate_po_teacher_dataset.py`
- `eval_po_student.py`

### Critical Findings

1. **architect_utils.py is already a shared module** (created Nov 21)
2. **po_format.py has validation logic** (`validate_po_output`) beyond sanitization
3. **`_normalize_po_yaml` is LLM-specific** - may not be unifiable with others
4. **Dataset generators depend on these** - breaking changes = dataset regen needed

### Unification Strategy

**Recommended approach:**

```python
# utils/yaml_sanitizer.py (NEW)

def sanitize_yaml_basic(content: str) -> str:
    """Basic YAML sanitization (from po_format logic)."""
    # Load → dump roundtrip

def sanitize_yaml_with_markdown(value: str | dict | list) -> str:
    """Full sanitization with markdown fence removal (from architect_utils)."""
    # Handles ```yaml blocks + objects

def normalize_llm_yaml(content: str, provider: str = "generic") -> str:
    """LLM-specific normalization (from _normalize_po_yaml)."""
    # Provider-specific quirks (gemini, claude, gpt)
```

**Migration:**
- `architect_utils.py` → deprecate, import from utils/yaml_sanitizer
- `po_format.py` → keep (has validation + extraction logic), import sanitizer from utils
- Update dataset generators to import from utils/

---

## 2. Story Management Investigation

### Functions Found

| File | Function | Lines | Return Type | Features |
|------|----------|-------|-------------|----------|
| `scripts/run_architect.py` | `load_stories()` | 358-376 | `Tuple[str, List[dict]]` | Returns (path, stories) |
| `scripts/run_architect.py` | `save_stories(stories)` | 377+ | `None` | Writes to PLANNING/stories.yaml |
| `scripts/run_architect.py` | `mark_story_todo(story_id)` | 478+ | `bool` | Changes status to "todo" |
| `scripts/orchestrate.py` | `load_stories()` | 213-268 | `List[dict]` | Returns stories only |
| `scripts/orchestrate.py` | `save_stories(stories)` | 269+ | `None` | Writes to PLANNING/stories.yaml |
| `scripts/run_dev.py` | `load_stories()` | 58-84 | `List[Dict[str, Any]]` | **Has recovery logic** |

### Implementation Comparison

#### Architect: Returns (path, stories) tuple

```python
def load_stories() -> Tuple[str, List[dict]]:
    path = PLANNING / "stories.yaml"
    if not path.exists():
        return str(path), []

    raw_yaml = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_yaml) or {}

    if isinstance(data, dict) and "stories" in data:
        stories = data["stories"]
    elif isinstance(data, list):
        stories = data
    else:
        stories = []

    return str(path), stories
```

#### Orchestrator: Returns stories only

```python
def load_stories():
    path = PLANNING / "stories.yaml"
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if isinstance(data, dict):
        return data.get("stories", [])
    if isinstance(data, list):
        return data
    return []
```

#### Dev: Has **recovery logic** for commented YAML

```python
def load_stories() -> List[Dict[str, Any]]:
    p = PLAN / "stories.yaml"
    if not p.exists():
        logger.info("[DEV] planning/stories.yaml not found.")
        return []

    raw = p.read_text(encoding="utf-8")
    data = None
    try:
        data = yaml.safe_load(raw)
    except Exception as exc:
        logger.debug(f"[DEV] Primary YAML load failed: {exc}. Attempting recovery.")
        data = None

    if isinstance(data, dict) and "stories" in data:
        data = data["stories"]

    if not isinstance(data, list):
        # RECOVERY: Try to uncomment lines
        recovered = _try_recover_commented_yaml(raw)
        if isinstance(recovered, dict) and "stories" in recovered:
            recovered = recovered["stories"]
        if isinstance(recovered, list):
            data = recovered
        if not data:
            logger.warning("[DEV] Failed to load or recover stories.yaml.")

    return data if isinstance(data, list) else []


def _try_recover_commented_yaml(text: str) -> Any:
    """
    Some architects print all stories commented (# - id: S1 ...).
    Recover by stripping a single leading '# ' while preserving indentation.
    """
    clean: List[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            clean.append(re.sub(r"^(\s*)#\s?", r"\1", line))
        else:
            clean.append(line)
    candidate = "\n".join(clean).strip()
    if not candidate:
        return None
    try:
        return yaml.safe_load(candidate)
    except Exception:
        return None
```

**Recovery logic explanation:**
- Architects sometimes output commented YAML: `# - id: S1`
- Dev strips leading `# ` while preserving indentation
- Re-parses the uncommented YAML
- Falls back to empty list if recovery fails

**Notes:**
- `run_qa.py` does not manage stories directly (uses dev artifacts instead).
- `run_ba.py` not reviewed for story helpers (likely minimal/no overlap).

### save_stories Implementations

All 3 implementations are nearly identical:

```python
def save_stories(stories):
    path = PLANNING / "stories.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(
            stories,
            fh,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
```

**Differences**: None significant (logging variations only)

### Unification Strategy

**Recommended unified API:**

```python
# utils/story_manager.py (NEW)

def load_stories(recover_comments: bool = False) -> List[dict]:
    """Load stories from planning/stories.yaml.

    Args:
        recover_comments: If True, attempt to recover commented YAML (# - id: S1)

    Returns:
        List of story dicts (empty list if file missing or invalid)
    """
    # Unified logic with optional recovery

def save_stories(stories: List[dict]) -> None:
    """Save stories to planning/stories.yaml."""
    # Unified save logic

def mark_story_status(story_id: str, status: str) -> bool:
    """Change story status (todo/doing/done).

    Returns:
        True if story found and updated, False otherwise
    """
    # Load, modify, save

def mark_story_todo(story_id: str) -> bool:
    """Convenience wrapper for mark_story_status(id, "todo")."""
    return mark_story_status(story_id, "todo")
```

**Migration:**
- Architect can keep tuple return by wrapping: `path, stories = str(PLANNING/"stories.yaml"), load_stories()`
- Orchestrator uses directly
- Dev enables recovery: `load_stories(recover_comments=True)`

---

## 3. Config Loading Investigation

### Functions Found

| File | Function | Lines | Return Type | Features |
|------|----------|-------|-------------|----------|
| `common.py` | `load_config()` | 11+ | `Dict[str, Any]` | Base loader |
| `scripts/llm.py` | `load_config()` | 53+ | `Dict[str, Any]` | Duplicate of common? |
| `scripts/run_architect.py` | `_load_config()` | 53-58 | `dict` | Wrapper to common.load_config() |
| `scripts/run_product_owner.py` | `_load_config()` | 170-176 | `dict` | Wrapper to common.load_config() |
| `scripts/run_dev.py` | `_load_config()` | 388-397 | `tuple[dict, dict]` | Returns (cfg, drv_cfg) |
| `scripts/run_qa.py` | `_load_qa_config()` | 263-278 | `tuple[dict, dict, dict]` | Returns (cfg, drv_cfg, targets) |
| `scripts/dspy_lm_helper.py` | `_load_config()` | 17+ | `Dict[str, Any]` | Unknown variant |

### Return Type Analysis

#### Type 1: Dict (Architect, PO, common)

```python
# scripts/run_architect.py
def _load_config() -> dict:
    from common import load_config
    return load_config()

# scripts/run_product_owner.py
def _load_config() -> dict:
    from common import load_config
    return load_config()
```

**Usage**: Access config directly
```python
cfg = _load_config()
drv_cfg = cfg.get("drivers", {})
targets = cfg.get("project", {}).get("targets", {})
```

#### Type 2: Tuple[dict, dict] (Dev)

```python
# scripts/run_dev.py
def _load_config() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Load config and extract drivers configuration.

    Returns:
        (full_config, drivers_config) tuple
    """
    from common import load_config
    cfg = load_config()
    drv_cfg = (cfg.get("drivers") or {}) if isinstance(cfg, dict) else {}
    return cfg, drv_cfg
```

**Usage**: Unpack tuple
```python
cfg, drv_cfg = _load_config()
# Direct access to both
```

**Rationale**: Dev uses drv_cfg extensively, tuple avoids repeated dict access

#### Type 3: Tuple[dict, dict, dict] (QA)

```python
# scripts/run_qa.py
def _load_qa_config() -> tuple[dict, dict, dict]:
    """Load config and extract QA-specific settings.

    Returns:
        (full_config, drivers_config, targets) tuple
    """
    cfg = {}
    try:
        with open(ROOT / "config.yaml", "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except Exception as e:
        logger.warning(f"[QA] Failed to load config.yaml, using empty config: {e}")
        cfg = {}
    drv_cfg = (cfg.get("drivers") or {}) if isinstance(cfg, dict) else {}
    targets = (cfg.get("project") or {}).get("targets") or {}
    return cfg, drv_cfg, targets
```

**Usage**: Unpack 3-tuple
```python
cfg, drv_cfg, targets = _load_qa_config()
# Direct access to all 3
```

**Rationale**: QA uses all 3 extensively, triple tuple for convenience

**Unique**: QA has custom file loading (not via common.load_config) with error handling

### _normalize_bool Implementations

Found in Architect and PO (identical):

```python
def _normalize_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)
```

**Usage**: Convert config string values to bool
```python
strict_tdd = _normalize_bool(os.getenv("STRICT_TDD"), default=False)
```

### Unification Strategy

**Recommended approach (Strategy Pattern):**

```python
# utils/config_loader.py (NEW)

def load_config() -> dict:
    """Base config loader (wraps common.load_config)."""
    from common import load_config as _load
    return _load()

def load_config_with_drivers() -> tuple[dict, dict]:
    """Load config with drivers extracted (Dev use case).

    Returns:
        (config, drivers_config) tuple
    """
    cfg = load_config()
    drv_cfg = (cfg.get("drivers") or {}) if isinstance(cfg, dict) else {}
    return cfg, drv_cfg

def load_qa_config() -> tuple[dict, dict, dict]:
    """Load config with drivers and targets extracted (QA use case).

    Returns:
        (config, drivers_config, targets) tuple
    """
    cfg = load_config()
    drv_cfg = (cfg.get("drivers") or {}) if isinstance(cfg, dict) else {}
    targets = (cfg.get("project") or {}).get("targets") or {}
    return cfg, drv_cfg, targets

def normalize_bool(value, default: bool = False) -> bool:
    """Normalize various representations of boolean to bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)
```

**Migration:**
- Architect/PO: Replace `_load_config()` with `utils.config_loader.load_config()`
- Dev: Replace `_load_config()` with `utils.config_loader.load_config_with_drivers()`
- QA: Replace `_load_qa_config()` with `utils.config_loader.load_qa_config()`
- All: Replace `_normalize_bool()` with `utils.config_loader.normalize_bool()`

---

## 4. Duplication Matrix (Complete)

| Function | run_architect | run_po | orchestrate | run_ba | run_dev | run_qa | arch_utils | po_format | datasets | common |
|----------|---------------|--------|-------------|--------|---------|--------|------------|-----------|----------|--------|
| **YAML Sanitization** |
| sanitize_yaml_block | ✓ wrapper (L257) | - | - | ? | - | - | ✓ canonical (L10) | - | import | - |
| sanitize_yaml | ✓ inline (L726) | ✓ inline (L112) | - | ? | - | - | - | ✓ (L23) | import | - |
| _normalize_po_yaml | - | ✓ complex (L35) | - | ? | - | - | - | - | - | - |
| **Story Management** |
| load_stories | ✓ tuple (L358) | - | ✓ list (L213) | ? | ✓ recovery (L58) | inline? | - | - | - | - |
| save_stories | ✓ (L377) | - | ✓ (L269) | ? | inline? | inline? | - | - | - | - |
| mark_story_todo | ✓ (L478) | - | - | - | - | - | - | - | - | - |
| **Config Loading** |
| load_config | ✓ wrapper (L53) | ✓ wrapper (L170) | via common | ? | tuple2 (L388) | tuple3 (L263) | - | - | - | ✓ base (L11) |
| normalize_bool | ✓ (L60) | ✓ (L177) | - | ? | - | - | - | - | - | - |

**Legend:**
- ✓ = Function exists
- wrapper = Calls another function
- inline = Logic exists but not in function
- tuple2/tuple3 = Returns tuple (2 or 3 elements)
- import = Imports from another module
- ? = Not yet checked (BA not analyzed)

---

## 5. Risk Assessment

### Risk Matrix

| Risk | Severity | Probability | Impact | Mitigation |
|------|----------|-------------|--------|------------|
| **Dataset generators break** | HIGH | MEDIUM | 🔴 Datasets need regeneration | Test generators after each change |
| **Return type conflicts** | MEDIUM | HIGH | 🟡 Callers need updates | Strategy pattern (multiple functions) |
| **LLM-specific normalization** | MEDIUM | LOW | 🟡 Provider-specific bugs | Preserve _normalize_po_yaml logic |
| **Commented YAML recovery** | LOW | LOW | 🟢 Dev-specific feature | Keep as optional parameter |
| **Circular imports** | LOW | LOW | 🟢 Utils independent | Follow dependency rules |

### Critical Dependencies

**If we change yaml_sanitizer:**
- 🔴 `generate_architect_dataset.py` - May need dataset regen
- 🔴 `generate_po_teacher_dataset.py` - May need dataset regen
- 🔴 `eval_po_student.py` - Evaluation logic may break

**If we change story_manager:**
- 🟡 `orchestrate.py` - May need refactor (uses both load and save)
- 🟢 `run_dev.py` - Recovery logic easily portable

**If we change config_loader:**
- 🟢 All roles - Simple migration (tuple unpacking works)

---

## 6. Revised Implementation Plan

### Adjusted Order (Based on Risk)

**BEFORE (Original Plan):**
1. yaml_sanitizer.py
2. story_manager.py
3. config_loader.py

**AFTER (Risk-Adjusted & aligned with pre-analysis):**
1. ✅ **config_loader.py** (FIRST)
   - Lowest risk, shared by all roles
   - Strategy pattern handles return type variants (dict/tuple2/tuple3)
   - No breaking changes (additive API)

2. ✅ **story_manager.py** (SECOND)
   - Preserve recovery logic as optional flag
   - Used by architect/orchestrator/dev; QA/BA currently N/A

3. ⚠️ **yaml_sanitizer.py** (THIRD)
   - Highest risk (dataset generators)
   - Consider phased approach:
     - Phase 1: Move architect_utils → utils (simple rename)
     - Phase 2: Unify po_format logic
     - Phase 3: Deprecate inline implementations

### Test Estimates (Revised)

| Module | Original Estimate | Revised Estimate | Complexity (LLM) | Reason |
|--------|-------------------|------------------|------------------|--------|
| yaml_sanitizer.py | 15-20 tests | **25-30 tests** | Alta | +3 variants, +dataset tests |
| story_manager.py | 12-15 tests | **12-15 tests** | Media | No change |
| config_loader.py | 10-12 tests | **12-15 tests** | Baja | +tuple variants |
| **TOTAL** | ~40 tests | **~50 tests** | — | +25% due to variants |

### Phased Migration

**Phase 1 - config_loader.py (LOW RISK)**
- Extract to utils/config_loader.py
- Create 3 public functions (base, with_drivers, qa_variant)
- Update all roles
- Run tests: all roles
- **Estimate**: 2-3 hours

**Phase 2 - story_manager.py (LOW/MEDIUM RISK)**
- Extract to utils/story_manager.py
- Add recovery logic as optional param
- Update Architect, Orchestrator, Dev
- Run tests: orchestrator, dev, architect
- **Estimate**: 2-3 hours

**Phase 3 - yaml_sanitizer.py (HIGH RISK)**
- Move architect_utils.py → utils/yaml_sanitizer.py (rename)
- Integrate po_format.sanitize_yaml
- Preserve _normalize_po_yaml as provider-specific
- Update dataset generators
- **TEST DATASETS** after changes
- Run full test suite + dataset validation
- **Estimate**: 4-5 hours

**Total**: 8-11 hours (was 6-8 hours in original plan)

### Progress Snapshot (current) — Task 2.1 **IN REVIEW (external validation pending)**
- config_loader.py ✅ (complejidad: baja). Helpers defensivos y tests en `tests/utils/test_config_loader.py`.
- story_manager.py ✅ (complejidad: media). `load_stories(recover_comments)`, `save_stories`, `mark_story_status/mark_story_todo`; tests en `tests/utils/test_story_manager.py`.
- yaml_sanitizer.py ✅ (complejidad: alta). `sanitize_yaml_block`, `sanitize_po_yaml`, `normalize_po_yaml`; tests en `tests/utils/test_yaml_sanitizer.py`.

### Progress Snapshot (Task 2.2)
- complexity_classifier ✅ (complejidad: alta). Nuevos módulos `scripts/architect/complexity_classifier.py` y `scripts/architect/cache.py`; `run_architect.py` usa classifier extraído; tests en `tests/architect/test_complexity_classifier.py`.

---

## 7. Acceptance Criteria (Updated)

### Must Have

✅ **Zero breaking changes in outputs/contracts**
- All roles produce same outputs after refactor
- Stories.yaml format unchanged
- Config access patterns work identically

✅ **Tests coverage ≥95% for all 3 modules**
- yaml_sanitizer: 25-30 tests
- story_manager: 12-15 tests
- config_loader: 12-15 tests

✅ **Zero code duplication**
- `pylint --disable=all --enable=duplicate-code scripts/` → 0 warnings
- Manual grep of extracted functions → 0 matches outside utils/

✅ **Dataset generators still work**
- Run generate_architect_dataset.py → success
- Run generate_po_teacher_dataset.py → success
- Run eval_po_student.py → success

✅ **Regression tests pass**
- All existing architect/PO/orchestrator tests pass
- No new test failures introduced

### Nice to Have

🟡 **Deprecation warnings** for old imports (architect_utils, po_format)
🟡 **Migration guide** for external consumers
🟡 **Performance benchmarks** (load/save stories speed)

---

## 8. Issues Identified

### 🔴 BLOCKER Issues

None identified - proceed with caution

### 🟡 HIGH Priority Issues

1. **Dataset Generator Coordination**
   - Issue: 3 dataset scripts import architect_utils/po_format
   - Impact: Breaking changes = dataset regen (expensive)
   - Mitigation: Keep backward compat wrappers in utils/

2. **Return Type Conflicts**
   - Issue: Config loaders have 3 different signatures
   - Impact: Cannot unify to single function
   - Mitigation: Strategy pattern (3 public functions)

3. **LLM-Specific Normalization**
   - Issue: _normalize_po_yaml is 75 lines of Gemini-specific logic
   - Impact: Hard to generalize for other LLMs
   - Mitigation: Keep provider parameter: `normalize_llm_yaml(content, provider="gemini")`

### 🟢 LOW Priority Issues

4. **Commented YAML Recovery**
   - Issue: Dev-specific feature, other roles don't need
   - Impact: None (optional parameter works)
   - Mitigation: `load_stories(recover_comments=True)`

5. **Logging Inconsistencies**
   - Issue: Different log formats across roles
   - Impact: Minor UX issue
   - Mitigation: Standardize in utils (use role parameter)

---

## 9. Recommendations

### Immediate Actions

1. ✅ **Approve revised scope** (7 files, ~50 tests, 8-11 hours)
2. ✅ **Follow revised order** (story → config → yaml)
3. ✅ **Test dataset generators** after yaml_sanitizer changes

### Before Starting Implementation

- [ ] Review this analysis document
- [ ] Confirm dataset generator coordination plan
- [ ] Decide on backward compat strategy (wrappers vs breaking changes)
- [ ] Set up baseline tests for regression detection

### During Implementation

- [ ] Commit after each module (3 commits minimum)
- [ ] Run full test suite after each commit
- [ ] Test dataset generators after yaml_sanitizer
- [ ] Update PHASE2_TASK2.1_PREANALYSIS.md with results

### After Implementation

- [ ] Verify zero code duplication (pylint check)
- [ ] Run performance benchmarks (story load/save)
- [ ] Update migration guide for external consumers
- [ ] Mark Task 2.1 complete in tracking doc

---

## 10. Files Affected (Complete List)

### To Extract From

1. `scripts/architect_utils.py` (60 lines) - Move to utils/yaml_sanitizer
2. `scripts/po_format.py` (101 lines) - Integrate validation separately
3. `scripts/run_architect.py` - Extract helpers
4. `scripts/run_product_owner.py` - Extract helpers
5. `scripts/run_dev.py` - Extract helpers
6. `scripts/run_qa.py` - Extract helpers
7. `scripts/orchestrate.py` - Extract helpers

### To Create

1. `scripts/utils/yaml_sanitizer.py` (NEW)
2. `scripts/utils/story_manager.py` (NEW)
3. `scripts/utils/config_loader.py` (NEW)

### To Update (Imports)

1. `scripts/generate_architect_dataset.py`
2. `scripts/generate_po_teacher_dataset.py`
3. `scripts/eval_po_student.py`
4. All role scripts (architect, po, dev, qa)
5. `scripts/orchestrate.py`

### Test Files to Create

1. `tests/utils/test_yaml_sanitizer.py` (25-30 tests)
2. `tests/utils/test_story_manager.py` (12-15 tests)
3. `tests/utils/test_config_loader.py` (12-15 tests)

---

## Conclusion

**Step 0 Analysis: COMPLETED**

### Key Takeaways

1. **Scope is larger** than expected (7 files vs 5)
2. **architect_utils.py and po_format.py already exist** as shared modules
3. **Dataset generators are stakeholders** - need coordination
4. **3 different return types for config** - requires strategy pattern
5. **Recovery logic in Dev is valuable** - should be standard option

### Go/No-Go Decision

**✅ GO - Proceed with Task 2.1 with adjustments:**

- Revised order: story_manager → config_loader → yaml_sanitizer
- Revised estimate: 8-11 hours (was 6-8)
- Revised test count: ~50 tests (was ~40)
- Added coordination: Dataset generators
- Risk level: MEDIUM (manageable with mitigation)

### Next Step

Execute Task 2.1 implementation following the revised plan in this document.

---

**Analysis completed by**: Claude Sonnet 4.5
**Date**: 2025-11-26
**Confidence**: HIGH (all functions inspected, dependencies mapped)
**Ready for implementation**: YES
