import asyncio

from sqlalchemy import text

from app.database import engine


async def main():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        )
        for row in result:
            print(row[0])
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
