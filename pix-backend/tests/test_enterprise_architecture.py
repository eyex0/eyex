from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from app.core.enterprise_architecture import (
    AutoScaler,
    Bulkhead,
    ConnectionPoolConfig,
    ConnectionPoolManager,
    EnterpriseArchitectureManager,
    ResourceQuota,
    ServiceInstance,
    ServiceRegistry,
    TenantContext,
    get_architecture_manager,
)


class TestTenantContext:
    def test_set_and_get(self):
        ctx = TenantContext(tenant_id="tenant-1", org_id="org-1", plan_tier="professional")
        TenantContext.set_current(ctx)
        assert TenantContext.get_current("tenant-1") is ctx
        assert ctx.plan_tier == "professional"
        TenantContext.clear("tenant-1")
        assert TenantContext.get_current("tenant-1") is None

    def test_default_plan_tier(self):
        ctx = TenantContext(tenant_id="t1", org_id="o1")
        assert ctx.plan_tier == "free"


class TestResourceQuota:
    def test_get_limit(self):
        ctx = TenantContext(tenant_id="t1", org_id="o1", plan_tier="professional")
        quota = ResourceQuota(ctx)
        assert quota.get_limit("max_users") == 100
        assert quota.get_limit("max_agents") == 50

    def test_free_tier_limits(self):
        ctx = TenantContext(tenant_id="t1", org_id="o1", plan_tier="free")
        quota = ResourceQuota(ctx)
        assert quota.get_limit("max_users") == 5
        assert quota.get_limit("max_agents") == 5
        assert quota.get_limit("max_tasks_per_month") == 1000

    def test_enterprise_tier_limits(self):
        ctx = TenantContext(tenant_id="t1", org_id="o1", plan_tier="enterprise")
        quota = ResourceQuota(ctx)
        assert quota.get_limit("max_users") == 10000
        assert quota.get_limit("max_agents") == 500

    def test_check_quota_allows(self):
        ctx = TenantContext(tenant_id="t1", org_id="o1", plan_tier="free")
        quota = ResourceQuota(ctx)
        assert quota.check_quota("max_users", 3, requested=2) is True

    def test_check_quota_denies(self):
        ctx = TenantContext(tenant_id="t1", org_id="o1", plan_tier="free")
        quota = ResourceQuota(ctx)
        assert quota.check_quota("max_users", 5, requested=1) is False

    def test_quota_overrides(self):
        ctx = TenantContext(tenant_id="t1", org_id="o1", plan_tier="free", quota_overrides={"max_users": 50})
        quota = ResourceQuota(ctx)
        assert quota.get_limit("max_users") == 50

    def test_verify_quota_no_store(self):
        ctx = TenantContext(tenant_id="t1", org_id="o1")
        quota = ResourceQuota(ctx)
        allowed, info = asyncio.run(quota.verify_quota("max_users"))
        assert allowed is True
        assert info["reason"] == "no_store"

    def test_to_dict(self):
        ctx = TenantContext(tenant_id="t1", org_id="o1", plan_tier="enterprise")
        quota = ResourceQuota(ctx)
        d = quota.to_dict()
        assert d["tenant_id"] == "t1"
        assert d["plan_tier"] == "enterprise"
        assert d["limits"]["max_users"] == 10000


class TestAutoScaler:
    def test_initial_state(self):
        scaler = AutoScaler(min_instances=2, max_instances=10)
        assert scaler.current_instances == 2
        assert scaler.min_instances == 2
        assert scaler.max_instances == 10

    def test_steady_state(self):
        scaler = AutoScaler(min_instances=2, max_instances=10)
        for _ in range(10):
            scaler.record_metric(cpu_pct=30, memory_pct=40, queue_depth=5, request_rate=50)
        result = scaler.evaluate()
        assert result["action"] == "steady"

    def test_scale_up(self):
        scaler = AutoScaler(min_instances=2, max_instances=10, cooldown_seconds=0)
        for _ in range(10):
            scaler.record_metric(cpu_pct=90, memory_pct=85, queue_depth=80, request_rate=900)
        result = scaler.evaluate()
        assert result["action"] == "scale_up"
        assert result["to"] > result["from"]

    def test_scale_down(self):
        scaler = AutoScaler(min_instances=1, max_instances=10, cooldown_seconds=0)
        for _ in range(10):
            scaler.record_metric(cpu_pct=90, memory_pct=85, queue_depth=80, request_rate=900)
        scaler.evaluate()
        for _ in range(10):
            scaler.record_metric(cpu_pct=5, memory_pct=10, queue_depth=0, request_rate=5)
        result = scaler.evaluate()
        assert result["action"] == "scale_down"
        assert result["to"] < result["from"]

    def test_cooldown_prevents_rapid_scaling(self):
        scaler = AutoScaler(min_instances=2, max_instances=10, cooldown_seconds=3600)
        scaler._last_scale_time = datetime.now(UTC)
        for _ in range(10):
            scaler.record_metric(cpu_pct=90, memory_pct=85, queue_depth=80, request_rate=900)
        result = scaler.evaluate()
        assert result["action"] == "cooldown"

    def test_get_stats(self):
        scaler = AutoScaler(min_instances=2, max_instances=10)
        for _ in range(5):
            scaler.record_metric(cpu_pct=50, memory_pct=50, queue_depth=10, request_rate=100)
        stats = scaler.get_stats()
        assert stats["current_instances"] == 2
        assert stats["min_instances"] == 2
        assert stats["max_instances"] == 10
        assert stats["recent_metrics_count"] == 5

    def test_no_metrics_returns_steady(self):
        scaler = AutoScaler(min_instances=2, max_instances=10)
        result = scaler.evaluate()
        assert result["action"] == "none"

    def test_max_instances_respected(self):
        scaler = AutoScaler(min_instances=2, max_instances=5, cooldown_seconds=0)
        for _ in range(10):
            scaler.record_metric(cpu_pct=99, memory_pct=99, queue_depth=200, request_rate=5000)
        for _ in range(5):
            result = scaler.evaluate()
        assert scaler.current_instances <= 5

    def test_min_instances_respected(self):
        scaler = AutoScaler(min_instances=2, max_instances=10, cooldown_seconds=0)
        for _ in range(10):
            scaler.record_metric(cpu_pct=99, memory_pct=85, queue_depth=80, request_rate=900)
        scaler.evaluate()
        for _ in range(10):
            scaler.record_metric(cpu_pct=1, memory_pct=2, queue_depth=0, request_rate=1)
        for _ in range(5):
            result = scaler.evaluate()
        assert scaler.current_instances >= 2

    def test_metrics_capped_at_1000(self):
        scaler = AutoScaler(min_instances=2, max_instances=10)
        for i in range(1100):
            scaler.record_metric(cpu_pct=i % 100, memory_pct=50, queue_depth=10, request_rate=100)
        assert len(scaler._metrics) <= 600


class TestBulkhead:
    @pytest.mark.asyncio
    async def test_acquire_release(self):
        bh = Bulkhead(name="test", max_concurrent=2, queue_size=5)
        assert await bh.acquire() is True
        assert await bh.acquire() is True
        assert bh._active == 2
        bh.release()
        assert bh._active == 1
        bh.release()
        assert bh._active == 0

    @pytest.mark.asyncio
    async def test_rejects_when_full(self):
        bh = Bulkhead(name="test", max_concurrent=2, queue_size=0)
        assert await bh.acquire() is True
        assert await bh.acquire() is True
        assert await bh.acquire() is False

    @pytest.mark.asyncio
    async def test_timeout_on_acquire(self):
        bh = Bulkhead(name="test", max_concurrent=1, queue_size=1)
        assert await bh.acquire() is True
        assert await bh.acquire(timeout=0.1) is False

    @pytest.mark.asyncio
    async def test_is_full_detection(self):
        bh = Bulkhead(name="test", max_concurrent=1, queue_size=0)
        assert bh.is_full is False
        await bh.acquire()
        assert bh.is_full is True

    @pytest.mark.asyncio
    async def test_queue_accepts_when_occupied(self):
        bh = Bulkhead(name="test", max_concurrent=1, queue_size=2)
        assert await bh.acquire() is True
        task = asyncio.create_task(bh.acquire(timeout=1.0))
        await asyncio.sleep(0.05)
        assert bh._queue.qsize() == 1
        bh.release()
        assert await task is True

    def test_get_stats(self):
        bh = Bulkhead(name="test-bulkhead", max_concurrent=5, queue_size=10)
        stats = bh.get_stats()
        assert stats["name"] == "test-bulkhead"
        assert stats["max_concurrent"] == 5
        assert stats["queue_size"] == 10
        assert stats["active"] == 0
        assert stats["total_accepted"] == 0
        assert stats["total_rejected"] == 0


class TestConnectionPoolManager:
    def test_register_and_get_pool(self):
        mgr = ConnectionPoolManager()
        pool = {"conn": "dummy"}
        mgr.register_pool("db", pool, ConnectionPoolConfig(pool_size=10))
        assert mgr.get_pool("db") is pool
        assert mgr.get_pool("nonexistent") is None

    def test_record_error(self):
        mgr = ConnectionPoolManager()
        pool = {"conn": "dummy"}
        mgr.register_pool("db", pool)
        mgr.record_error("db")
        assert mgr._pools["db"]["stats"]["errors"] == 1

    def test_health_check_without_status(self):
        mgr = ConnectionPoolManager()
        pool = {"conn": "dummy"}
        mgr.register_pool("cache", pool)

        async def check():
            results = await mgr.health_check()
            assert "cache" in results
            assert results["cache"]["healthy"] is True

        asyncio.run(check())

    def test_get_stats(self):
        mgr = ConnectionPoolManager()
        mgr.register_pool("db", {"conn": "x"})
        mgr.register_pool("redis", {"conn": "y"})
        stats = mgr.get_stats()
        assert "db" in stats
        assert "redis" in stats


class TestServiceInstance:
    def test_address_property(self):
        inst = ServiceInstance(service_id="s1", host="10.0.0.1", port=8080, region="us-east")
        assert inst.address == "10.0.0.1:8080"

    def test_is_expired(self):
        inst = ServiceInstance(service_id="s1", host="10.0.0.1", port=8080, region="us-east")
        inst.last_heartbeat = datetime(2020, 1, 1, tzinfo=UTC)
        assert inst.is_expired(ttl_seconds=30) is True
        inst.last_heartbeat = datetime.now(UTC)
        assert inst.is_expired(ttl_seconds=30) is False

    def test_default_metadata(self):
        inst = ServiceInstance(service_id="s1", host="10.0.0.1", port=8080, region="us-east")
        assert inst.metadata == {}


class TestServiceRegistry:
    def test_register_and_get(self):
        reg = ServiceRegistry()
        inst = ServiceInstance(service_id="s1", host="10.0.0.1", port=8080, region="us-east")
        reg.register("api", inst)
        instances = reg.get_instances("api")
        assert len(instances) == 1
        assert instances[0].service_id == "s1"

    def test_deregister(self):
        reg = ServiceRegistry()
        inst = ServiceInstance(service_id="s1", host="10.0.0.1", port=8080, region="us-east")
        reg.register("api", inst)
        reg.deregister("api", "s1")
        assert len(reg.get_instances("api")) == 0

    def test_heartbeat(self):
        reg = ServiceRegistry()
        inst = ServiceInstance(service_id="s1", host="10.0.0.1", port=8080, region="us-east")
        inst.healthy = False
        reg.register("api", inst)
        assert reg.heartbeat("api", "s1") is True
        assert inst.healthy is True

    def test_heartbeat_unknown(self):
        reg = ServiceRegistry()
        assert reg.heartbeat("api", "unknown") is False

    def test_filter_by_region(self):
        reg = ServiceRegistry()
        reg.register("api", ServiceInstance("s1", "10.0.0.1", 8080, "us-east"))
        reg.register("api", ServiceInstance("s2", "10.0.0.2", 8080, "eu-west"))
        assert len(reg.get_instances("api", region="us-east")) == 1
        assert len(reg.get_instances("api", region="eu-west")) == 1
        assert len(reg.get_instances("api", region="ap-southeast")) == 0

    def test_get_random_instance(self):
        reg = ServiceRegistry()
        inst = ServiceInstance("s1", "10.0.0.1", 8080, "us-east")
        reg.register("api", inst)
        result = reg.get_random_instance("api")
        assert result is inst

    def test_get_random_instance_empty(self):
        reg = ServiceRegistry()
        assert reg.get_random_instance("nonexistent") is None

    def test_prune_expired(self):
        reg = ServiceRegistry()
        s1 = ServiceInstance("s1", "10.0.0.1", 8080, "us-east")
        s2 = ServiceInstance("s2", "10.0.0.2", 8080, "us-east")
        s1.last_heartbeat = datetime(2020, 1, 1, tzinfo=UTC)
        s2.last_heartbeat = datetime(2020, 1, 1, tzinfo=UTC)
        reg.register("api", s1)
        reg.register("api", s2)
        pruned = reg.prune_expired(ttl_seconds=30)
        assert pruned == 2
        assert len(reg.get_instances("api")) == 0

    def test_weighted_distribution(self):
        reg = ServiceRegistry()
        reg.register("api", ServiceInstance("s1", "10.0.0.1", 8080, "us-east", weight=10))
        reg.register("api", ServiceInstance("s2", "10.0.0.2", 8080, "us-east", weight=1))
        results = {"s1": 0, "s2": 0}
        for _ in range(1000):
            inst = reg.get_random_instance("api")
            if inst:
                results[inst.service_id] += 1
        assert results["s1"] > results["s2"]

    def test_get_stats(self):
        reg = ServiceRegistry()
        reg.register("api", ServiceInstance("s1", "10.0.0.1", 8080, "us-east"))
        reg.register("worker", ServiceInstance("s2", "10.0.0.2", 8081, "eu-west"))
        stats = reg.get_stats()
        assert "api" in stats
        assert "worker" in stats
        assert stats["api"]["instances"] == 1
        assert stats["api"]["regions"] == ["us-east"]

    def test_healthy_only_filter(self):
        reg = ServiceRegistry()
        reg.register("api", ServiceInstance("s1", "10.0.0.1", 8080, "us-east"))
        reg.register("api", ServiceInstance("s2", "10.0.0.2", 8080, "us-east"))
        inst2 = reg._services["api"]["s2"]
        inst2.healthy = False
        assert len(reg.get_instances("api", healthy_only=True)) == 1
        assert len(reg.get_instances("api", healthy_only=False)) == 2


class TestEnterpriseArchitectureManager:
    def test_singleton(self):
        m1 = get_architecture_manager()
        m2 = get_architecture_manager()
        assert m1 is m2

    def test_register_and_get_bulkhead(self):
        mgr = EnterpriseArchitectureManager()
        bh = mgr.register_bulkhead("db", max_concurrent=5)
        assert mgr.get_bulkhead("db") is bh
        assert mgr.get_bulkhead("nonexistent") is None

    def test_get_system_status(self):
        mgr = EnterpriseArchitectureManager()
        mgr.register_bulkhead("db", max_concurrent=5)
        status = mgr.get_system_status()
        assert "auto_scaler" in status
        assert "connection_pools" in status
        assert "service_registry" in status
        assert "bulkheads" in status
        assert "db" in status["bulkheads"]
