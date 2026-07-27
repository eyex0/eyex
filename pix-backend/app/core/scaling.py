from __future__ import annotations

import asyncio
import functools
import hashlib
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("pix.core.scaling")


class LRUCache:
    """In-memory LRU cache with TTL support for high-throughput scenarios."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300) -> None:
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl

    def _key(self, *args: Any, **kwargs: Any) -> str:
        raw = f"{args}|{kwargs}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        if key not in self._cache:
            return None
        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expiry = time.time() + (ttl or self._default_ttl)
        self._cache[key] = (value, expiry)
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)


def cached(ttl: int = 300, max_size: int = 1000):
    """Decorator for caching async function results."""
    cache = LRUCache(max_size=max_size, default_ttl=ttl)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = cache._key(func.__name__, *args, **kwargs)
            result = cache.get(key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result
        return wrapper
    return decorator


class AgentPool:
    """Manages a pool of reusable agent instances for high concurrency.

    Instead of creating new agent instances per request, agents are
    pre-created and borrowed from the pool.
    """

    def __init__(self, factory: Callable, pool_size: int = 5, name: str = "agent") -> None:
        self._factory = factory
        self._pool_size = pool_size
        self._name = name
        self._pool: list[Any] = []
        self._in_use: set[int] = set()
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        async with self._lock:
            for _ in range(self._pool_size):
                instance = self._factory()
                self._pool.append(instance)
            logger.info("Initialized %s pool with %d instances", self._name, self._pool_size)

    async def acquire(self) -> Any:
        async with self._lock:
            for i, instance in enumerate(self._pool):
                if i not in self._in_use:
                    self._in_use.add(i)
                    return instance
        logger.warning("No available %s instances, creating temporary", self._name)
        return self._factory()

    async def release(self, instance: Any) -> None:
        async with self._lock:
            for i, inst in enumerate(self._pool):
                if inst is instance:
                    self._in_use.discard(i)
                    return

    @property
    def available(self) -> int:
        return self._pool_size - len(self._in_use)

    @property
    def total(self) -> int:
        return self._pool_size


class PaginatedResult:
    """Standard pagination wrapper for list endpoints."""

    def __init__(
        self, items: list[Any], total: int, page: int, per_page: int,
    ):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.total_pages = max(1, (total + per_page - 1) // per_page)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "per_page": self.per_page,
            "total_pages": self.total_pages,
            "has_next": self.page < self.total_pages,
            "has_prev": self.page > 1,
        }


_scaling_cache: LRUCache | None = None


def get_scaling_cache() -> LRUCache:
    global _scaling_cache
    if _scaling_cache is None:
        _scaling_cache = LRUCache()
    return _scaling_cache
