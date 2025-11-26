from __future__ import annotations

import pytest

from scripts.architect.complexity_classifier import (
    InMemoryComplexityCache,
    classify_complexity_with_llm,
    fallback_complexity,
    parse_complexity_response,
)


class DummyClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def chat(self, system: str, user: str):
        self.calls.append((system, user))
        return self.responses.pop(0)


def test_parse_complexity_response():
    assert parse_complexity_response("simple") == "simple"
    assert parse_complexity_response(" Medium ") == "medium"
    assert parse_complexity_response("corporate!!!") == "corporate"
    assert parse_complexity_response("unknown") is None


def test_fallback_complexity():
    assert fallback_complexity("short text") == "simple"
    assert fallback_complexity("word " * 500) == "medium"
    assert fallback_complexity("word " * 950) == "corporate"


@pytest.mark.asyncio
async def test_classify_complexity_with_cache(monkeypatch):
    cache = InMemoryComplexityCache(ttl_seconds=1000)
    cache.set("k", "simple")
    monkeypatch.setattr("scripts.architect.complexity_classifier._complexity_cache_key", lambda _: "k")

    tier = await classify_complexity_with_llm("whatever", cache=cache)
    assert tier == "simple"


@pytest.mark.asyncio
async def test_classify_complexity_llm_path(monkeypatch):
    cache = InMemoryComplexityCache(ttl_seconds=0.1)
    dummy = DummyClient(["medium"])
    monkeypatch.setattr("scripts.architect.complexity_classifier.Client", lambda role: dummy)
    tier = await classify_complexity_with_llm("some requirements", cache=cache, ttl_seconds=0.1)
    assert tier == "medium"
    # Second call should hit cache
    tier2 = await classify_complexity_with_llm("some requirements", cache=cache, ttl_seconds=0.1)
    assert tier2 == "medium"
    assert len(dummy.calls) == 1
