from __future__ import annotations

import asyncio
import json
import os
import re
from typing import List, Tuple

import yaml

from common import ensure_dirs, PLANNING, ROOT
from llm import Client


DEFAULT_ARCHITECT_PROMPT = (ROOT / "prompts" / "architect.md").read_text(encoding="utf-8")

REVIEW_ADJUSTMENT_PROMPT = """You are a Technical Requirements Analyst that adjusts a SINGLE user story when it fails QA.

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


def get_architect_prompt(mode: str) -> str:
    return REVIEW_ADJUSTMENT_PROMPT if mode == "review_adjustment" else DEFAULT_ARCHITECT_PROMPT


def load_stories() -> Tuple[str, List[dict]]:
    stories_file = PLANNING / "stories.yaml"
    if not stories_file.exists():
        return ("", [])

    content = stories_file.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(content) or []
    except Exception:
        data = []

    if isinstance(data, dict) and "stories" in data:
        data = data["stories"]

    if not isinstance(data, list):
        return (content, [])
    return (content, data)


def save_stories(stories: List[dict]) -> None:
    stories_file = PLANNING / "stories.yaml"
    stories_file.write_text(
        yaml.safe_dump(stories, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def extract_qa_failure_context(story_id: str) -> str:
    """Extract detailed QA failure context for the requested story."""
    try:
        qa_report_path = ROOT / "artifacts" / "qa" / "last_report.json"
        if not qa_report_path.exists():
            return "No QA report available"

        qa_data = json.loads(qa_report_path.read_text(encoding="utf-8"))
        failure_details = qa_data.get("failure_details", {})
        story_context = qa_data.get("story_context", "")

        if story_context and story_context != story_id:
            return f"QA failures correspond to {story_context}, not {story_id}"

        failure_info: List[str] = []
        for module, details in failure_details.items():
            errors = details.get("errors", []) if isinstance(details, dict) else []
            warnings = details.get("warnings", []) if isinstance(details, dict) else []
            if errors:
                failure_info.append(f"Module {module.upper()}:")
                for error in errors:
                    failure_info.append(f"  - Test {error.get('test','?')}: {error.get('error','')[:200]}...")
            if warnings:
                failure_info.append(f"Warnings {module.upper()}:")
                for warning in warnings:
                    failure_info.append(f"  - {warning}")

        return "\n".join(failure_info) if failure_info else "No detailed QA errors extracted"
    except Exception as exc:
        return f"Error extracting QA context: {exc}"


def try_programmatic_adjustment(story_id: str, detail_level: str) -> bool:
    """Attempt to adjust a story without invoking the LLM."""
    stories_content, stories = load_stories()
    if not stories:
        print(f"[ARCHITECT] No stories available to adjust for {story_id}")
        return False

    target = None
    for story in stories:
        if isinstance(story, dict) and str(story.get("id")) == story_id:
            target = story
            break

    if not target:
        print(f"[ARCHITECT] Story {story_id} not found for programmatic adjustment")
        return False

    acceptance = target.get("acceptance", [])
    if not isinstance(acceptance, list):
        acceptance = [acceptance] if acceptance else []

    additions: List[str] = []
    level = detail_level.lower()
    if level == "high":
        additions = [
            "Documentar validaciones exhaustivas con formatos y límites claros.",
            "Definir códigos HTTP o mensajes de error específicos para cada fallo esperado.",
            "Cubrir escenarios edge incluyendo datos nulos, duplicados o inconsistentes.",
        ]
        print(f"[ARCHITECT] Adding HIGH detail acceptance criteria to {story_id}")
    elif level == "maximum":
        qa_context = extract_qa_failure_context(story_id)
        if "pytest_execution" in qa_context:
            additions = [
                "Configurar correctamente backend/.venv/bin/pytest y asegurar su disponibilidad.",
                "Verificar instalación de dependencias de testing y rutas relativas.",
            ]
            print(f"[ARCHITECT] Adding pytest-focused fixes to {story_id}")
        else:
            additions = [
                "Aplicar validaciones con expresiones regulares para cada entrada crítica.",
                "Agregar logging detallado a nivel debug para rastrear incidentes.",
                "Manejar timeouts y reconexiones en llamados externos involucrados.",
            ]
            print(f"[ARCHITECT] Adding MAXIMUM technical requirements to {story_id}")

    for item in additions:
        if item not in acceptance:
            acceptance.append(item)

    if not additions:
        print(f"[ARCHITECT] No programmatic additions computed for {story_id} (detail level {detail_level})")
        return False

    target["acceptance"] = acceptance
    target["status"] = "todo"
    save_stories(stories)
    print(f"[ARCHITECT] Programmatic adjustment complete for {story_id}")
    return True


def mark_story_todo(story_id: str) -> bool:
    """Fallback: mark story as todo when adjustments cannot be automated."""
    _, stories = load_stories()
    if not stories:
        return False

    updated = False
    for story in stories:
        if isinstance(story, dict) and str(story.get("id")) == story_id:
            story["status"] = "todo"
            updated = True
            break

    if not updated:
        return False

    save_stories(stories)
    return True


async def main() -> None:
    ensure_dirs()

    architect_mode = os.environ.get("ARCHITECT_MODE", "normal")
    concept = os.environ.get("CONCEPT", "").strip()
    story_id = os.environ.get("STORY", "").strip()
    detail_level = os.environ.get("DETAIL_LEVEL", "medium")
    try:
        iteration_count = int(os.environ.get("ITERATION_COUNT", "1"))
    except ValueError:
        iteration_count = 1

    requirements_path = PLANNING / "requirements.yaml"
    requirements_content = requirements_path.read_text(encoding="utf-8") if requirements_path.exists() else ""
    stories_content, _stories_snapshot = load_stories()

    if architect_mode == "review_adjustment" and story_id:
        print(f"[ARCHITECT] Programmatic review adjustment for {story_id} (level={detail_level}, iteration={iteration_count})")
        if try_programmatic_adjustment(story_id, detail_level):
            print(f"✓ Arquitecto ajustó criterios de {story_id} (programático)")
            return
        if mark_story_todo(story_id):
            print(f"✓ Arquitecto marcó {story_id} como todo (fallback)")
            return
        print(f"[ARCHITECT] Programmatic adjustment failed; falling back to LLM for {story_id}")

    arch_prompt = get_architect_prompt(architect_mode)

    if architect_mode == "review_adjustment":
        user_input = (
            f"CURRENT_STORIES:\n{stories_content}\n\n"
            f"DETAIL_LEVEL: {detail_level}\nITERATION_COUNT: {iteration_count}\n"
            "INSTRUCTION: Ajusta únicamente las historias en estado in_review o bloqueadas, "
            "añadiendo criterios de aceptación técnicos y accionables."
        )
        if story_id:
            user_input += f"\nTARGET_STORY: {story_id}"
    else:
        user_input = (
            f"CONCEPT:\n{concept}\n\nREQUIREMENTS:\n{requirements_content}\n\n"
            "Follow the exact output format."
        )

    client = Client(role="architect")
    print(f"Using CONCEPT: {concept or 'No concept defined'}")
    print(f"Architect mode: {architect_mode}")
    print(
        f"Provider: {client.provider_type} | Model: {client.model} | "
        f"Temp: {client.temperature} | Max tokens: {client.max_tokens}"
    )
    print(f"System prompt length: {len(arch_prompt)}")
    print(f"User input preview: {user_input[:300]}...")

    text = await client.chat(system=arch_prompt, user=user_input)

    (ROOT / "debug_architect_response.txt").write_text(text, encoding="utf-8")

    def grab(tag: str, label: str) -> str:
        match = re.search(rf"```{tag}\s+{label}\s*([\s\S]*?)```", text)
        return match.group(1).strip() if match else ""

    (PLANNING / "prd.yaml").write_text(grab("yaml", "PRD"), encoding="utf-8")
    (PLANNING / "architecture.yaml").write_text(grab("yaml", "ARCH"), encoding="utf-8")
    (PLANNING / "epics.yaml").write_text(grab("yaml", "EPICS"), encoding="utf-8")
    (PLANNING / "stories.yaml").write_text(grab("yaml", "STORIES"), encoding="utf-8")
    (PLANNING / "tasks.csv").write_text(grab("csv", "TASKS"), encoding="utf-8")

    print("✓ planning written under planning/")


if __name__ == "__main__":
    asyncio.run(main())
