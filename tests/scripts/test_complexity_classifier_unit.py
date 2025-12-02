import asyncio

import pytest

from scripts.architect import complexity_classifier as cc


class DummyCache:
    def __init__(self):
        self.store = {}
        self.get_calls = 0
        self.set_calls = 0

    def get(self, key):
        self.get_calls += 1
        return self.store.get(key)

    def set(self, key, value):
        self.set_calls += 1
        self.store[key] = (value, cc.time.time())


class DummyClient:
    def __init__(self, role=None):
        self.role = role

    async def chat(self, system, user):
        return "medium"


@pytest.mark.asyncio
async def test_classify_complexity_uses_cache(monkeypatch):
    cache = DummyCache()
    monkeypatch.setattr(cc, "Client", DummyClient)
    text = "Build an API with auth and pagination."
    # First call populates cache
    out1 = await cc.classify_complexity_with_llm(text, cache=cache, ttl_seconds=60)
    # Second call hits cache
    out2 = await cc.classify_complexity_with_llm(text, cache=cache, ttl_seconds=60)
    assert out1 == out2 == "medium"
    assert cache.get_calls >= 2
    assert cache.set_calls >= 1


@pytest.mark.asyncio
async def test_classify_complexity_fallback_on_error(monkeypatch):
    class FailingClient:
        async def chat(self, system, user):
            raise RuntimeError("fail")

    monkeypatch.setattr(cc, "Client", FailingClient)
    # Short text -> fallback should be simple
    out = await cc.classify_complexity_with_llm("short text", cache=DummyCache(), ttl_seconds=60)
    assert out == "simple"
