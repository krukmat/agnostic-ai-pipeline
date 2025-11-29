from __future__ import annotations

"""Drivers CLI (list/show/plan/validate) delegating to loader/validator.

This module is imported by drivers/registry.py to preserve the legacy entrypoint
(`python -m drivers.registry ...`).

Design: Pure functions for each command; detectors injected for testability (DIP).
"""

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from .loader import load_driver, validate_all
from .validator import VALID_CATEGORIES

# Type alias for detector functions (injectable)
DetectorMap = Dict[str, Callable[[], Tuple[bool, str]]]


def _get_default_detectors() -> DetectorMap:
    """Load default toolchain detectors (idf, west, etc.)

    Can be mocked/injected for testing without requiring real binaries.
    """
    detectors: DetectorMap = {}
    try:
        from drivers.detect import has_idf, has_west  # type: ignore
        detectors["idf"] = has_idf
        detectors["west"] = has_west
    except Exception:  # pragma: no cover - import optional
        # Fallback if detect module not available
        detectors["idf"] = lambda: (False, "idf.py not found")
        detectors["west"] = lambda: (False, "west not found")
    return detectors


def list_drivers() -> Dict[str, List[str]]:
    """Pure function: list all available drivers per category.

    Returns:
        Dict[category, [driver_ids]]
    """
    from .loader import DRIVERS_ROOT

    out: Dict[str, List[str]] = {}
    for cat in sorted(VALID_CATEGORIES):
        d = DRIVERS_ROOT / cat
        if not d.exists():
            continue
        out[cat] = sorted(p.stem for p in d.glob("*.yaml"))
    return out


def show_driver(category: str, driver_id: str) -> Dict[str, Any]:
    """Pure function: load and return driver as dict.

    Raises:
        FileNotFoundError or ValueError if driver not found/invalid.
    """
    drv = load_driver(category, driver_id)
    return asdict(drv)


def plan_from_config(config_path: str, detectors: Optional[DetectorMap] = None) -> Tuple[int, Dict[str, Any]]:
    """Pure function: generate plan from config.yaml with optional toolchain detection.

    Args:
        config_path: Path to config.yaml
        detectors: Dict of detector functions (e.g., {"idf": has_idf, "west": has_west})
                   If None, no embedded detection available (safe fallback).

    Returns:
        Tuple of (rc, report_dict) where rc is 0 on success, 2 if config not found.
    """
    if detectors is None:
        detectors = {}

    cfg_path = Path(config_path)
    if not cfg_path.exists():
        return 2, {"error": f"config not found: {cfg_path}"}

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
        return 0, report

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
            if is_esp and "idf" in detectors:
                ok, detect_msg = detectors["idf"]()
            elif is_zephyr and "west" in detectors:
                ok, detect_msg = detectors["west"]()
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
    return 0, report


def _cmd_list() -> int:
    """CLI adapter: list drivers."""
    out = list_drivers()
    print(yaml.safe_dump(out, sort_keys=True, allow_unicode=True))
    return 0


def _cmd_show(category: str, driver_id: str) -> int:
    """CLI adapter: show driver."""
    drv_dict = show_driver(category, driver_id)
    print(yaml.safe_dump(drv_dict, sort_keys=False, allow_unicode=True))
    return 0


def _cmd_plan(config_path: str) -> int:
    """CLI adapter: plan from config."""
    detectors = _get_default_detectors()
    rc, report = plan_from_config(config_path, detectors)
    if rc != 0:
        print(f"❌ {report.get('error', 'unknown error')}")
    else:
        print(yaml.safe_dump(report, sort_keys=False, allow_unicode=True))
    return rc


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

