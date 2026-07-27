"""Lightweight metrics middleware — request timing."""
from __future__ import annotations
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Response-Time-ms"] = f"{duration * 1000:.1f}"
        return response


class MetricsCollector:
    """Simple in-memory metrics collector."""
    def __init__(self):
        self._counters = {}
        self._histograms = {}

    def increment(self, name: str, value: int = 1):
        self._counters[name] = self._counters.get(name, 0) + value

    def observe(self, name: str, value: float):
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)

    def summary(self) -> dict:
        return {
            "counters": dict(self._counters),
            "histograms": {k: {"count": len(v), "avg": sum(v) / len(v) if v else 0} for k, v in self._histograms.items()},
        }


_metrics: MetricsCollector | None = None

def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
