from __future__ import annotations

import shutil
import subprocess
from typing import Tuple


def _probe(cmd: str) -> Tuple[bool, str]:
    exe = shutil.which(cmd)
    if not exe:
        return False, f"{cmd} not found in PATH"
    try:
        res = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5)
        out = (res.stdout or res.stderr or "").strip() or "(no version output)"
        return True, f"{cmd} at {exe} → {out}"
    except Exception as e:
        return True, f"{cmd} at {exe} (version probe failed: {e})"


def has_idf() -> Tuple[bool, str]:
    """Detect ESP‑IDF toolchain (idf.py)."""
    return _probe("idf.py")


def has_west() -> Tuple[bool, str]:
    """Detect Zephyr west tool."""
    return _probe("west")

