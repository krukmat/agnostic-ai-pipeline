from __future__ import annotations

from typing import Dict, Optional, Tuple
import time


class InMemoryCache:
    """Generic in-memory cache with TTL."""

    def __init__(self, ttl_seconds: float = 600.0) -> None:
        self.ttl = ttl_seconds
        self._store: Dict[str, Tuple[object, float]] = {}

    def get(self, key: str) -> Optional[Tuple[object, float]]:
        item = self._store.get(key)
        if not item:
            return None
        value, ts = item
        if time.time() - ts > self.ttl:
            return None
        return item

    def set(self, key: str, value: object) -> None:
        self._store[key] = (value, time.time())
