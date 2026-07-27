import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)


async def init_database() -> None:
    engine = create_async_engine(
        settings.database_url,
        isolation_level="AUTOCOMMIT",
    )
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT 1 FROM pg_database WHERE datname = :dbname"
                ),
                {"dbname": settings.postgres_db},
            )
            if not result.scalar():
                await conn.execute(
                    text(f'CREATE DATABASE "{settings.postgres_db}"')
                )
                logger.info("Database %s created", settings.postgres_db)
            else:
                logger.info("Database %s already exists", settings.postgres_db)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
