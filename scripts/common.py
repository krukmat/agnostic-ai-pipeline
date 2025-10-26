from __future__ import annotations
import os, yaml, time, pathlib, shutil
from typing import Dict, Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
PLANNING = ROOT / "planning"
PROJECT = ROOT / "project"
DEFAULTS = ROOT / "project-defaults"

def load_config() -> Dict[str, Any]:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

def load_a2a_config() -> Dict[str, Any]:
    """Return sanitized A2A configuration with defaults."""
    raw = load_config().get("a2a") or {}
    agents = raw.get("agents") if isinstance(raw, dict) else {}
    if not isinstance(agents, dict):
        agents = {}
    auth = raw.get("authentication") if isinstance(raw, dict) else {}
    if not isinstance(auth, dict):
        auth = {"mode": "none"}

    normalized: Dict[str, Any] = {}
    if isinstance(raw, dict):
        normalized.update({k: v for k, v in raw.items() if k not in {"agents", "authentication"}})
    normalized["agents"] = agents
    normalized["authentication"] = auth
    return normalized

def ensure_dirs():
    ART.mkdir(exist_ok=True, parents=True)
    PLANNING.mkdir(exist_ok=True, parents=True)
    PROJECT.mkdir(exist_ok=True, parents=True)
    _ensure_project_defaults()

def _ensure_project_defaults():
    if not DEFAULTS.exists():
        return
    for root, dirs, files in os.walk(DEFAULTS):
        rel_root = pathlib.Path(root).relative_to(DEFAULTS)
        dest_root = PROJECT / rel_root
        dest_root.mkdir(parents=True, exist_ok=True)
        for fn in files:
            if fn.endswith((".pyc", ".pyo")) or fn == ".DS_Store":
                continue
            src_file = pathlib.Path(root, fn)
            dest_file = dest_root / fn
            if not dest_file.exists():
                shutil.copy2(src_file, dest_file)

def save_text(path: pathlib.Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def repo_tree(limit:int=400) -> str:
    files = []
    for root, dirs, fns in os.walk(PROJECT):
        parts = pathlib.Path(root).parts
        if any(seg in ("node_modules",".venv",".git",".pytest_cache",".coverage") for seg in parts):
            continue
        for fn in fns:
            rel = pathlib.Path(root, fn).relative_to(ROOT)
            files.append(str(rel).replace("\\","/"))
    return "\n".join(files[:limit])
