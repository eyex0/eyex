from collections.abc import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


async def redis_client() -> AsyncGenerator[Redis, None]:
    async for client in get_redis():
        yield client
