# E2E Test Battery Documentation

## Overview

The E2E Test Battery script (`scripts/test_e2e_battery.sh`) is a comprehensive end-to-end integration testing framework for the Agnostic AI Pipeline. It validates the complete workflow from Business Analyst through QA, measuring performance metrics and generating detailed reports.

## Purpose

This script is designed for:

- **Integration Testing**: Validate the complete BA→PO→Architect→Dev→QA pipeline
- **Performance Benchmarking**: Measure execution times and resource usage
- **Regression Testing**: Ensure changes don't break existing functionality
- **CI/CD Integration**: Automated testing with parseable results
- **Quality Assurance**: Validate artifact generation and data integrity

## Features

### 1. Multiple Test Scenarios

- **Simple**: Basic health check API (1 loop, ~2-3 min)
- **Medium**: Calculator API with validation (2 loops, ~5-7 min)
- **Complex**: Full-featured todo app (3 loops, ~10-15 min)
- **Database**: Integration with SQLite layer (2 loops, ~5-7 min)

### 2. Comprehensive Metrics

- Execution duration per scenario
- Pass/fail rates
- Artifact validation
- Success rate calculation
- JSON metrics export

### 3. Detailed Reporting

- Markdown report with summary
- Individual scenario breakdowns
- Configuration snapshot
- Actionable recommendations
- Artifact location tracking

### 4. Validation Checks

- **Pre-flight**: Environment, providers, authentication
- **Post-execution**: Artifacts, file structure, error detection
- **Data integrity**: YAML validation, field presence

## Usage

### Basic Usage

```bash
# Run all scenarios
./scripts/test_e2e_battery.sh

# Run specific scenario
./scripts/test_e2e_battery.sh --scenario simple

# Quick mode (skip complex tests)
./scripts/test_e2e_battery.sh --quick

# Verbose output
./scripts/test_e2e_battery.sh --verbose
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--scenario <name>` | Run specific scenario: `simple`, `medium`, `complex`, `database`, `all` |
| `--quick` | Skip complex scenarios for faster execution |
| `--verbose` | Show detailed real-time output |
| `--no-cleanup` | Preserve artifacts between tests |
| `--report-dir <path>` | Custom output directory (default: `artifacts/e2e_reports/<timestamp>`) |
| `-h, --help` | Show usage information |

### Examples

```bash
# Quick smoke test (simple scenario only)
./scripts/test_e2e_battery.sh --scenario simple --verbose

# Full regression suite
./scripts/test_e2e_battery.sh --scenario all

# Database integration test with artifacts preserved
./scripts/test_e2e_battery.sh --scenario database --no-cleanup --verbose

# Custom report location
./scripts/test_e2e_battery.sh --report-dir /tmp/my_test_run
```

## Test Scenarios

### 1. Simple Health Check (`simple_health_check`)

**Concept**: Simple REST API with a /health endpoint that returns status ok

**Purpose**: Validate basic pipeline functionality

**Duration**: ~2-3 minutes

**Validates**:
- BA requirements generation
- PO validation
- Architect story creation
- Developer implementation
- QA testing

**Expected Artifacts**:
- `planning/requirements.yaml`
- `planning/stories.yaml`
- `project/backend-fastapi/` (or similar)
- Basic health endpoint implementation

---

### 2. Medium Calculator (`medium_calculator`)

**Concept**: Calculator REST API with add, subtract, multiply, divide endpoints and input validation

**Purpose**: Test moderate complexity with multiple endpoints

**Duration**: ~5-7 minutes

**Validates**:
- Multi-story handling
- Input validation logic
- Error handling
- Test generation
- Story dependencies

**Expected Artifacts**:
- Multiple stories (3-5)
- API routes implementation
- Validation schemas
- Unit tests
- QA report with test results

---

### 3. Complex Todo App (`complex_todo_app`)

**Concept**: Todo list REST API with user authentication, CRUD operations, due dates, categories, and search functionality

**Purpose**: Stress test with complex requirements

**Duration**: ~10-15 minutes

**Validates**:
- Complex story breakdown
- Authentication implementation
- Database modeling
- Advanced features (search, filtering)
- Multiple iterations

**Expected Artifacts**:
- 6+ stories
- Authentication middleware
- Database models
- CRUD endpoints
- Comprehensive test suite

---

### 4. Database Integration (`database_integration`)

**Concept**: User management API with SQLite database, CRUD operations, and pagination

**Purpose**: Validate database layer integration

**Duration**: ~5-7 minutes

**Validates**:
- DB layer activation
- Dual-write functionality
- Story persistence
- Metrics collection
- Database backups

**Expected Artifacts**:
- `data/pipeline.db`
- Database models in generated code
- Migration scripts (if applicable)
- Backup in `artifacts/db_backups/`

## Output Structure

After execution, the report directory contains:

```
artifacts/e2e_reports/<timestamp>/
├── report.md                          # Main report
├── metrics.json                       # JSON metrics
├── simple_health_check_test.log       # Test logs
├── simple_health_check_artifacts/     # Snapshot
│   ├── planning/
│   ├── project/
│   └── artifacts/
├── medium_calculator_test.log
├── medium_calculator_artifacts/
├── complex_todo_app_test.log
├── complex_todo_app_artifacts/
└── database_integration_artifacts/
```

### Report Contents

**report.md** includes:

1. **Summary**: Pass/fail counts, success rate
2. **Test Results**: Per-scenario status and duration
3. **Configuration**: Current settings snapshot
4. **Recommendations**: Actionable next steps
5. **Artifacts Location**: Paths to all generated files

**metrics.json** structure:

```json
{
  "timestamp": "20251201_103045",
  "total_tests": 4,
  "passed": 3,
  "failed": 1,
  "skipped": 0,
  "success_rate": 75.00,
  "scenarios": {
    "simple_health_check": {
      "result": "PASS",
      "duration_seconds": 142,
      "artifacts_path": "artifacts/e2e_reports/.../simple_health_check_artifacts"
    },
    ...
  }
}
```

## Validation Checks

### Pre-flight Checks

Before running tests, the script validates:

1. **Environment**:
   - Python venv exists
   - pytest installed
   - config.yaml present

2. **Providers**:
   - Vertex AI authentication (gcloud)
   - Ollama connectivity (optional)
   - Provider configuration

3. **State**:
   - planning/ directory status
   - Database layer status
   - Existing artifacts warning

### Artifact Validation

After each test, validates:

- ✅ `planning/requirements.yaml` exists
- ✅ `planning/stories.yaml` exists and valid
- ✅ `project/` directory has content
- ✅ QA reports generated
- ✅ No critical errors in logs
- ✅ Stories have required fields

## Integration with Makefile

The test battery complements existing make targets:

```bash
# Unit tests (fast)
make test                              # or .venv/bin/pytest

# Smoke tests (provider connectivity)
.venv/bin/pytest tests/smoke/ -v

# E2E tests (full pipeline)
./scripts/test_e2e_battery.sh

# Single iteration (manual)
make iteration CONCEPT="Your idea"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: make setup
      - name: Authenticate GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - name: Run E2E battery (quick)
        run: ./scripts/test_e2e_battery.sh --quick --verbose
      - name: Upload report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-report
          path: artifacts/e2e_reports/
```

### Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed
- Other: Script error (missing deps, invalid scenario, etc.)

## Troubleshooting

### Common Issues

#### 1. Provider Authentication Failed

```
[WARN] Vertex AI: not authenticated
```

**Solution**:
```bash
gcloud auth application-default login
```

#### 2. Tests Timeout

**Solution**:
- Use `--quick` mode
- Increase timeout in `make iteration` (edit Makefile)
- Check provider latency

#### 3. Artifact Validation Fails

```
[FAIL] Missing: planning/stories.yaml
```

**Solution**:
- Check `<scenario>_test.log` for errors
- Verify Architect role configuration
- Run manually: `make ba CONCEPT="..." && make po && make plan`

#### 4. Database Tests Fail

**Solution**:
- Verify `config.yaml` has `database.enabled: true`
- Check `data/pipeline.db` permissions
- Run: `./scripts/db_verify.py`

### Debug Mode

For detailed debugging:

```bash
# Verbose + no cleanup
./scripts/test_e2e_battery.sh --scenario simple --verbose --no-cleanup

# Then inspect
ls -la planning/
ls -la project/
tail -f artifacts/e2e_reports/<timestamp>/simple_health_check_test.log
```

## Best Practices

### Before Running

1. ✅ Authenticate with providers: `gcloud auth application-default login`
2. ✅ Ensure clean state: `make clean FLUSH=1`
3. ✅ Verify config: `make show-config`
4. ✅ Check connectivity: `.venv/bin/pytest tests/smoke/ -v`

### During Development

- Run `--scenario simple` frequently for quick feedback
- Use `--no-cleanup` when debugging specific scenarios
- Enable `--verbose` to see real-time progress

### For Releases

- Run full battery: `./scripts/test_e2e_battery.sh --scenario all`
- Archive reports: `tar -czf e2e_reports_vX.Y.Z.tar.gz artifacts/e2e_reports/`
- Compare metrics across versions

## Performance Benchmarks

Typical execution times (on MacBook Pro M1, Vertex AI gemini-2.5-flash):

| Scenario | Duration | Stories | Iterations |
|----------|----------|---------|------------|
| Simple   | 2-3 min  | 1-2     | 1          |
| Medium   | 5-7 min  | 3-5     | 2          |
| Complex  | 10-15 min| 6-8     | 3          |
| Database | 5-7 min  | 3-4     | 2          |
| **All**  | **20-30 min** | **13-19** | **8** |

**Note**: Times vary based on:
- Provider latency
- Model speed (flash vs pro)
- Network connectivity
- Story complexity classification

## Extending the Battery

To add new scenarios, edit `scripts/test_e2e_battery.sh`:

```bash
run_my_custom_scenario() {
  run_test_scenario \
    "my_custom_test" \
    "Description of what to build" \
    2 \        # max_loops
    "medium"   # complexity
}
```

Then add to `main()`:

```bash
case "$SCENARIO" in
  ...
  custom)
    run_my_custom_scenario
    ;;
  all)
    ...
    run_my_custom_scenario
    ;;
esac
```

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Project overview
- [DATABASE_LAYER_PLAN.md](DATABASE_LAYER_PLAN.md) - Database architecture
- [COMPLEXITY_ANALYZER.md](COMPLEXITY_ANALYZER.md) - Routing system
- [README.md](../README.md) - Getting started

## Support

For issues or questions:

1. Check test logs in `artifacts/e2e_reports/<timestamp>/`
2. Review [troubleshooting](#troubleshooting) section
3. Run individual components: `make ba`, `make plan`, `make dev STORY=S1`
4. Open GitHub issue with report.md and relevant logs

---

**Task**: E2E test battery - Documentation
**Last Updated**: 2025-12-01
