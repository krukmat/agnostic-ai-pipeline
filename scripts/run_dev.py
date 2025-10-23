from __future__ import annotations

import asyncio
import datetime
import json
import os
import re
import sys
import textwrap
import pathlib
from typing import List, Dict, Any

import yaml


# --- Paths ---
ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "planning"
PROJECT = ROOT / "project"
ART_DIR = ROOT / "artifacts" / "dev"
ART_DIR.mkdir(parents=True, exist_ok=True)

LOG_ALL = ART_DIR / "last_raw.txt"
FILES_JSON = ART_DIR / "last_files.json"


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
        return None
    try:
        return yaml.safe_load(candidate)
    except Exception:
        return None


def load_stories() -> List[Dict[str, Any]]:
    p = PLAN / "stories.yaml"
    if not p.exists():
        return []
    raw = p.read_text(encoding="utf-8")
    data = None
    try:
        data = yaml.safe_load(raw)
    except Exception:
        data = None

    if isinstance(data, dict) and "stories" in data:
        data = data["stories"]

    if not isinstance(data, list):
        recovered = _try_recover_commented_yaml(raw)
        if isinstance(recovered, dict) and "stories" in recovered:
            recovered = recovered["stories"]
        if isinstance(recovered, list):
            data = recovered

    # ensure we return list
    return data if isinstance(data, list) else []


def save_stories(stories: List[Dict[str, Any]]) -> None:
    (PLAN / "stories.yaml").write_text(
        yaml.safe_dump(stories, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def pick_story(stories: List[Dict[str, Any]], sid_env: str | None) -> Dict[str, Any] | None:
    if sid_env:
        sid_env_l = sid_env.strip().lower()
        for s in stories:
            sid = str(s.get("id", "")).strip().lower()
            if sid == sid_env_l:
                return s
        return None
    for s in stories:
        if str(s.get("status", "")).lower() == "todo":
            return s
    return None


# --- Repo tree snapshot ---
def repo_tree(limit: int = 300) -> str:
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
                return "\n".join(files)
    return "\n".join(files)


# --- LLM plumbing ---
def extract_files_block(text: str) -> List[Dict[str, str]] | None:
    LOG_ALL.write_text(text, encoding="utf-8")
    candidates: List[str] = []

    # Try to find a single JSON object representing a file
    json_match = re.search(r'(\{[\s\S]*?\})', text.strip())
    if json_match:
        candidates.append(json_match.group(1))

    # Extract and clean file object
    parsed_file_entry = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
            if isinstance(parsed, dict) and "path" in parsed and "code" in parsed:
                parsed_file_entry = parsed
                break
        except Exception:
            continue

    if not parsed_file_entry:
        return None

    # Clean and convert from new format (code field) to old format (content field)
    if "code" in parsed_file_entry:
        code = parsed_file_entry["code"]
        # Aggressively clean markdown blocks
        code = re.sub(r'```\w*\s*\n?', '', code.strip())
        code = re.sub(r'```', '', code)
        code = code.strip()

        # Convert to content field
        parsed_file_entry["content"] = code

        # Remove the code field
        del parsed_file_entry["code"]

    # Ensure path is a string
    if not isinstance(parsed_file_entry.get("path"), str):
        return None

    return [parsed_file_entry] # Return as a list of one file for compatibility


def safe_write(rel_path: str, content: str) -> str:
    if not rel_path.startswith("project/"):
        rel_path = f"project/{rel_path.lstrip('/')}"
    target = ROOT / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    resolved = target.resolve()
    if not str(resolved).startswith(str(PROJECT.resolve())):
        raise ValueError(f"path escapes project/: {rel_path}")
    target.write_text(content, encoding="utf-8")
    return rel_path


async def llm_call(story: Dict[str, Any], files_ctx: str) -> str:
    from llm import Client
    client = Client(role="dev")

    # Load prompt from file like other roles
    system_prompt = ""
    if DEV_PROMPT.exists():
        system_prompt = DEV_PROMPT.read_text(encoding="utf-8")

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
    return await client.chat(system=system_prompt, user=user)


def mark_in_review(story_id: str) -> None:
    stories = load_stories()
    for s in stories:
        if str(s.get("id")) == str(story_id):
            s["status"] = "in_review"
            break
    save_stories(stories)


async def main() -> None:
    story_id = os.environ.get("STORY", "").strip()
    retries = int(os.environ.get("DEV_RETRIES", "3"))

    stories = load_stories()
    story = pick_story(stories, story_id if story_id else None)
    if not story:
        print("No stories to implement (stories.yaml vacío o sin 'todo'). Ejecuta make plan o normaliza stories.yaml.")
        sys.exit(1)

    sid = story.get("id", "S?")
    print(f"[dev] Implementando: {sid} - {story.get('description', '(sin desc)')}")

    files_ctx = repo_tree(limit=300)
    files = None
    last_err = None

    for i in range(1, retries + 1):
        try:
            print(f"[dev] LLM intento {i}/{retries}…")
            response = await llm_call(story, files_ctx)
            files = extract_files_block(response or "")
            if files:
                break
            last_err = "Developer response did not include FILES JSON block."
        except Exception as e:
            last_err = str(e)
        await asyncio.sleep(0.2)

    if not files:
        print(last_err or "No FILES parsed")
        sys.exit(2)

    written = []
    for entry in files:
        rel = entry["path"]
        cnt = entry["content"]
        rel2 = safe_write(rel, cnt)
        written.append(rel2)

    FILES_JSON.write_text(json.dumps(files, indent=2, ensure_ascii=False), encoding="utf-8")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = ART_DIR / f"{sid}-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "files.json").write_text(json.dumps(files, indent=2, ensure_ascii=False), encoding="utf-8")

    mark_in_review(sid)

    print(f"✓ wrote {len(written)} files under project/ (story {sid})")
    for w in written:
        print(" -", w)


if __name__ == "__main__":
    import asyncio as _asyncio
    try:
        _asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
