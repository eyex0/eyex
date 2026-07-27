import asyncio

from sqlalchemy import text

from app.database import engine


async def main():
    tables = [
        "organizations",
        "profiles",
        "organization_members",
        "org_members",
        "data_sources",
        "sales_orders",
        "projects_projects",
    ]
    async with engine.connect() as conn:
        for table in tables:
            try:
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                count = result.scalar()
                print(f"{table}: {count}")
            except Exception as exc:
                print(f"{table}: error - {exc}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
