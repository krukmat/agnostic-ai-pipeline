from __future__ import annotations

"""Drivers CLI (list/show/plan/validate) delegating to loader/validator.

This module is imported by drivers/registry.py to preserve the legacy entrypoint
(`python -m drivers.registry ...`).
"""

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .loader import load_driver, validate_all
from .validator import VALID_CATEGORIES

try:  # optional detection for 'plan'
    from drivers.detect import has_idf, has_west  # type: ignore
except Exception:  # pragma: no cover - import optional
    def has_idf():
        return False, "idf.py not found"

    def has_west():
        return False, "west not found"


def _cmd_list() -> int:
    from .loader import DRIVERS_ROOT

    out: Dict[str, List[str]] = {}
    for cat in sorted(VALID_CATEGORIES):
        d = DRIVERS_ROOT / cat
        if not d.exists():
            continue
        out[cat] = sorted(p.stem for p in d.glob("*.yaml"))
    print(yaml.safe_dump(out, sort_keys=True, allow_unicode=True))
    return 0


def _cmd_show(category: str, driver_id: str) -> int:
    drv = load_driver(category, driver_id)
    print(yaml.safe_dump(asdict(drv), sort_keys=False, allow_unicode=True))
    return 0


def _cmd_plan(config_path: str) -> int:
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        print(f"❌ config not found: {cfg_path}")
        return 2
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    drv_cfg = (cfg.get("drivers") or {}) if isinstance(cfg, dict) else {}
    enabled = bool(drv_cfg.get("enabled", False))
    targets = (cfg.get("project") or {}).get("targets") or {}
    report: Dict[str, Any] = {
        "drivers.enabled": enabled,
        "targets": targets,
        "plan": {},
    }
    if not enabled:
        report["note"] = "drivers disabled; legacy behavior only"
        print(yaml.safe_dump(report, sort_keys=False, allow_unicode=True))
        return 0
    # Backend / Frontend / GPU are simple; Embedded adds detection
    for cat in ("backend", "frontend", "gpu", "embedded"):
        sel = targets.get(cat)
        if not sel or str(sel).lower() == "none":
            continue
        try:
            drv = load_driver(cat, sel)
        except Exception as e:
            report["plan"][cat] = {"error": str(e)}
            continue
        entry: Dict[str, Any] = {
            "id": drv.id,
            "framework": drv.framework,
            "commands": {
                "build": getattr(drv.build, "command", None),
                "test": getattr(drv.test, "command", None),
                "lint": getattr(drv.lint, "command", None),
            },
            "would_run": {},
        }
        if cat == "embedded":
            emb_flags = (drv_cfg.get("embedded") or {})
            is_esp = drv.framework.lower().startswith("esp-idf") or drv.id.startswith("esp32")
            is_zephyr = drv.framework.lower().startswith("zephyr")
            ok = False
            detect_msg = ""
            if is_esp:
                ok, detect_msg = has_idf()
            elif is_zephyr:
                ok, detect_msg = has_west()
            entry["detection"] = {"ok": ok, "message": detect_msg}
            entry["flags"] = {
                "run_build": bool(emb_flags.get("run_build", False)),
                "run_test": bool(emb_flags.get("run_test", False)),
            }
            entry["would_run"] = {
                "build": bool(ok and emb_flags.get("run_build") and getattr(drv, "build", None)),
                "test": bool(ok and emb_flags.get("run_test") and getattr(drv, "test", None)),
                "lint": False,
            }
        else:
            entry["would_run"] = {
                "build": bool(getattr(drv, "build", None)),
                "test": bool(getattr(drv, "test", None)),
                "lint": bool(getattr(drv, "lint", None)),
            }
        report["plan"][cat] = entry
    print(yaml.safe_dump(report, sort_keys=False, allow_unicode=True))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Driver registry CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate drivers")
    p_val.add_argument("--all", action="store_true", help="Validate all drivers")

    p_load = sub.add_parser("load", help="Load a specific driver (YAML dump)")
    p_load.add_argument("category", choices=sorted(VALID_CATEGORIES))
    p_load.add_argument("driver_id")

    p_show = sub.add_parser("show", help="Alias of 'load'")
    p_show.add_argument("category", choices=sorted(VALID_CATEGORIES))
    p_show.add_argument("driver_id")

    sub.add_parser("list", help="List available drivers per category")

    p_plan = sub.add_parser("plan", help="Dry-run: explain what would execute given config.yaml")
    p_plan.add_argument("--config", default=str((Path(__file__).resolve().parents[1] / "config.yaml")))

    args = parser.parse_args(argv)
    if args.cmd == "validate":
        if args.all:
            return validate_all()
        parser.error("--all required for now")
    elif args.cmd in {"load", "show"}:
        return _cmd_show(args.category, args.driver_id)
    elif args.cmd == "list":
        return _cmd_list()
    elif args.cmd == "plan":
        return _cmd_plan(args.config)
    return 0

