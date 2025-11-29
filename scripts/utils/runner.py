from __future__ import annotations

import os
import subprocess
import shlex
from pathlib import Path
from typing import Optional


def area_from_name(name: str) -> str:
    if name.startswith("backend_"):
        return "backend"
    if name.startswith("frontend_"):
        return "web"
    if name.startswith("web_"):
        return "web"
    if name.startswith("embedded_"):
        return "embedded"
    return "general"


def prepare_env_for_name(name: str, root: Path, base: Optional[dict] = None) -> dict:
    env = dict(base or os.environ)
    if name.startswith("backend_"):
        be_path = str(root / "project" / "backend-fastapi")
        env["PYTHONPATH"] = f"{be_path}:{env.get('PYTHONPATH','')}" if env.get("PYTHONPATH") else be_path
    return env


def run_driver_cmd(
    cmd: str,
    name: str,
    root: Path,
    log_path: Path,
    logger,
    *,
    role: str = "DEV",
) -> int:
    """Execute a driver command with standardized logging and env preparation.

    - Writes combined stdout/stderr to `log_path`.
    - Logs RUN/DONE/ERROR/SKIP messages with [ROLE][area] prefix.
    - Adds backend PYTHONPATH when needed.
    """
    if not cmd:
        return 0
    area = area_from_name(name)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"[{role}][{area}] RUN: {cmd}")
    try:
        env = prepare_env_for_name(name, root)
        # Prefer argv list to avoid shell interpretation
        try:
            argv = shlex.split(cmd)
        except Exception:
            argv = None
        if argv and argv[0]:
            res = subprocess.run(argv, shell=False, cwd=str(root), capture_output=True, text=True, env=env)
        else:
            # Fallback to shell if we couldn't split (should be rare)
            res = subprocess.run(cmd, shell=True, cwd=str(root), capture_output=True, text=True, env=env)
        out = (res.stdout or "") + ("\n" + (res.stderr or "") if res.stderr else "")
        log_path.write_text(out, encoding="utf-8")
        if res.returncode != 0:
            logger.warning(f"[{role}][{area}] ERROR rc={res.returncode} (see {log_path})")
        else:
            logger.info(f"[{role}][{area}] DONE (see {log_path})")
        return res.returncode
    except FileNotFoundError as e:
        logger.info(f"[{role}][{area}] SKIP tool missing: {e}")
        return 127
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(f"[{role}][{area}] ERROR: {e}")
        return 1


def driver_log_name(area: str, driver_id: str, cmd: str) -> str:
    """Compose standardized driver log filename."""
    return f"{area}_{driver_id}_{cmd}.log"


def normalize_rc(rc: Optional[int], tool_missing: bool = False) -> int:
    """Normalize return codes for summaries."""
    if tool_missing:
        return 127
    if rc is None:
        return 0
    try:
        return int(rc)
    except Exception:
        return 1
