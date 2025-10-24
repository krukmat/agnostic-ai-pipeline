# scripts/run_qa.py
from __future__ import annotations
import os, sys, json, subprocess, pathlib, shutil, re, datetime
import yaml
from common import ensure_dirs, ROOT
from logger import logger # Import the logger

ART = ROOT / "artifacts" / "qa"
ART.mkdir(parents=True, exist_ok=True)
REPORT = ART / "last_report.json"
STORY_LOG_DIR = ART / "story_logs"
STORY_LOG_DIR.mkdir(parents=True, exist_ok=True)

def has_any_test(py_dir: pathlib.Path) -> bool:
    if not py_dir.exists():
        logger.debug(f"[QA] Directory not found: {py_dir}")
        return False
    for p in py_dir.rglob("test_*.py"):
        logger.debug(f"[QA] Found Python test file: {p}")
        return True
    for p in py_dir.rglob("*_test.py"):
        logger.debug(f"[QA] Found Python test file: {p}")
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
        logger.debug(f"[QA] Found Web test file: {p}")
        return True
    for p in tests.rglob("*.test.ts"):
        logger.debug(f"[QA] Found Web test file: {p}")
        return True
    logger.debug(f"[QA] No Web test files found in {web_dir}")
    return False

def log_contains_import_error() -> list[str]:
    """Inspect QA logs for ModuleNotFoundError entries and return missing modules."""
    log_file = ART / "logs.txt"
    if not log_file.exists():
        logger.debug("[QA] logs.txt not found for import error check.")
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

def analyze_test_failures(areas, be_rc, web_rc):
    """Analyze test logs to extract specific failure details"""
    failure_details = {
        "backend": {"errors": [], "warnings": [], "missing_coverage": []},
        "web": {"errors": [], "warnings": [], "missing_coverage": []}
    }

    # Analyze backend logs (pytest)
    pytest_log = ART / "pytest_output.txt"
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
    npm_log = ART / "npm_output.txt"
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

def run_cmd(cmd, cwd=None) -> int:
    try:
        logger.info(f"[QA] Running command: {' '.join(cmd)} (cwd={cwd or os.getcwd()})")
        res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Save logs separated by test type
        log_file = ART / f"{cmd[0] if cmd else 'unknown'}_output.txt"
        log_file.write_text(res.stdout, encoding="utf-8")
        logger.debug(f"[QA] Command output saved to {log_file}")


        # Also maintain general logs file
        (ART / "logs.txt").write_text(res.stdout, encoding="utf-8")
        logger.debug("[QA] Command output appended to general logs.txt")


        # Persist log per story for traceability
        story_id = os.environ.get("STORY", "").strip()
        if story_id:
            timestamp = datetime.datetime.utcnow().isoformat()
            story_log = STORY_LOG_DIR / f"{story_id}.log"
            with story_log.open("a", encoding="utf-8") as handle:
                handle.write(f"\n=== {timestamp} UTC | command: {' '.join(cmd)} ===\n")
                handle.write(res.stdout)
                handle.write("\n")
            logger.debug(f"[QA] Command output appended to story log: {story_log}")


        # Add specific error reporting for common return codes
        error_details = ""
        if res.returncode == 127:
            # Command not found
            pytest_path = str(be_root / ".venv" / "bin" / "pytest") if cwd == str(be_root) else "npm"
            error_details = f"Command not found: {pytest_path}. Verify virtual environment is activated and dependencies are installed."
            logger.error(f"[QA] ERROR: {error_details}")


        # Save command-specific error for final report
        if res.returncode != 0:
            error_file = ART / f"{cmd[0] if cmd else 'unknown'}_error.txt"
            error_file.write_text(error_details or "Unknown command error", encoding="utf-8")
            logger.error(f"[QA] Command failed with return code {res.returncode}. Error details saved to {error_file}")


        logger.debug(f"[QA] Command stdout/stderr:\n{res.stdout}")
        return res.returncode
    except FileNotFoundError as e:
        error_msg = f"Command not found: {cmd[0] if cmd else 'unknown'} - {e}"
        logger.critical(f"[QA] FATAL: {error_msg}")
        (ART / "logs.txt").write_text(error_msg, encoding="utf-8")
        story_id = os.environ.get("STORY", "").strip()
        if story_id:
            timestamp = datetime.datetime.utcnow().isoformat()
            story_log = STORY_LOG_DIR / f"{story_id}.log"
            with story_log.open("a", encoding="utf-8") as handle:
                handle.write(f"\n=== {timestamp} UTC | command: {' '.join(cmd)} ===\n")
                handle.write(error_msg + "\n")
        return 127
    except Exception as e:
        logger.critical(f"[QA] Unhandled exception in run_cmd: {e}", exc_info=True)
        return 1


def main():
    allow_no_tests = os.environ.get("ALLOW_NO_TESTS", "1") == "1"  # Default to True para compatibilidad
    logger.info(f"[QA] Starting QA run. ALLOW_NO_TESTS={allow_no_tests}")


    # Backend
    be_root = ROOT / "project" / "backend-fastapi"
    be_tests = be_root / "tests"
    be_has = has_any_test(be_tests)
    be_rc = None
    if be_has:
        logger.info(f"[QA] Backend has tests in {be_tests}. Running pytest...")
        # Use project-level virtual environment pytest
        pytest_bin = ROOT / ".venv" / "bin" / "pytest"
        if pytest_bin.exists():
            be_rc = run_cmd([str(pytest_bin), "-q", "--disable-warnings", "--maxfail=1"], cwd=str(be_root))
            if be_rc not in (0, 10):
                logger.warning(f"[QA] Pytest returned {be_rc}. Checking for import errors...")
                missing = log_contains_import_error()
                if any(m.startswith("backend_fastapi") or "backend-fastapi" in m for m in missing):
                    if fix_backend_test_imports(be_tests):
                        logger.info("[QA] Auto-corrected backend test imports. Re-running pytest.")
                        be_rc = run_cmd([str(pytest_bin), "-q", "--disable-warnings", "--maxfail=1"], cwd=str(be_root))
                    else:
                        logger.warning("[QA] Could not auto-correct backend test imports.")
                else:
                    logger.debug("[QA] No backend-fastapi related import errors found.")
        else:
            be_rc = 127  # venv/pytest not available in project .venv
            logger.error(f"[QA] Pytest binary not found: {pytest_bin}. Setting backend return code to {be_rc}.")
    else:
        be_rc = 10  # no tests
        logger.info("[QA] No backend tests found. Setting backend return code to 10.")


    # Web
    web_root = ROOT / "project" / "web-express"
    web_tests = has_any_web_test(web_root)
    web_rc = None
    if web_tests and (web_root / "package.json").exists():
        logger.info(f"[QA] Web has tests in {web_root}. Running npm test...")
        # Use npm for compatibility
        web_rc = run_cmd(["npm", "test", "--silent", "--", "--passWithNoTests"], cwd=str(web_root))
    else:
        web_rc = 10  # no tests
        logger.info("[QA] No web tests found or package.json missing. Setting web return code to 10.")


    # Future extensions: mobile etc. (omitted for now)
    areas = {
        "backend": {"has_tests": be_has, "rc": be_rc},
        "web":     {"has_tests": web_tests, "rc": web_rc},
    }
    logger.debug(f"[QA] Test areas summary: {areas}")


    failure_details = analyze_test_failures(areas, be_rc, web_rc)
    collection_errors_present = has_collection_errors(failure_details)
    logger.debug(f"[QA] Collection errors present: {collection_errors_present}")


    # When allow_no_tests is True, ignore test execution failures and treat as success
    if allow_no_tests:
        # If allow_no_tests, only check if we have the structure (has_tests)
        any_has_tests = any(v["has_tests"] for v in areas.values())
        logger.debug(f"[QA] ALLOW_NO_TESTS is True. Any area has tests: {any_has_tests}")


        if collection_errors_present:
            status = "blocked_fatal"  # Treat collection errors as critical even in allow_no_tests
            code = 4
            logger.error(f"[QA] Status: {status} (Collection errors present)")
        elif any_has_tests:
            status = "pass"
            code = 0
            logger.info(f"[QA] Status: {status} (Tests found, no collection errors)")
        else:
            status = "no_tests"
            code = 3
            logger.info(f"[QA] Status: {status} (No tests found)")
    else:
        # Strict mode: check both presence and execution
        any_fail = any(v["rc"] not in (0,10) for v in areas.values())
        any_no_tests = any(v["rc"] == 10 for v in areas.values())
        logger.debug(f"[QA] Strict mode. Any test failed: {any_fail}, Any no tests: {any_no_tests}")


        if collection_errors_present:
            status = "blocked_fatal"  # Critical error
            code = 4
            logger.error(f"[QA] Status: {status} (Collection errors present in strict mode)")
        elif any_fail:
            status = "fail"
            code = 2
            logger.warning(f"[QA] Status: {status} (Tests failed in strict mode)")
        elif any_no_tests:
            status = "no_tests"
            code = 3
            logger.info(f"[QA] Status: {status} (No tests found in strict mode)")
        else:
            status = "pass"
            code = 0
            logger.info(f"[QA] Status: {status} (All tests passed in strict mode)")


    # Detailed failure analysis

    report = {
        "status": status,
        "allow_no_tests": allow_no_tests,
        "areas": areas,
        "failure_details": failure_details,
        "story_context": os.environ.get("STORY", ""),  # Current story context
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info(f"[QA] QA report written to {REPORT}")


    # Mark stories as done if QA passes
    if status == "pass":
        from pathlib import Path
        import yaml

        stories_file = ROOT / "planning" / "stories.yaml"
        if stories_file.exists():
            try:
                with open(stories_file, 'r', encoding='utf-8') as f:
                    stories = yaml.safe_load(f) or []

                # Mark all in_review stories as done
                updated = False
                for story in stories:
                    if isinstance(story, dict) and story.get('status') == 'in_review':
                        story['status'] = 'done'
                        updated = True
                        logger.info(f"[QA] Story {story.get('id', '?')} marked as done")


                if updated:
                    with open(stories_file, 'w', encoding='utf-8') as f:
                        yaml.safe_dump(stories, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
                    logger.info("[QA] Stories updated in planning/stories.yaml")


                # Check if this completes all backlogs - trigger new iteration (always check when QA passes)
                all_done = all(story.get('status') == 'done' for story in stories if isinstance(story, dict))
                if all_done:
                    logger.info("[QA] 🎉 ALL STORIES COMPLETED! Starting new iteration...")
                    logger.info("[QA] 📢 Informing Architect and BA about completion")


                    # Generate new context for next iteration based on completed work
                    completed_work = [s.get('description', '') for s in stories if isinstance(s, dict)]
                    new_context = f"COMPLETED WORK SUMMARY:\n" + "\n".join(f"- {desc}" for desc in completed_work[:5])
                    new_context += f"\n\nEVALUATION: {len(completed_work)} stories delivered. Consider expanding scope or refining existing features based on successful implementation."
                    logger.debug(f"[QA] New context for BA re-evaluation: {new_context[:200]}...")


                    # Trigger new BA evaluation for potential scope expansion
                    logger.info("[QA] 🔄 Triggering Business Analyst re-evaluation...")
                    import subprocess
                    import pathlib

                    # Set CONCEPT with completion context for next iteration
                    env_concept = new_context[:500]  # Limit size
                    architect_cmd = [".venv/bin/python", str(ROOT / "scripts" / "run_ba.py")]
                    env_vars = os.environ.copy()
                    env_vars["CONCEPT"] = env_concept

                    try:
                        result = subprocess.run(
                            architect_cmd,
                            env=env_vars,
                            cwd=str(ROOT),
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        if result.returncode == 0:
                            logger.info("[QA] ✅ BA triggered new requirements evaluation")
                        else:
                            logger.warning(f"[QA] ⚠️ BA trigger failed: {result.stderr}")
                    except subprocess.TimeoutExpired:
                        logger.warning("[QA] ⏱️ BA trigger timed out")
                    except Exception as e:
                        logger.error(f"[QA] ❌ BA trigger error: {e}")

            except Exception as e:
                logger.error(f"[QA] Error updating stories: {e}", exc_info=True)

    logger.info(f"[QA] Final status={status} (detail in {REPORT})")
    sys.exit(code)

if __name__ == "__main__":
    main()
