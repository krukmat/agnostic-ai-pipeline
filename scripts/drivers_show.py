#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from drivers.registry import load_driver, VALID_CATEGORIES  # noqa: E402


def main() -> int:
    cfg_path = ROOT / "config.yaml"
    cfg: Dict[str, Any] = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    drivers_cfg = cfg.get("drivers") or {}
    enabled = bool(drivers_cfg.get("enabled", False))
    targets = (cfg.get("project") or {}).get("targets") or {}

    print(f"drivers.enabled: {enabled}")
    if not enabled:
        print("(Set drivers.enabled: true and project.targets to resolve drivers)")

    resolved: Dict[str, Dict[str, Any]] = {}
    for cat in sorted(VALID_CATEGORIES):
        sel = targets.get(cat)
        if not sel or str(sel).lower() == "none":
            continue
        try:
            drv = load_driver(cat, sel)
            resolved[cat] = {
                "id": drv.id,
                "category": drv.category,
                "language": drv.language,
                "framework": drv.framework,
                "build": getattr(drv.build, "command", None),
                "test": getattr(drv.test, "command", None),
                "lint": getattr(drv.lint, "command", None),
                "artifact_paths": drv.artifact_paths,
                "board": getattr(drv, "board", None),
                "flash_command": getattr(drv, "flash_command", None),
                "monitor_command": getattr(drv, "monitor_command", None),
                "gpu_arch": getattr(drv, "gpu_arch", None),
            }
        except Exception as e:
            resolved[cat] = {"error": str(e)}

    if resolved:
        print(yaml.safe_dump(resolved, sort_keys=True, allow_unicode=True))
    else:
        print("No targets resolved (check project.targets in config.yaml)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

