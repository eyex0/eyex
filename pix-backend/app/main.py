from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router as api_v1_router
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.middleware import setup_middleware
from app.database import async_session_factory, engine
from app.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.app_debug,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

setup_middleware(app)

if settings.is_production:
    if settings.app_secret_key == "change-this-to-a-random-64-char-string":
        logger.error("Default APP_SECRET_KEY in production. Refusing to start.")
        raise SystemExit(1)

try:
    from app.core.telemetry import setup_telemetry
    setup_telemetry(app)
except ImportError:
    pass


@app.exception_handler(AppError)
async def app_exception_handler(_request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "detail": exc.detail, "status_code": exc.status_code},
    )


app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def root_health():
    return {"status": "healthy", "service": settings.app_name, "version": settings.app_version}

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "service": settings.app_name, "version": settings.app_version}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    import traceback
    tb = traceback.format_exc()
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": tb, "status_code": 500},
    )
