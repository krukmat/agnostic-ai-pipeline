from __future__ import annotations

"""Driver loader: dataclasses and YAML I/O.

Relies on drivers.validator for schema/convention checks.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .validator import validate_driver_dict, VALID_CATEGORIES

DRIVERS_ROOT = Path(__file__).resolve().parent


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


def load_driver(category: str, driver_id: str) -> Driver:
    if category not in VALID_CATEGORIES:
        raise ValueError(f"invalid category '{category}'")
    path = DRIVERS_ROOT / category / f"{driver_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(str(path))

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("driver YAML must be a mapping")

    validate_driver_dict(data)

    templates = [Template(**t) for t in data.get("templates", [])]

    def _cmd(name: str) -> Optional[Command]:
        c = data.get(name)
        return Command(**c) if isinstance(c, dict) and "command" in c else None

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
        flash_command=data.get("flash_command"),
        monitor_command=data.get("monitor_command"),
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
            except Exception as e:  # pragma: no cover - CLI feedback only
                print(f"❌ {cat}/{yml.name}: {e}")
                errors += 1
    return errors

