"""Checkpoint helpers for synthetic generation pipelines."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CheckpointData:
    role: str
    checkpoint_version: str = "1.0"
    created_at: str = ""
    generated: int = 0
    failed: int = 0
    filtered: int = 0
    last_batch_id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = payload["created_at"] or utc_now_iso()
        return payload


def load_checkpoint(path: Path, role: str) -> Dict[str, Any]:
    if not path.exists():
        return CheckpointData(role=role, created_at=utc_now_iso()).to_dict()

    data = json.loads(path.read_text(encoding="utf-8"))

    # simple forward compatibility for old shapes
    if "stats" in data and isinstance(data["stats"], dict):
        stats = data["stats"]
        return {
            "role": data.get("role", role),
            "checkpoint_version": data.get("checkpoint_version", "1.0"),
            "created_at": data.get("created_at", utc_now_iso()),
            "generated": int(stats.get("generated", 0)),
            "failed": int(stats.get("failed", 0)),
            "filtered": int(stats.get("filtered", 0)),
            "last_batch_id": int(data.get("last_batch_id", 0)),
        }

    return {
        "role": data.get("role", role),
        "checkpoint_version": data.get("checkpoint_version", "1.0"),
        "created_at": data.get("created_at", utc_now_iso()),
        "generated": int(data.get("generated", 0)),
        "failed": int(data.get("failed", 0)),
        "filtered": int(data.get("filtered", 0)),
        "last_batch_id": int(data.get("last_batch_id", 0)),
    }


def save_checkpoint(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
