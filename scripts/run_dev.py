from __future__ import annotations

import asyncio
import datetime
import json
import os
import re
import sys
import textwrap
import pathlib
from typing import List, Dict, Any, Optional

import typer
import yaml
from common import ensure_dirs, PLANNING, ROOT
from llm import Client
from logger import logger # Import the logger

# --- Paths ---
ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "planning"
PROJECT = ROOT / "project"
DEV_ART_DIR = ROOT / "artifacts" / "dev"
DEV_ART_DIR.mkdir(parents=True, exist_ok=True)


DEV_PROMPT = ROOT / "prompts" / "developer.md"


# --- YAML helpers (robust load that can recover from commented YAML) ---
def _try_recover_commented_yaml(text: str) -> Any:
    """
    Some architects print all stories commented (# - id: S1 ...).
    Recover by stripping a single leading '# ' while preserving indentation.
    """
    clean: List[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            clean.append(re.sub(r"^(\s*)#\s?", r"\1", line))
        else:
            clean.append(line)
    candidate = "\n".join(clean).strip()
    if not candidate:
        logger.debug("[DEV] No candidate text for YAML recovery.")
        return None
    try:
        return yaml.safe_load(candidate)
    except Exception as exc:
        logger.debug(f"[DEV] YAML recovery failed: {exc}")
        return None


def load_stories() -> List[Dict[str, Any]]:
    p = PLAN / "stories.yaml"
    if not p.exists():
        logger.info("[DEV] planning/stories.yaml not found.")
        return []
    raw = p.read_text(encoding="utf-8")
    data = None
    try:
        data = yaml.safe_load(raw)
    except Exception as exc:
        logger.debug(f"[DEV] Primary YAML load failed: {exc}. Attempting recovery.")
        data = None

    if isinstance(data, dict) and "stories" in data:
        data = data["stories"]

    if not isinstance(data, list):
        recovered = _try_recover_commented_yaml(raw)
        if isinstance(recovered, dict) and "stories" in recovered:
            recovered = recovered["stories"]
        if isinstance(recovered, list):
            data = recovered
        if not data:
            logger.warning("[DEV] Failed to load or recover stories.yaml.")

    # ensure we return list
    return data if isinstance(data, list) else []


def pick_story(stories: List[Dict[str, Any]], sid_env: str | None) -> Dict[str, Any] | None:
    if sid_env:
        sid_env_l = sid_env.strip().lower()
        for s in stories:
            sid = str(s.get("id", "")).strip().lower()
            if sid == sid_env_l:
                logger.info(f"[DEV] Picked story from env: {sid}")
                return s
        logger.warning(f"[DEV] Story ID '{sid_env}' from env not found.")
        return None
    for s in stories:
        if str(s.get("status", "")).lower() == "todo":
            logger.info(f"[DEV] Picked next 'todo' story: {s.get('id', 'S?')}")
            return s
    logger.info("[DEV] No 'todo' stories found.")
    return None


# --- Repo tree snapshot with caching ---
_repo_tree_cache = {"mtime": 0.0, "content": ""}

def repo_tree(limit: int = 300) -> str:
    """Generate a snapshot of the repository tree, with in-memory caching."""
    global _repo_tree_cache
    
    try:
        current_mtime = (ROOT / "project").stat().st_mtime
    except FileNotFoundError:
        current_mtime = 0.0

    if current_mtime == _repo_tree_cache["mtime"] and _repo_tree_cache["content"]:
        logger.debug("[DEV] Using cached repo tree.")
        return _repo_tree_cache["content"]

    logger.debug("[DEV] Generating new repo tree (project directory changed).")
    skip = {".venv","node_modules",".git","__pycache__","artifacts",".pytest_cache",".DS_Store",".idea",".vscode","dist","build"}
    files: List[str] = []
    for root, _, fns in os.walk(ROOT):
        rel = os.path.relpath(root, ROOT)
        parts = pathlib.Path(rel).parts
        if any(seg in skip for seg in parts):
            continue
        for fn in fns:
            if fn.startswith("."):
                continue
            p = pathlib.Path(root, fn)
            relp = p.relative_to(ROOT).as_posix()
            files.append(relp)
            if len(files) >= limit:
                logger.debug(f"[DEV] Repo tree limited to {limit} files.")
                break
    
    content = "\n".join(files)
    _repo_tree_cache["mtime"] = current_mtime
    _repo_tree_cache["content"] = content
    
    logger.debug(f"[DEV] Repo tree generated and cached with {len(files)} files.")
    return content


# --- LLM plumbing ---
def extract_files_block(text: str, story_id: str) -> List[Dict[str, str]] | None:
    story_art_dir = DEV_ART_DIR / story_id
    story_art_dir.mkdir(parents=True, exist_ok=True)
    (story_art_dir / "last_raw.txt").write_text(text, encoding="utf-8")

    def _json_load(candidate: str) -> Any | None:
        try:
            return json.loads(candidate)
        except Exception as exc:
            logger.debug(f"[DEV] Failed to load JSON candidate: {exc}")
            return None

    def _find_file_entry(obj: Any) -> Dict[str, Any] | None:
        if isinstance(obj, dict):
            if "path" in obj and "code" in obj:
                return obj
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    found = _find_file_entry(value)
                    if found:
                        return found
                elif isinstance(value, str):
                    candidate = value.strip()
                    if candidate.startswith("{") or candidate.startswith("["):
                        nested = _json_load(candidate)
                        if nested:
                            found = _find_file_entry(nested)
                            if found:
                                return found
        elif isinstance(obj, list):
            for item in obj:
                found = _find_file_entry(item)
                if found:
                    return found
        return None

    parsed_file_entry = None
    stripped_text = text.strip()

    # Task: fix-gemini-parser - Strip markdown fences before parsing
    # Gemini often wraps JSON in ```json...```
    cleaned_text = re.sub(r'^```\w*\s*\n', '', stripped_text, flags=re.MULTILINE)
    cleaned_text = re.sub(r'\n```\s*$', '', cleaned_text).strip()

    # First, attempt to load the entire payload as JSON (covers wrapped responses)
    top_level = _json_load(cleaned_text)
    if top_level:
        parsed_file_entry = _find_file_entry(top_level)
        if parsed_file_entry:
            logger.debug("[DEV] Extracted file entry from top-level JSON structure (after fence cleanup).")

    # Fallback: search for inline JSON object snippets
    if not parsed_file_entry:
        candidates: List[str] = []
        # Task: fix-gemini-parser - use cleaned_text for fallback too
        for match in re.finditer(r"(\{[\s\S]*?\})", cleaned_text):
            candidates.append(match.group(1))

        if candidates:
            logger.debug(f"[DEV] Scanned {len(candidates)} inline JSON candidate(s).")
        else:
            logger.debug("[DEV] No inline JSON candidates located.")

        for candidate in candidates:
            parsed = _json_load(candidate.strip())
            if isinstance(parsed, dict) and "path" in parsed and "code" in parsed:
                parsed_file_entry = parsed
                logger.debug("[DEV] Successfully parsed file entry from inline JSON block.")
                break

    if not parsed_file_entry:
        logger.warning("[DEV] No valid FILES JSON block parsed from LLM response.")
        return None

    # Clean and convert from new format (code field) to old format (content field)
    if "code" in parsed_file_entry:
        code = parsed_file_entry["code"]
        # Aggressively clean markdown blocks
        code = re.sub(r'```\w*\s*\n?', '', code.strip())
        code = re.sub(r'```', '', code)
        code = code.strip()
        logger.debug(f"[DEV] Cleaned code block with {len(code)} characters.")


        # Convert to content field
        parsed_file_entry["content"] = code

        # Remove the code field
        del parsed_file_entry["code"]

    # Ensure path is a string
    if not isinstance(parsed_file_entry.get("path"), str):
        logger.error(f"[DEV] Invalid path type in parsed file entry: {type(parsed_file_entry.get('path'))}")
        return None

    return [parsed_file_entry] # Return as a list of one file for compatibility


def safe_write(rel_path: str, content: str) -> str:
    if not rel_path.startswith("project/"):
        rel_path = f"project/{rel_path.lstrip('/')}"
    target = ROOT / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    resolved = target.resolve()
    if not str(resolved).startswith(str(PROJECT.resolve())):
        logger.error(f"[DEV] Path escapes project/: {rel_path}")
        raise ValueError(f"path escapes project/: {rel_path}")
    target.write_text(content, encoding="utf-8")
    logger.info(f"[DEV] Wrote file: {rel_path} ({len(content)} bytes)")
    return rel_path


async def llm_call(story: Dict[str, Any], files_ctx: str) -> tuple[str, Dict[str, Any]]:
    from llm import Client
    from common import load_config

    # Task: recovery-system - Check for model_override in story metadata
    model_override = story.get("metadata", {}).get("model_override", {})

    if model_override:
        override_provider = model_override.get("provider")
        override_model = model_override.get("model")
        logger.info(f"[DEV] Using model override: provider={override_provider}, model={override_model}")

        # Task: fix-client-override - Load full provider config to rehydrate CLI settings
        config = load_config()
        providers = config.get("providers", {})
        provider_cfg = providers.get(override_provider, {})

        if not provider_cfg:
            logger.error(f"[DEV] Provider '{override_provider}' not found in config.yaml. Cannot fallback.")
            raise ValueError(f"Provider '{override_provider}' not configured in config.yaml providers section")

        # Initialize client normally to get role config first
        client = Client(role="dev")

        # Override provider settings with full config rehydration
        provider_type = provider_cfg.get("type", override_provider)
        client.provider_type = provider_type
        client.model = override_model
        client.provider_options = provider_cfg

        # Rehydrate provider-specific settings based on type
        if provider_type in ("codex_cli", "claude_cli"):
            default_command = ["codex", "chat"] if provider_type == "codex_cli" else ["claude", "-p", "--print"]
            client.cli_command = provider_cfg.get("command", default_command)
            client.cli_cwd = provider_cfg.get("cwd", ".")
            client.cli_env = provider_cfg.get("env", {})
            client.cli_timeout = int(provider_cfg.get("timeout", 300))
            client.cli_input_format = provider_cfg.get("input_format", "stdin_text")
            client.cli_output_clean = bool(provider_cfg.get("output_clean", True))
            client.cli_extra_args = provider_cfg.get("extra_args", [])
            client.cli_parse_json = bool(provider_cfg.get("parse_json", False))
            client.cli_append_model_flag = bool(provider_cfg.get("append_model", True))
            client.cli_append_system_prompt = bool(provider_cfg.get("append_system_prompt", False))
            client.cli_append_temperature_flag = bool(provider_cfg.get("append_temperature", False))
            client.cli_append_max_tokens_flag = bool(provider_cfg.get("append_max_tokens", False))

            prompt_template_default = (
                "{user}" if provider_type == "claude_cli" else
                "System: {system}\n\nUser: {user}\n\nSettings: temperature={temperature}, max_tokens={max_tokens}"
            )
            client.cli_prompt_template = provider_cfg.get("prompt_template", prompt_template_default)

            default_debug_args = ["--verbose", "--debug"] if provider_type == "claude_cli" else []
            debug_args_cfg = provider_cfg.get("debug_args", default_debug_args)
            if isinstance(debug_args_cfg, (list, tuple)):
                client.cli_debug_args = [str(arg) for arg in debug_args_cfg]
            else:
                client.cli_debug_args = default_debug_args

            client.cli_debug = bool(provider_cfg.get("debug", False))
            client.cli_log_stderr = bool(provider_cfg.get("log_stderr", client.cli_debug))
            logger.debug(f"[DEV] Rehydrated CLI settings for {provider_type}: command={client.cli_command}")
        elif provider_type == "ollama":
            base_url = provider_cfg.get("base_url", "http://localhost:11434")
            client.ollama_base = os.environ.get("OLLAMA_BASE_URL") or base_url
            logger.debug(f"[DEV] Rehydrated Ollama settings: base_url={client.ollama_base}")
        elif provider_type == "openai":
            base_url = provider_cfg.get("base_url", "http://localhost:4010/v1")
            client.oai_base = os.environ.get("OPENAI_API_BASE") or base_url
            client.oai_key = os.environ.get("OPENAI_API_KEY", "dummy")
            logger.debug(f"[DEV] Rehydrated OpenAI settings: base_url={client.oai_base}")
        elif provider_type in ("vertex_cli", "vertex_sdk"):
            # Vertex providers are handled by PROVIDER_REGISTRY in Client.chat()
            logger.debug(f"[DEV] Using Vertex provider: {provider_type}")
        else:
            logger.warning(f"[DEV] Unknown provider type '{provider_type}', may not work correctly")
    else:
        client = Client(role="dev")

    logger.debug(f"[DEV] LLM Client initialized: provider={client.provider_type}, model={client.model}")

    # Task: fix-metadata-persistence - Return model info instead of mutating story
    model_info = {
        "provider": client.provider_type,
        "model": client.model,
        "timestamp": datetime.datetime.now().isoformat()
    }

    # Load prompt from file like other roles
    system_prompt = ""
    if DEV_PROMPT.exists():
        system_prompt = DEV_PROMPT.read_text(encoding="utf-8")
        logger.debug(f"[DEV] Loaded system prompt from {DEV_PROMPT} ({len(system_prompt)} chars)")
    else:
        logger.error(f"[DEV] Developer prompt file not found: {DEV_PROMPT}")
        raise FileNotFoundError(f"Developer prompt file not found: {DEV_PROMPT}")


    story_txt = yaml.safe_dump(story, sort_keys=False, allow_unicode=True)
    user = textwrap.dedent(
        f"""\
        STORY (YAML):
        ```yaml
        {story_txt}
        ```

        REPO TREE (first lines):
        ```
        {files_ctx}
        ```
        """
    )
    logger.debug(f"[DEV] User prompt prepared ({len(user)} chars)")

    # Task: fix-metadata-persistence - Return model_info even when client.chat() fails
    # This ensures we can track which models were attempted even on errors
    try:
        response = await client.chat(system=system_prompt, user=user)
        return response, model_info
    except Exception as e:
        # client.chat() failed, but we still return model_info for tracking
        # The exception message becomes the error, model_info shows which model failed
        logger.debug(f"[DEV] client.chat() failed: {e}")
        return None, model_info  # Return None response but preserve model_info


async def implement_story(story_id: str | None = None, retries: int = 3) -> dict:
    stories = load_stories()
    story = pick_story(stories, story_id if story_id else None)
    if not story:
        logger.info("No stories to implement (stories.yaml vacío o sin 'todo'). Ejecuta make plan o normaliza stories.yaml.")
        sys.exit(1)

    sid = story.get("id", "S?")
    story_art_dir = DEV_ART_DIR / sid
    story_art_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"[DEV] Implementando: {sid} - {story.get('description', '(sin desc)')}")

    files_ctx = repo_tree(limit=300)
    files = None
    last_err = None
    model_info = None

    for i in range(1, retries + 1):
        logger.info(f"[DEV] LLM intento {i}/{retries}…")
        # Task: fix-metadata-persistence - llm_call now always returns model_info
        response, model_info = await llm_call(story, files_ctx)

        # response can be None if client.chat() failed
        if response is None:
            last_err = "LLM call failed to return a response"
            logger.warning(f"[DEV] Attempt {i} failed: {last_err}")
            await asyncio.sleep(0.2)
            continue

        files = extract_files_block(response or "", sid)
        if files:
            logger.info(f"[DEV] LLM response parsed successfully after {i} attempts.")
            break
        last_err = "Developer response did not include FILES JSON block."
        logger.warning(f"[DEV] Attempt {i} failed: {last_err}")
        await asyncio.sleep(0.2)

    if not files:
        error_msg = last_err or "[DEV] No FILES parsed from LLM response after all retries."
        logger.error(error_msg)
        # Task: fix-metadata-persistence - Return error dict with model_info instead of sys.exit()
        # This allows orchestrator to capture model_history even on failure
        return {
            "status": "error",
            "error": error_msg,
            "story_id": sid,
            "model_info": model_info,  # Include last model_info attempt
            "exit_code": 2
        }

    written = []
    for entry in files:
        rel = entry["path"]
        cnt = entry["content"]
        rel2 = safe_write(rel, cnt)
        written.append(rel2)

    (story_art_dir / "files.json").write_text(json.dumps(files, indent=2, ensure_ascii=False), encoding="utf-8")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = story_art_dir / f"run-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "files.json").write_text(json.dumps(files, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.debug(f"[DEV] Artifacts for run saved to {run_dir}")

    # The orchestrator is now responsible for marking the story status.
    # We no longer call mark_in_review(sid) here.

    logger.info(f"✓ wrote {len(written)} files under project/ (story {sid})")
    for w in written:
        logger.info(f" - {w}")

    return {
        "story_id": sid,
        "files_written": written,
        "artifacts_dir": str(run_dir),
        "model_info": model_info,  # Task: fix-metadata-persistence - Return model info for orchestrator
    }


async def _main_env() -> None:
    story_id = os.environ.get("STORY", "").strip() or None
    retries = int(os.environ.get("DEV_RETRIES", "3"))
    result = await implement_story(story_id, retries)
    logger.info(json.dumps(result, indent=2))


app = typer.Typer(help="Developer agent CLI")


@app.command()
def run(
    story_id: Optional[str] = typer.Option(None, help="Story identifier"),
    retries: int = typer.Option(3, help="LLM retry attempts"),
) -> None:
    result = asyncio.run(implement_story(story_id, retries))
    typer.echo(json.dumps(result, indent=2))


@app.command()
def serve(reload: bool = typer.Option(False, help="Auto-reload server on code changes")) -> None:
    from a2a.cards import developer_card
    from a2a.runtime import run_agent

    card, handlers = developer_card()
    run_agent("developer", card, handlers, reload=reload)


if __name__ == "__main__":
    # Check if running via make or directly
    if len(sys.argv) == 1 and os.environ.get("STORY"):
        asyncio.run(_main_env())
    else:
        app()
