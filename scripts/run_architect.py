from __future__ import annotations
import os, re, asyncio, pathlib
from common import load_config, ensure_dirs, PLANNING, ROOT
from llm import LLMClient

ARCH_PROMPT = ""

# Select appropriate prompt based on mode
architect_mode = os.environ.get("ARCHITECT_MODE", "normal")
if architect_mode == "review_adjustment":
    # Special prompt for review adjustment mode
    ARCH_PROMPT = """You are a Technical Requirements Analyst that adjusts a SINGLE user story when it fails QA.

IMPORTANT: DO NOT CREATE NEW EPICS OR STORIES. ONLY ADJUST THE EXISTING STORY.

Take the CURRENT_STORIES section and find the specific story ID mentioned.
MODIFY ONLY THAT STORY'S acceptance criteria to be more technical and specific.

OUTPUT FORMAT: Return ONLY the adjusted story with the same ID, adding more technical details to acceptance criteria.

Example output:
```yaml STORIES
- id: S2
  epic: E1
  description: Existing description here
  acceptance:
    - More technical criterion 1
    - More technical criterion 2
    - Include specific validations, formats, error codes
  priority: P1
  status: todo
```

Include specific technical requirements, test cases, missing imports, missing dependencies not installed, validation rules, error codes, and edge cases in the acceptance criteria."""
else:
    # Normal architect prompt
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
                # DIRECT TEMPLATE-BASED ADJUSTMENTS - More reliable than LLM
                print(f"[ARCHITECT] Aplicando ajustes programáticos para {story_id} - nivel {detail_level}")

                # Parse current stories
                import yaml
                try:
                    stories = yaml.safe_load(stories_content)
                    if isinstance(stories, dict) and "stories" in stories:
                        stories = stories["stories"]
                    elif isinstance(stories, list):
                        pass
                    else:
                        raise ValueError("Invalid stories format")

                    # Find the story to adjust
                    story_found = None
                    for story in stories:
                        if isinstance(story, dict) and story.get("id") == story_id:
                            story_found = story
                            break

                    if story_found:
                        acceptance = story_found.get("acceptance", [])
                        if not isinstance(acceptance, list):
                            acceptance = [acceptance] if acceptance else []

                        # Apply template-based improvements based on detail level
                        if detail_level == "high":
                            # Add technical requirements template
                            technical_reqs = [
                                "Implementar validaciones específicas con formatos y límites claros",
                                "Definir códigos HTTP apropiados para diferentes escenarios de error",
                                "Incluir manejo de casos edge como datos nulos o inválidos"
                            ]
                            acceptance.extend(technical_reqs)
                            print(f"[ARCHITECT] Added HIGH technical requirements to criteria")

                        elif detail_level == "maximum":
                            qa_context = extract_qa_failure_context(story_id)
                            # Add specific improvements based on QA errors
                            if "pytest_execution" in qa_context:
                                acceptance.append("Configurar entorno pytest correctamente en backend/.venv/bin/pytest")
                                acceptance.append("Asegurar que dependencias de testing estén instaladas")
                                print("[ARCHITECT] Added pytest-specific requirements to criteria")
                            else:
                                technical_reqs = [
                                    "Validar todos los inputs con regex patterns específicos",
                                    "Implementar logging detallado para debugging",
                                    "Verificar manejo de conexiones de red y timeouts"
                                ]
                                acceptance.extend(technical_reqs)
                                print(f"[ARCHITECT] Added MAXIMUM technical requirements to criteria")

                        # Update the story
                        story_found["acceptance"] = acceptance
                        story_found["status"] = "todo"  # Ready for dev rework

                        # Save back to file
                        with open(PLANNING / "stories.yaml", 'w', encoding='utf-8') as f:
                            yaml.safe_dump(stories, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

                        print(f"✓ Arquitecto ajustó criterios de {story_id} (programáticamente)")
                        return  # Exit successfully after programatic adjustment

                except Exception as e:
                    print(f"[ARCHITECT] Error en ajustes programáticos: {e}")
                    # Fall back to minimal fallback - just mark story as todo
                    print(f"[ARCHITECT] Fallback: marking {story_id} as todo for reattempt")

                    try:
                        import yaml
                        stories = yaml.safe_load(stories_content)
                        if isinstance(stories, dict) and "stories" in stories:
                            stories = stories["stories"]
                        elif isinstance(stories, list):
                            pass

                        for story in stories:
                            if isinstance(story, dict) and story.get("id") == story_id:
                                story["status"] = "todo"
                                break

                        with open(PLANNING / "stories.yaml", 'w', encoding='utf-8') as f:
                            yaml.safe_dump(stories, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

                        print(f"✓ Arquitecto marcó {story_id} como todo (fallback)")
                        return

                    except Exception as e2:
                        print(f"[ARCHITECT] Critical fallback error: {e2}")
                        return
        else:
            user_input = f"REQUIREMENTS:\n{requirements_content}\n\nINSTRUCTION: Revisa y ajusta las historias que están en review para mejorar su claridad técnica y criterios de aceptación."
    else:
        # Normal planning mode - BREAKDOWN INCREMENTAL para proyectos enterprise
        user_input = f"CONCEPT:\n{concept}\n\nREQUIREMENTS:\n{requirements_content}\n\nFollow the exact output format."

    # Log the input for debugging
    print(f"[DEBUG] Architect input length: {len(user_input)}")
    print(f"[DEBUG] Architect mode: {architect_mode}")
    if architect_mode == "review_adjustment":
        print(f"[DEBUG] Reviewing story: {story_id}, level: {detail_level}, iteration: {iteration_count}")

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
