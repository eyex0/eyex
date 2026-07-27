from __future__ import annotations
import json, logging
from typing import Any

logger = logging.getLogger("pix.cache")
DEFAULT_TTL = 300

class RedisCache:
    def __init__(self, redis=None, default_ttl: int = DEFAULT_TTL):
        self._redis = redis
        self._default_ttl = default_ttl
        self._local: dict[str, Any] = {}

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from app.database import get_redis_pool
            pool = get_redis_pool()
            if pool is None:
                return None
            import redis.asyncio as aioredis
            self._redis = aioredis.Redis(connection_pool=pool)
            return self._redis
        except Exception:
            return None

    async def get(self, key: str):
        r = await self._get_redis()
        if r is None:
            return self._local.get(key)
        try:
            val = await r.get(key)
            return json.loads(val) if val else None
        except Exception:
            return self._local.get(key)

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL):
        self._local[key] = value
        r = await self._get_redis()
        if r is None:
            return
        try:
            await r.set(key, json.dumps(value), ex=ttl)
        except Exception:
            pass

    async def delete(self, key: str):
        self._local.pop(key, None)
        r = await self._get_redis()
        if r is None:
            return
        try:
            await r.delete(key)
        except Exception:
            pass

_cache: RedisCache | None = None

def get_cache() -> RedisCache:
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache
