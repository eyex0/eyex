from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar, Protocol, TypeVar

logger = logging.getLogger("pix.core.architecture")

T = TypeVar("T")


class TenantStore(Protocol):
    async def get_quota(self, tenant_id: str) -> dict[str, Any]: ...
    async def get_usage(self, tenant_id: str) -> dict[str, Any]: ...


@dataclass
class TenantContext:
    tenant_id: str
    org_id: str
    plan_tier: str = "free"
    quota_overrides: dict[str, int] = field(default_factory=dict)

    _active: ClassVar[dict[str, TenantContext]] = {}

    @classmethod
    def set_current(cls, ctx: TenantContext) -> None:
        cls._active[ctx.tenant_id] = ctx

    @classmethod
    def get_current(cls, tenant_id: str) -> TenantContext | None:
        return cls._active.get(tenant_id)

    @classmethod
    def clear(cls, tenant_id: str) -> None:
        cls._active.pop(tenant_id, None)


class ResourceQuota:
    TIER_LIMITS: dict[str, dict[str, int]] = {
        "free": {"max_users": 5, "max_agents": 5, "max_tasks_per_month": 1000, "max_workspaces": 2, "max_api_keys": 3, "storage_mb": 100},
        "starter": {"max_users": 20, "max_agents": 15, "max_tasks_per_month": 10000, "max_workspaces": 5, "max_api_keys": 10, "storage_mb": 500},
        "professional": {"max_users": 100, "max_agents": 50, "max_tasks_per_month": 100000, "max_workspaces": 20, "max_api_keys": 25, "storage_mb": 2000},
        "enterprise": {"max_users": 10000, "max_agents": 500, "max_tasks_per_month": 10000000, "max_workspaces": 500, "max_api_keys": 100, "storage_mb": 50000},
    }

    def __init__(self, tenant: TenantContext, store: TenantStore | None = None) -> None:
        self.tenant = tenant
        self._store = store
        self._limits = self.TIER_LIMITS.get(tenant.plan_tier, self.TIER_LIMITS["free"]).copy()
        self._limits.update(tenant.quota_overrides)

    def get_limit(self, resource: str) -> int:
        return self._limits.get(resource, 0)

    def check_quota(self, resource: str, current_usage: int, requested: int = 1) -> bool:
        limit = self.get_limit(resource)
        return current_usage + requested <= limit

    async def verify_quota(self, resource: str, requested: int = 1) -> tuple[bool, dict[str, Any]]:
        if self._store is None:
            return True, {"allowed": True, "reason": "no_store"}
        usage = await self._store.get_usage(self.tenant.tenant_id)
        current = usage.get(resource, 0)
        limit = self.get_limit(resource)
        allowed = current + requested <= limit
        return allowed, {"allowed": allowed, "current": current, "limit": limit, "resource": resource}

    def to_dict(self) -> dict[str, Any]:
        return {"tenant_id": self.tenant.tenant_id, "plan_tier": self.tenant.plan_tier, "limits": self._limits}


class AutoScaler:
    def __init__(self, min_instances: int = 2, max_instances: int = 50, scale_up_threshold: float = 0.75, scale_down_threshold: float = 0.25, cooldown_seconds: int = 60) -> None:
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self._current = min_instances
        self._last_scale_time = datetime.min.replace(tzinfo=UTC)
        self._metrics: list[dict[str, Any]] = []
        self._scale_events: list[dict[str, Any]] = []

    @property
    def current_instances(self) -> int:
        return self._current

    def record_metric(self, cpu_pct: float, memory_pct: float, queue_depth: int, request_rate: float) -> None:
        self._metrics.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "cpu_pct": cpu_pct,
            "memory_pct": memory_pct,
            "queue_depth": queue_depth,
            "request_rate": request_rate,
            "instances": self._current,
        })
        if len(self._metrics) > 1000:
            self._metrics = self._metrics[-500:]

    def evaluate(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        if now - self._last_scale_time < self.cooldown:
            return {"action": "cooldown", "instances": self._current}

        recent = self._metrics[-10:] if len(self._metrics) >= 10 else self._metrics
        if not recent:
            return {"action": "none", "instances": self._current}

        avg_cpu = sum(m["cpu_pct"] for m in recent) / len(recent)
        avg_memory = sum(m["memory_pct"] for m in recent) / len(recent)
        avg_queue = sum(m["queue_depth"] for m in recent) / len(recent)
        avg_rate = sum(m["request_rate"] for m in recent) / len(recent)

        load_score = (avg_cpu / 100) * 0.4 + (avg_memory / 100) * 0.3 + min(avg_queue / 100, 1.0) * 0.2 + min(avg_rate / 1000, 1.0) * 0.1

        if load_score >= self.scale_up_threshold and self._current < self.max_instances:
            delta = max(1, int((load_score - self.scale_up_threshold) * 10))
            new_count = min(self.max_instances, self._current + delta)
            self._record_scale("up", self._current, new_count, load_score)
            self._current = new_count
            return {"action": "scale_up", "from": self._current - delta, "to": self._current, "load_score": round(load_score, 3)}

        if load_score <= self.scale_down_threshold and self._current > self.min_instances:
            delta = max(1, int((self.scale_down_threshold - load_score) * 10))
            new_count = max(self.min_instances, self._current - delta)
            self._record_scale("down", self._current, new_count, load_score)
            self._current = new_count
            return {"action": "scale_down", "from": self._current + delta, "to": self._current, "load_score": round(load_score, 3)}

        return {"action": "steady", "instances": self._current, "load_score": round(load_score, 3)}

    def _record_scale(self, direction: str, from_count: int, to_count: int, load_score: float) -> None:
        self._last_scale_time = datetime.now(UTC)
        self._scale_events.append({
            "timestamp": self._last_scale_time.isoformat(),
            "direction": direction,
            "from": from_count,
            "to": to_count,
            "load_score": round(load_score, 3),
        })

    def get_stats(self) -> dict[str, Any]:
        return {
            "current_instances": self._current,
            "min_instances": self.min_instances,
            "max_instances": self.max_instances,
            "scale_up_threshold": self.scale_up_threshold,
            "scale_down_threshold": self.scale_down_threshold,
            "total_scale_events": len(self._scale_events),
            "recent_metrics_count": len(self._metrics),
            "last_scale_event": self._scale_events[-1] if self._scale_events else None,
        }


class Bulkhead:
    def __init__(self, name: str, max_concurrent: int = 10, queue_size: int = 20) -> None:
        self.name = name
        self.max_concurrent = max_concurrent
        self.queue_size = queue_size
        self._active = 0
        self._queue: asyncio.Queue[asyncio.Event] = asyncio.Queue(maxsize=queue_size)
        self._total_accepted = 0
        self._total_rejected = 0
        self._total_queued = 0

    async def acquire(self, timeout: float = 5.0) -> bool:
        if self._active < self.max_concurrent:
            self._active += 1
            self._total_accepted += 1
            return True

        if self._queue.qsize() < self.queue_size:
            event = asyncio.Event()
            try:
                await asyncio.wait_for(self._queue.put(event), timeout=timeout)
            except TimeoutError:
                self._total_rejected += 1
                return False
            self._total_queued += 1
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            except TimeoutError:
                self._total_rejected += 1
                return False
            self._active += 1
            self._total_accepted += 1
            return True

        self._total_rejected += 1
        return False

    def release(self) -> None:
        self._active -= 1
        if not self._queue.empty():
            event = self._queue.get_nowait()
            event.set()

    @property
    def is_full(self) -> bool:
        return self._active >= self.max_concurrent and self._queue.qsize() >= self.queue_size

    def get_stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "active": self._active,
            "max_concurrent": self.max_concurrent,
            "queue_size": self.queue_size,
            "queued": self._queue.qsize(),
            "total_accepted": self._total_accepted,
            "total_rejected": self._total_rejected,
            "total_queued": self._total_queued,
            "is_full": self.is_full,
        }


class ConnectionPoolConfig:
    def __init__(self, pool_size: int = 20, max_overflow: int = 10, pool_timeout: int = 30, pool_pre_ping: bool = True, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_pre_ping = pool_pre_ping
        self.max_retries = max_retries
        self.retry_delay = retry_delay


class ConnectionPoolManager:
    def __init__(self) -> None:
        self._pools: dict[str, dict[str, Any]] = {}

    def register_pool(self, name: str, pool: Any, config: ConnectionPoolConfig | None = None) -> None:
        self._pools[name] = {"pool": pool, "config": config or ConnectionPoolConfig(), "stats": {"acquires": 0, "releases": 0, "errors": 0, "created_at": datetime.now(UTC).isoformat()}}

    def get_pool(self, name: str) -> Any | None:
        entry = self._pools.get(name)
        if entry:
            entry["stats"]["acquires"] += 1
            return entry["pool"]
        return None

    def record_error(self, name: str) -> None:
        entry = self._pools.get(name)
        if entry:
            entry["stats"]["errors"] += 1

    async def health_check(self) -> dict[str, Any]:
        results = {}
        for name, entry in self._pools.items():
            config = entry["config"]
            is_healthy = True
            error = None
            start = time.perf_counter()
            try:
                pool = entry["pool"]
                if hasattr(pool, "status"):
                    status = pool.status()
                    if hasattr(status, "get"):
                        is_healthy = status.get("healthy", True) if isinstance(status, dict) else True
            except Exception as exc:
                is_healthy = False
                error = str(exc)
            elapsed = (time.perf_counter() - start) * 1000
            results[name] = {"healthy": is_healthy, "latency_ms": round(elapsed, 2), "error": error, "config": {"pool_size": config.pool_size, "max_overflow": config.max_overflow}, "stats": entry["stats"]}
        return results

    def get_stats(self) -> dict[str, Any]:
        return {name: entry["stats"] for name, entry in self._pools.items()}


class ServiceInstance:
    def __init__(self, service_id: str, host: str, port: int, region: str, weight: int = 1, metadata: dict[str, Any] | None = None) -> None:
        self.service_id = service_id
        self.host = host
        self.port = port
        self.region = region
        self.weight = weight
        self.metadata = metadata or {}
        self.healthy = True
        self.last_heartbeat = datetime.now(UTC)
        self.registered_at = datetime.now(UTC)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def is_expired(self, ttl_seconds: int = 30) -> bool:
        return datetime.now(UTC) - self.last_heartbeat > timedelta(seconds=ttl_seconds)


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: dict[str, dict[str, ServiceInstance]] = defaultdict(dict)

    def register(self, service_name: str, instance: ServiceInstance) -> None:
        self._services[service_name][instance.service_id] = instance
        logger.info("Registered %s instance %s at %s (%s)", service_name, instance.service_id, instance.address, instance.region)

    def deregister(self, service_name: str, service_id: str) -> None:
        self._services[service_name].pop(service_id, None)

    def heartbeat(self, service_name: str, service_id: str) -> bool:
        instance = self._services[service_name].get(service_id)
        if instance:
            instance.last_heartbeat = datetime.now(UTC)
            instance.healthy = True
            return True
        return False

    def get_instances(self, service_name: str, region: str | None = None, healthy_only: bool = True) -> list[ServiceInstance]:
        instances = list(self._services.get(service_name, {}).values())
        if healthy_only:
            instances = [i for i in instances if i.healthy and not i.is_expired()]
        if region:
            instances = [i for i in instances if i.region == region]
        return instances

    def get_random_instance(self, service_name: str, region: str | None = None) -> ServiceInstance | None:
        instances = self.get_instances(service_name, region)
        if not instances:
            return None
        weighted = [i for i in instances for _ in range(i.weight)]
        return random.choice(weighted) if weighted else random.choice(instances)

    def prune_expired(self, ttl_seconds: int = 30) -> int:
        pruned = 0
        for service_name in list(self._services.keys()):
            for service_id in list(self._services[service_name].keys()):
                if self._services[service_name][service_id].is_expired(ttl_seconds):
                    del self._services[service_name][service_id]
                    pruned += 1
        return pruned

    def get_stats(self) -> dict[str, Any]:
        return {
            service: {
                "instances": len(instances),
                "healthy": sum(1 for i in instances.values() if i.healthy),
                "regions": list({i.region for i in instances.values()}),
            }
            for service, instances in self._services.items()
        }


class EnterpriseArchitectureManager:
    def __init__(self) -> None:
        self.auto_scaler = AutoScaler()
        self.connection_pool_manager = ConnectionPoolManager()
        self.service_registry = ServiceRegistry()
        self._bulkheads: dict[str, Bulkhead] = {}

    def register_bulkhead(self, name: str, max_concurrent: int = 10, queue_size: int = 20) -> Bulkhead:
        bh = Bulkhead(name=name, max_concurrent=max_concurrent, queue_size=queue_size)
        self._bulkheads[name] = bh
        return bh

    def get_bulkhead(self, name: str) -> Bulkhead | None:
        return self._bulkheads.get(name)

    def get_system_status(self) -> dict[str, Any]:
        return {
            "auto_scaler": self.auto_scaler.get_stats(),
            "connection_pools": self.connection_pool_manager.get_stats(),
            "service_registry": self.service_registry.get_stats(),
            "bulkheads": {name: bh.get_stats() for name, bh in self._bulkheads.items()},
        }


_architecture_manager: EnterpriseArchitectureManager | None = None


def get_architecture_manager() -> EnterpriseArchitectureManager:
    global _architecture_manager
    if _architecture_manager is None:
        _architecture_manager = EnterpriseArchitectureManager()
    return _architecture_manager
