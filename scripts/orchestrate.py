# scripts/orchestrate.py
from __future__ import annotations
import os, sys, yaml, pathlib, subprocess, json, datetime

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

def main():
    max_loops = int(os.environ.get("MAX_LOOPS","1"))
    allow_no_tests = os.environ.get("ALLOW_NO_TESTS","0") == "1"
    create_child = os.environ.get("BACKFLOW_CREATE_TEST_STORY","1") == "1"
    status_no_tests = os.environ.get("BACKFLOW_STATUS_FOR_NO_TESTS", "in_review")

    for it in range(1, max_loops+1):
        print(f"[loop] Iteración {it}/{max_loops}")
        stories = load_stories()
        story = next_todo(stories)
        if not story:
            print("[loop] backlog vacío o sin 'todo'. Fin.")
            return 0

        sid = story["id"]

        # 1) DEV
        rc_dev = run_cmd([str(ROOT/".venv/bin/python"), str(ROOT/"scripts"/"run_dev.py")], env={**os.environ, "STORY": sid, "DEV_RETRIES": os.environ.get("DEV_RETRIES","3")})
        if rc_dev != 0:
            append_note(f"- Dev no pudo implementar {sid} (rc={rc_dev}). Revisa artifacts/auto-dev.")
            story["status"] = "blocked"
            save_stories(stories)
            print(f"[loop] {sid} -> blocked (Dev rc {rc_dev})")
            continue

        # 2) QA
        qa_env = {**os.environ, "ALLOW_NO_TESTS": "1" if allow_no_tests else "0"}
        rc_qa = run_cmd([str(ROOT/".venv/bin/python"), str(ROOT/"scripts"/"run_qa.py")], env=qa_env)

        qa_status = "unknown"
        if QA_REPORT.exists():
            try:
                rep = json.loads(QA_REPORT.read_text(encoding="utf-8"))
                qa_status = rep.get("status","unknown")
            except Exception:
                qa_status = "unknown"

        # 3) Gates & backflow
        if qa_status == "pass":
            story["status"] = "done"
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
            story["status"] = "blocked"
            save_stories(stories)
            append_note(f"- {sid} rebotado: QA fail (rc={rc_qa}). Revisa {QA_REPORT}.")
            print(f"[loop] {sid} -> blocked (QA fail)")

    return 0

if __name__ == "__main__":
    sys.exit(main())

