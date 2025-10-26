# scripts/orchestrate.py
from __future__ import annotations
import os, sys, yaml, pathlib, subprocess, json, datetime, shutil
import asyncio
from typing import Any, Dict
from common import load_config, ensure_dirs
from logger import logger # Import the logger

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from a2a.executors import get_executor, RoleExecutor
from a2a.metrics import save_metrics, instrumented
from scripts.run_ba import generate_requirements
from scripts.run_product_owner import main as run_po
from scripts.run_architect import run_architect_job
from scripts.run_dev import implement_story
from scripts.run_qa import run_quality_checks

ROLE_SKILLS = {
    "business_analyst": "extract_requirements",
    "product_owner": "evaluate_alignment",
    "architect": "generate_plan",
    "developer": "implement_story",
    "qa": "run_quality_checks",
}


async def _local_business_analyst_handler(**payload: Any) -> Dict[str, Any]:
    concept = (payload.get("concept") or "").strip()
    if not concept:
        return {"status": "error", "detail": "concept is required"}
    try:
        result = await generate_requirements(concept)
        return {"status": "ok", **result}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[Executor] Business analyst handler failed.")
        return {"status": "exception", "error": str(exc)}


async def _local_product_owner_handler(**payload: Any) -> Dict[str, Any]:
    try:
        await run_po()
        return {"status": "ok"}
    except SystemExit as exc:
        exit_code = int(exc.code or 1)
        logger.warning(f"[Executor] Product owner exited with code {exit_code}.")
        return {"status": "error", "exit_code": exit_code}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[Executor] Product owner handler failed.")
        return {"status": "exception", "error": str(exc)}


async def _local_architect_handler(**payload: Any) -> Dict[str, Any]:
    try:
        result = await run_architect_job(
            concept=payload.get("concept"),
            architect_mode=payload.get("architect_mode", "normal"),
            story_id=payload.get("story_id", ""),
            detail_level=payload.get("detail_level", "medium"),
            iteration_count=int(payload.get("iteration_count", 1) or 1),
            force_tier=payload.get("force_tier"),
        )
        return {"status": "ok", **result}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[Executor] Architect handler failed.")
        return {"status": "exception", "error": str(exc)}


async def _local_developer_handler(**payload: Any) -> Dict[str, Any]:
    story_id = payload.get("story_id")
    retries_raw = payload.get("retries", payload.get("DEV_RETRIES", 3))
    try:
        retries = int(retries_raw)
    except (TypeError, ValueError):
        retries = 3
    try:
        result = await implement_story(story_id=story_id, retries=retries)
        return {"status": "ok", **result}
    except SystemExit as exc:
        exit_code = int(exc.code or 1)
        logger.warning(
            f"[Executor] Developer exited with code {exit_code} for story {story_id}."
        )
        return {"status": "error", "exit_code": exit_code, "story_id": story_id}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[Executor] Developer handler failed.")
        return {"status": "exception", "error": str(exc), "story_id": story_id}


async def _local_qa_handler(**payload: Any) -> Dict[str, Any]:
    allow_flag = payload.get("allow_no_tests", True)
    if isinstance(allow_flag, str):
        allow_no_tests = str(allow_flag).lower() not in {"0", "false", "no"}
    else:
        allow_no_tests = bool(allow_flag)
    story_id = payload.get("story_id", "") or ""

    result = await asyncio.to_thread(
        run_quality_checks,
        allow_no_tests=allow_no_tests,
        story=story_id,
    )
    status = result.get("status", "unknown")
    return {"status": status, **result}


LOCAL_ROLE_HANDLERS = {
    "business_analyst": _local_business_analyst_handler,
    "product_owner": _local_product_owner_handler,
    "architect": _local_architect_handler,
    "developer": _local_developer_handler,
    "qa": _local_qa_handler,
}

_ROLE_EXECUTORS: dict[str, RoleExecutor] = {}


def _get_executor_for_role(role: str) -> RoleExecutor:
    if role not in LOCAL_ROLE_HANDLERS:
        raise KeyError(f"Unknown role '{role}' requested.")
    executor = _ROLE_EXECUTORS.get(role)
    if executor is None:
        handler = LOCAL_ROLE_HANDLERS[role]
        executor = get_executor(role, handler, skill_id=ROLE_SKILLS[role])
        _ROLE_EXECUTORS[role] = executor
    return executor


async def execute_role(role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    executor = _get_executor_for_role(role)

    @instrumented(role)
    async def _run() -> Dict[str, Any]:
        return await executor.execute(payload)

    return await _run()

# Tracking the number of iterations per story
story_arch_attempts: dict[str, int] = {}
story_dev_attempts: dict[str, int] = {}

_config = load_config()
FORCE_APPROVAL_THRESHOLD = max(
    1,
    int(
        (_config.get("pipeline") or {}).get("force_approval_attempts", 3)
        or 3
    ),
)
DEV_RETRY_THRESHOLD = max(
    1,
    int(
        (_config.get("pipeline") or {}).get("dev_retry_attempts", 3)
        or 3
    ),
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "planning"
STORIES_P = PLAN / "stories.yaml"
NOTES_P = PLAN / "notes.md"
QA_REPORT = ROOT / "artifacts" / "qa" / "last_report.json"
DEV_FAILED_REPORT = ROOT / "artifacts" / "dev" / "failed_stories.md"

def load_stories():
    """Load stories with automatic YAML error recovery"""
    if not STORIES_P.exists():
        logger.info("[loop] planning/stories.yaml not found.")
        return []

    text = STORIES_P.read_text(encoding="utf-8")

    # Primary loading attempt
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "stories" in data:
            data = data["stories"]
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"[loop] Primary YAML error: {e}. Attempting recovery.")
        append_note(f"Primary YAML error: {e}")
        # Try automatic recovery
        try:
            return recover_yaml_automatic(text)
        except Exception as e2:
            logger.error(f"[loop] Automatic recovery failed: {e2}")
            append_note(f"Automatic recovery failed: {e2}")

            # Fallback: try to run fix_stories automatically
            if fix_stories_automatic():
                try:
                    data = yaml.safe_load(STORIES_P.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and "stories" in data:
                        data = data["stories"]
                    return data if isinstance(data, list) else []
                except Exception as e3:
                    logger.critical(f"[loop] Automatic fix failed: {e3}")
                    append_note(f"Automatic fix failed: {e3}")

            # Last fallback: return empty list
            logger.critical("[loop] FATAL: Returning empty story list")
            append_note("FALLBACK: Returning empty story list")
            return []

def save_stories(stories):
    STORIES_P.write_text(yaml.safe_dump(stories, sort_keys=False, allow_unicode=True), encoding="utf-8")
    logger.debug("[loop] Stories saved to planning/stories.yaml")

def recover_yaml_automatic(text: str) -> list:
    """Try to recover YAML automatically with repair strategies"""
    import re

    # Strategy 1: Remove problematic characters at the beginning
    text = text.lstrip()

    # Strategy 2: If everything is commented, automatically uncomment
    if all(line.lstrip().startswith('#') for line in text.splitlines() if line.strip()):
        lines = []
        for line in text.splitlines():
            if line.lstrip().startswith('#'):
                lines.append(re.sub(r'^(\s*)#\s?', r'\1', line))
            else:
                lines.append(line)
        text = '\n'.join(lines)
        logger.debug("[loop] YAML: Applied uncomment strategy.")

    # Strategy 3: Repair common acceptance formats
    lines = text.splitlines()
    fixed_lines = []
    for line in lines:
        # Repair inline acceptance: acceptance: - item
        if 'acceptance:' in line and ('- ' in line or '; ' in line):
            indent = line.find('acceptance:')
            match = re.match(r'^(\s*)acceptance:\s*(.+)', line)
            if match:
                ind, val = match.groups()
                # Convert to multiline
                items = [item.strip('- ;') for item in re.split(r'[,;]-| -', val) if item.strip()]
                if len(items) > 1:
                    fixed_lines.append(f"{ind}acceptance:")
                    for item in items:
                        fixed_lines.append(f"{ind}  - {item}")
                    logger.debug("[loop] YAML: Applied acceptance format repair.")
                    continue
        fixed_lines.append(line)
    text = '\n'.join(fixed_lines)

    # Try to parse again
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "stories" in data:
            data = data["stories"]
        return data if isinstance(data, list) else []
    except Exception as e:
        # Create backup and try minimal repair
        backup_path = STORIES_P.with_suffix('.backup.broken')
        STORIES_P.replace(backup_path)
        logger.error(f"[loop] Unrepairable YAML - backup created: {backup_path}")
        append_note(f"Unrepairable YAML - backup created: {backup_path}")
        raise e

def fix_stories_automatic() -> bool:
    """Automatically run fix_stories to repair YAML"""
    try:
        import subprocess
        result = subprocess.run([
            str(ROOT / ".venv" / "bin" / "python"),
            str(ROOT / "scripts" / "fix_stories.py")
        ], capture_output=True, text=True, cwd=str(ROOT))
        success = result.returncode == 0
        if success:
            logger.info("[loop] fix_stories automatically executed")
            append_note("fix_stories automatically executed")
        else:
            logger.warning(f"[loop] fix_stories failed: {result.stderr}")
            append_note(f"fix_stories failed: {result.stderr}")
        return success
    except Exception as e:
        logger.error(f"[loop] Error running fix_stories: {e}")
        append_note(f"Error running fix_stories: {e}")
        return False

def _wipe_directory_contents(path: pathlib.Path) -> tuple[int, int]:
    """Delete all children inside the given directory (but keep the directory)."""
    if not path.exists():
        logger.debug(f"[cleanup] Directory not found: {path}")
        return (0, 0)

    total_files = 0
    total_bytes = 0
    for child in list(path.iterdir()):
        try:
            if child.is_dir():
                size = sum(f.stat().st_size for f in child.rglob('*') if f.is_file())
                shutil.rmtree(child)
                total_bytes += size
            else:
                total_bytes += child.stat().st_size
                child.unlink()
            total_files += 1
        except Exception as exc:
            logger.warning(f"[cleanup] Warning: could not remove {child}: {exc}")
            append_note(f"Cleanup warning: could not remove {child}: {exc}")
    return (total_files, total_bytes)


def cleanup_artifacts():
    """Automatic cleanup of artifacts, with optional flush of planning/project."""
    try:
        artifacts_dir = ROOT / "artifacts"
        total_files_cleaned = 0
        total_space_cleaned = 0

        if artifacts_dir.exists():
            files, size = _wipe_directory_contents(artifacts_dir)
            total_files_cleaned += files
            total_space_cleaned += size
            logger.debug(f"[cleanup] Cleaned {files} items from artifacts/, freed {size/1024:.1f}KB.")


        # Always recreate qa/dev directories expected by other steps
        ensure_dirs()

        flush_requested = os.environ.get("CLEAN_FLUSH", "0") == "1"
        if flush_requested:
            logger.info("[cleanup] Full flush requested. Cleaning planning/ and project/.")
            files, size = _wipe_directory_contents(PLAN)
            total_files_cleaned += files
            total_space_cleaned += size

            files, size = _wipe_directory_contents(ROOT / "project") # Use ROOT / "project"
            total_files_cleaned += files
            total_space_cleaned += size

            ensure_dirs()  # restore structure after flush
            logger.debug("[cleanup] Restored default project structure after flush.")


        if total_files_cleaned > 0:
            logger.info(
                f"[cleanup] Automatic cleanup: {total_files_cleaned} items removed, {total_space_cleaned/1024:.1f}KB freed"
            )
            append_note(
                f"Automatic cleanup: {total_files_cleaned} items removed, {total_space_cleaned/1024:.1f}KB freed"
            )

    except Exception as e:
        logger.critical(f"[cleanup] Error during cleanup: {e}", exc_info=True)
        append_note(f"Error in automatic cleanup: {e}")

def append_note(text: str):
    NOTES_P.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with NOTES_P.open("a", encoding="utf-8") as f:
        f.write(f"\n### {now}\n{text}\n")
    logger.debug(f"[loop] Appended note to {NOTES_P}")

async def run_architect_for_review(story_id: str, iteration_count: int = 1) -> Dict[str, Any]:
    """Run architect to adjust criteria when story is in review"""
    logger.info(f"[loop] Architect intervening to adjust {story_id} criteria (attempt {iteration_count})")

    # Read concept from multiple sources
    concept = os.environ.get("CONCEPT", "")
    if not concept:
        # Try reading requirements.yaml as backup
        req_file = ROOT / "planning" / "requirements.yaml"
        if req_file.exists():
            with open(req_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract first meaningful line as concept
                lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                concept = lines[0] if lines else "Collaborative task management system"
            logger.debug(f"[loop] Concept from requirements.yaml: {concept[:50]}...")


    if not concept:
        logger.error("[loop] Concept not found for architect intervention.")
        return {"status": "error", "detail": "Concept not available"}

    # Adjust detail level based on iteration
    detail_level = "medium"
    if iteration_count == 1:
        detail_level = "high"  # First intervention: maximum detail
    elif iteration_count == 2:
        detail_level = "maximum"  # Second intervention: extreme detail
    elif iteration_count >= FORCE_APPROVAL_THRESHOLD:
        detail_level = "force_approve"  # Consider forced approval once threshold reached
    else:
        detail_level = "maximum"
    logger.debug(f"[loop] Architect detail level for review: {detail_level}")

    payload = {
        "concept": concept,
        "architect_mode": "review_adjustment",
        "story_id": story_id,
        "detail_level": detail_level,
        "iteration_count": iteration_count,
    }

    result = await execute_role("architect", payload)
    result.setdefault("detail_level", detail_level)
    result.setdefault("story_id", story_id)
    return result

def next_todo(stories):
    for s in stories:
        if s.get("status","").lower() == "todo":
            logger.debug(f"[loop] Found 'todo' story: {s.get('id', 'S?')}")
            return s
    logger.debug("[loop] No 'todo' stories found.")
    return None

# REMOVED: No longer creating separate test stories - tests are part of each user story per TDD

def find_in_review_stories(stories):
    """Find stories in review that need architect intervention"""
    in_review = [s for s in stories if s.get("status","").lower() == "in_review"]
    if in_review:
        logger.debug(f"[loop] Found {len(in_review)} stories in 'in_review' status.")
    return in_review

def check_and_activate_waiting_stories(stories, completed_story_id):
    """Check if ANY quality_gate_waiting stories can be activated after ANY test story completes"""
    activated = []

    # When ANY story that involves tests completes, it potentially frees up ALL quality_gate_waiting stories
    # This is more intelligent - if a story adds or improves tests, ALL waiting stories can now try QA

    story_id_upper = completed_story_id.upper()
    is_test_related_story = (
        "TEST" in story_id_upper or
        "QA" in story_id_upper or
        # Any story that adds substantial testing/code coverage potential
        True  # For now: any successful completion could enable waiting stories
    )
    logger.debug(f"[loop] Completed story {completed_story_id} is test-related: {is_test_related_story}")


    if is_test_related_story:
        # Activate ALL stories currently in quality_gate_waiting
        for story in stories:
            if story.get("status", "").lower() == "quality_gate_waiting":
                # Activate this waiting story back to todo for QA retry
                story["status"] = "todo"
                activated.append(story["id"])
                logger.info(f"[loop] [DEPENDENCY] Activated waiting story {story['id']} after testing capacity improvement by {completed_story_id}")


    return activated

def analyze_qa_failure_severity(qa_failure_details):
    """Analyze the severity of QA failures and determine the type of problem

    Distinguishes between force-acceptable errors (coverage, timing) vs critical errors (syntax, imports).
    """
    failure_details = qa_failure_details or {}
    logger.debug(f"[loop] Analyzing QA failure severity: {json.dumps(failure_details)[:200]}...")


    backend_errors = failure_details.get("backend", {}).get("errors", [])
    web_errors = failure_details.get("web", {}).get("errors", [])

    # Classify errors by severity
    critical_errors = []      # Syntax, import, config issues - NEVER force-approve
    force_applicable = []    # Missing tests, coverage, timeouts - CAN force-approve for P1/P0
    other_errors = []         # Standard test failures

    # Analyze backend errors
    for error in backend_errors:
        error_msg = error.get("error", "").lower()
        error_type = error.get("type", "")

        # Critical errors that block completely
        if "command not found" in error_msg or "environment_fail" in error_type:
            critical_errors.append(error)
        elif "syntaxerror" in error_msg or "invalid syntax" in error_msg:
            critical_errors.append(error)
        elif error_type in ["pytest_error"] and ("import" in error_msg or "module not found" in error_msg):
            critical_errors.append(error)

        # Force-applicable errors (coverage, missing tests, etc.)
        elif "pytest_execution" in error.get("test", "") and "requires testing framework" in error_msg:
            force_applicable.append(error)  # Missing test framework - install and retry
        elif error_type in ["pytest_failure"] and "coverage" in error_msg:
            force_applicable.append(error)  # Coverage issues
        elif error_type == "environment_fail":
            force_applicable.append(error)  # Environment setup (frequently resolvable)

        # Other standard errors
        else:
            other_errors.append(error)

    # Analyze web errors with same logic
    for error in web_errors:
        error_msg = error.get("error", "").lower()
        error_type = error.get("type", "")

        if "command not found" in error_msg or "environment_fail" in error_type:
            critical_errors.append(error)

        elif "syntax error" in error_msg or "referenceerror" in error_msg or "typeerror" in error_msg:
            critical_errors.append(error)

        elif "no tests" in error_msg or "timeout" in error_msg:
            force_applicable.append(error)

        else:
            other_errors.append(error)

    # Severity determination
    total_critical = len(critical_errors)
    total_force_applicable = len(force_applicable)
    total_other = len(other_errors)
    logger.debug(f"[loop] QA analysis: Critical={total_critical}, Force-applicable={total_force_applicable}, Other={total_other}")


    # CRITICAL: Never force-approve - block permanently
    if total_critical > 0:
        return {
            "severity": "blocked_fatal",
            "details": f"CRITICAL ERRORS ({total_critical}): Syntax/import/environment issues detected. Cannot force-approve.",
            "errors": critical_errors
        }

    # FORCE-APPLICABLE: Can force-approve for high priority high iteration stories
    if total_force_applicable > 0:
        return {
            "severity": "force_applicable",
            "details": f"FORCE-APPLICABLE ERRORS ({total_force_applicable}): Missing tests/coverage/environment setup issues. Can force-approve for P1/P0 after multiple iterations.",
            "errors": force_applicable
        }

    # TEST ONLY: Pure test logic failures (no code issues)
    if total_other > 0 and total_critical == 0 and total_force_applicable == 0:
        return {
            "severity": "test_only",
            "details": f"TEST LOGIC ERRORS ({total_other}): Only test assertion/logic failures. Code structure OK.",
            "errors": other_errors
        }

    # PERSISTENT: Multiple iterations even with other error types
    iteration_count = story_dev_attempts.get(os.environ.get("STORY", ""), 0)
    if iteration_count >= 2:
        return {
            "severity": "persistent",
            "details": f"PERSISTENT FAILURE ({iteration_count} iterations). Consider quality assessment."
        }

    # FALLBACK: Standard handling
    return {
        "severity": "standard",
        "details": f"STANDARD ERRORS: Total={total_critical + total_force_applicable + total_other}, Critical={total_critical}, Force-applicable={total_force_applicable}"
    }


async def _process_iteration(
    iteration_index: int,
    stories: list[dict[str, Any]],
    *,
    allow_no_tests: bool,
    enable_architect_intervention: bool,
    status_no_tests: str,
) -> bool:
    logger.info(f"[loop] Iteración {iteration_index}: processing {len(stories)} stories")

    in_review_stories = find_in_review_stories(stories)
    if in_review_stories and enable_architect_intervention:
        logger.info(f"[loop] {len(in_review_stories)} stories in review need architect intervention")
        for story in in_review_stories[:2]:
            story_id = story["id"]
            story_arch_attempts[story_id] = story_arch_attempts.get(story_id, 0) + 1

            logger.info(f"[loop] Architect adjusting criteria for {story_id}")
            arch_result = await run_architect_for_review(
                story_id,
                story_arch_attempts[story_id],
            )
            if arch_result.get("status") == "ok":
                attempt_count = story_arch_attempts[story_id]
                was_force_approved = attempt_count >= FORCE_APPROVAL_THRESHOLD and story.get("priority") in ["P1", "P0"]
                if was_force_approved:
                    story["status"] = "done_force_architect"
                    append_note(
                        f"- Architect FORCE APPROVED {story_id} (immediate, attempt {attempt_count}, "
                        f"P{story.get('priority')} priority)"
                    )
                    logger.info(f"[loop] Architect FORCE APPROVED {story_id} (iteration {attempt_count})")
                    story_dev_attempts.pop(story_id, None)
                    story_arch_attempts.pop(story_id, None)
                else:
                    attempt = attempt_count
                    story["status"] = "todo"
                    story_arch_attempts[story_id] = 0
                    append_note(f"- Architect adjusted criteria for {story_id} (attempt {attempt}) → Dev must rework")
                    logger.info(f"[loop] Architect adjusted criteria for {story_id} → Dev must rework (counter reset)")
            else:
                detail = arch_result.get("detail") or arch_result.get("error") or arch_result
                logger.warning(f"[loop] Architect could not adjust criteria for {story_id} (detail={detail})")
                append_note(f"- Architect could not adjust criteria for {story_id} (detail={detail})")

        stories = load_stories()
        save_stories(stories)

    story = next_todo(stories)
    if not story:
        logger.info("[loop] Backlog vacío o sin 'todo'. Fin.")
        return False

    sid = story["id"]
    story_dev_attempts[sid] = story_dev_attempts.get(sid, 0) + 1

    append_note(f"- Dev implementando {sid} (iteración {story_dev_attempts[sid]})")
    logger.info(f"[loop] Dev implementing {sid} (attempt {story_dev_attempts[sid]})")

    dev_payload = {"story_id": sid, "retries": os.environ.get("DEV_RETRIES", "3")}
    dev_result = await execute_role("developer", dev_payload)
    dev_status = dev_result.get("status", "unknown")

    if dev_status != "ok":
        dev_attempt_count = story_dev_attempts.get(sid, 0)
        exit_code = int(dev_result.get("exit_code", 1))
        error_details = (
            dev_result.get("error")
            or dev_result.get("detail")
            or dev_result.get("message")
            or f"Developer status {dev_status}"
        )

        if dev_attempt_count >= DEV_RETRY_THRESHOLD:
            story["status"] = "blocked_dev"
            append_note(f"- {sid} BLOCKED_DEV: {error_details}")
            report_developer_failure(sid, error_details, qa_failure_details={})
            logger.error(
                f"[loop] {sid} -> blocked_dev (status={dev_status}, attempts={dev_attempt_count}, exit_code={exit_code})"
            )
            story_dev_attempts.pop(sid, None)
        else:
            story["status"] = "in_review"
            append_note(
                f"- Dev no pudo implementar {sid} (status={dev_status}). Revisa artifacts/auto-dev. "
                f"Reintentando (intento {dev_attempt_count}/{DEV_RETRY_THRESHOLD})."
            )
            logger.warning(
                f"[loop] {sid} -> in_review (Developer status={dev_status}, exit_code={exit_code}, reintentando)"
            )
        save_stories(stories)
        return True

    qa_payload = {"allow_no_tests": allow_no_tests, "story_id": sid}
    qa_result = await execute_role("qa", qa_payload)
    qa_status = qa_result.get("status", "unknown")
    qa_code = int(qa_result.get("code", 0 if qa_status == "pass" else 1))
    logger.debug(f"[loop] QA run finished with status={qa_status}, code={qa_code}")

    qa_failure_details: Dict[str, Any] = {}
    if QA_REPORT.exists():
        try:
            rep = json.loads(QA_REPORT.read_text(encoding="utf-8"))
            qa_status = rep.get("status", "unknown")
            qa_failure_details = rep.get("failure_details", {})
            logger.debug(f"[loop] QA report loaded. Status: {qa_status}")
        except Exception as exc:
            qa_status = "unknown"
            logger.error(f"[loop] Error loading QA report: {exc}", exc_info=True)

    if qa_status == "pass":
        story["status"] = "done"
        story_dev_attempts.pop(sid, None)
        story_arch_attempts.pop(sid, None)
        logger.info(f"[loop] {sid} -> done (QA pass)")
        append_note(f"- {sid} aprobado por QA.")
        activated_waiters = check_and_activate_waiting_stories(stories, sid)
        save_stories(stories)
        if activated_waiters:
            logger.info(
                f"[loop] ✅ DEPENDENCY RESOLUTION: Activated {len(activated_waiters)} waiting stories: {activated_waiters}"
            )
        return True

    if qa_status == "no_tests":
        if QA_REPORT.exists():
            rep = json.loads(QA_REPORT.read_text(encoding="utf-8"))
            backend_has_tests = rep.get("areas", {}).get("backend", {}).get("has_tests", False)
            backend_rc = rep.get("areas", {}).get("backend", {}).get("rc", 1)
            logger.debug(
                f"[loop] QA status 'no_tests'. Backend has tests: {backend_has_tests}, Backend RC: {backend_rc}"
            )

            if backend_has_tests and backend_rc == 0:
                story["status"] = "done"
                append_note(f"- {sid} ✅ TDD APPROVED: Backend tests executed and passed.")
                logger.info(f"[loop] {sid} -> done (✅ TDD: backend tests passed)")
            else:
                story["status"] = "blocked_no_tests"
                append_note(f"- {sid} ❌ TDD FAILURE: Backend requires tests as integral part.")
                logger.warning(f"[loop] {sid} -> blocked_no_tests (❌ TDD: backend needs tests)")

            save_stories(stories)
            return True

        if allow_no_tests:
            story["status"] = "in_review"
            append_note(f"- {sid} QA -> in_review (no tests, allowed).")
            logger.info(f"[loop] {sid} -> in_review (QA: no tests allowed)")
        else:
            story["status"] = status_no_tests
            append_note(f"- {sid} BLOQUEADO por falta de tests (QA). Requiere intervención.")
            logger.warning(f"[loop] {sid} -> {status_no_tests} (QA: no tests not allowed)")
        save_stories(stories)
        return True

    failure_analysis = analyze_qa_failure_severity(qa_failure_details)
    severity = failure_analysis.get("severity", "standard")
    logger.info(f"[loop] QA failure severity for {sid}: {severity}")

    append_note(f"- QA FAIL {sid}: {failure_analysis.get('details', 'Sin detalle')}")
    logger.info(f"[loop] QA failure details: {json.dumps(failure_analysis, indent=2, ensure_ascii=False)}")

    if severity == "blocked_fatal":
        story["status"] = "blocked_fatal"
        append_note(f"- {sid} BLOCKED_FATAL: QA fatal errors. {failure_analysis.get('details', '')}")
        logger.error(f"[loop] {sid} -> blocked_fatal (fatal QA errors)")

    elif severity == "force_applicable":
        attempt_counter = story_arch_attempts.get(sid, 0) + 1
        story_arch_attempts[sid] = attempt_counter
        if attempt_counter >= FORCE_APPROVAL_THRESHOLD and story.get("priority") in ["P1", "P0"]:
            story["status"] = "done_force_architect"
            append_note(f"- {sid} FORCE APPROVED after QA by architect (force applicable, attempt {attempt_counter}).")
            logger.warning(f"[loop] {sid} -> done_force_architect (QA force approval)")
        else:
            story["status"] = "in_review"
            append_note(
                f"- {sid} QA -> in_review (force-applicable). Architect iteration {attempt_counter}/{FORCE_APPROVAL_THRESHOLD}"
            )
            logger.info(f"[loop] {sid} -> in_review (QA force-applicable, attempt {attempt_counter})")

    elif severity == "test_only":
        story["status"] = "in_review_tests"
        append_note(f"- {sid} QA -> in_review_tests (solo fallas de tests). Requiere ajuste de casos.")
        logger.info(f"[loop] {sid} -> in_review_tests (solo fallas de tests)")

    elif severity == "persistent":
        iteration_count = story_dev_attempts.get(sid, 0)
        if iteration_count >= DEV_RETRY_THRESHOLD:
            story["status"] = "blocked_quality_issues"
            append_note(f"- {sid} BLOQUEADO por issues de calidad después de {iteration_count} intentos.")
            logger.error(f"[loop] {sid} -> blocked_quality_issues (múltiples fallos calidad)")
        else:
            story["status"] = "in_review_retry"
            append_note(f"- {sid} Persistent failure ({iteration_count} iterations). Escalating complexity.")
            logger.warning(f"[loop] {sid} -> in_review_retry (persistent failure)")

    else:
        story["status"] = "in_review"
        append_note(
            f"- {sid} QA Fail estándar (code={qa_code}): {failure_analysis['details'][:80]}. "
            "Requiere intervención de arquitecto."
        )
        logger.info(f"[loop] {sid} -> in_review (QA fail - architect review needed)")

    save_stories(stories)

    stories = load_stories()
    in_review_stories = find_in_review_stories(stories)
    if in_review_stories:
        logger.info(f"[loop] 🔄 IMMEDIATE ARCHITECT INTERVENTION FOR: {[s['id'] for s in in_review_stories]}")
        for story in in_review_stories[:2]:
            story_id = story["id"]
            story_arch_attempts[story_id] = story_arch_attempts.get(story_id, 0) + 1

            logger.info(f"[loop] Architect IMMEDIATELY adjusting criteria for {story_id}")
            arch_result = await run_architect_for_review(
                story_id,
                story_arch_attempts[story_id],
            )
            if arch_result.get("status") == "ok":
                attempt_count = story_arch_attempts[story_id]
                was_force_approved = attempt_count >= FORCE_APPROVAL_THRESHOLD and story.get("priority") in ["P1", "P0"]

                if was_force_approved:
                    story["status"] = "done_force_architect"
                    append_note(
                        f"- Architect FORCE APPROVED {story_id} (immediate, attempt {attempt_count}, "
                        f"P{story.get('priority')} priority)"
                    )
                    logger.info(f"[loop] Architect IMMEDIATELY FORCE APPROVED {story_id}")
                    story_dev_attempts.pop(story_id, None)
                    story_arch_attempts.pop(story_id, None)
                else:
                    attempt = attempt_count
                    story["status"] = "todo"
                    story_arch_attempts[story_id] = 0
                    append_note(
                        f"- Architect IMMEDIATELY adjusted criteria for {story_id} (attempt {attempt}) → Dev must rework"
                    )
                    logger.info(
                        f"[loop] Architect IMMEDIATELY adjusted criteria for {story_id} → Ready for dev rework (counter reset)"
                    )
            else:
                detail = arch_result.get("detail") or arch_result.get("error") or arch_result
                logger.warning(f"[loop] Architect could not adjust criteria for {story_id} (detail={detail})")
                append_note(f"- Architect could not adjust criteria for {story_id} (detail={detail})")

    save_stories(stories)
    return True

async def main():
    max_loops = int(os.environ.get("MAX_LOOPS", "1"))
    allow_no_tests = os.environ.get("ALLOW_NO_TESTS", "0") == "1"
    status_no_tests = os.environ.get("BACKFLOW_STATUS_FOR_NO_TESTS", "in_review")
    enable_architect_intervention = os.environ.get("ARCHITECT_INTERVENTION", "1") == "1"

    logger.info(
        f"[loop] Starting orchestrator. Max loops: {max_loops}, Allow no tests: {allow_no_tests}, "
        f"Architect intervention: {enable_architect_intervention}"
    )

    cleanup_artifacts()

    for it in range(1, max_loops + 1):
        stories = load_stories()
        should_continue = await _process_iteration(
            it,
            stories,
            allow_no_tests=allow_no_tests,
            enable_architect_intervention=enable_architect_intervention,
            status_no_tests=status_no_tests,
        )
        if not should_continue:
            save_metrics()
            return 0

    save_metrics()
    return 0

def report_developer_failure(story_id: str, error_message: str, qa_failure_details: dict):
    """Generates a detailed report for a blocked developer story."""
    DEV_FAILED_REPORT.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_content = f"### ❌ Developer Failure Report - Story {story_id} ({now})\n\n"
    report_content += f"**Error:** {error_message}\n\n"
    
    if qa_failure_details:
        report_content += f"**QA Failure Details:**\n```json\n{json.dumps(qa_failure_details, indent=2, ensure_ascii=False)}\n```\n\n"
    else:
        report_content += "**QA Failure Details:** No detailed QA report available for this failure type.\n\n"

    report_content += "**Recommendations:**\n"
    report_content += "- Review the Developer prompt (`prompts/developer.md`) for clarity on code structure, imports, and test generation.\n"
    report_content += "- Consider using a more capable LLM for the Developer role if the issue persists.\n"
    report_content += "- Manually inspect the generated code in `project/` and logs in `artifacts/dev/` for insights.\n\n"
    report_content += "---\n\n"

    with DEV_FAILED_REPORT.open("a", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"[loop] Developer failure reported for {story_id} in {DEV_FAILED_REPORT}")

if __name__ == "__main__":
    asyncio.run(main())
