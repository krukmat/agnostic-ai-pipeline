from __future__ import annotations

"""Minimal driver registry for loading and validating driver YAMLs.

Schema v1 (stable keys):
- id: str
- schema_version: int (default 1)
- category: one of backend|frontend|mobile|embedded|gpu
- language: str
- framework: str
- templates: list[{path:str, source:str}] (optional)
- build: {command:str} (optional)
- test: {command:str} (optional)
- lint: {command:str} (optional)
- artifact_paths: list[str] (optional)
- metadata: dict (optional)
"""

import argparse
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

try:
    # Optional import for detection used by 'plan' subcommand
    from drivers.detect import has_idf, has_west  # type: ignore
except Exception:  # pragma: no cover - optional at import time
    def has_idf() -> Tuple[bool, str]:
        return False, "idf.py not found"

    def has_west() -> Tuple[bool, str]:
        return False, "west not found"

DRIVERS_ROOT = Path(__file__).resolve().parent
VALID_CATEGORIES = {"backend", "frontend", "mobile", "embedded", "gpu"}


@dataclass
class Command:
    command: str


@dataclass
class Template:
    path: str
    source: str


@dataclass
class Driver:
    id: str
    category: str
    language: str
    framework: str
    schema_version: int = 1
    templates: List[Template] = field(default_factory=list)
    build: Optional[Command] = None
    test: Optional[Command] = None
    lint: Optional[Command] = None
    artifact_paths: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Embedded‑specific (optional)
    board: Optional[str] = None
    flash_command: Optional[str] = None
    monitor_command: Optional[str] = None
    # GPU‑specific (optional)
    gpu_arch: Optional[str] = None
    profiler_command: Optional[str] = None


def _require(d: Dict[str, Any], key: str, typ):
    if key not in d:
        raise ValueError(f"missing required key '{key}'")
    if not isinstance(d[key], typ):
        raise ValueError(f"key '{key}' must be {typ}, got {type(d[key])}")


def _validate_dict(d: Dict[str, Any]) -> None:
    _require(d, "id", str)
    _require(d, "category", str)
    _require(d, "language", str)
    _require(d, "framework", str)
    # ID convention: lowercase, digits, underscore (safe for filenames)
    if not re.fullmatch(r"[a-z0-9_]+", d["id"]):
        raise ValueError("id must match ^[a-z0-9_]+$ (lowercase, digits, underscore)")
    if d["category"] not in VALID_CATEGORIES:
        raise ValueError(f"invalid category '{d['category']}'")
    if "templates" in d:
        if not isinstance(d["templates"], list):
            raise ValueError("templates must be a list")
        for t in d["templates"]:
            if not isinstance(t, dict) or "path" not in t or "source" not in t:
                raise ValueError("each template must be a dict with 'path' and 'source'")
    for k in ("build", "test", "lint"):
        if k in d:
            if not isinstance(d[k], dict) or "command" not in d[k] or not isinstance(d[k]["command"], str):
                raise ValueError(f"{k} must be a dict with 'command': str")
            # Basic convention: non-empty command string
            if not d[k]["command"].strip():
                raise ValueError(f"{k}.command must be a non-empty string")
    if "artifact_paths" in d and not isinstance(d["artifact_paths"], list):
        raise ValueError("artifact_paths must be a list of strings")
    # Embedded: board/flash_command/monitor_command
    if d.get("category") == "embedded":
        if "board" in d and not isinstance(d["board"], str):
            raise ValueError("embedded.board must be a string")
        if "flash" in d:
            # transitional support: flash: {command: ...}
            if not isinstance(d["flash"], dict) or not isinstance(d["flash"].get("command"), str):
                raise ValueError("embedded.flash must be a dict with 'command': str")
        if "flash_command" in d and not isinstance(d["flash_command"], str):
            raise ValueError("embedded.flash_command must be a string")
        if "monitor_command" in d and not isinstance(d["monitor_command"], str):
            raise ValueError("embedded.monitor_command must be a string")
    # GPU: gpu_arch/profiler_command
    if d.get("category") == "gpu":
        arch = d.get("gpu_arch") or d.get("arch")
        if arch is not None and not isinstance(arch, str):
            raise ValueError("gpu.gpu_arch must be a string")
        if arch and not (arch.startswith("sm_") or arch.startswith("gfx")):
            # heuristic validation; allow empty to stay optional
            raise ValueError("gpu.gpu_arch seems invalid (expected 'sm_XX' or 'gfxXXXX')")
        if "profiler_command" in d and not isinstance(d["profiler_command"], str):
            raise ValueError("gpu.profiler_command must be a string")


def load_driver(category: str, driver_id: str) -> Driver:
    path = DRIVERS_ROOT / category / f"{driver_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(str(path))
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("driver YAML must be a mapping")
    _validate_dict(data)
    templates = [Template(**t) for t in data.get("templates", [])]
    def _cmd(name: str) -> Optional[Command]:
        c = data.get(name)
        return Command(**c) if isinstance(c, dict) and "command" in c else None
    # Transitional mapping for embedded/gpu fields
    flash_cmd = None
    mon_cmd = None
    if isinstance(data.get("flash"), dict):
        cmd = data.get("flash", {}).get("command")
        # Some legacy flash entries included both flash+monitor; keep as-is
        if isinstance(cmd, str):
            # naive split if user included both actions in one line
            if " monitor" in cmd:
                parts = cmd.split(" monitor", 1)
                flash_cmd = parts[0].strip()
                mon_cmd = ("idf.py monitor" if "idf.py" in cmd else "monitor").strip()
            else:
                flash_cmd = cmd
    return Driver(
        id=data["id"],
        category=data["category"],
        language=data["language"],
        framework=data["framework"],
        schema_version=int(data.get("schema_version", 1)),
        templates=templates,
        build=_cmd("build"),
        test=_cmd("test"),
        lint=_cmd("lint"),
        artifact_paths=list(data.get("artifact_paths", []) or []),
        metadata=dict(data.get("metadata", {}) or {}),
        board=data.get("board"),
        flash_command=data.get("flash_command") or flash_cmd,
        monitor_command=data.get("monitor_command") or mon_cmd,
        gpu_arch=data.get("gpu_arch") or data.get("arch"),
        profiler_command=data.get("profiler_command"),
    )


def validate_all() -> int:
    errors = 0
    for cat in VALID_CATEGORIES:
        d = DRIVERS_ROOT / cat
        if not d.exists():
            continue
        for yml in sorted(d.glob("*.yaml")):
            try:
                _ = load_driver(cat, yml.stem)
                print(f"✅ {cat}/{yml.name}")
            except Exception as e:
                print(f"❌ {cat}/{yml.name}: {e}")
                errors += 1
    return errors


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

    p_plan = sub.add_parser(
        "plan",
        help="Dry-run: explain what would execute given config.yaml",
    )
    p_plan.add_argument(
        "--config",
        default=str((Path(__file__).resolve().parents[1] / "config.yaml")),
        help="Path to config.yaml (defaults to repo root)",
    )

    args = parser.parse_args(argv)
    if args.cmd == "validate":
        if args.all:
            return validate_all()
        parser.error("--all required for now")
    elif args.cmd in {"load", "show"}:
        drv = load_driver(args.category, args.driver_id)
        print(yaml.safe_dump(asdict(drv), sort_keys=False, allow_unicode=True))
        return 0
    elif args.cmd == "list":
        out: Dict[str, List[str]] = {}
        for cat in sorted(VALID_CATEGORIES):
            d = DRIVERS_ROOT / cat
            if not d.exists():
                continue
            out[cat] = sorted(p.stem for p in d.glob("*.yaml"))
        print(yaml.safe_dump(out, sort_keys=True, allow_unicode=True))
        return 0
    elif args.cmd == "plan":
        cfg_path = Path(args.config)
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
        # Backend / Frontend / GPU are simple existence checks; Embedded adds detection flags
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
                entry["detection"] = {
                    "ok": ok,
                    "message": detect_msg,
                }
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
