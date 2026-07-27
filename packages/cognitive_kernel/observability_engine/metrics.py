from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.scaling import LRUCache


class MetricsCollector:
    """Lightweight in-memory metrics collector for RC1 monitoring."""

    def __init__(self) -> None:
        self.request_count = 0
        self.request_errors = 0
        self.request_duration_total = 0.0
        self.endpoint_counts: dict[str, int] = {}
        self.status_counts: dict[int, int] = {}
        self._slow_requests: LRUCache = LRUCache(max_size=100, default_ttl=3600)

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        self.request_count += 1
        key = f"{method} {path}"
        self.endpoint_counts[key] = self.endpoint_counts.get(key, 0) + 1
        self.status_counts[status_code] = self.status_counts.get(status_code, 0) + 1
        self.request_duration_total += duration_ms
        if status_code >= 500:
            self.request_errors += 1
        if duration_ms > 1000:
            self._slow_requests.set(key, {"duration_ms": duration_ms, "status_code": status_code})

    @property
    def average_duration_ms(self) -> float:
        return self.request_duration_total / self.request_count if self.request_count else 0.0

    def summary(self) -> dict[str, Any]:
        return {
            "request_count": self.request_count,
            "request_errors": self.request_errors,
            "average_duration_ms": round(self.average_duration_ms, 2),
            "endpoint_counts": self.endpoint_counts,
            "status_counts": self.status_counts,
            "slow_requests": [
                {"endpoint": k, "duration_ms": v["duration_ms"], "status_code": v["status_code"]}
                for k, v in self._slow_requests._cache.items()
            ],
        }


_METRICS: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _METRICS
    if _METRICS is None:
        _METRICS = MetricsCollector()
    return _METRICS


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request metrics for the monitoring endpoint."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        get_metrics().record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
