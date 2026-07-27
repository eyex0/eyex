import asyncio

from sqlalchemy import text

from app.database import engine


async def main():
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='organizations' "
                "ORDER BY ordinal_position"
            )
        )
        for row in result:
            print(row)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
