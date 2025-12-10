"""
Caching Layer for intelligent caching of orchestrator computations.

Caches:
- Coherence check results (1h TTL)
- Performance predictions (until story changes)
- Optimization recommendations (until history updates)
- Pattern analysis results (24h TTL)
"""

from typing import Dict, Optional, Any
from pathlib import Path
import json
import hashlib
import time
from logger import logger


class CacheManager:
    """Intelligent caching for orchestrator computations."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: int = 3600):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cache files. Defaults to artifacts/cache
            ttl_seconds: Default time-to-live for cache entries (seconds)
        """
        self.cache_dir = cache_dir or Path("artifacts/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.memory_cache: Dict[str, Dict] = {}  # In-memory cache
        self.stats = {"hits": 0, "misses": 0}
        logger.info(f"[cache] Initialized: dir={self.cache_dir}, TTL={ttl_seconds}s")

    def _make_key(self, pattern: str, *args) -> str:
        """Generate cache key from pattern and arguments.

        Args:
            pattern: Key pattern (e.g., "coherence:ba:po")
            *args: Arguments to include in hash

        Returns:
            Cache key
        """
        content = f"{pattern}:{':'.join(str(a) for a in args)}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{pattern}_{hash_val}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        # Check memory cache first
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if time.time() < entry["expires"]:
                self.stats["hits"] += 1
                logger.debug(f"[cache] HIT: {key}")
                return entry["value"]
            else:
                del self.memory_cache[key]

        # Check disk cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                if time.time() < data["expires"]:
                    self.stats["hits"] += 1
                    # Move to memory cache
                    self.memory_cache[key] = data
                    logger.debug(f"[cache] HIT (disk): {key}")
                    return data["value"]
                else:
                    cache_file.unlink()  # Delete expired
            except Exception as e:
                logger.debug(f"[cache] Failed to read {key}: {e}")

        self.stats["misses"] += 1
        logger.debug(f"[cache] MISS: {key}")
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set cache value.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live override
        """
        ttl = ttl_seconds or self.ttl_seconds
        expires = time.time() + ttl

        entry = {"value": value, "expires": expires, "created": time.time()}

        # Store in memory
        self.memory_cache[key] = entry

        # Store on disk
        try:
            cache_file = self.cache_dir / f"{key}.json"
            cache_file.write_text(json.dumps(entry, default=str))
            logger.debug(f"[cache] SET: {key} (TTL={ttl}s)")
        except Exception as e:
            logger.warning(f"[cache] Failed to write {key}: {e}")

    def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern.

        Args:
            pattern: Pattern to match (e.g., "coherence:*", "predict:story_123")

        Returns:
            Number of entries invalidated
        """
        count = 0

        # Handle wildcards
        if "*" in pattern:
            prefix = pattern.replace("*", "")
            # Memory cache
            keys_to_delete = [k for k in self.memory_cache.keys() if k.startswith(prefix)]
            count += len(keys_to_delete)
            for key in keys_to_delete:
                del self.memory_cache[key]

            # Disk cache
            for cache_file in self.cache_dir.glob(f"{prefix}*.json"):
                cache_file.unlink()
                count += 1
        else:
            # Exact match
            if pattern in self.memory_cache:
                del self.memory_cache[pattern]
                count += 1

            cache_file = self.cache_dir / f"{pattern}.json"
            if cache_file.exists():
                cache_file.unlink()
                count += 1

        logger.info(f"[cache] Invalidated {count} entries matching '{pattern}'")
        return count

    def clear(self) -> None:
        """Clear entire cache."""
        self.memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.info("[cache] Cleared all")

    def get_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, memory entries, disk entries
        """
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total if total > 0 else 0
        )

        memory_entries = len(self.memory_cache)
        disk_entries = len(list(self.cache_dir.glob("*.json")))

        stats = {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "total": total,
            "hit_rate": hit_rate,
            "memory_entries": memory_entries,
            "disk_entries": disk_entries,
        }

        logger.debug(f"[cache] Stats: {hit_rate:.0%} hit rate, "
                    f"{memory_entries} memory, {disk_entries} disk")

        return stats

    def cache_coherence_check(
        self, ba_hash: str, po_hash: str, result: Dict, ttl: int = 3600
    ) -> None:
        """Cache coherence check result.

        Args:
            ba_hash: Hash of BA output
            po_hash: Hash of PO output
            result: Coherence check result
            ttl: Time-to-live in seconds (default 1 hour)
        """
        key = self._make_key("coherence", ba_hash, po_hash)
        self.set(key, result, ttl)

    def get_cached_coherence_check(self, ba_hash: str, po_hash: str) -> Optional[Dict]:
        """Get cached coherence check result.

        Args:
            ba_hash: Hash of BA output
            po_hash: Hash of PO output

        Returns:
            Cached result or None
        """
        key = self._make_key("coherence", ba_hash, po_hash)
        return self.get(key)

    def cache_prediction(
        self, story_id: str, duration: float, resources: Dict
    ) -> None:
        """Cache performance prediction.

        Args:
            story_id: Story identifier
            duration: Predicted duration
            resources: Predicted resources
        """
        key = self._make_key("predict", story_id)
        prediction = {"duration": duration, "resources": resources}
        self.set(key, prediction, ttl_seconds=3600)

    def get_cached_prediction(self, story_id: str) -> Optional[Dict]:
        """Get cached prediction.

        Args:
            story_id: Story identifier

        Returns:
            Cached prediction or None
        """
        key = self._make_key("predict", story_id)
        return self.get(key)
