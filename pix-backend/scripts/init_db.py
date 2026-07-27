from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings


async def init_database() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)

    sql_dir = Path(__file__).parent / ".." / "supabase"
    setup_sql = sql_dir / "setup.sql"

    print(f"Connecting to {settings.database_url}")

    async with engine.begin() as conn:
        if setup_sql.exists():
            print(f"Executing {setup_sql}...")
            sql = setup_sql.read_text()
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    await conn.execute(text(stmt))
            print("Database initialized successfully.")
        else:
            print("Creating tables from models...")
            from app.models.base import Base

            await conn.run_sync(Base.metadata.create_all)
            print("Tables created.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
