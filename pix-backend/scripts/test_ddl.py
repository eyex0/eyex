import asyncio

from sqlalchemy import text

from app.database import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE TABLE IF NOT EXISTS pix_backend.test_table2 (id int)")
        )
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema='pix_backend' AND table_name='test_table2'"
            )
        )
        print("exists:", result.scalar())
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
