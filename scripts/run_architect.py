from __future__ import annotations

import asyncio
import json
import os
import re
from typing import List, Tuple

import yaml

from common import ensure_dirs, PLANNING, ROOT
from llm import Client


ARCHITECT_PROMPTS = {
    "simple": (ROOT / "prompts" / "architect_simple.md").read_text(encoding="utf-8"),
    "medium": (ROOT / "prompts" / "architect.md").read_text(encoding="utf-8"),
    "corporate": (ROOT / "prompts" / "architect_corporate.md").read_text(encoding="utf-8"),
}

REVIEW_ADJUSTMENT_PROMPT = (ROOT / "prompts" / "architect_review_adjustment.md").read_text(
    encoding="utf-8"
)
COMPLEXITY_CLASSIFIER_PROMPT = (
    ROOT / "prompts" / "architect_complexity_classifier.md"
).read_text(encoding="utf-8")


def get_architect_prompt(mode: str, tier: str) -> str:
    if mode == "review_adjustment":
        return REVIEW_ADJUSTMENT_PROMPT
    return ARCHITECT_PROMPTS.get(tier, ARCHITECT_PROMPTS["medium"])


async def classify_complexity_with_llm(requirements_text: str) -> str:
    """Ask the architect model to classify requirements as simple/medium/corporate."""
    cleaned = (requirements_text or "").strip()
    if not cleaned:
        return "simple"

    try:
        client = Client(role="architect")
        user = (
            "REQUIREMENTS:\n"
            f"{cleaned}\n\n"
            "Respond with exactly one word: simple, medium, or corporate."
        )
        response = await client.chat(system=COMPLEXITY_CLASSIFIER_PROMPT, user=user)
        tier = parse_complexity_response(response)
        if tier:
            return tier
        print(f"[ARCHITECT] Unexpected classifier response: {response[:120]!r}")
    except Exception as exc:
        print(f"[ARCHITECT] Complexity classifier failed via LLM: {exc}")

    return fallback_complexity(cleaned)


def parse_complexity_response(text: str) -> str | None:
    if not text:
        return None
    lowered = text.strip().split()
    if not lowered:
        return None
    candidate = lowered[0].lower().strip(",.:;")
    if candidate in {"simple", "medium", "corporate"}:
        return candidate
    return None


def fallback_complexity(requirements_text: str) -> str:
    """Fallback heuristic when the classifier cannot determine a tier."""
    words = len(requirements_text.split())
    if words <= 350:
        return "simple"
    if words >= 900:
        return "corporate"
    return "medium"


def extract_original_concept(requirements_text: str) -> str:
    """Pull the stored concept from requirements metadata if available."""
    if not requirements_text.strip():
        return ""
    try:
        data = yaml.safe_load(requirements_text)
    except Exception as exc:
        print(f"[ARCHITECT] Failed to parse requirements metadata: {exc}")
        return ""

    if isinstance(data, dict):
        meta = data.get("meta")
        if isinstance(meta, dict):
            original = meta.get("original_request")
            if isinstance(original, str):
                return original.strip()
    return ""


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
    concept_env = os.environ.get("CONCEPT", "").strip()
    story_id = os.environ.get("STORY", "").strip()
    detail_level = os.environ.get("DETAIL_LEVEL", "medium")
    try:
        iteration_count = int(os.environ.get("ITERATION_COUNT", "1"))
    except ValueError:
        iteration_count = 1

    requirements_path = PLANNING / "requirements.yaml"
    requirements_content = requirements_path.read_text(encoding="utf-8") if requirements_path.exists() else ""
    concept_meta = extract_original_concept(requirements_content)
    concept = concept_meta or concept_env
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

    force_tier = os.environ.get("FORCE_ARCHITECT_TIER", "").strip().lower()
    if force_tier in {"simple", "medium", "corporate"}:
        complexity_tier = force_tier
        print(f"[ARCHITECT] Forced complexity tier via env: {complexity_tier}")
    elif architect_mode == "review_adjustment":
        complexity_tier = "medium"
    else:
        complexity_tier = await classify_complexity_with_llm(requirements_content)

    arch_prompt = get_architect_prompt(architect_mode, complexity_tier)

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
            f"COMPLEXITY_TIER: {complexity_tier.upper()}\n\n"
            "Follow the exact output format."
        )

    client = Client(role="architect")
    if concept_meta and not concept_env:
        print("[ARCHITECT] Using concept from requirements metadata.")
    elif concept_env and not concept_meta:
        print("[ARCHITECT] Concept provided via environment (no metadata found).")
    elif concept_env and concept_meta and concept_env != concept_meta:
        print("[ARCHITECT] Concept differs between env and metadata; using metadata.")
    print(f"Using CONCEPT: {concept or 'No concept defined'}")
    print(f"Architect mode: {architect_mode}")
    if architect_mode != "review_adjustment":
        print(f"Complexity tier selected: {complexity_tier}")
    print(
        f"Provider: {client.provider_type} | Model: {client.model} | "
        f"Temp: {client.temperature} | Max tokens: {client.max_tokens}"
    )
    print(f"System prompt length: {len(arch_prompt)}")
    print(f"User input preview: {user_input[:300]}...")

    text = await client.chat(system=arch_prompt, user=user_input)

    (ROOT / "debug_architect_response.txt").write_text(text, encoding="utf-8")

    def grab(tag: str, label: str) -> str:
        # Updated regex to be more robust for YAML/CSV block extraction
        pattern = re.compile(rf"```{tag}\s*{label}\s*\n([\s\S]+?)\n```", re.MULTILINE)
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    # Extract and save all planning artifacts
    (PLANNING / "prd.yaml").write_text(grab("yaml", "PRD"), encoding="utf-8")
    (PLANNING / "architecture.yaml").write_text(grab("yaml", "ARCHITECTURE"), encoding="utf-8") # Changed label to match prompt
    (PLANNING / "epics.yaml").write_text(grab("yaml", "EPICS"), encoding="utf-8")
    (PLANNING / "stories.yaml").write_text(grab("yaml", "STORIES"), encoding="utf-8")
    (PLANNING / "tasks.csv").write_text(grab("csv", "TASKS"), encoding="utf-8")

    print("✓ planning written under planning/")


if __name__ == "__main__":
    asyncio.run(main())
