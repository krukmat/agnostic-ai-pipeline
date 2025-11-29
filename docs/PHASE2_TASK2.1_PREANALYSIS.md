# Phase 2 - Task 2.1 Pre-Analysis: DRY Foundation

**Status**: 📋 PLANNING
**Task**: 2.1 - Create shared utilities (yaml_sanitizer, story_manager, config_loader)
**Estimated Time**: 2-3 hours for pre-analysis (Step 0)

---

## Table of Contents

1. [Overview](#overview)
2. [Task 2.1 Scope](#task-21-scope)
3. [Step 0: Pre-Analysis (Detailed)](#step-0-pre-analysis-detailed)
4. [Deliverables](#deliverables)
5. [Decision Checklist](#decision-checklist)

---

## Overview

**Purpose**: Before extracting duplicated code into shared utilities, we must thoroughly analyze:
- What functions are actually duplicated across roles
- Where they exist and how they differ
- What edge cases each implementation handles
- What dependencies exist and potential circular import risks

**Why Step 0 is Critical**:
- Avoid extracting functions that aren't truly duplicated
- Preserve subtle variations that may be intentional
- Identify breaking changes before they happen
- Plan extraction order to minimize risk

---

## Task 2.1 Scope

### Modules to Create

1. **`scripts/utils/yaml_sanitizer.py`**
   - Extract: `_sanitize_yaml_block()`, `sanitize_yaml()` from Architect
   - Extract: `_normalize_po_yaml()` from Product Owner
   - Helpers: markdown stripping, inline JSON parsing, comment removal

2. **`scripts/utils/story_manager.py`**
   - Extract: `load_stories()`, `save_stories()`, `mark_story_todo()`
   - Used by: Architect, Orchestrator, Dev, QA
   - Centralize: story state management, status transitions, dependency tracking

3. **`scripts/utils/config_loader.py`**
   - Extract: `_load_config()` variants from Architect, PO, QA
   - Extract: `_normalize_bool()`, flag access patterns
   - Centralize: drivers config, dspy settings, feature flags

### Recommended Implementation Order

**Change from original plan:**

```
Original Order:          Recommended Order:
1. yaml_sanitizer    →   1. config_loader     (lowest risk, most used)
2. story_manager     →   2. story_manager     (critical, stable contracts)
3. config_loader     →   3. yaml_sanitizer    (highest risk, LLM sensitivity)
```

**Rationale**:
- `config_loader.py`: Simple, well-defined, used by all roles
- `story_manager.py`: Critical but contracts are stable (status: todo/doing/done)
- `yaml_sanitizer.py`: Complex, highest risk of breaking LLM compatibility

### Acceptance Criteria

✅ **No breaking changes**: Outputs/contracts remain unchanged
✅ **Tests coverage**: ≥95% for all three modules
✅ **Zero duplication**: `pylint --disable=all --enable=duplicate-code scripts/` → 0 warnings
✅ **Regression tests pass**: All existing architect/PO/orchestrator tests still pass
✅ **Roles consume utilities**: No duplicated code remains in run_*.py files

---

## Step 0: Pre-Analysis (Detailed)

### Activity 1: Inventory of Candidate Functions (30-45 min)

#### 1.1 YAML Sanitization Functions

**Search commands:**
```bash
# Find all sanitization functions
grep -rn "def.*sanitize" scripts/ --include="*.py"
grep -rn "def.*normalize.*yaml" scripts/ --include="*.py"
grep -rn "yaml.safe_load\|yaml.safe_dump" scripts/ --include="*.py"

# Find markdown cleaning patterns
grep -rn "```yaml\|```" scripts/ --include="*.py"
grep -rn "strip()\|replace(" scripts/ --include="*.py" | grep -i yaml
```

**Expected output locations:**
```
scripts/run_architect.py:245:    def _sanitize_yaml_block(text: str) -> str:
scripts/run_architect.py:267:    def sanitize_yaml(response: str) -> str:
scripts/run_product_owner.py:156:    def _normalize_po_yaml(text: str) -> dict:
scripts/run_dev.py:89:    # inline YAML parsing logic (no function)
```

**Document:**
- Line numbers for each function
- Function signatures (params, return types)
- Whether it's a function or inline logic

#### 1.2 Story Management Functions

**Search commands:**
```bash
# Find story functions
grep -rn "def.*load_stories\|def.*save_stories" scripts/ --include="*.py"
grep -rn "def.*mark_story" scripts/ --include="*.py"
grep -rn "stories.yaml" scripts/ --include="*.py"

# Find story status access patterns
grep -rn "story\[.status.\]\|story.get(.status" scripts/ --include="*.py"
grep -rn "todo\|doing\|done" scripts/ --include="*.py" | grep -i story
```

**Expected output locations:**
```
scripts/run_architect.py:89:    stories = load_stories()
scripts/orchestrate.py:123:    def load_stories():
scripts/orchestrate.py:145:    def save_stories(stories):
scripts/run_dev.py:234:    stories = yaml.safe_load(...)  # inline
scripts/run_qa.py:178:    stories = yaml.safe_load(...)  # inline
common.py:45:    STORIES_PATH = PLANNING / "stories.yaml"
```

**Document:**
- Which roles use functions vs inline logic
- Path resolution patterns (ROOT / PLANNING vs hardcoded)
- Default values when file missing

#### 1.3 Config Loading Functions

**Search commands:**
```bash
# Find config functions
grep -rn "def.*load_config\|def.*_load_config" scripts/ --include="*.py"
grep -rn "config.yaml" scripts/ --include="*.py"
grep -rn "def.*normalize.*bool" scripts/ --include="*.py"

# Find flag access patterns
grep -rn "cfg.get(.drivers.\)\|cfg\[.drivers.\]" scripts/ --include="*.py"
grep -rn "STRICT_TDD\|ALLOW_NO_TESTS" scripts/ --include="*.py"
```

**Expected output locations:**
```
scripts/run_architect.py:67:    def _load_config() -> dict:
scripts/run_product_owner.py:45:    def _load_config() -> dict:
scripts/run_dev.py:123:    cfg = load_config()  # from common
scripts/run_qa.py:98:    def _load_qa_config():  # custom variant
common.py:23:    def load_config() -> dict:
```

**Document:**
- Relationship to `common.load_config()`
- Custom variants (like `_load_qa_config`)
- Environment variable overrides

---

### Activity 2: Duplication Matrix (20-30 min)

**Template:**

| Function/Pattern | Architect | PO | Orchestrator | BA | Dev | QA | common.py |
|------------------|-----------|-------|--------------|-----|-----|-----|-----------|
| sanitize_yaml() | ✓ (L245) | ✓ _normalize_po_yaml (L156) | - | ? | inline? | - | - |
| load_stories() | ✓ (L89) | ? | ✓ (L123) | ? | inline (L234) | inline (L178) | - |
| save_stories() | ✓ | ? | ✓ (L145) | ? | ✓ | ✓ | - |
| load_config() | ✓ _load_config (L67) | ✓ _load_config (L45) | via common | via common | via common | ✓ custom (L98) | ✓ (L23) |
| normalize_bool() | ? | ? | ? | ? | inline? | inline? | - |
| mark_story_todo() | ✓ | ? | ✓ | - | - | - | - |
| strip markdown | ✓ | ✓ | - | ? | - | - | - |
| inline JSON parse | ✓ | ✓ | - | ? | - | - | - |

**Legend:**
- ✓ (L123) = Has function at line 123
- "inline" = Has equivalent logic without function
- "?" = Not yet reviewed
- "-" = Confirmed NOT used
- "via common" = Uses common.py import

**Action**: Fill each cell by reviewing actual files

**Additional patterns to check:**
- Prompt loading (`prompts/*.md`)
- LLM client usage patterns
- Artifact path construction (`artifacts/{role}/...`)
- Logging patterns (`[ROLE][area]`)

---

## Step 0 Results (inventory summary)

- **YAML sanitization**: `_sanitize_yaml_block` + `sanitize_yaml` in `scripts/run_architect.py`; `_normalize_po_yaml` + `sanitize_yaml` in `scripts/run_product_owner.py`; shared variants in `scripts/architect_utils.py` and `scripts/po_format.py`. Dataset generators import these helpers.
- **Story management**: `load_stories`/`save_stories`/`mark_story_todo` in `scripts/run_architect.py`; `load_stories`/`save_stories` in `scripts/orchestrate.py`; inline loaders in `scripts/run_dev.py` (with recovery) and `scripts/run_qa.py`. Path pattern: `PLANNING/stories.yaml`.
- **Config loading**: `_load_config` + `_normalize_bool` duplicated in `scripts/run_architect.py` and `scripts/run_product_owner.py`; variants in `scripts/run_dev.py` (`_load_config` tuple) and `_load_qa_config` in `scripts/run_qa.py`; base `load_config` in `common.py`. Flags handled via `_normalize_bool` + env overrides.
- **Complejidad por módulo (LLM)**: config_loader = baja; story_manager = media; yaml_sanitizer = alta (por variantes y generadores de datasets).

---

### Activity 3: Side-by-Side Comparison (30-45 min)

For each duplicated function, extract and compare implementations.

#### 3.1 Example: YAML Sanitization

**Extract functions:**
```bash
# Architect version
sed -n '245,267p' scripts/run_architect.py > /tmp/arch_sanitize.py

# PO version
sed -n '156,180p' scripts/run_product_owner.py > /tmp/po_sanitize.py

# Compare
diff -u /tmp/arch_sanitize.py /tmp/po_sanitize.py
```

**Expected diff analysis:**
```diff
--- /tmp/arch_sanitize.py
+++ /tmp/po_sanitize.py
@@ -1,5 +1,5 @@
-def _sanitize_yaml_block(text: str) -> str:
+def _normalize_po_yaml(text: str) -> dict:
     """Remove markdown yaml blocks and strip."""
-    text = text.strip()
-    if text.startswith("```yaml"):
-        text = text[7:]  # remove ```yaml
+    text = text.strip().lower()  # ← PO LOWERCASES! Critical difference
+    if text.startswith("```"):
+        text = text[3:]  # ← Different offset
```

**Document critical variations:**
- Does PO lowercase but Architect doesn't? → Case-sensitive keys may break
- Different offsets (`[7:]` vs `[3:]`)? → One handles ` ```yaml `, other ` ``` `
- Different return types (str vs dict)? → Needs wrapper or unification
- Different error handling? → One crashes, other returns default?

#### 3.2 Example: load_stories

**Compare:**
```bash
diff -u \
  <(sed -n '89,110p' scripts/run_architect.py) \
  <(sed -n '123,145p' scripts/orchestrate.py)
```

**Check for differences in:**
- ✓ **Encoding**: UTF-8 explicit or OS default?
- ✓ **Error handling**: try/except or crash?
- ✓ **Default value**: `[]` or `{}` if file missing?
- ✓ **Path resolution**: `ROOT / PLANNING` vs hardcoded?
- ✓ **Schema validation**: Validates structure or trusts content?

#### 3.3 Example: load_config

**Compare:**
```bash
diff -u \
  <(sed -n '67,85p' scripts/run_architect.py) \
  <(sed -n '45,60p' scripts/run_product_owner.py)
```

**Check for:**
- Environment variable overrides (STRICT_TDD, etc.)
- Default values for missing keys
- Type coercion (string → bool, int, etc.)
- Nested key access safety (`.get()` chains vs `[]`)

**Document template:**
```markdown
## Comparison Results

### sanitize_yaml variants

**Architect version** (L245-267):
- Strips ````yaml` prefix (7 chars)
- Returns str
- No lowercasing
- Handles nested blocks: NO

**PO version** (L156-180):
- Strips ``` prefix (3 chars)
- Returns dict (parses YAML)
- LOWERCASES input (breaks case-sensitive keys!)
- Handles nested blocks: YES

**Unified approach**:
- Use Architect logic (preserve case)
- Add optional `parse=True` parameter to return dict
- Handle both ` ```yaml ` and ` ``` ` prefixes
- Add nested block handling from PO
```

---

### Activity 4: Dependency Analysis (15-20 min)

**Goal**: Prevent circular imports

**Dependency graph:**
```
common.py
  └── load_config()
  └── ROOT, PLANNING constants

scripts/utils/config_loader.py (NEW)
  ├── CAN import: pathlib, yaml, os, typing
  ├── CANNOT import: scripts/* (circular!)
  ├── MAY import: common (for constants only)
  └── Used by: run_architect, run_po, run_ba, run_dev, run_qa

scripts/utils/story_manager.py (NEW)
  ├── CAN import: common.py (ROOT, PLANNING), pathlib, yaml
  ├── CANNOT import: run_* (circular!)
  └── Used by: run_architect, orchestrate, run_dev, run_qa

scripts/utils/yaml_sanitizer.py (NEW)
  ├── CAN import: re, json, yaml
  ├── CANNOT import: any project scripts (pure utility)
  └── Used by: run_architect, run_po
```

**Verification commands:**
```bash
# Find imports in candidate functions
grep -B5 -A20 "def _sanitize_yaml\|def load_stories\|def _load_config" scripts/*.py | grep "^import\|^from"
```

**Identify external dependencies:**
- Uses `common.ROOT`? → story_manager needs to import it
- Uses `logger`? → Needs logger parameter (DIP pattern)
- Uses `os.environ`? → config_loader can access directly
- Uses LLM client? → CANNOT be in utils (too heavy)

**Rules:**
1. `utils/` modules must be **pure utilities** (no business logic)
2. **No imports from `scripts/run_*.py`** (always circular)
3. **Minimal imports from `common.py`** (constants OK, functions risky)
4. **Logger as parameter** (don't import logging at module level)

---

### Activity 5: Baseline Tests (10-15 min)

**Find existing tests:**
```bash
# Search for architect/PO tests
find tests/ -name "*architect*" -o -name "*product_owner*" -o -name "*po*"

# Count current tests
PYTHONPATH=. pytest tests/ -k "architect or product_owner or po" --collect-only

# Search for story management tests
grep -rn "load_stories\|save_stories" tests/ --include="*.py"
```

**Run baseline coverage:**
```bash
PYTHONPATH=. pytest tests/ \
  --cov=scripts.run_architect \
  --cov=scripts.run_product_owner \
  --cov=scripts.orchestrate \
  --cov-report=term-missing
```

**Document results:**
```markdown
## Baseline Test Status

**Existing tests:**
- tests/test_architect.py: 0 tests (file doesn't exist)
- tests/test_product_owner.py: 0 tests (file doesn't exist)
- tests/test_orchestrator.py: 3 tests (include story load/save?)

**Current coverage:**
- run_architect.py: ?%
- run_product_owner.py: ?%
- orchestrate.py: ?%

**Target for Task 2.1:**
- yaml_sanitizer.py: 95%+ (15-20 tests)
- story_manager.py: 98%+ (12-15 tests)
- config_loader.py: 95%+ (10-12 tests)
```

---

### Activity 6: Edge Cases Identification (20-30 min)

#### 6.1 YAML Sanitization Edge Cases

**Search for edge case handling:**
```bash
# Nested YAML blocks?
grep -A10 "sanitize" scripts/run_architect.py | grep -i "nested\|recursive"

# JSON inline handling?
grep -B5 -A10 "json.loads\|JSON" scripts/run_architect.py scripts/run_product_owner.py

# Unicode handling?
grep -i "utf-8\|encoding\|unicode" scripts/run_architect.py scripts/run_product_owner.py
```

**Document edge cases:**
```markdown
### YAML Sanitization Edge Cases

1. **Multiple code blocks**:
   ```
   Some text
   ```yaml
   key: value1
   ```
   More text
   ```yaml
   key: value2
   ```
   ```
   Expected: Extract both blocks or first only?

2. **JSON inline**:
   ```yaml
   config:
     data: {"nested": "json", "inline": true}
   ```
   Expected: Parse JSON or keep as string?

3. **YAML comments**:
   ```yaml
   # This is a comment
   key: value  # inline comment
   ```
   Expected: Preserve or strip?

4. **Anchors and aliases**:
   ```yaml
   defaults: &default
     timeout: 30
   service:
     <<: *default
   ```
   Expected: Support or reject?

5. **Multiline strings**:
   ```yaml
   description: |
     Line 1
     Line 2
   ```
   Expected: Handle correctly?

6. **Unicode/emojis**:
   ```yaml
   title: "Add feature 🚀"
   ```
   Expected: Preserve encoding?

7. **Empty response**:
   LLM returns ""
   Expected: Return {} or raise error?

8. **Malformed YAML**:
   ```yaml
   key: [unclosed
   ```
   Expected: Return error or attempt fix?
```

#### 6.2 Story Management Edge Cases

**Search for edge case handling:**
```bash
# Missing file handling
grep -B5 -A10 "FileNotFoundError\|not.*exist" scripts/orchestrate.py

# Concurrent access
grep -i "lock\|atomic\|race" scripts/orchestrate.py

# Schema validation
grep -B5 -A10 "status.*todo\|depends_on" scripts/orchestrate.py
```

**Document edge cases:**
```markdown
### Story Management Edge Cases

1. **stories.yaml missing**:
   Expected: Create with [] default or raise error?

2. **stories.yaml malformed**:
   ```yaml
   - id: S1
     title: [should be string]
   ```
   Expected: Crash or skip invalid entries?

3. **Concurrent save_stories()**:
   Two processes write simultaneously
   Expected: Last write wins (document as not thread-safe)

4. **Story without 'status' field**:
   ```yaml
   - id: S1
     title: "Test"
     # missing status
   ```
   Expected: Validate and reject or default to 'todo'?

5. **Story with invalid 'depends_on'**:
   ```yaml
   - id: S2
     depends_on: ["S99"]  # S99 doesn't exist
   ```
   Expected: Validate or allow?

6. **UTF-8 in descriptions**:
   ```yaml
   - id: S1
     title: "Test función ñ 中文"
   ```
   Expected: Force UTF-8 encoding on read/write

7. **Empty stories list**:
   stories.yaml contains: []
   Expected: Valid state, no error

8. **Duplicate story IDs**:
   ```yaml
   - id: S1
   - id: S1  # duplicate
   ```
   Expected: Validate and reject?
```

#### 6.3 Config Loading Edge Cases

**Search for edge case handling:**
```bash
# Missing config
grep -B5 -A10 "config.*not.*found\|missing.*config" scripts/

# Boolean normalization
grep -B5 -A10 "bool\|true\|false" scripts/ | grep -i normalize

# Env var overrides
grep "os.environ\|getenv" scripts/run_dev.py scripts/run_qa.py
```

**Document edge cases:**
```markdown
### Config Loading Edge Cases

1. **config.yaml missing**:
   Expected: Return {} default or raise error?

2. **drivers.enabled not specified**:
   Expected: Default to false

3. **Environment variable overrides**:
   STRICT_TDD=1 in env, config.yaml has strict_tdd: false
   Expected: Env takes precedence?

4. **Boolean coercion**:
   Input: "true", "1", "yes", "True", "YES"
   Expected: All → True

5. **Missing nested keys**:
   cfg['drivers']['embedded']['run_build']
   Expected: KeyError or default value?

6. **Type mismatches**:
   enabled: "not a bool"
   Expected: Coerce or raise error?

7. **Comments in YAML**:
   ```yaml
   # This is a comment
   drivers:
     enabled: true  # inline comment
   ```
   Expected: Handle correctly (YAML parser does)

8. **Empty config file**:
   config.yaml contains nothing or just comments
   Expected: Return {} default
```

---

### Activity 7: Create Test Fixtures (15-20 min)

**Capture real outputs from LLM:**
```bash
# Extract Architect responses
tail -100 artifacts/architect/last_raw.txt > /tmp/arch_sample.txt

# Extract PO responses
tail -100 artifacts/product_owner/last_raw.txt > /tmp/po_sample.txt

# Copy current stories
cp planning/stories.yaml /tmp/stories_baseline.yaml

# Copy current config
cp config.yaml /tmp/config_baseline.yaml
```

**Create fixture files:**

#### tests/fixtures/yaml_samples.py
```python
"""Real YAML samples from LLM responses for regression testing."""

ARCHITECT_CLEAN_RESPONSE = """
```yaml
stories:
  - id: S1
    title: "Add user authentication"
    status: todo
    description: "Implement JWT-based auth"
```
"""

ARCHITECT_DIRTY_RESPONSE = """
Sure, here are the stories:

```yaml
stories:
  - id: S1
    title: "Add user auth"
    status: todo
```

Let me know if you need changes!
"""

PO_MALFORMED_RESPONSE = """
```YAML
  approved: true
  comments: "needs refinement"
```
"""

NESTED_JSON_SAMPLE = """
```yaml
config:
  data: {"nested": "json", "inline": true}
  array: [1, 2, 3]
```
"""

MULTILINE_STRING_SAMPLE = """
```yaml
description: |
  This is line 1
  This is line 2
  This is line 3
```
"""

UNICODE_SAMPLE = """
```yaml
title: "Add feature 🚀"
description: "Función ñ 中文"
```
"""

EMPTY_RESPONSE = ""

MALFORMED_YAML = """
```yaml
key: [unclosed bracket
another: {unclosed brace
```
"""
```

#### tests/fixtures/story_samples.py
```python
"""Story samples for story_manager tests."""

VALID_STORIES = [
    {
        "id": "S1",
        "title": "Add user auth",
        "description": "Implement JWT authentication",
        "status": "todo",
        "acceptance_criteria": ["User can login", "Token expires after 24h"],
    },
    {
        "id": "S2",
        "title": "Add dashboard",
        "description": "Create user dashboard",
        "status": "doing",
        "depends_on": ["S1"],
    },
]

INVALID_STORIES_MISSING_STATUS = [
    {
        "id": "S1",
        "title": "Test story",
        # missing status
    }
]

INVALID_STORIES_DUPLICATE_IDS = [
    {"id": "S1", "title": "Story 1", "status": "todo"},
    {"id": "S1", "title": "Story 1 duplicate", "status": "todo"},
]

STORIES_WITH_INVALID_DEPENDS_ON = [
    {
        "id": "S1",
        "title": "Story with bad dependency",
        "status": "todo",
        "depends_on": ["S99"],  # S99 doesn't exist
    }
]

EMPTY_STORIES = []

STORIES_WITH_UTF8 = [
    {
        "id": "S1",
        "title": "Test función ñ 中文 🚀",
        "status": "todo",
    }
]
```

#### tests/fixtures/config_samples.py
```python
"""Config samples for config_loader tests."""

VALID_CONFIG = {
    "drivers": {
        "enabled": True,
        "embedded": {
            "run_build": False,
            "run_test": False,
        }
    },
    "dspy": {
        "optimizer": "BootstrapFewShot",
        "max_rounds": 3,
    },
    "project": {
        "targets": {
            "backend": "fastapi",
            "frontend": "next_js",
        }
    }
}

MINIMAL_CONFIG = {
    "drivers": {
        "enabled": False
    }
}

EMPTY_CONFIG = {}

CONFIG_WITH_BOOL_STRINGS = {
    "drivers": {
        "enabled": "true",  # string, should coerce to bool
    },
    "strict_tdd": "1",  # should coerce to True
    "allow_no_tests": "yes",  # should coerce to True
}

CONFIG_MISSING_NESTED_KEYS = {
    "drivers": {
        # missing 'enabled' key
    }
}
```

---

## Deliverables

After completing Step 0, you should have:

### 📄 Documentation Files

1. **`docs/PHASE2_TASK2.1_ANALYSIS.md`** (results of pre-analysis)
   - Completed duplication matrix
   - List of functions to extract with exact line numbers
   - Side-by-side diff comparisons
   - Documented critical variations
   - Edge cases with examples
   - Baseline coverage report

2. **`tests/fixtures/yaml_samples.py`**
   - Real LLM responses (clean, dirty, malformed)
   - Unicode, JSON, multiline test cases

3. **`tests/fixtures/story_samples.py`**
   - Valid/invalid story structures
   - Edge cases (duplicates, missing fields, UTF-8)

4. **`tests/fixtures/config_samples.py`**
   - Valid configs, empty configs, type coercion cases

5. **Dependency graph diagram** (text or visual)
   ```
   utils/config_loader.py → common.py (constants only)
   utils/story_manager.py → common.py (ROOT, PLANNING)
   utils/yaml_sanitizer.py → (no internal deps)
   ```

### ✅ Pre-Implementation Checklist

Before proceeding to implementation (Steps 1-4):

- [ ] All candidate functions mapped in duplication matrix
- [ ] Side-by-side diffs completed for each duplicated function
- [ ] Critical variations documented (e.g., PO lowercases, Architect doesn't)
- [ ] Edge cases listed with real examples
- [ ] Dependency graph validated (no circular imports)
- [ ] Baseline coverage executed and recorded
- [ ] Test fixtures created from real artifacts/
- [ ] Implementation order decided:
  - [ ] config_loader first (lowest risk)
  - [ ] story_manager second (critical, stable)
  - [ ] yaml_sanitizer third (highest risk)
- [ ] Test estimates per module:
  - [ ] yaml_sanitizer: ~15-20 tests
  - [ ] story_manager: ~12-15 tests
  - [ ] config_loader: ~10-12 tests
  - [ ] Total: ~40 tests

---

## Decision Checklist

After Step 0, you must be able to answer:

### ✅ Feasibility Questions

1. **How many functions are truly duplicated?**
   - [ ] Answer: ___ functions across ___ roles

2. **Are there variations that prevent direct unification?**
   - [ ] Yes / No
   - [ ] If yes, document: ___

3. **What implementation order minimizes risk?**
   - [ ] config_loader → story_manager → yaml_sanitizer
   - [ ] Other: ___

4. **How many tests do we need to write?**
   - [ ] Total: ~___ tests
   - [ ] yaml_sanitizer: ___
   - [ ] story_manager: ___
   - [ ] config_loader: ___

5. **Are there technical blockers?**
   - [ ] Circular dependencies: Yes / No
   - [ ] Missing data/artifacts: Yes / No
   - [ ] Incompatible variations: Yes / No
   - [ ] Other: ___

### 🚨 Go/No-Go Decision

**Proceed with Task 2.1 implementation if:**
- ✅ No circular dependency issues found
- ✅ Variations are reconcilable (can create unified version)
- ✅ Edge cases are documented and testable
- ✅ Baseline tests exist or can be created
- ✅ Fixtures captured from real usage

**STOP and replant if:**
- ❌ Circular dependencies cannot be resolved
- ❌ Variations are fundamentally incompatible
- ❌ Missing critical data (no artifacts to test against)
- ❌ Functions aren't actually duplicated (false positive)

---

## Time Estimates

**Total for Step 0: 2-3 hours**

| Activity | Estimated Time |
|----------|----------------|
| 1. Inventory of functions | 30-45 min |
| 2. Duplication matrix | 20-30 min |
| 3. Side-by-side comparison | 30-45 min |
| 4. Dependency analysis | 15-20 min |
| 5. Baseline tests | 10-15 min |
| 6. Edge cases identification | 20-30 min |
| 7. Create test fixtures | 15-20 min |
| **Buffer** | 15-30 min |

---

## Next Steps After Step 0

Once Step 0 is complete and approved:

1. **Step 1**: Extract functions to new modules (config_loader first)
2. **Step 2**: Write unit tests with fixtures
3. **Step 3**: Verify behavior matches (regression tests)
4. **Step 4**: Rewire roles to use new utilities

**Each step should be a separate commit with tests passing before proceeding to next step.**

---

**Last Updated**: 2025-11-26
**Status**: Ready for execution
**Next Action**: Execute Activity 1 (Inventory) or request approval to proceed
