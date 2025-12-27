import json
import time

from scripts.orchestrator.cache_manager import CacheManager


def test_make_key_is_stable():
    cache = CacheManager(cache_dir=None)
    key1 = cache._make_key("coherence", "a", "b")
    key2 = cache._make_key("coherence", "a", "b")
    assert key1 == key2
    assert key1.startswith("coherence_")


def test_set_get_memory_cache(tmp_path):
    cache = CacheManager(cache_dir=tmp_path, ttl_seconds=60)
    cache.set("k1", {"a": 1})
    assert cache.get("k1") == {"a": 1}
    assert cache.stats["hits"] == 1


def test_get_disk_cache_after_memory_clear(tmp_path):
    cache = CacheManager(cache_dir=tmp_path, ttl_seconds=60)
    cache.set("k2", {"b": 2})
    cache.memory_cache.clear()
    assert cache.get("k2") == {"b": 2}
    assert cache.stats["hits"] == 1


def test_get_expired_entry(tmp_path, monkeypatch):
    cache = CacheManager(cache_dir=tmp_path, ttl_seconds=1)
    cache.set("k3", {"c": 3})
    cache.memory_cache.clear()

    future = time.time() + 10
    monkeypatch.setattr(time, "time", lambda: future)

    assert cache.get("k3") is None
    assert cache.stats["misses"] == 1
    assert not (tmp_path / "k3.json").exists()


def test_get_handles_corrupt_disk_entry(tmp_path):
    cache = CacheManager(cache_dir=tmp_path, ttl_seconds=60)
    path = tmp_path / "bad.json"
    path.write_text("not-json")
    assert cache.get("bad") is None
    assert cache.stats["misses"] == 1


def test_invalidate_wildcard_and_exact(tmp_path):
    cache = CacheManager(cache_dir=tmp_path, ttl_seconds=60)
    cache.set("coherence_1", {"x": 1})
    cache.set("coherence_2", {"y": 2})
    cache.set("other_1", {"z": 3})

    assert cache.invalidate("coherence_*") == 4
    assert not list(tmp_path.glob("coherence_*.json"))

    cache.set("exact", {"v": 1})
    assert cache.invalidate("exact") == 2


def test_clear_and_stats(tmp_path):
    cache = CacheManager(cache_dir=tmp_path, ttl_seconds=60)
    cache.set("k4", {"v": 4})
    stats = cache.get_stats()
    assert stats["disk_entries"] == 1
    cache.clear()
    stats = cache.get_stats()
    assert stats["memory_entries"] == 0
    assert stats["disk_entries"] == 0


def test_helpers_cache_and_fetch(tmp_path):
    cache = CacheManager(cache_dir=tmp_path, ttl_seconds=60)
    cache.cache_coherence_check("ba", "po", {"aligned": True}, ttl=30)
    assert cache.get_cached_coherence_check("ba", "po") == {"aligned": True}

    cache.cache_prediction("S1", 3.5, {"cpu": 1})
    assert cache.get_cached_prediction("S1") == {"duration": 3.5, "resources": {"cpu": 1}}
