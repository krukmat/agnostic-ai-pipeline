# scripts/orchestrate.py
from __future__ import annotations
import os, sys, yaml, pathlib, subprocess, json, datetime

# Tracking the number of iterations per story for detail adjustment
story_iteration_count = {}

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "planning"
STORIES_P = PLAN / "stories.yaml"
NOTES_P = PLAN / "notes.md"
QA_REPORT = ROOT / "artifacts" / "qa" / "last_report.json"

def load_stories():
    """Load stories with automatic YAML error recovery"""
    if not STORIES_P.exists(): return []

    text = STORIES_P.read_text(encoding="utf-8")

    # Primary loading attempt
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "stories" in data:
            data = data["stories"]
        return data if isinstance(data, list) else []
    except Exception as e:
        append_note(f"Primary YAML error: {e}")
        print(f"[loop] Primary YAML error: {e}")

        # Try automatic recovery
        try:
            return recover_yaml_automatic(text)
        except Exception as e2:
            append_note(f"Automatic recovery failed: {e2}")
            print(f"[loop] Automatic recovery failed: {e2}")

            # Fallback: try to run fix_stories automatically
            if fix_stories_automatic():
                try:
                    data = yaml.safe_load(STORIES_P.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and "stories" in data:
                        data = data["stories"]
                    return data if isinstance(data, list) else []
                except Exception as e3:
                    append_note(f"Automatic fix failed: {e3}")
                    print(f"[loop] Automatic fix failed: {e3}")

            # Last fallback: return empty list
            append_note("FALLBACK: Returning empty story list")
            print("[loop] FATAL: Returning empty story list")
            return []

def save_stories(stories):
    STORIES_P.write_text(yaml.safe_dump(stories, sort_keys=False, allow_unicode=True), encoding="utf-8")

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
            append_note("fix_stories automatically executed")
            print("[loop] fix_stories automatically executed")
        else:
            append_note(f"fix_stories failed: {result.stderr}")
            print(f"[loop] fix_stories failed: {result.stderr}")
        return success
    except Exception as e:
        append_note(f"Error running fix_stories: {e}")
        print(f"[loop] Error running fix_stories: {e}")
        return False

def cleanup_artifacts():
    """Automatic cleanup of old artifacts to prevent accumulation"""
    try:
        max_age_days = int(os.environ.get("ARTIFACT_RETENTION_DAYS", "7"))
        max_age_seconds = max_age_days * 24 * 60 * 60
        now = datetime.datetime.now().timestamp()

        artifacts_dir = ROOT / "artifacts"
        if not artifacts_dir.exists():
            return

        # Cleanup counters
        total_files_cleaned = 0
        total_space_cleaned = 0

        # Clean artifacts/dev/* (dev logs)
        dev_dir = artifacts_dir / "dev"
        if dev_dir.exists():
            for file_path in dev_dir.glob("*"):
                if file_path.is_file():
                    file_age = now - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        total_files_cleaned += 1
                        total_space_cleaned += size

        # Clean artifacts/qa/* except last_report.json
        qa_dir = artifacts_dir / "qa"
        if qa_dir.exists():
            for file_path in qa_dir.glob("*"):
                if file_path.is_file() and file_path.name != "last_report.json":
                    file_age = now - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        total_files_cleaned += 1
                        total_space_cleaned += size

        # Clean *.pyc and __pycache__ if they exist
        for pyc_file in ROOT.rglob("*.pyc"):
            age = now - pyc_file.stat().st_mtime
            if age > (1 * 60 * 60):  # More than 1 hour
                size = pyc_file.stat().st_size
                pyc_file.unlink()
                total_files_cleaned += 1
                total_space_cleaned += size

        import shutil
        for cache_dir in ROOT.rglob("__pycache__"):
            if cache_dir.is_dir():
                try:
                    shutil.rmtree(cache_dir)
                    total_files_cleaned += 1  # Count directory as deletion
                except:
                    pass  # Ignore permission errors

        if total_files_cleaned > 0 or total_space_cleaned > 0:
            append_note(f"Automatic cleanup: {total_files_cleaned} files deleted, {total_space_cleaned/1024:.1f}KB freed")
            print(f"[cleanup] {total_files_cleaned} old files deleted, {total_space_cleaned/1024:.1f}KB freed")

    except Exception as e:
        append_note(f"Error in automatic cleanup: {e}")
        print(f"[cleanup] Error during cleanup: {e}")

def append_note(text: str):
    NOTES_P.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with NOTES_P.open("a", encoding="utf-8") as f:
        f.write(f"\n### {now}\n{text}\n")

def run_cmd(cmd, env=None) -> int:
    print(f"[loop] run: {' '.join(cmd)}")
    res = subprocess.run(cmd, env=env or os.environ.copy())
    return res.returncode

def run_architect_for_review(story_id: str, iteration_count: int = 1) -> int:
    """Run architect to adjust criteria when story is in review"""
    print(f"[loop] Architect intervening to adjust {story_id} criteria (attempt {iteration_count})")

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

    if not concept:
        print("[loop] Concept not found for architect")
        return 1

    # Adjust detail level based on iteration
    detail_level = "medium"
    if iteration_count == 1:
        detail_level = "high"  # First intervention: maximum detail
    elif iteration_count == 2:
        detail_level = "maximum"  # Second intervention: extreme detail
    elif iteration_count >= 3:
        detail_level = "force_approve"  # Third+ intervention: consider forced approval

    # Run architect with specific instructions to adjust criteria
    arch_env = {
        **os.environ,
        "CONCEPT": concept,
        "ARCHITECT_MODE": "review_adjustment",
        "STORY": story_id,
        "DETAIL_LEVEL": detail_level,
        "ITERATION_COUNT": str(iteration_count)
    }
    return run_cmd([str(ROOT/".venv/bin/python"), str(ROOT/"scripts"/"run_architect.py")], env=arch_env)

def next_todo(stories):
    for s in stories:
        if s.get("status","").lower() == "todo":
            return s
    return None

# REMOVED: No longer creating separate test stories - tests are part of each user story per TDD

def find_in_review_stories(stories):
    """Find stories in review that need architect intervention"""
    return [s for s in stories if s.get("status","").lower() == "in_review"]

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

    if is_test_related_story:
        # Activate ALL stories currently in quality_gate_waiting
        for story in stories:
            if story.get("status", "").lower() == "quality_gate_waiting":
                # Activate this waiting story back to todo for QA retry
                story["status"] = "todo"
                activated.append(story["id"])
                print(f"[DEPENDENCY] Activated waiting story {story['id']} after testing capacity improvement by {completed_story_id}")

    return activated

def analyze_qa_failure_severity(qa_failure_details):
    """Analyze the severity of QA failures and determine the type of problem

    Distinguishes between force-acceptable errors (coverage, timing) vs critical errors (syntax, imports).
    """
    failure_details = qa_failure_details or {}

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

    # CRITICAL: Never force-approve - block permanently
    if total_critical > 0:
        return {
            "severity": "critically_blocked",
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
    iteration_count = story_iteration_count.get(os.environ.get("STORY", ""), 0)
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

def main():
    max_loops = int(os.environ.get("MAX_LOOPS","1"))
    allow_no_tests = os.environ.get("ALLOW_NO_TESTS","0") == "1"
    create_child = os.environ.get("BACKFLOW_CREATE_TEST_STORY","1") == "1"
    status_no_tests = os.environ.get("BACKFLOW_STATUS_FOR_NO_TESTS", "in_review")
    enable_architect_intervention = os.environ.get("ARCHITECT_INTERVENTION","1") == "1"

    # Ejecutar limpieza automática de artifacts antiguos al inicio
    cleanup_artifacts()

    for it in range(1, max_loops+1):
        print(f"[loop] Iteración {it}/{max_loops}")
        stories = load_stories()

                # 1) Check for stories in review that need architect intervention
        in_review_stories = find_in_review_stories(stories)
        if in_review_stories and enable_architect_intervention:
            print(f"[loop] {len(in_review_stories)} stories in review need architect intervention")
            for story in in_review_stories[:2]:  # Limit to 2 per iteration to avoid infinite loops
                story_id = story['id']
                # Update iteration counter for this story
                if story_id not in story_iteration_count:
                    story_iteration_count[story_id] = 0
                story_iteration_count[story_id] += 1

                print(f"[loop] Architect adjusting criteria for {story_id}")
                rc_arch = run_architect_for_review(story_id, story_iteration_count[story_id])
                if rc_arch == 0:
                    # Check if this was force approval (iteration >= 3)
                    was_force_approved = story_iteration_count[story_id] >= 3 and story.get("priority") in ["P1", "P0"]

                    if was_force_approved:
                        # Force approval - mark as done, don't rework
                        story['status'] = 'done_force_architect'
                        append_note(f"- Architect FORCE APPROVED {story_id} (attempt {story_iteration_count[story_id]}, P{story.get('priority')} priority)")
                        print(f"[loop] Architect FORCE APPROVED {story_id} (iteration {story_iteration_count[story_id]})")
                    else:
                        # Normal adjustment - return to todo so dev can rework it
                        story['status'] = 'todo'  # Return to todo so dev can rework it
                        append_note(f"- Architect adjusted criteria for {story_id} (attempt {story_iteration_count[story_id]}) → Dev must rework")
                        print(f"[loop] Architect adjusted criteria for {story_id} → Dev must rework")
                else:
                    append_note(f"- Architect could not adjust criteria for {story_id} (rc={rc_arch})")
                    print(f"[loop] Architect could not adjust criteria for {story_id}")

            # RECARGAR historias después de architect interventions
            stories = load_stories()
            save_stories(stories)

        story = next_todo(stories)
        if not story:
            print("[loop] backlog vacío o sin 'todo'. Fin.")
            return 0

        sid = story["id"]

        # 2) Track iterations for this story
        if sid not in story_iteration_count:
            story_iteration_count[sid] = 0
        story_iteration_count[sid] += 1

        append_note(f"- Dev implementando {sid} (iteración {story_iteration_count[sid]})")

        # 3) DEV
        rc_dev = run_cmd([str(ROOT/".venv/bin/python"), str(ROOT/"scripts"/"run_dev.py")], env={**os.environ, "STORY": sid, "DEV_RETRIES": os.environ.get("DEV_RETRIES","3")})
        if rc_dev != 0:
            append_note(f"- Dev no pudo implementar {sid} (rc={rc_dev}). Revisa artifacts/auto-dev.")
            story["status"] = "blocked"
            save_stories(stories)
            print(f"[loop] {sid} -> blocked (Dev rc {rc_dev})")
            continue

        # 4) QA
        qa_env = {**os.environ, "ALLOW_NO_TESTS": "1" if allow_no_tests else "0"}
        rc_qa = run_cmd([str(ROOT/".venv/bin/python"), str(ROOT/"scripts"/"run_qa.py")], env=qa_env)

        qa_status = "unknown"
        qa_failure_details = {}
        if QA_REPORT.exists():
            try:
                rep = json.loads(QA_REPORT.read_text(encoding="utf-8"))
                qa_status = rep.get("status","unknown")
                qa_failure_details = rep.get("failure_details", {})
            except Exception:
                qa_status = "unknown"

        # 5) Advanced Gate Management with intermediate states
        if qa_status == "pass":
            # ✅ QA PASS: Historia aprobada
            story["status"] = "done"
            if sid in story_iteration_count:
                story_iteration_count[sid] = 0

            # Check if any waiting stories can now be activated (dependency resolution)
            activated_waiters = check_and_activate_waiting_stories(stories, sid)

            save_stories(stories)
            append_note(f"- {sid} aprobado por QA.")
            print(f"[loop] {sid} -> done (QA pass)")

            if activated_waiters:
                print(f"[loop] ✅ DEPENDENCY RESOLUTION: Activated {len(activated_waiters)} waiting stories: {activated_waiters}")

        elif qa_status == "no_tests":
            # NUEVA LÓGICA TDD: Verificar QUE backend (principal) tenga tests
            if QA_REPORT.exists():
                rep = json.loads(QA_REPORT.read_text(encoding="utf-8"))
                backend_has_tests = rep.get("areas", {}).get("backend", {}).get("has_tests", False)
                backend_rc = rep.get("areas", {}).get("backend", {}).get("rc", 1)

                if backend_has_tests and backend_rc == 0:
                    # ✅ Backend tiene tests que pasan - TDD cumplo
                    story["status"] = "done"
                    append_note(f"- {sid} ✅ TDD APPROVED: Backend tests executed and passed.")
                    print(f"[loop] {sid} -> done (✅ TDD: backend tests passed)")
                else:
                    # ❌ Backend no tiene tests validables - bloqueado
                    story["status"] = "blocked_no_tests"
                    append_note(f"- {sid} ❌ TDD FAILURE: Backend requires tests as integral part.")
                    print(f"[loop] {sid} -> blocked_no_tests (❌ TDD: backend needs tests)")
            else:
                # Fallback si no hay reporte
                story["status"] = "blocked_no_tests"
                append_note(f"- {sid} ❌ TDD FAILURE: QA report missing - tests required.")
                print(f"[loop] {sid} -> blocked_no_tests (QA report missing)")

        else:
            # ❌ QA FAIL: Análisis de fallos con estados específicos
            # Analyze QA failure details for smarter decisions
            failure_analysis = analyze_qa_failure_severity(qa_failure_details)

            # LÓGICA SOBRE FORCE-APPROVAL INTELIGENTE
            if failure_analysis["severity"] == "critically_blocked":
                # 🚫 NUNCA force-approve: Errores críticos (syntax, imports, environment)
                story["status"] = "blocked_fatal"  # Bloqueado permanentemente
                append_note(f"- {sid} FATAL BLOCK: {failure_analysis['details'][:100]}. Cannot force-approve!")
                print(f"[loop] {sid} -> blocked_fatal (CRÍTICO - no force-approve)")

            elif failure_analysis["severity"] == "force_applicable":
                # ✅ FORCE-APPROVE SOLO P1/P0 mayor a 3 iteraciones: Errores force-applicable
                iteration_count = story_iteration_count.get(sid, 0)
                story_priority = story.get("priority", "P2")

                if iteration_count >= 3 and story_priority in ["P1", "P0"]:
                    story["status"] = "done_force_architect"
                    append_note(f"- {sid} FORCE-APPROVED: {failure_analysis['details'][:80]} (Safe to approve P{story_priority} after {iteration_count} retries)")
                    print(f"[loop] {sid} -> done_force_architect (SAFE FORCE-APPROVAL)")
                else:
                    story["status"] = "in_review"
                    append_note(f"- {sid} Aguardando force-approval: {failure_analysis['details'][:80]} (Needs P1/P0 + ≥3 iterations)")
                    print(f"[loop] {sid} -> in_review (waiting force-approval criteria)")

            elif failure_analysis["severity"] == "test_only":
                # Solo fallan tests - funcionalidad básica OK, pero tests no pasan
                story["status"] = "blocked_test_only"
                append_note(f"- {sid} TESTS FALLANDO: Código funcional OK pero tests no pasan: {failure_analysis['details'][:80]} (TDD: tests son parte integral)")
                print(f"[loop] {sid} -> blocked_test_only (TDD: fix implementation to make tests pass)")

            elif failure_analysis["severity"] == "persistent":
                # Múltiples fallos: considerar calidad
                iteration_count = story_iteration_count.get(sid, 0)
                story_priority = story.get("priority", "P2")

                if iteration_count >= 5:  # Solo forzar después de MUCHAS iteraciones
                    story["status"] = "blocked_quality_issues"
                    append_note(f"- {sid} BLOCKED: Múltiples fallos de calidad ({iteration_count} iteraciones). Revisión manual requerida.")
                    print(f"[loop] {sid} -> blocked_quality_issues (múltiples fallos calidad)")
                else:
                    story["status"] = "in_review_retry"
                    append_note(f"- {sid} Persistent failure ({iteration_count} iterations). Escalating complexity.")
                    print(f"[loop] {sid} -> in_review_retry (persistent failure)")

            else:
                # Problema estándar - necesita revisión del arquitecto
                story["status"] = "in_review"
                append_note(f"- {sid} QA Fail estándar (rc={rc_qa}): {failure_analysis['details'][:80]}. Requiere intervención de arquitecto.")
                print(f"[loop] {sid} -> in_review (QA fail - architect review needed)")

        # NUEVO: IMMEDIATELY PROCESS architect interventions after QA fail
        # This makes the loop truly fluent - architect intervenes immediately in same iteration
        save_stories(stories)

        # After saving story state, immediately check for architect interventions
        stories = load_stories()  # Reload to get any changes
        in_review_stories = find_in_review_stories(stories)
        if in_review_stories:
            print(f"[loop] 🔄 IMMEDIATE ARCHITECT INTERVENTION FOR: {[s['id'] for s in in_review_stories]}")
            for story in in_review_stories[:2]:  # Process up to 2 immediately
                story_id = story['id']
                # Update iteration counter for this story
                if story_id not in story_iteration_count:
                    story_iteration_count[story_id] = 0
                story_iteration_count[story_id] += 1

                print(f"[loop] Architect IMMEDIATELY adjusting criteria for {story_id}")
                rc_arch = run_architect_for_review(story_id, story_iteration_count[story_id])
                if rc_arch == 0:
                    # Check if this was force approval (iteration >= 3)
                    was_force_approved = story_iteration_count[story_id] >= 3 and story.get("priority") in ["P1", "P0"]

                    if was_force_approved:
                        # Force approval - mark as done, don't rework
                        story['status'] = 'done_force_architect'
                        append_note(f"- Architect FORCE APPROVED {story_id} (immediate, attempt {story_iteration_count[story_id]}, P{story.get('priority')} priority)")
                        print(f"[loop] Architect IMMEDIATELY FORCE APPROVED {story_id}")
                    else:
                        # Normal adjustment - return to todo so dev can rework it
                        story['status'] = 'todo'
                        append_note(f"- Architect IMMEDIATELY adjusted criteria for {story_id} (attempt {story_iteration_count[story_id]}) → Dev must rework")
                        print(f"[loop] Architect IMMEDIATELY adjusted criteria for {story_id} → Ready for dev rework")
                else:
                    append_note(f"- Architect could not adjust criteria for {story_id} (immediate, rc={rc_arch})")
                    print(f"[loop] Architect could not IMMEDIATELY adjust criteria for {story_id}")

        save_stories(stories)

    return 0

if __name__ == "__main__":
    sys.exit(main())
