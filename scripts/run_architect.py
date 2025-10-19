from __future__ import annotations
import os, re, asyncio, pathlib
from common import load_config, ensure_dirs, PLANNING, ROOT
from llm import LLMClient

ARCH_PROMPT = (ROOT/"prompts"/"architect.md").read_text(encoding="utf-8")

async def main():
    ensure_dirs()
    cfg = load_config()

    # Check if this is a review adjustment call
    architect_mode = os.environ.get("ARCHITECT_MODE", "normal")

def extract_qa_failure_context(story_id: str) -> str:
    """Extracts QA failure details from the last report for architect context"""
    try:
        qa_report_path = ROOT / "artifacts" / "qa" / "last_report.json"
        if not qa_report_path.exists():
            return "No QA report available"

        with open(qa_report_path, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)

        failure_details = qa_data.get("failure_details", {})
        story_context = qa_data.get("story_context", "")

        if story_context != story_id:
            return f"QA failures do not correspond to this story ({story_context} vs {story_id})"

        # Format failure details
        failure_info = []
        for module, details in failure_details.items():
            if details:
                errors = details.get("errors", [])
                warnings = details.get("warnings", [])
                if errors:
                    failure_info.append(f"Module {module.upper()}:")
                    for error in errors:
                        failure_info.append(f"  - Test {error['test']}: {error['error'][:200]}...")
                if warnings:
                    failure_info.append(f"Warnings {module.upper()}:")
                    for warning in warnings:
                        failure_info.append(f"  - {warning}")

        if failure_info:
            return "\n".join(failure_info)
        else:
            return "Could not analyze specific failure details from QA"

    except Exception as e:
        return f"Error extracting QA context: {e}"

def get_story_priority(stories_content: str, story_id: str) -> str:
    """Extrae la prioridad de una historia específica del contenido YAML"""
    import yaml
    try:
        stories = yaml.safe_load(stories_content)
        if isinstance(stories, dict) and "stories" in stories:
            stories = stories["stories"]

        for story in stories:
            if isinstance(story, dict) and story.get("id") == story_id:
                return story.get("priority", "P2")
        return "P2"
    except Exception as e:
        print(f"Error parsing stories for priority: {e}")
        return "P2"

async def main():
    ensure_dirs()
    cfg = load_config()

    # Check if this is a review adjustment call
    architect_mode = os.environ.get("ARCHITECT_MODE", "normal")

    role = cfg["roles"]["architect"]
    prov = role.get("provider","ollama")
    base = cfg["providers"]["ollama"].get("base_url","http://localhost:11434") if prov=="ollama" else cfg["providers"].get("openai",{}).get("base_url")

    # Read requirements if available
    requirements_file = PLANNING/"requirements.yaml"
    requirements_content = ""
    if requirements_file.exists():
        requirements_content = requirements_file.read_text(encoding="utf-8")

    client = LLMClient(prov, role["model"], role.get("temperature",0.2), role.get("max_tokens",2048), base)
    concept = os.environ.get("CONCEPT","")

    if architect_mode == "review_adjustment":
        # Mode for adjusting stories in review
        story_id = os.environ.get("STORY", "")
        detail_level = os.environ.get("DETAIL_LEVEL", "medium")
        iteration_count = int(os.environ.get("ITERATION_COUNT", "1"))

        if story_id:
            # Read current stories to find the one in review
            stories_file = PLANNING/"stories.yaml"
            if stories_file.exists():
                stories_content = stories_file.read_text(encoding="utf-8")

                # Adjust detail level based on iteration
                if detail_level == "high":
                    instruction = f"REVISIÓN TÉCNICA CRÍTICA: Ajusta los criterios de aceptación para la historia {story_id} que está en review. Los criterios actuales son ambiguos y el desarrollador no pudo implementarlos correctamente.\n\nREQUERIMIENTOS ESPECÍFICOS:\n- Especifica EXACTAMENTE qué debe hacer cada función\n- Define formatos de request/response PRECISOS\n- Incluye validaciones ESPECÍFICAS con ejemplos\n- Especifica códigos de error EXACTOS\n- Define estructuras de datos COMPLETAS\n- Incluye casos edge ESPECÍFICOS\n\nEl desarrollador necesita instrucciones TÉCNICAMENTE PRECISAS para implementar correctamente."
                elif detail_level == "maximum":
                    qa_context_info = extract_qa_failure_context(story_id)
                    instruction = f"REVISIÓN TÉCNICA MÁXIMA: La historia {story_id} ha sido rechazada {iteration_count} veces. Los criterios deben ser EXTREMADAMENTE DETALLADOS.\n\nDETALLES DE FALLOS QA:\n{qa_context_info}\n\nREQUERIMIENTOS CRÍTICOS:\n- ESPECIFICA CADA VALIDACIÓN con regex exactos\n- DEFINE CADA ENDPOINT con ejemplos de request/response COMPLETOS\n- INCLUYE MANEJO DE ERRORES para CADA caso posible\n- ESPECIFICA FORMATOS de datos con tipos y longitudes\n- DEFINE COMPORTAMIENTOS exactos para casos edge\n- INCLUYE EJEMPLOS de código para cada función\n\nEl desarrollador necesita un ESPECIFICACIÓN TÉCNICA COMPLETA."
                elif detail_level == "force_approve":
                    instruction = f"APROBACIÓN POR URGENCIA: La historia {story_id} ha sido rechazada {iteration_count} veces. Dado que es prioridad {get_story_priority(stories_content, story_id)}, el arquitecto puede aprobarla.\n\nINSTRUCCIÓN: Si la funcionalidad básica está implementada y solo faltan detalles menores de testing, puedes generar una versión simplificada de la historia que permita al desarrollador completarla exitosamente.\n\nConsidera: ¿La funcionalidad core está presente? ¿Solo faltan tests o detalles menores? ¿El bloqueo impide progreso del proyecto?"
                else:
                    instruction = f"Ajusta los criterios de aceptación para la historia {story_id} que está en review. Haz los criterios más claros y específicos para que el desarrollador pueda implementarlos correctamente."

                user_input = f"REQUIREMENTS:\n{requirements_content}\n\nCURRENT_STORIES:\n{stories_content}\n\n{detail_level.upper()}: {instruction}"
        else:
            user_input = f"REQUIREMENTS:\n{requirements_content}\n\nINSTRUCTION: Revisa y ajusta las historias que están en review para mejorar su claridad técnica y criterios de aceptación."
    else:
        # Normal planning mode - BREAKDOWN INCREMENTAL para proyectos enterprise
        user_input = f"CONCEPT:\n{concept}\n\nREQUIREMENTS:\n{requirements_content}\n\nFollow the exact output format."

    print(f"Using CONCEPT: {os.environ.get('CONCEPT', 'No concept defined')}")
    print(f"Architect mode: {architect_mode}")
    print(f"Model: {role['model']}, Temp: {role.get('temperature', 0.2)}, Max tokens: {role.get('max_tokens', 2048)}")
    print(f"System prompt length: {ARCH_PROMPT}")
    print(f"User input: {user_input}...")

    text = await client.chat(system=ARCH_PROMPT, user=user_input)

    # DEBUG: Save full response
    (ROOT / "debug_architect_response.txt").write_text(text, encoding="utf-8")

    def grab(tag, label):
        m = re.search(rf"```{tag}\s+{label}\s*([\s\S]*?)```", text)
        return m.group(1).strip() if m else ""

    # Extract sections
    prd_content = grab("yaml","PRD")
    arch_content = grab("yaml","ARCH")
    epics_content = grab("yaml","EPICS")
    stories_content = grab("yaml","STORIES")
    tasks_content = grab("csv","TASKS")

    # Write sections to files
    (PLANNING/"prd.yaml").write_text(prd_content, encoding="utf-8")
    (PLANNING/"architecture.yaml").write_text(arch_content, encoding="utf-8")
    (PLANNING/"epics.yaml").write_text(epics_content, encoding="utf-8")
    (PLANNING/"stories.yaml").write_text(stories_content, encoding="utf-8")
    (PLANNING/"tasks.csv").write_text(tasks_content, encoding="utf-8")

    print("✓ planning written under planning/")

if __name__ == "__main__":
    asyncio.run(main())
