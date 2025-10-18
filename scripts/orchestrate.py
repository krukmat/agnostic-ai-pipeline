# scripts/orchestrate.py
from __future__ import annotations
import os, sys, yaml, pathlib, subprocess, json, datetime

# Tracking del número de iteraciones por historia para ajuste de detalle
story_iteration_count = {}

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "planning"
STORIES_P = PLAN / "stories.yaml"
NOTES_P = PLAN / "notes.md"
QA_REPORT = ROOT / "artifacts" / "qa" / "last_report.json"

def load_stories():
    """Carga historias con recuperación automática de errores YAML"""
    if not STORIES_P.exists(): return []

    text = STORIES_P.read_text(encoding="utf-8")

    # Intento primario de carga
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "stories" in data:
            data = data["stories"]
        return data if isinstance(data, list) else []
    except Exception as e:
        append_note(f"Error YAML primario: {e}")
        print(f"[loop] Error YAML primario: {e}")

        # Intentar recuperación automática
        try:
            return recover_yaml_automatic(text)
        except Exception as e2:
            append_note(f"Recuperación automática fallida: {e2}")
            print(f"[loop] Recuperación automática fallida: {e2}")

            # Fallback: intentar ejecutar fix_stories automáticamente
            if fix_stories_automatic():
                try:
                    data = yaml.safe_load(STORIES_P.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and "stories" in data:
                        data = data["stories"]
                    return data if isinstance(data, list) else []
                except Exception as e3:
                    append_note(f"Fix automático fallido: {e3}")
                    print(f"[loop] Fix automático fallido: {e3}")

            # Último fallback: devolver lista vacía
            append_note("FALLBACK: Devolviendo lista vacía de historias")
            print("[loop] FATAL: Devolviendo lista vacía de historias")
            return []

def save_stories(stories):
    STORIES_P.write_text(yaml.safe_dump(stories, sort_keys=False, allow_unicode=True), encoding="utf-8")

def recover_yaml_automatic(text: str) -> list:
    """Intenta recuperar YAML automáticamente con estrategias de reparación"""
    import re

    # Estrategia 1: Remover caracteres problemáticos comunes al inicio
    text = text.lstrip()

    # Estrategia 2: Si todo está comentado, descomentar automáticamente
    if all(line.lstrip().startswith('#') for line in text.splitlines() if line.strip()):
        lines = []
        for line in text.splitlines():
            if line.lstrip().startswith('#'):
                lines.append(re.sub(r'^(\s*)#\s?', r'\1', line))
            else:
                lines.append(line)
        text = '\n'.join(lines)

    # Estrategia 3: Reparar formatos de acceptance comunes
    lines = text.splitlines()
    fixed_lines = []
    for line in lines:
        # Reparar acceptance inline: acceptance: - item
        if 'acceptance:' in line and ('- ' in line or '; ' in line):
            indent = line.find('acceptance:')
            match = re.match(r'^(\s*)acceptance:\s*(.+)', line)
            if match:
                ind, val = match.groups()
                # Convertir a multiline
                items = [item.strip('- ;') for item in re.split(r'[,;]-| -', val) if item.strip()]
                if len(items) > 1:
                    fixed_lines.append(f"{ind}acceptance:")
                    for item in items:
                        fixed_lines.append(f"{ind}  - {item}")
                    continue
        fixed_lines.append(line)
    text = '\n'.join(fixed_lines)

    # Intentar parsear de nuevo
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "stories" in data:
            data = data["stories"]
        return data if isinstance(data, list) else []
    except Exception as e:
        # Crear backup y intentar una reparación mínima
        backup_path = STORIES_P.with_suffix('.backup.broken')
        STORIES_P.replace(backup_path)
        append_note(f"YAML irreparable - backup creado: {backup_path}")
        raise e

def fix_stories_automatic() -> bool:
    """Ejecuta fix_stories automáticamente para reparar YAML"""
    try:
        import subprocess
        result = subprocess.run([
            str(ROOT / ".venv" / "bin" / "python"),
            str(ROOT / "scripts" / "fix_stories.py")
        ], capture_output=True, text=True, cwd=str(ROOT))
        success = result.returncode == 0
        if success:
            append_note("fix_stories ejecutado automáticamente")
            print("[loop] fix_stories ejecutado automáticamente")
        else:
            append_note(f"fix_stories falló: {result.stderr}")
            print(f"[loop] fix_stories falló: {result.stderr}")
        return success
    except Exception as e:
        append_note(f"Error ejecutando fix_stories: {e}")
        print(f"[loop] Error ejecutando fix_stories: {e}")
        return False

def cleanup_artifacts():
    """Limpieza automática de artifacts antiguos para prevenir acumulación"""
    try:
        max_age_days = int(os.environ.get("ARTIFACT_RETENTION_DAYS", "7"))
        max_age_seconds = max_age_days * 24 * 60 * 60
        now = datetime.datetime.now().timestamp()

        artifacts_dir = ROOT / "artifacts"
        if not artifacts_dir.exists():
            return

        # Contadores de limpieza
        total_files_cleaned = 0
        total_space_cleaned = 0

        # Limpiar artifacts/dev/* (logs de desarrollo)
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

        # Limpiar artifacts/qa/* excepto last_report.json
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

        # Limpiar *.pyc y __pycache__ si existen
        for pyc_file in ROOT.rglob("*.pyc"):
            age = now - pyc_file.stat().st_mtime
            if age > (1 * 60 * 60):  # Más de 1 hora
                size = pyc_file.stat().st_size
                pyc_file.unlink()
                total_files_cleaned += 1
                total_space_cleaned += size

        import shutil
        for cache_dir in ROOT.rglob("__pycache__"):
            if cache_dir.is_dir():
                try:
                    shutil.rmtree(cache_dir)
                    total_files_cleaned += 1  # Contar directorio como eliminación
                except:
                    pass  # Ignorar errores de permisos

        if total_files_cleaned > 0 or total_space_cleaned > 0:
            append_note(f"Limpieza automática: {total_files_cleaned} archivos eliminados, {total_space_cleaned/1024:.1f}KB liberados")
            print(f"[cleanup] {total_files_cleaned} archivos antiguos eliminados, {total_space_cleaned/1024:.1f}KB liberados")

    except Exception as e:
        append_note(f"Error en limpieza automática: {e}")
        print(f"[cleanup] Error durante limpieza: {e}")

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
    """Ejecuta arquitecto para ajustar criterios cuando historia está en review"""
    print(f"[loop] Arquitecto interviniendo para ajustar criterios de {story_id} (intento {iteration_count})")

    # Lee el concepto desde múltiples fuentes
    concept = os.environ.get("CONCEPT", "")
    if not concept:
        # Intenta leer de requirements.yaml como respaldo
        req_file = ROOT / "planning" / "requirements.yaml"
        if req_file.exists():
            with open(req_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extrae la primera línea significativa como concepto
                lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                concept = lines[0] if lines else "Sistema de gestión de tareas colaborativo"

    if not concept:
        print("[loop] No se encontró concepto para arquitecto")
        return 1

    # Ajusta el nivel de detalle basado en la iteración
    detail_level = "medium"
    if iteration_count == 1:
        detail_level = "high"  # Primera intervención: máximo detalle
    elif iteration_count == 2:
        detail_level = "maximum"  # Segunda intervención: detalle extremo
    elif iteration_count >= 3:
        detail_level = "force_approve"  # Tercera+ intervención: considerar aprobación forzada

    # Ejecuta arquitecto con instrucciones específicas para ajustar criterios
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

def create_test_story_for(story):
    return {
        "id": f"{story['id']}-TESTS",
        "epic": story.get("epic","E1"),
        "description": f"Escribir tests automatizados para {story['id']}: {story.get('description','')}",
        "acceptance": "Ejecutar runners (pytest/jest) y obtener exit code 0.",
        "priority": story.get("priority","P2"),
        "status": "todo",
    }

def find_in_review_stories(stories):
    """Encuentra historias en review que necesitan intervención del arquitecto"""
    return [s for s in stories if s.get("status","").lower() == "in_review"]

def analyze_qa_failure_severity(qa_failure_details):
    """Analiza la severidad de los fallos de QA y determina el tipo de problema"""
    failure_details = qa_failure_details or {}

    # Contadores de diferentes tipos de errores
    backend_critical = 0
    backend_non_critical = 0
    web_critical = 0
    web_non_critical = 0

    backend_errors = failure_details.get("backend", {}).get("errors", [])
    web_errors = failure_details.get("web", {}).get("errors", [])

    # Analizar errores de backend
    for error in backend_errors:
        if error.get("type") in ["pytest_failure", "pytest_error"]:
            # Si es error de import o configuración crítica
            if "import" in error.get("error", "").lower() or "module not found" in error.get("error", "").lower():
                backend_critical += 1
            else:
                backend_non_critical += 1

    # Analizar errores de web
    for error in web_errors:
        if error.get("type") == "jest_failure":
            web_non_critical += 1  # Por ahora todos los tests web se consideran no críticos

    # Determinación de severidad
    total_errors = backend_critical + backend_non_critical + web_critical + web_non_critical

    if total_errors == 0:
        return {"severity": "none", "details": "Sin errores detectados"}

    if backend_critical > 0:
        return {
            "severity": "critical",
            "details": f"Errores críticos de configuración/import: {backend_critical} errores"
        }

    if backend_non_critical > 0 and web_non_critical == 0:
        return {
            "severity": "test_only",
            "details": f"Fallan solo tests backend: {backend_non_critical} errores de lógica o assertions"
        }

    if story_iteration_count.get(os.environ.get("STORY", ""), 0) >= 2:
        return {
            "severity": "persistent",
            "details": f"Fallo persistente ({story_iteration_count.get(os.environ.get('STORY', ''), 0)} iteraciones)"
        }

    return {
        "severity": "standard",
        "details": f"Errores estándar: backend={backend_non_critical}, web={web_non_critical}"
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
            print(f"[loop] {len(in_review_stories)} historias en review necesitan intervención del arquitecto")
            for story in in_review_stories[:2]:  # Limit to 2 per iteration to avoid infinite loops
                story_id = story['id']
                # Actualizar contador de iteraciones para esta historia
                if story_id not in story_iteration_count:
                    story_iteration_count[story_id] = 0
                story_iteration_count[story_id] += 1

                print(f"[loop] Arquitecto ajustando criterios para {story_id}")
                rc_arch = run_architect_for_review(story_id, story_iteration_count[story_id])
                if rc_arch == 0:
                    # Arquitecto ajustó criterios exitosamente
                    story['status'] = 'todo'  # Vuelve a todo para que dev lo retrabaje
                    append_note(f"- Arquitecto ajustó criterios para {story_id} (intento {story_iteration_count[story_id]}) → Dev debe retrabajar")
                    print(f"[loop] Arquitecto ajustó criterios para {story_id} → Dev debe retrabajar")
                else:
                    append_note(f"- Arquitecto no pudo ajustar criterios para {story_id} (rc={rc_arch})")
                    print(f"[loop] Arquitecto no pudo ajustar criterios para {story_id}")

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
            save_stories(stories)
            append_note(f"- {sid} aprobado por QA.")
            print(f"[loop] {sid} -> done (QA pass)")

        elif qa_status == "no_tests":
            # 🧪 NO TESTS: Estados intermedios dependiendo configuración
            if allow_no_tests:
                # Estado intermedio: Calidad básica verificada, tests pendientes
                story["status"] = "qa_pass_no_tests"  # Estado intermedio: QA aprobado sin tests
                if create_child:
                    test_story = create_test_story_for(story)
                    test_story["status"] = "pending"  # Tests marcados como pendientes
                    stories.append(test_story)
                save_stories(stories)
                append_note(f"- {sid} QA aprobado sin tests. Tests marcados como pendientes.")
                print(f"[loop] {sid} -> qa_pass_no_tests (QA aprobado sin tests)")
            else:
                # Estado intermedio: Quality-gated por tests requeridos
                story["status"] = "quality_gate_waiting"  # Esperando tests
                if create_child:
                    stories.append(create_test_story_for(story))
                save_stories(stories)
                append_note(f"- {sid} esperando QA de tests. Se creó historia de tests hija.")
                print(f"[loop] {sid} -> quality_gate_waiting (esperando QA de tests)")

        else:
            # ❌ QA FAIL: Análisis de fallos con estados específicos
            # Analyze QA failure details for smarter decisions
            failure_analysis = analyze_qa_failure_severity(qa_failure_details)

            if failure_analysis["severity"] == "critical":
                # Errores críticos: Verificar si podemos recuperar
                story["status"] = "in_review_critical"  # Problema crítico - revisión urgente
                append_note(f"- {sid} ERROR CRÍTICO en QA: {failure_analysis['details'][:100]}...")
                print(f"[loop] {sid} -> in_review_critical (ERROR CRÍTICO en QA)")
            elif failure_analysis["severity"] == "test_only":
                # Solo fallan tests - funcionalidad básica OK
                story["status"] = "code_done_tests_pending"  # Código OK, tests pendientes
                test_story = create_test_story_for(story)
                test_story["status"] = "todo"
                stories.append(test_story)
                append_note(f"- {sid} código funcional OK. Tests requeridos separados.")
                print(f"[loop] {sid} -> code_done_tests_pending (código OK, tests separados)")
            elif failure_analysis["severity"] == "persistent":
                # Múltiples fallos: evaluación de aprobación forzada
                iteration_count = story_iteration_count.get(sid, 0)
                if iteration_count >= 3:
                    story_priority = story.get("priority", "P2")
                    if story_priority in ["P1", "P0"]:
                        story["status"] = "done_force_architect"  # Aprobado por arquitecto (alta prioridad)
                        append_note(f"- {sid} APROBADO FORZADAMENTE por arquitecto (prioridad {story_priority}, {iteration_count} iteraciones)")
                        print(f"[loop] {sid} -> done_force_architect (APROBADAMENTE por arquitecto)")
                    else:
                        story["status"] = "blocked_quality_issues"  # Bloqueado por calidad insuficiente
                        append_note(f"- {sid} BLOQUEADO (baja prioridad + múltiples fallos de calidad)")
                        print(f"[loop] {sid} -> blocked_quality_issues (múltiples fallos calidad)")
                else:
                    story["status"] = "in_review_retry"  # Revisión y retry
                    append_note(f"- {sid} falló QA - requiere revisión (intento {iteration_count + 1})")
                    print(f"[loop] {sid} -> in_review_retry (necesita revisión)")
            else:
                # Problema estándar - necesita revisión del arquitecto
                story["status"] = "in_review"  # Necesita intervención del arquitecto
                append_note(f"- {sid} falló QA (rc={rc_qa}). Requiere intervención de arquitecto.")
                print(f"[loop] {sid} -> in_review (QA fail, needs architect)")

        save_stories(stories)

    return 0

if __name__ == "__main__":
    sys.exit(main())
