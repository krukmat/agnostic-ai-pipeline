from __future__ import annotations

import os
import shutil
import pathlib
import datetime
import re

# Define paths relative to the script
ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
PLANNING = ROOT / "planning"
PROJECT = ROOT / "project"
DEFAULTS = ROOT / "project-defaults"
NOTES_P = PLANNING / "notes.md" # For logging cleanup actions

def append_note(text: str):
    NOTES_P.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with NOTES_P.open("a", encoding="utf-8") as f:
        f.write(f"\n### {now}\n{text}\n")

def cleanup_artifacts_and_planning(flush_all: bool = False):
    """
    Cleans up generated artifacts and optionally planning/project directories.
    """
    print("[cleanup] Starting cleanup...")
    total_files_cleaned = 0
    total_space_cleaned = 0
    now = datetime.datetime.now().timestamp()
    max_age_seconds = int(os.environ.get("ARTIFACT_RETENTION_DAYS", "7")) * 24 * 60 * 60

    # Clean artifacts directory
    if ART.exists():
        for item in ART.rglob("*"):
            if item.is_file():
                file_age = now - item.stat().st_mtime
                if file_age > max_age_seconds or flush_all:
                    try:
                        size = item.stat().st_size
                        item.unlink()
                        total_files_cleaned += 1
                        total_space_cleaned += size
                    except OSError as e:
                        print(f"[cleanup] Warning: Could not delete {item}: {e}")
            elif item.is_dir() and not list(item.iterdir()): # Remove empty directories
                try:
                    item.rmdir()
                except OSError as e:
                    print(f"[cleanup] Warning: Could not remove empty dir {item}: {e}")
        # Remove any remaining empty artifact directories
        for item in sorted(ART.iterdir(), reverse=True):
            if item.is_dir() and not list(item.iterdir()):
                try:
                    item.rmdir()
                except OSError as e:
                    print(f"[cleanup] Warning: Could not remove empty dir {item}: {e}")
    
    # Clean __pycache__ and *.pyc files
    for pyc_file in ROOT.rglob("*.pyc"):
        if flush_all or (now - pyc_file.stat().st_mtime > (1 * 60 * 60)): # More than 1 hour
            try:
                size = pyc_file.stat().st_size
                pyc_file.unlink()
                total_files_cleaned += 1
                total_space_cleaned += size
            except OSError as e:
                print(f"[cleanup] Warning: Could not delete {pyc_file}: {e}")

    for cache_dir in ROOT.rglob("__pycache__"):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir)
                total_files_cleaned += 1 # Count directory as deletion
            except OSError as e:
                print(f"[cleanup] Warning: Could not remove __pycache__ {cache_dir}: {e}")

    # Optional: Clean planning and project directories
    if flush_all:
        for dir_to_clean in [PLANNING, PROJECT]:
            if dir_to_clean.exists():
                print(f"[cleanup] Flushing {dir_to_clean}...")
                for item in dir_to_clean.iterdir():
                    if item.name == ".gitkeep": # Preserve .gitkeep files
                        continue
                    try:
                        if item.is_file():
                            size = item.stat().st_size
                            item.unlink()
                            total_files_cleaned += 1
                            total_space_cleaned += size
                        elif item.is_dir():
                            shutil.rmtree(item)
                            total_files_cleaned += 1
                    except OSError as e:
                        print(f"[cleanup] Warning: Could not remove {item} from {dir_to_clean}: {e}")
        
        # Re-create default project structure if it was flushed
        _ensure_project_defaults()


    if total_files_cleaned > 0 or total_space_cleaned > 0:
        msg = f"Automatic cleanup: {total_files_cleaned} files deleted, {total_space_cleaned/1024:.1f}KB freed"
        append_note(msg)
        print(f"[cleanup] {msg}")
    else:
        print("[cleanup] No old files to clean.")

def _ensure_project_defaults():
    # This function should be in common.py, but for now, define it here to avoid circular imports
    # and ensure it's available for cleanup.
    DEFAULTS.mkdir(exist_ok=True, parents=True) # Ensure project-defaults exists
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


def main() -> None:
    flush = os.environ.get("FLUSH", os.environ.get("CLEAN_FLUSH", "0"))
    flush_all = (flush == "1")
    cleanup_artifacts_and_planning(flush_all)


if __name__ == "__main__":
    main()
