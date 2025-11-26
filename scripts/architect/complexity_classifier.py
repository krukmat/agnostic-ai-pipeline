from __future__ import annotations

"""Architect complexity classifier helpers (extract from run_architect)."""

import hashlib
import time
from typing import Dict, Optional, Protocol, Tuple

from llm import Client


class ComplexityCache(Protocol):
    def get(self, key: str) -> Optional[Tuple[str, float]]: ...
    def set(self, key: str, value: str) -> None: ...


class InMemoryComplexityCache:
    """Simple in-memory cache with TTL."""

    def __init__(self, ttl_seconds: float = 600.0) -> None:
        self.ttl = ttl_seconds
        self._store: Dict[str, Tuple[str, float]] = {}

    def get(self, key: str) -> Optional[Tuple[str, float]]:
        item = self._store.get(key)
        if not item:
            return None
        value, ts = item
        if time.time() - ts > self.ttl:
            return None
        return item

    def set(self, key: str, value: str) -> None:
        self._store[key] = (value, time.time())


def _complexity_cache_key(requirements_text: str) -> str:
    return hashlib.sha256(requirements_text.encode("utf-8")).hexdigest()


def parse_complexity_response(text: str) -> Optional[str]:
    if not text:
        return None
    lowered = text.strip().split()
    if not lowered:
        return None
    candidate = lowered[0].lower().strip(",.:;!")
    if candidate in {"simple", "medium", "corporate"}:
        return candidate
    return None


def fallback_complexity(requirements_text: str) -> str:
    words = len(requirements_text.split())
    if words <= 350:
        return "simple"
    if words >= 900:
        return "corporate"
    return "medium"


async def classify_complexity_with_llm(
    requirements_text: str,
    cache: Optional[ComplexityCache] = None,
    ttl_seconds: float = 600.0,
) -> str:
    """Classify requirements as simple/medium/corporate using LLM + cache."""
    cleaned = (requirements_text or "").strip()
    if not cleaned:
        return "simple"

    cache_obj = cache or InMemoryComplexityCache(ttl_seconds)
    cache_key = _complexity_cache_key(cleaned)
    cached = cache_obj.get(cache_key)
    now = time.time()
    if cached:
        cached_value, cached_at = cached
        if now - cached_at <= (cache_obj.ttl if hasattr(cache_obj, "ttl") else ttl_seconds):
            return cached_value

    try:
        client = Client(role="architect")
        user = (
            "REQUIREMENTS:\n"
            f"{cleaned}\n\n"
            "Respond with exactly one word: simple, medium, or corporate."
        )
        from scripts.run_architect import COMPLEXITY_CLASSIFIER_PROMPT  # lazy import to avoid cycles

        response = await client.chat(system=COMPLEXITY_CLASSIFIER_PROMPT, user=user)
        tier = parse_complexity_response(response)
        if tier:
            cache_obj.set(cache_key, tier)
            return tier
    except Exception:
        pass

    fallback = fallback_complexity(cleaned)
    cache_obj.set(cache_key, fallback)
    return fallback
