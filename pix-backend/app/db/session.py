from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from app.config import get_settings

settings = get_settings()

_pool: ConnectionPool | None = None


def get_redis_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
    return _pool


async def get_redis() -> Redis:
    pool = get_redis_pool()
    return Redis(connection_pool=pool)
