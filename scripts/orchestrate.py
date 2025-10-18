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
    if not STORIES_P.exists(): return []
    data = yaml.safe_load(STORIES_P.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "stories" in data:
        data = data["stories"]
    return data or []

def save_stories(stories):
    STORIES_P.write_text(yaml.safe_dump(stories, sort_keys=False, allow_unicode=True), encoding="utf-8")

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

def main():
    max_loops = int(os.environ.get("MAX_LOOPS","1"))
    allow_no_tests = os.environ.get("ALLOW_NO_TESTS","0") == "1"
    create_child = os.environ.get("BACKFLOW_CREATE_TEST_STORY","1") == "1"
    status_no_tests = os.environ.get("BACKFLOW_STATUS_FOR_NO_TESTS", "in_review")
    enable_architect_intervention = os.environ.get("ARCHITECT_INTERVENTION","1") == "1"

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

        # 5) Gates & backflow
        if qa_status == "pass":
            story["status"] = "done"
            # Reset iteration count on success
            if sid in story_iteration_count:
                story_iteration_count[sid] = 0
            save_stories(stories)
            append_note(f"- {sid} aprobado por QA.")
            print(f"[loop] {sid} -> done (QA pass)")

        elif qa_status == "no_tests":
            if allow_no_tests:
                # pasa como 'in_review' pero generamos historia de tests
                story["status"] = "in_review"
                if create_child:
                    stories.append(create_test_story_for(story))
                save_stories(stories)
                append_note(f"- {sid} sin tests (permitido). Se creó historia de tests hija.")
                print(f"[loop] {sid} -> in_review (no_tests permitido)")
            else:
                story["status"] = status_no_tests  # in_review o blocked
                if create_child:
                    stories.append(create_test_story_for(story))
                save_stories(stories)
                append_note(f"- {sid} rebotado: QA no encontró tests. Se creó historia de tests hija.")
                print(f"[loop] {sid} -> {status_no_tests} (no_tests NO permitido)")

        else:
            # QA fail - check if we should force approval after multiple attempts
            if story_iteration_count.get(sid, 0) >= 3:
                story_priority = story.get("priority", "P2")
                append_note(f"- {sid} rechazado múltiples veces (iteración {story_iteration_count[sid]}) - considerando aprobación forzada por prioridad {story_priority}")
                print(f"[loop] {sid} falló QA en MÚLTIPLES intentos - considerando aprobación forzada")

                # Arquitecto puede aprobar forzadamente basado en prioridad y urgencia
                if story_priority in ["P1", "P0"]:
                    story["status"] = "done"
                    append_note(f"- {sid} APROBADO FORZADAMENTE por arquitecto (prioridad {story_priority})")
                    print(f"[loop] {sid} -> done (APROBADO FORZADAMENTE por arquitecto)")
                else:
                    story["status"] = "blocked"
                    append_note(f"- {sid} bloqueado definitivamente (baja prioridad, múltiples fallos)")
                    print(f"[loop] {sid} -> blocked (múltiples QA fails)")
            else:
                story["status"] = "in_review"  # Needs architect review
                append_note(f"- {sid} rebotado: QA fail (rc={rc_qa}). Requiere intervención de arquitecto.")
                print(f"[loop] {sid} -> in_review (QA fail, needs architect)")

        save_stories(stories)

    return 0

if __name__ == "__main__":
    sys.exit(main())
