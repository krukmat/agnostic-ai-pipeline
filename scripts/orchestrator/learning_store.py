"""Learning memory store for orchestrator story outcomes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from common import ART, load_config
from logger import logger


DEFAULT_RETENTION = 20
LEARNING_DIR = ART / "learning"
LEARNING_FILE = LEARNING_DIR / "learning_store.jsonl"


@dataclass
class StoryOutcome:
    story_id: str
    phase: str
    status: str
    timestamp: str
    attempt: int
    error: Optional[str]
    implements: List[str]
    policy: Optional[str]
    comment: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "phase": self.phase,
            "status": self.status,
            "timestamp": self.timestamp,
            "attempt": self.attempt,
            "error": self.error,
            "implements": self.implements,
            "policy": self.policy,
            "comment": self.comment,
        }


class LearningStore:
    """Append-only store for story results with retention per story."""

    def __init__(
        self,
        path: Optional[Path] = None,
        retention_per_story: Optional[int] = None,
    ) -> None:
        self.path = path or LEARNING_FILE
        self.retention_per_story = retention_per_story or self._load_retention()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load_retention(self) -> int:
        try:
            config = load_config()
            features = config.get("features") or {}
            learning = features.get("learning_store") or {}
            value = learning.get("retention_per_story")
            if isinstance(value, int) and value > 0:
                return value
        except Exception as exc:
            logger.debug("[learning_store] Failed to read config retention: %s", exc)
        return DEFAULT_RETENTION

    def record_story_result(
        self,
        story_id: str,
        phase: str,
        status: str,
        attempt: int = 1,
        error: Optional[str] = None,
        implements: Optional[List[str]] = None,
        policy: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> None:
        entry = StoryOutcome(
            story_id=story_id,
            phase=phase,
            status=status,
            timestamp=datetime.utcnow().isoformat() + "Z",
            attempt=attempt,
            error=error,
            implements=implements or [],
            policy=policy,
            comment=comment,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict()) + "\n")
        self._enforce_retention(story_id)

    def _read_all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entries.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    logger.warning("[learning_store] Skipping invalid entry: %s", exc)
        return entries

    def _write_all(self, entries: Iterable[Dict[str, Any]]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry) + "\n")

    def _enforce_retention(self, story_id: str) -> None:
        entries = self._read_all()
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for entry in entries:
            grouped.setdefault(entry.get("story_id", ""), []).append(entry)
        trimmed: List[Dict[str, Any]] = []
        for sid, group in grouped.items():
            group_sorted = sorted(
                group,
                key=lambda item: item.get("timestamp", ""),
                reverse=True,
            )
            trimmed.extend(group_sorted[: self.retention_per_story])
        trimmed_sorted = sorted(trimmed, key=lambda itm: itm.get("timestamp", ""))
        self._write_all(trimmed_sorted)

    def get_recent_attempts(self, story_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        entries = [
            entry
            for entry in self._read_all()
            if entry.get("story_id") == story_id
        ]
        entries_sorted = sorted(
            entries,
            key=lambda entry: entry.get("timestamp", ""),
            reverse=True,
        )
        if limit:
            return entries_sorted[:limit]
        return entries_sorted

    def get_error_summary(self, story_id: str) -> Dict[str, int]:
        attempts = self.get_recent_attempts(story_id)
        summary: Dict[str, int] = {}
        for entry in attempts:
            error = entry.get("error") or "no_error"
            summary[error] = summary.get(error, 0) + 1
        return summary

    def get_story_stats(self) -> Dict[str, Dict[str, Any]]:
        entries = self._read_all()
        stats: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            sid = entry.get("story_id") or "unknown"
            stats.setdefault(sid, {"attempts": 0, "successes": 0})
            stats[sid]["attempts"] += 1
            if entry.get("status") == "ok":
                stats[sid]["successes"] += 1
        return stats
