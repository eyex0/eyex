from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

logger = logging.getLogger("pix.database")
settings = get_settings()

_engine_kwargs = {"pool_pre_ping": True, "echo": settings.app_debug}
if not settings.database_url.startswith("sqlite"):
    _engine_kwargs["pool_size"] = settings.database_pool_size
    _engine_kwargs["max_overflow"] = settings.database_max_overflow

engine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)


async def get_db_session() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Redis pool (optional — works without Redis in dev mode)
try:
    import redis.asyncio as aioredis
    _redis_pool: aioredis.ConnectionPool | None = None

    def get_redis_pool() -> aioredis.ConnectionPool:
        global _redis_pool
        if _redis_pool is None:
            _redis_pool = aioredis.ConnectionPool.from_url(
                settings.redis_url, max_connections=settings.redis_max_connections,
                decode_responses=True,
            )
        return _redis_pool

    async def get_redis() -> aioredis.Redis:
        return aioredis.Redis(connection_pool=get_redis_pool())
except ImportError:
    _redis_pool = None
    def get_redis_pool(): return None
    async def get_redis(): return None
