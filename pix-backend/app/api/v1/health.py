from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.cache import get_cache
from app.config import get_settings
from app.core.metrics import get_metrics

health_router = APIRouter(tags=["Health"])

_health_start = datetime.now(UTC)


@health_router.get("/health")
async def health_check(request: Request):
    uptime = (datetime.now(UTC) - _health_start).total_seconds()

    deps = {"postgresql": False, "redis": False, "openai": False, "tools": 0}

    cache = get_cache()
    cached = await cache.get("health:status")
    if cached is not None:
        cached["uptime_seconds"] = round(uptime, 2)
        cached["timestamp"] = datetime.now(UTC).isoformat()
        return cached

    memory = getattr(request.app.state, "memory", None)
    if memory:
        try:
            mh = await memory.health()
            deps["postgresql"] = mh.get("postgresql", False)
            deps["redis"] = mh.get("redis", False)
        except Exception:
            pass

    deps["openai"] = bool(get_settings().openai_api_key)

    from app.agents.tools.registry import get_registry
    deps["tools"] = len(get_registry().list_all_tools())

    all_ok = (
        deps.get("postgresql", False)
        and deps.get("redis", False)
        and deps.get("openai", False)
    )

    payload = {
        "status": "ok" if all_ok else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": get_settings().app_version,
        "service": get_settings().app_name,
        "dependencies": deps,
        "uptime_seconds": round(uptime, 2),
    }
    await cache.set("health:status", payload, ttl=30)
    return payload


@health_router.get("/metrics")
async def metrics_check():
    return get_metrics().summary()
