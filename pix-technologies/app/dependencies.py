from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from pix_backend.app.database import async_session_factory
from app.config import settings


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> Redis:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()
