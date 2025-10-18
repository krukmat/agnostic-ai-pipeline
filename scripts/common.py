from __future__ import annotations
import os, yaml, time, pathlib
from typing import Dict, Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
PLANNING = ROOT / "planning"
PROJECT = ROOT / "project"

def load_config() -> Dict[str, Any]:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

def ensure_dirs():
    ART.mkdir(exist_ok=True, parents=True)
    PLANNING.mkdir(exist_ok=True, parents=True)
    PROJECT.mkdir(exist_ok=True, parents=True)

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
