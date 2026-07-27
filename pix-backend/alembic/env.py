import os
from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context
from sqlalchemy import pool, create_engine, String, JSON
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.models import Base  # noqa: F401

# --- Compatibility shims for SQLite ---
# Patch sa.JSONB and sa.UUID so migrations work on both PostgreSQL and SQLite
if not hasattr(sa, 'JSONB'):
    sa.JSONB = JSON
from sqlalchemy.dialects import postgresql
postgresql.JSONB = JSON
if not hasattr(sa, 'UUID'):
    sa.UUID = String

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    return os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


def is_sqlite() -> bool:
    return get_database_url().startswith("sqlite")


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=is_sqlite(),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_sync() -> None:
    """Sync mode for SQLite."""
    url = get_database_url().replace("+aiosqlite", "")
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite(),
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


def run_migrations_async() -> None:
    """Async mode for PostgreSQL."""
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = get_database_url()
    connectable = async_engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool,
    )

    async def do_run_migrations(connection) -> None:
        context.configure(connection=connection, target_metadata=target_metadata)
        await context.run_migrations()

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            await do_run_migrations(connection)
        await connectable.dispose()

    import asyncio
    asyncio.run(run_async_migrations())


def run_migrations_online() -> None:
    if is_sqlite():
        run_migrations_sync()
    else:
        run_migrations_async()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
