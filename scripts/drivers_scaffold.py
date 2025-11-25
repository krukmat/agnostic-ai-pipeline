#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from drivers.registry import load_driver  # noqa: E402
from logger import logger  # noqa: E402


def main() -> int:
    cfg_path = ROOT / "config.yaml"
    cfg: Dict[str, Any] = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    drv_cfg = (cfg.get("drivers") or {}) if isinstance(cfg, dict) else {}
    enabled = bool(drv_cfg.get("enabled", False))
    if not enabled:
        print("drivers.enabled is false; nothing to scaffold.")
        return 0
    targets = (cfg.get("project") or {}).get("targets") or {}
    tpl_apply = bool(((drv_cfg.get("templates") or {}).get("apply", True)))
    if not tpl_apply:
        print("drivers.templates.apply is false; skipping template expansion.")
        return 0

    created = 0
    for cat in ("backend", "frontend", "embedded"):
        sel = targets.get(cat)
        if not sel or str(sel).lower() == "none":
            continue
        try:
            drv = load_driver(cat, sel)
        except Exception as e:
            logger.warning(f"[drivers-scaffold] Failed to load {cat}/{sel}: {e}")
            continue
        for t in drv.templates:
            dest = ROOT / t.path
            if dest.exists():
                continue
            src = ROOT / t.source
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                content = src.read_text(encoding="utf-8")
                dest.write_text(content, encoding="utf-8")
                created += 1
                print(f"Scaffolded {t.path} from {t.source}")
            except Exception as e:
                logger.warning(f"[drivers-scaffold] Could not scaffold {t.path}: {e}")

    print(f"Scaffold complete. Files created: {created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

