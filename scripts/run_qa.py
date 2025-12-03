# scripts/run_qa.py
from __future__ import annotations
import os, sys, json, subprocess, pathlib, re, datetime
from scripts.utils.db_context import get_db_context_or_default
from scripts.utils.db_logger import DbLogger
from scripts.utils.qa_prompt_builder import build_qa_config
from scripts.utils.orchestrator_facade import log_cycle_end, log_cycle_start
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from typing import Optional
import yaml
import typer
from common import ensure_dirs, ROOT
from logger import logger # Import the logger
from drivers.registry import load_driver  # P2.2: Driver integration for QA
from scripts.utils.runner import driver_log_name, normalize_rc, run_driver_cmd
from drivers.detect import has_idf, has_west
from scripts.utils.driver_command import DriverCommand

QA_ART_DIR = ROOT / "artifacts" / "qa"
QA_ART_DIR.mkdir(parents=True, exist_ok=True)
# REPORT and STORY_LOG_DIR are now dynamic per story
DEV_ART_DIR = ROOT / "artifacts" / "dev"

BACKEND_PREFIX = "project/backend-fastapi/"
WEB_PREFIX = "project/web-express/"

def _matches_area(path: str, prefix: str) -> bool:
    return path.startswith(prefix) or path == prefix.rstrip("/")

def has_any_test(py_dir: pathlib.Path) -> bool:
    if not py_dir.exists():
        logger.debug(f"[QA] Directory not found: {py_dir}")
        return False
    for p in py_dir.rglob("test_*.py"):
        logger.debug(f"[QA] Found Python test file: {p}")
        return True
    for p in py_dir.rglob("*_test.py"):
        return True
    logger.debug(f"[QA] No Python test files found in {py_dir}")
    return False

def has_any_web_test(web_dir: pathlib.Path) -> bool:
    if not web_dir.exists():
        logger.debug(f"[QA] Web directory not found: {web_dir}")
        return False
    tests = web_dir / "tests"
    if not tests.exists():
        logger.debug(f"[QA] Web tests directory not found: {tests}")
        return False
    for p in tests.rglob("*.test.js"):
        return True
    for p in tests.rglob("*.test.ts"):
        return True
    logger.debug(f"[QA] No Web test files found in {web_dir}")
    return False

def load_dev_snapshot(story_id: str) -> list[str]:
    """Load the last developer artifact list for a story."""
    if not story_id:
        return []

    story_dir = DEV_ART_DIR / story_id
    files_path = story_dir / "files.json"
    if not files_path.exists():
        logger.debug(f"[QA] No developer snapshot found for story {story_id} in {files_path}")
        return []

    try:
        data = json.loads(files_path.read_text(encoding="utf-8"))
        paths = []
        if isinstance(data, list):
            for entry in data:
                rel_path = entry.get("path")
                if isinstance(rel_path, str):
                    paths.append(rel_path.strip())
        logger.debug(f"[QA] Loaded {len(paths)} changed paths from developer snapshot for {story_id}")
        return paths
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"[QA] Failed to load developer snapshot for {story_id}: {exc}")
        return []

def log_contains_import_error(story_art_dir: pathlib.Path) -> list[str]:
    """Inspect QA logs for ModuleNotFoundError entries and return missing modules."""
    log_file = story_art_dir / "logs.txt"
    if not log_file.exists():
        logger.debug(f"[QA] logs.txt not found in {story_art_dir} for import error check.")
        return []
    text = log_file.read_text(encoding="utf-8")
    matches = re.findall(r"ModuleNotFoundError: No module named '([^']+)'", text)
    if matches:
        logger.debug(f"[QA] Found import errors for modules: {', '.join(matches)}")
    return matches

def fix_backend_test_imports(test_dir: pathlib.Path) -> bool:
    """Normalize backend test imports so they reference local app package."""
    if not test_dir.exists():
        logger.warning(f"[QA] Test directory not found for import fix: {test_dir}")
        return False

    replacements = [
        ("project.backend-fastapi.app", "app"),
        ("backend_fastapi.app", "app"),
    ]
    changed = False

    for py_test in test_dir.rglob("test_*.py"):
        try:
            text = py_test.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning(f"[QA] Could not read {py_test} for import fix: {exc}")
            continue

        new_text = text
        for old, new in replacements:
            new_text = new_text.replace(old, new)

        if new_text != text:
            py_test.write_text(new_text, encoding="utf-8")
            changed = True
            logger.info(f"[QA] Fixed imports in {py_test}")

    if changed:
        logger.info("[QA] Backend test imports auto-corrected.")
    else:
        logger.debug("[QA] No backend test imports needed correction.")
    return changed

def analyze_test_failures(story_art_dir: pathlib.Path, areas, be_rc, web_rc):
    """Analyze test logs to extract specific failure details"""
    failure_details = {
        "backend": {"errors": [], "warnings": [], "missing_coverage": []},
        "web": {"errors": [], "warnings": [], "missing_coverage": []}
    }

    # Analyze backend logs (pytest)
    pytest_log = story_art_dir / "pytest_output.txt"
    if pytest_log.exists():
        pytest_output = pytest_log.read_text(encoding="utf-8")
        failure_details["backend"]["errors"].extend(extract_pytest_errors(pytest_output))
        failure_details["backend"]["warnings"].extend(extract_pytest_warnings(pytest_output))
        logger.debug(f"[QA] Pytest output analyzed. Errors: {len(failure_details['backend']['errors'])}, Warnings: {len(failure_details['backend']['warnings'])}")


        # Add error for command failures
        if be_rc == 127:
            error_msg = "pytest command not found. Make sure pytest is installed in project .venv/bin/pytest"
            failure_details["backend"]["errors"].append({
                "test": "pytest_execution",
                "error": error_msg,
                "type": "environment_fail"
            })
            logger.error(f"[QA] Backend test environment error: {error_msg}")


        # Add error for web command failures
        if web_rc == 127:
            error_msg = "npm command not found. Make sure npm is available for web tests"
            failure_details["web"]["errors"].append({
                "test": "npm_execution",
                "error": error_msg,
                "type": "environment_fail"
            })
            logger.error(f"[QA] Web test environment error: {error_msg}")


    # Analyze web logs (npm test - jest)
    npm_log = story_art_dir / "npm_output.txt"
    if npm_log.exists():
        npm_output = npm_log.read_text(encoding="utf-8")
        failure_details["web"]["errors"].extend(extract_npm_errors(npm_output))
        logger.debug(f"[QA] NPM output analyzed. Errors: {len(failure_details['web']['errors'])}")


    return failure_details

def extract_pytest_errors(output: str):
    """Extract specific pytest errors"""
    errors = []
    lines = output.split('\n')
    for i, line in enumerate(lines):
        # Look for pytest error patterns
        if 'FAILED' in line and '::' in line:
            test_name = line.strip().split('::')[-1].split()[0]
            # Get following error lines
            error_detail = []
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip() and not lines[j].startswith('='):
                    error_detail.append(lines[j])
                    if 'AssertionError' in lines[j] or 'Exception' in lines[j]:
                        break
            errors.append({
                "test": test_name,
                "error": '\n'.join(error_detail[:3]),  # First 3 error lines
                "type": "pytest_failure"
            })
            logger.debug(f"[QA] Pytest failure detected: {test_name}")
        elif 'ERROR' in line and '::' in line:
            test_name = line.strip().split('::')[-1].split()[0]
            errors.append({
                "test": test_name,
                "error": "Configuration or import error",
                "type": "pytest_error"
            })
            logger.debug(f"[QA] Pytest configuration/import error detected: {test_name}")
        elif line.strip().startswith("ERROR collecting "):
            collected_target = line.strip()[len("ERROR collecting "):]
            # capture a few follow-up lines for context
            detail_lines = []
            for j in range(i+1, min(i+6, len(lines))):
                if lines[j].strip() and not lines[j].startswith('='):
                    detail_lines.append(lines[j])
            errors.append({
                "test": collected_target,
                "error": '\n'.join(detail_lines[:3]),
                "type": "pytest_collection_error"
            })
            logger.error(f"[QA] Pytest collection error detected for: {collected_target}")
    return errors

def extract_pytest_warnings(output: str):
    """Extract pytest warnings"""
    warnings = []
    if 'no tests ran' in output.lower():
        warnings.append("No tests found to execute")
        logger.warning("[QA] Pytest: No tests found to execute.")
    if 'warning' in output.lower():
        warnings.append("There are warnings in test execution")
        logger.warning("[QA] Pytest: Warnings in test execution.")
    return warnings

def extract_npm_errors(output: str):
    """Extract specific npm/jest errors"""
    errors = []
    lines = output.split('\n')
    for i, line in enumerate(lines):
        # Look for failed tests in Jest
        if '✗' in line or '✕' in line:
            # Extract test name
            test_info = []
            for j in range(max(0, i-3), min(i+5, len(lines))):
                test_info.append(lines[j])
            clean_test_info = '\n'.join(test_info).strip()
            errors.append({
                "test": "Unknown test",
                "error": clean_test_info,
                "type": "jest_failure"
            })
            logger.debug(f"[QA] Jest failure detected: {clean_test_info[:100]}...")
    return errors


def has_collection_errors(failure_details: dict) -> bool:
    """Return True if failure details include pytest collection errors."""
    for area in failure_details.values():
        for err in area.get("errors", []):
            err_type = err.get("type", "")
            err_text = (err.get("error") or "").lower()
            if err_type in {"pytest_collection_error", "pytest_error"}:
                logger.debug(f"[QA] Collection error found: type={err_type}, text={err_text[:50]}...")
                return True
            if "error collecting" in err_text:
                logger.debug(f"[QA] 'error collecting' keyword found in error text: {err_text[:50]}...")
                return True
    logger.debug("[QA] No collection errors found.")
    return False

# Task 1.4: Extract helpers for SRP/SoC + testability

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


def _build_qa_summary(
    story_art_dir: pathlib.Path,
    be_rc: int | None,
    web_rc: int | None,
    run_backend_tests: bool,
    run_web_tests: bool,
    collection_errors_present: bool
) -> dict:
    """Build standardized QA summary (pure function for report generation).

    Args:
        story_art_dir: artifacts directory for this story
        be_rc: backend test return code
        web_rc: web test return code
        run_backend_tests: whether backend tests were executed
        run_web_tests: whether web tests were executed
        collection_errors_present: whether pytest collection errors were found

    Returns:
        qa_summary dict with version, timestamp, areas
    """
    def _norm(area_name: str, rc_val: int | None, executed: bool, tools: dict | None, logs: list[str], reason: str | None) -> dict:
        def _normalized_rc(raw: int | None) -> int:
            if raw is None or raw == 0:
                return 0
            if raw == 127:
                return 127
            return 1 if not collection_errors_present else 4
        # status mapping
        if rc_val is None:
            status_m = "skip_not_configured"
        elif rc_val == 0:
            status_m = "run_pass" if executed else "skip_no_tests"
        elif rc_val == 127:
            status_m = "skip_tool_missing"
        elif collection_errors_present:
            status_m = "error_collection"
        else:
            status_m = "run_fail"
        return {
            "area": area_name,
            "executed": bool(executed),
            "rc": _normalized_rc(rc_val),
            "status": status_m,
            "reason": reason,
            "tools_present": tools or {},
            "logs": logs,
        }

    def _glob_logs(prefix: str) -> list[str]:
        out = []
        for p in story_art_dir.glob(f"{prefix}*.log"):
            try:
                out.append(str(p.relative_to(ROOT)))
            except Exception:
                out.append(str(p))
        return sorted(out)

    tools_backend = {"pytest": (ROOT / ".venv" / "bin" / "pytest").exists()}
    tools_web = {"jest": (ROOT / "project" / "web-express" / "node_modules" / ".bin" / "jest").exists()}
    tools_emb: dict = {}

    qa_summary = {
        "version": 1,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "areas": {
            "backend": _norm("backend", be_rc if be_rc is not None else (0 if not run_backend_tests else None), bool(run_backend_tests), tools_backend, _glob_logs("backend_"), None if (be_rc in (0, None)) else "backend tests failed"),
            "web": _norm("web", web_rc if web_rc is not None else (0 if not run_web_tests else None), bool(run_web_tests), tools_web, _glob_logs("frontend_") + _glob_logs("web_"), None if (web_rc in (0, None)) else "web tests failed"),
            "embedded": _norm("embedded", 0, False, tools_emb, _glob_logs("embedded_"), "Not executed in QA unless configured"),
        },
    }

    return qa_summary


def run_cmd(cmd: list[str], story_art_dir: pathlib.Path, cwd: str | None = None) -> int:
    try:
        logger.info(f"[QA] Running command: {' '.join(cmd)} (cwd={cwd or os.getcwd()})")
        res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Save logs separated by test type
        log_file = story_art_dir / f"{cmd[0] if cmd else 'unknown'}_output.txt"
        log_file.write_text(res.stdout, encoding="utf-8")
        logger.debug(f"[QA] Command output saved to {log_file}")


        # Also maintain general logs file
        (story_art_dir / "logs.txt").write_text(res.stdout, encoding="utf-8")
        logger.debug(f"[QA] Command output saved to story-specific logs.txt")


        # Persist log per story for traceability
        story_id = story_art_dir.name
        timestamp = datetime.datetime.utcnow().isoformat()
        story_log = story_art_dir / "run.log"
        with story_log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== {timestamp} UTC | command: {' '.join(cmd)} ===\n")
            handle.write(res.stdout)
            handle.write("\n")
        logger.debug(f"[QA] Command output appended to story log: {story_log}")


        # Add specific error reporting for common return codes
        error_details = ""
        if res.returncode == 127:
            # Command not found
            error_details = f"Command not found: {cmd[0]}. Verify virtual environment is activated and dependencies are installed."
            logger.error(f"[QA] ERROR: {error_details}")


        # Save command-specific error for final report
        if res.returncode != 0:
            error_file = story_art_dir / f"{cmd[0] if cmd else 'unknown'}_error.txt"
            error_file.write_text(error_details or "Unknown command error", encoding="utf-8")
            logger.error(f"[QA] Command failed with return code {res.returncode}. Error details saved to {error_file}")


        logger.debug(f"[QA] Command stdout/stderr:\n{res.stdout}")
        return res.returncode
    except FileNotFoundError as e:
        error_msg = f"Command not found: {cmd[0] if cmd else 'unknown'} - {e}"
        logger.critical(f"[QA] FATAL: {error_msg}")
        (story_art_dir / "logs.txt").write_text(error_msg, encoding="utf-8")
        timestamp = datetime.datetime.utcnow().isoformat()
        story_log = story_art_dir / "run.log"
        with story_log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== {timestamp} UTC | command: {' '.join(cmd)} ===\n")
            handle.write(error_msg + "\n")
        return 127
    except Exception as e:
        logger.critical(f"[QA] Unhandled exception in run_cmd: {e}", exc_info=True)
        return 1


def main() -> None:
    """Execute QA checks for the current story, writing artifacts and summary."""
    story_env = os.environ.get("STORY", "")
    story_id, allow_no_tests, run_tests = build_qa_config(story_env)
    cfg, drivers_cfg, targets = _load_qa_config()
    db = get_db_context_or_default()
    log_cycle_start(db, "qa", story_id, "QA run started")

    story_art_dir = QA_ART_DIR / story_id
    story_art_dir.mkdir(parents=True, exist_ok=True)
    backend_tests_dir = ROOT / "project" / "backend-fastapi" / "tests"
    web_root = ROOT / "project" / "web-express"

    # Detect touched areas from dev snapshot
    changed_paths = load_dev_snapshot(story_id)
    be_has = any(_matches_area(p, BACKEND_PREFIX) for p in changed_paths)
    web_has = any(_matches_area(p, WEB_PREFIX) for p in changed_paths)

    run_backend_tests = run_tests or be_has or not changed_paths
    run_web_tests = run_tests or web_has

    be_tests_present = has_any_test(backend_tests_dir)
    web_tests_present = has_any_web_test(web_root)

    areas = {
        "backend": {"has_tests": be_tests_present, "rc": None},
        "web": {"has_tests": web_tests_present, "rc": None},
        "embedded": {"has_tests": False, "rc": None},
    }

    be_rc = None
    web_rc = None

    if run_backend_tests and be_tests_present:
        fix_backend_test_imports(backend_tests_dir)
        be_rc = run_cmd(
            [str(ROOT / ".venv" / "bin" / "pytest"), "-q", "--disable-warnings", "--maxfail=1"],
            story_art_dir,
            cwd=str(ROOT / "project" / "backend-fastapi"),
        )
    else:
        be_rc = 0
    areas["backend"]["rc"] = be_rc

    if run_web_tests and web_tests_present and (web_root / "package.json").exists():
        npm_cmd = ["npm", "test", "--", "--passWithNoTests"]
        web_rc = run_cmd(npm_cmd, story_art_dir, cwd=str(web_root))
    else:
        web_rc = 0 if not run_web_tests else None
    areas["web"]["rc"] = web_rc

    # Embedded drivers (optional)
    emb_rc = None
    if drivers_cfg.get("enabled") and targets.get("embedded"):
        emb = load_driver("embedded", targets["embedded"])
        if emb and getattr(emb, "test", None):
            emb_cmd = DriverCommand("embedded", emb.id, "test", emb.test.command, story_art_dir)
            emb_rc = emb_cmd.execute()
    areas["embedded"]["rc"] = emb_rc if emb_rc is not None else 0

    failure_details = analyze_test_failures(story_art_dir, areas, be_rc, web_rc)
    collection_errors_present = has_collection_errors(failure_details)

    if allow_no_tests:
        any_has_tests = any(v["has_tests"] for v in areas.values())
        if collection_errors_present:
            status = "blocked_fatal"
            code = 4
        elif any_has_tests:
            status = "pass"
            code = 0
        else:
            status = "no_tests"
            code = 3
    else:
        any_fail = any(v["rc"] not in (0,) for v in areas.values())
        if collection_errors_present:
            status = "blocked_fatal"
            code = 4
        elif any_fail:
            status = "fail"
            code = 2
        else:
            status = "pass"
            code = 0

    report = {
        "status": status,
        "allow_no_tests": allow_no_tests,
        "areas": areas,
        "failure_details": failure_details,
        "story_context": story_id,
    }

    qa_summary = _build_qa_summary(
        story_art_dir,
        be_rc,
        web_rc,
        run_backend_tests,
        run_web_tests,
        collection_errors_present
    )

    try:
        (story_art_dir / "qa_summary.json").write_text(json.dumps(qa_summary, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"[QA] Wrote summary: {story_art_dir / 'qa_summary.json'}")
    except Exception as e:
        logger.warning(f"[QA] Could not write qa_summary.json: {e}")

    report_path = story_art_dir / "report.json"
    report_json = json.dumps(report, indent=2)
    report_path.write_text(report_json, encoding="utf-8")
    (QA_ART_DIR / "last_report.json").write_text(report_json, encoding="utf-8")
    logger.info(f"[QA] QA report for {story_id} written to {report_path}")

    if db.enabled:
        db.save_artifact("qa", "report_json", report_json)
        if qa_summary:
            db.save_artifact("qa", "qa_summary", json.dumps(qa_summary, indent=2, ensure_ascii=False))
        attempt_status = "success" if status == "pass" else "error"
        error_msg = None if status == "pass" else f"QA failed: {status}"
        db.log_attempt(
            story_id=story_id,
            role="qa",
            provider="local",
            model="pytest",
            status=attempt_status,
            duration_ms=None,
            error_message=error_msg,
            artifacts_path=str(story_art_dir),
        )
        log_cycle_end(db, "qa", story_id, status, f"QA completed with status: {status}")

    logger.info(f"[QA] Final status={status} (detail in {report_path})")
    sys.exit(code)


def run_quality_checks(*, allow_no_tests: bool = True, story: str = "") -> dict:
    previous_story = os.environ.get("STORY")
    previous_allow = os.environ.get("ALLOW_NO_TESTS")
    os.environ["ALLOW_NO_TESTS"] = "1" if allow_no_tests else "0"
    if story:
        os.environ["STORY"] = story
    elif "STORY" in os.environ:
        os.environ.pop("STORY")

    exit_code = 0
    try:
        main()
    except SystemExit as exc:
        exit_code = int(exc.code or 0)
    finally:
        if previous_allow is not None:
            os.environ["ALLOW_NO_TESTS"] = previous_allow
        else:
            os.environ.pop("ALLOW_NO_TESTS", None)
        if previous_story is not None:
            os.environ["STORY"] = previous_story
        else:
            os.environ.pop("STORY", None)

    report_path = QA_ART_DIR / "last_report.json"
    report_data = {}
    if report_path.exists():
        try:
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report_data = {}

    status = report_data.get("status", "unknown")
    return {
        "status": status,
        "code": exit_code,
        "report_path": str(report_path),
        "report": report_data,
    }


app = typer.Typer(help="QA agent CLI")


@app.command()
def run(
    allow_no_tests: bool = typer.Option(True, help="Allow passing when tests are missing"),
    story_id: Optional[str] = typer.Option(None, help="Story identifier for logging"),
) -> None:
    result = run_quality_checks(allow_no_tests=allow_no_tests, story=story_id or "")
    typer.echo(json.dumps(result, indent=2))


@app.command()
def serve(reload: bool = typer.Option(False, help="Auto-reload server on code changes")) -> None:
    from a2a.cards import qa_card
    from a2a.runtime import run_agent

    card, handlers = qa_card()
    run_agent("qa", card, handlers, reload=reload)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        main()
    else:
        app()
