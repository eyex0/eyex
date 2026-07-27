from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("pix.core.platform")


@dataclass
class HealthCheckResult:
    component: str
    status: str  # healthy | degraded | unhealthy
    latency_ms: float = 0.0
    error: str | None = None
    last_checked: str = ""


class CircuitBreaker:
    """Prevents cascading failures by stopping calls to failing services."""

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = self.STATE_CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.total_calls = 0
        self.total_failures = 0

    async def call(self, func: Callable[[], Any]) -> Any:
        self.total_calls += 1
        if self.state == self.STATE_OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = self.STATE_HALF_OPEN
                logger.info("Circuit breaker %s: half-open (attempting recovery)", self.name)
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            result = func()
            if asyncio.iscoroutine(result):
                result = await result
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self.state == self.STATE_HALF_OPEN:
            logger.info("Circuit breaker %s: recovered, closing", self.name)
        self.state = self.STATE_CLOSED
        self.failure_count = 0

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = self.STATE_OPEN
            logger.warning("Circuit breaker %s: OPEN (threshold=%d)", self.name, self.failure_threshold)

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name, "state": self.state,
            "failure_count": self.failure_count,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "failure_rate": round(self.total_failures / max(self.total_calls, 1) * 100, 2),
        }


class GlobalDeploymentConfig:
    """Configuration for global multi-region deployment."""

    REGIONS = {
        "us-east": {"provider": "aws", "latency_ms": 50, "status": "active"},
        "eu-west": {"provider": "aws", "latency_ms": 80, "status": "active"},
        "me-central": {"provider": "aws", "latency_ms": 20, "status": "active"},
        "ap-southeast": {"provider": "aws", "latency_ms": 120, "status": "standby"},
    }

    @classmethod
    def get_active_regions(cls) -> list[str]:
        return [k for k, v in cls.REGIONS.items() if v["status"] == "active"]

    @classmethod
    def get_nearest_region(cls, client_latency_ms: float = 0) -> str:
        return min(cls.REGIONS, key=lambda r: cls.REGIONS[r]["latency_ms"])

    @classmethod
    def get_region_config(cls, region: str) -> dict[str, Any] | None:
        return cls.REGIONS.get(region)


class PlatformHealthMonitor:
    """Comprehensive health monitoring for enterprise deployment."""

    def __init__(self) -> None:
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._health_checks: list[HealthCheckResult] = []
        self._start_time = time.time()

    def register_circuit_breaker(self, name: str, threshold: int = 5, timeout: float = 30.0) -> CircuitBreaker:
        cb = CircuitBreaker(name=name, failure_threshold=threshold, recovery_timeout=timeout)
        self._circuit_breakers[name] = cb
        return cb

    def get_circuit_breaker(self, name: str) -> CircuitBreaker | None:
        return self._circuit_breakers.get(name)

    def record_health(self, component: str, status: str, latency_ms: float = 0.0, error: str | None = None) -> HealthCheckResult:
        result = HealthCheckResult(
            component=component, status=status,
            latency_ms=round(latency_ms, 2), error=error,
            last_checked=datetime.now(UTC).isoformat(),
        )
        self._health_checks.append(result)
        return result

    async def run_all_checks(self) -> list[HealthCheckResult]:
        checks = [
            ("database", self._check_database()),
            ("redis", self._check_redis()),
            ("openai", self._check_openai()),
            ("memory_system", self._check_memory()),
            ("agent_graph", self._check_graph()),
        ]
        for name, coro in checks:
            start = time.perf_counter()
            try:
                async with asyncio.timeout(5):
                    result = await coro
                    elapsed = (time.perf_counter() - start) * 1000
                    self.record_health(name, "healthy" if result else "degraded", elapsed)
            except TimeoutError:
                elapsed = (time.perf_counter() - start) * 1000
                self.record_health(name, "unhealthy", elapsed, "Health check timed out")
            except Exception as exc:
                elapsed = (time.perf_counter() - start) * 1000
                self.record_health(name, "unhealthy", elapsed, str(exc))
        return self._health_checks[-len(checks):]

    async def _check_database(self) -> bool:
        from app.database import get_session_factory
        async with get_session_factory()() as db:
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1"))
            return result.scalar() == 1

    async def _check_redis(self) -> bool:
        from redis.asyncio import Redis

        from pix_backend.app.database import get_redis_pool
        r = Redis(connection_pool=get_redis_pool())
        return await r.ping()

    async def _check_openai(self) -> bool:
        try:
            from app.config import get_settings
            settings = get_settings()
            if not settings.openai_api_key:
                return True
            import openai
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            await client.models.list()
            return True
        except Exception:
            return False

    async def _check_memory(self) -> bool:
        try:
            from packages.cognitive-kernel.memory-engine import get_global_memory
            mem = get_global_memory()
            if mem is None:
                return True
            health = await mem.health()
            return health.get("healthy", False)
        except Exception:
            return False

    async def _check_graph(self) -> bool:
        try:
            from app.agents.graph import AgentGraph
            graph = AgentGraph()
            graph.build()
            return graph.graph is not None
        except Exception:
            return False

    def get_system_health(self) -> dict[str, Any]:
        latest = {}
        for check in self._health_checks:
            if check.component not in latest or check.last_checked > latest[check.component].last_checked:
                latest[check.component] = check

        unhealthy = [c for c in latest.values() if c.status != "healthy"]
        circuit_status = {name: cb.get_status() for name, cb in self._circuit_breakers.items()}

        return {
            "overall": "healthy" if not unhealthy else "degraded" if any(c.status == "degraded" for c in unhealthy) else "unhealthy",
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "components": {
                name: {"status": c.status, "latency_ms": c.latency_ms, "error": c.error}
                for name, c in latest.items()
            },
            "circuit_breakers": circuit_status,
            "unhealthy_components": [c.component for c in unhealthy],
            "healthy_count": sum(1 for c in latest.values() if c.status == "healthy"),
            "total_components": len(latest),
            "regions": GlobalDeploymentConfig.get_active_regions(),
        }


_monitor: PlatformHealthMonitor | None = None


def get_platform_monitor() -> PlatformHealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = PlatformHealthMonitor()
    return _monitor
