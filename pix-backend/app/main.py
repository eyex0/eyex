from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from packages.cognitive-kernel.agent-runtime import set_global_persistent_memory
from app.api.v1.router import api_v1_router
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.middleware import setup_middleware
from app.database import async_session_factory, engine
from packages.cognitive-kernel.memory-engine import PersistentMemory
from pix_backend.app.database import get_redis_pool
from app.logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

settings = get_settings()

_memory: PersistentMemory | None = None


def get_memory() -> PersistentMemory:
    global _memory
    if _memory is None:
        _memory = PersistentMemory(
            session_factory=async_session_factory,
            redis_client=Redis(connection_pool=get_redis_pool()),
        )
        set_global_persistent_memory(_memory)
    return _memory


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)
    memory = get_memory()
    health = await memory.health()
    _app.state.memory = memory
    _app.state.memory_health = health
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.app_debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
)

setup_middleware(app)

if settings.is_production:
    if settings.app_secret_key == "change-this-to-a-random-64-char-string":
        logger.error("Default APP_SECRET_KEY detected in production. Refusing to start.")
        raise SystemExit(1)
    if settings.openai_api_key == "":
        logger.warning("OPENAI_API_KEY is not set in production. AI features will fail.")
    logger.info("Production security checks passed")

try:
    from app.core.telemetry import setup_telemetry
    setup_telemetry(app)
except ImportError:
    logger.info("OpenTelemetry not installed — observability disabled")


@app.exception_handler(AppError)
async def app_exception_handler(_request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


app.include_router(api_v1_router)
