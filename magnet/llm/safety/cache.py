"""
magnet/llm/safety/cache.py - Response Caching with TTL

Caches LLM responses to reduce API calls and costs for identical prompts.
Uses content-based hashing for cache keys.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..protocol import LLMResponse

logger = logging.getLogger("llm.cache")


@dataclass
class CacheEntry:
    """A cached LLM response with expiration."""

    response: "LLMResponse"
    created_at: float
    ttl_seconds: int
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() > (self.created_at + self.ttl_seconds)

    def touch(self) -> None:
        """Record a cache hit."""
        self.hit_count += 1


class ResponseCache:
    """
    TTL-based cache for LLM responses.

    Uses content-based hashing to identify identical prompts.
    Automatically evicts expired entries on access.
    """

    def __init__(
        self,
        default_ttl_seconds: int = 3600,
        max_entries: int = 1000,
    ):
        """
        Initialize the cache.

        Args:
            default_ttl_seconds: Default TTL for cache entries (1 hour)
            max_entries: Maximum number of entries before eviction
        """
        self.default_ttl = default_ttl_seconds
        self.max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    def _make_key(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Create a cache key from prompt content.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            model: Optional model identifier

        Returns:
            SHA-256 hash of the combined content
        """
        content = f"{model or 'default'}:{system_prompt or ''}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional["LLMResponse"]:
        """
        Get a cached response if available and not expired.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            model: Optional model identifier

        Returns:
            Cached LLMResponse or None if not found/expired
        """
        key = self._make_key(prompt, system_prompt, model)
        entry = self._cache.get(key)

        if entry is None:
            self._stats["misses"] += 1
            return None

        if entry.is_expired:
            del self._cache[key]
            self._stats["misses"] += 1
            self._stats["evictions"] += 1
            logger.debug(f"Cache entry expired: {key}")
            return None

        entry.touch()
        self._stats["hits"] += 1
        logger.debug(f"Cache hit: {key} (hits={entry.hit_count})")

        # Mark response as cached
        response = entry.response
        response.cached = True
        return response

    def set(
        self,
        prompt: str,
        response: "LLMResponse",
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Cache a response.

        Args:
            prompt: The user prompt
            response: The LLM response to cache
            system_prompt: Optional system prompt
            model: Optional model identifier
            ttl_seconds: Override default TTL
        """
        # Evict if at capacity
        if len(self._cache) >= self.max_entries:
            self._evict_oldest()

        key = self._make_key(prompt, system_prompt, model)
        self._cache[key] = CacheEntry(
            response=response,
            created_at=time.time(),
            ttl_seconds=ttl_seconds or self.default_ttl,
        )
        logger.debug(f"Cached response: {key}")

    def _evict_oldest(self) -> None:
        """Evict the oldest entry."""
        if not self._cache:
            return

        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at,
        )
        del self._cache[oldest_key]
        self._stats["evictions"] += 1
        logger.debug(f"Evicted oldest entry: {oldest_key}")

    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with hits, misses, evictions, entries, hit_rate
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0.0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "entries": len(self._cache),
            "hit_rate": round(hit_rate, 3),
        }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items() if entry.is_expired
        ]
        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self._stats["evictions"] += len(expired_keys)
            logger.info(f"Cleaned up {len(expired_keys)} expired entries")

        return len(expired_keys)
