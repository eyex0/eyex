from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

from pix_backend.app.database import get_redis

logger = logging.getLogger("pix.cache")

DEFAULT_TTL = 300


class RedisCache:
    """Simple async Redis cache with JSON serialization."""

    def __init__(self, redis: Redis | None = None, default_ttl: int = DEFAULT_TTL) -> None:
        self._redis = redis
        self._default_ttl = default_ttl

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def get(self, key: str) -> Any | None:
        try:
            redis = await self._get_redis()
            data = await redis.get(key)
            if data is None:
                return None
            return json.loads(data)
        except Exception as exc:
            logger.warning("Redis cache get failed for %s: %s", key, exc)
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            redis = await self._get_redis()
            await redis.set(key, json.dumps(value), ex=ttl or self._default_ttl)
        except Exception as exc:
            logger.warning("Redis cache set failed for %s: %s", key, exc)

    async def delete(self, key: str) -> None:
        try:
            redis = await self._get_redis()
            await redis.delete(key)
        except Exception as exc:
            logger.warning("Redis cache delete failed for %s: %s", key, exc)

    async def clear_pattern(self, pattern: str) -> None:
        try:
            redis = await self._get_redis()
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)
        except Exception as exc:
            logger.warning("Redis cache clear pattern failed for %s: %s", pattern, exc)


_cache: RedisCache | None = None


def get_cache() -> RedisCache:
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache
