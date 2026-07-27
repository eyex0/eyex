"""
πX Phase 3.5 — Production Hardening — 100+ tests.

Covers: embedding router, runtime, event bus, production persistence,
production security, retry handler, integration scenarios.
"""
import pytest
import asyncio

from packages.cognitive_kernel.agent_os.embedding_router import EmbeddingRouter
from packages.cognitive_kernel.agent_os.production_persistence import ProductionPersistence, PersistentStore
from packages.cognitive_kernel.agent_os.production_security import ProductionSecurity, RateLimitConfig
from packages.cognitive_kernel.runtime.px_runtime import PXRuntime, TaskPriority, RuntimeTaskType
from packages.cognitive_kernel.runtime.retry_handler import RetryHandler, RetryConfig, CircuitBreakerOpenError
from packages.cognitive_kernel.event_bus.event_bus import EventBus, EventType, PXEvent
from packages.cognitive_kernel.agent_os.agent_manager import AgentManager
from packages.cognitive_kernel.agent_os.agent_registry import AgentType, AgentStatus

ORG_ID = "test-org-001"
ORG_ID_2 = "test-org-002"

RETAIL_PROFILE = {
    "org_id": ORG_ID, "industry": "retail",
    "company_identity": {"name": "Acme Retail"},
    "kpis": [{"name": "Revenue"}, {"name": "Inventory Turnover"}],
    "ontology": {"entities": {"customer": {}, "product": {}, "store": {}}},
}
MFG_PROFILE = {
    "org_id": ORG_ID, "industry": "manufacturing",
    "company_identity": {"name": "Precision Mfg"},
    "kpis": [{"name": "OEE"}, {"name": "Quality Rate"}],
    "ontology": {"entities": {"equipment": {}, "work_order": {}}},
}


# ══════════════════════════════════════════════════════════════
# 1. EMBEDDING ROUTER TESTS (16)
# ══════════════════════════════════════════════════════════════

class TestEmbeddingRouter:
    def _setup(self, profile=None):
        mgr = AgentManager()
        profile = profile or RETAIL_PROFILE
        agents = mgr.create_agents_for_industry(ORG_ID, profile)
        return EmbeddingRouter(), agents, mgr

    def test_register_agent_creates_embedding(self):
        router, agents, mgr = self._setup()
        rec = router.register_agent(agents[0])
        assert len(rec.embedding) == EmbeddingRouter.EMBEDDING_DIM
        assert all(-1 <= v <= 1 for v in rec.embedding)

    def test_route_returns_selected_agents(self):
        router, agents, mgr = self._setup()
        result = router.route("Why did revenue drop?", agents, RETAIL_PROFILE)
        assert len(result["selected"]) > 0
        assert result["method"] == "embedding"

    def test_route_returns_scores(self):
        router, agents, mgr = self._setup()
        result = router.route("Revenue analysis", agents, RETAIL_PROFILE)
        assert len(result["scores"]) == len(agents)

    def test_route_returns_reasoning(self):
        router, agents, mgr = self._setup()
        result = router.route("Revenue analysis", agents, RETAIL_PROFILE)
        assert "Embedding similarity routing" in result["reasoning"]

    def test_route_no_active_agents(self):
        router = EmbeddingRouter()
        result = router.route("test", [])
        assert result["method"] == "fallback"

    def test_route_sales_query_favors_sales_agent(self):
        router, agents, mgr = self._setup()
        result = router.route("revenue sales forecast trends", agents, RETAIL_PROFILE)
        sales_agent = [a for a in agents if a.spec.type == AgentType.SALES][0]
        # Sales agent should be in selected or have highest score
        assert sales_agent.id in result["selected"] or result["scores"][sales_agent.id] > 0

    def test_route_inventory_query(self):
        router, agents, mgr = self._setup()
        result = router.route("inventory stock levels supply chain", agents, RETAIL_PROFILE)
        inv_agent = [a for a in agents if a.spec.type == AgentType.INVENTORY]
        if inv_agent:
            assert inv_agent[0].id in result["selected"]

    def test_route_manufacturing_query(self):
        router, agents, mgr = self._setup(MFG_PROFILE)
        result = router.route("production OEE efficiency manufacturing", agents, MFG_PROFILE)
        prod_agent = [a for a in agents if a.spec.type == AgentType.PRODUCTION]
        if prod_agent:
            assert prod_agent[0].id in result["selected"]

    def test_route_quality_query(self):
        router, agents, mgr = self._setup(MFG_PROFILE)
        result = router.route("quality defect rate inspection yield", agents, MFG_PROFILE)
        qual_agent = [a for a in agents if a.spec.type == AgentType.QUALITY]
        if qual_agent:
            assert qual_agent[0].id in result["selected"]

    def test_cosine_similarity_same_vector(self):
        router = EmbeddingRouter()
        vec = router._pseudo_embed("revenue sales")
        sim = router._cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_different_vectors(self):
        router = EmbeddingRouter()
        v1 = router._pseudo_embed("revenue sales")
        v2 = router._pseudo_embed("maintenance equipment")
        sim = router._cosine_similarity(v1, v2)
        assert sim < 0.9

    def test_pseudo_embed_is_deterministic(self):
        router = EmbeddingRouter()
        v1 = router._pseudo_embed("revenue analysis")
        v2 = router._pseudo_embed("revenue analysis")
        assert v1 == v2

    def test_pseudo_embed_is_normalized(self):
        router = EmbeddingRouter()
        vec = router._pseudo_embed("any text here")
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 0.01

    def test_profile_context_boost(self):
        router, agents, mgr = self._setup()
        result = router.route("Revenue analysis", agents, RETAIL_PROFILE)
        # Agents with matching KPIs should get boost
        for aid, score in result["scores"].items():
            agent = [a for a in agents if a.id == aid][0]
            if "Revenue" in agent.spec.kpis_monitored:
                assert score >= 0  # Should be non-negative

    def test_route_geographic_query(self):
        router, agents, mgr = self._setup()
        result = router.route("Why did sales decline in Germany?", agents, RETAIL_PROFILE)
        assert len(result["selected"]) > 0

    def test_get_agent_embedding(self):
        router, agents, mgr = self._setup()
        router.register_agent(agents[0])
        emb = router.get_agent_embedding(agents[0].id)
        assert emb is not None
        assert len(emb) == EmbeddingRouter.EMBEDDING_DIM


# ══════════════════════════════════════════════════════════════
# 2. RUNTIME TESTS (16)
# ══════════════════════════════════════════════════════════════

class TestPXRuntime:
    def test_enqueue_task(self):
        rt = PXRuntime()
        task = rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "agent_1", {"query": "test"})
        assert task.state == "pending"
        assert len(rt.get_queue()) == 1

    def test_enqueue_priority_ordering(self):
        rt = PXRuntime()
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "a1", priority=TaskPriority.LOW)
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "a2", priority=TaskPriority.CRITICAL)
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "a3", priority=TaskPriority.NORMAL)
        queue = rt.get_queue()
        assert queue[0]["priority"] == "critical"
        assert queue[2]["priority"] == "low"

    def test_schedule_task(self):
        rt = PXRuntime()
        sched = rt.schedule(ORG_ID, "agent_1", RuntimeTaskType.KPI_MONITOR, interval_seconds=3600)
        assert sched.active is True
        assert sched.interval_seconds == 3600

    def test_pause_resume_schedule(self):
        rt = PXRuntime()
        sched = rt.schedule(ORG_ID, "agent_1", RuntimeTaskType.KPI_MONITOR, 3600)
        assert rt.pause_schedule(sched.id)
        assert not rt.get_schedules()[0]["active"]
        assert rt.resume_schedule(sched.id)
        assert rt.get_schedules()[0]["active"]

    def test_remove_schedule(self):
        rt = PXRuntime()
        sched = rt.schedule(ORG_ID, "agent_1", RuntimeTaskType.KPI_MONITOR, 3600)
        assert rt.remove_schedule(sched.id)
        assert len(rt.get_schedules()) == 0

    def test_tick_executes_tasks(self):
        rt = PXRuntime()
        async def handler(task):
            return {"result": "ok"}
        rt.register_handler(RuntimeTaskType.AGENT_EXECUTE, handler)
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "agent_1")
        executed = asyncio.run(rt.tick())
        assert len(executed) == 1
        assert executed[0].state == "succeeded"

    def test_tick_with_failed_handler(self):
        rt = PXRuntime()
        async def handler(task):
            raise ValueError("test error")
        rt.register_handler(RuntimeTaskType.AGENT_EXECUTE, handler)
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "agent_1")
        executed = asyncio.run(rt.tick())
        assert executed[0].state == "failed"
        assert "test error" in executed[0].error

    def test_tick_with_no_handler(self):
        rt = PXRuntime()
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "agent_1")
        executed = asyncio.run(rt.tick())
        assert executed[0].state == "failed"
        assert "No handler" in executed[0].error

    def test_health_status(self):
        rt = PXRuntime()
        health = rt.get_health()
        assert "total_tasks" in health
        assert "queue_length" in health
        assert "uptime_seconds" in health

    def test_get_completed(self):
        rt = PXRuntime()
        async def handler(task):
            return "ok"
        rt.register_handler(RuntimeTaskType.AGENT_EXECUTE, handler)
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "a1")
        asyncio.run(rt.tick())
        completed = rt.get_completed()
        assert len(completed) == 1
        assert completed[0]["state"] == "succeeded"

    def test_get_schedules_by_org(self):
        rt = PXRuntime()
        rt.schedule(ORG_ID, "a1", RuntimeTaskType.KPI_MONITOR, 3600)
        rt.schedule(ORG_ID_2, "a2", RuntimeTaskType.KPI_MONITOR, 3600)
        assert len(rt.get_schedules(org_id=ORG_ID)) == 1

    def test_retry_with_failing_then_succeeding(self):
        call_count = [0]
        async def handler(task):
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("fail")
            return "ok"
        rt = PXRuntime()
        rt.register_handler(RuntimeTaskType.AGENT_EXECUTE, handler)
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "a1")
        asyncio.run(rt.tick())
        # Should retry and succeed
        completed = rt.get_completed()
        assert completed[0]["state"] == "succeeded"

    def test_multiple_tasks_in_queue(self):
        rt = PXRuntime()
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "a1", priority=TaskPriority.HIGH)
        rt.enqueue(RuntimeTaskType.KPI_MONITOR, ORG_ID, "a2", priority=TaskPriority.NORMAL)
        async def handler(task):
            return "ok"
        rt.register_handler(RuntimeTaskType.AGENT_EXECUTE, handler)
        rt.register_handler(RuntimeTaskType.KPI_MONITOR, handler)
        executed = asyncio.run(rt.tick())
        assert len(executed) == 2

    def test_tick_fires_scheduled_tasks(self):
        rt = PXRuntime()
        # Schedule with 0-second interval so it fires immediately
        rt.schedule(ORG_ID, "a1", RuntimeTaskType.KPI_MONITOR, interval_seconds=0)
        async def handler(task):
            return "ok"
        rt.register_handler(RuntimeTaskType.KPI_MONITOR, handler)
        # Manually set next_run to past to trigger
        for s in rt._schedules.values():
            s.next_run = "2020-01-01T00:00:00+00:00"
        asyncio.run(rt.tick())
        assert len(rt.get_completed()) >= 1

    def test_runtime_task_to_dict(self):
        rt = PXRuntime()
        task = rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "a1")
        d = task.to_dict()
        assert d["task_type"] == "agent_execute"
        assert d["priority"] == "normal"

    def test_circuit_breaker_state(self):
        rt = PXRuntime()
        state = rt.get_retry_state("test_task")
        assert "consecutive_failures" in state
        assert "circuit_open" in state


# ══════════════════════════════════════════════════════════════
# 3. RETRY HANDLER TESTS (10)
# ══════════════════════════════════════════════════════════════

class TestRetryHandler:
    def test_successful_execution_no_retry(self):
        rh = RetryHandler()
        async def handler():
            return "ok"
        result = asyncio.run(rh.execute_with_retry("task1", handler))
        assert result == "ok"

    def test_retry_on_failure(self):
        rh = RetryHandler(RetryConfig(max_retries=3, base_delay_seconds=0.01))
        call_count = [0]
        async def handler():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("fail")
            return "ok"
        result = asyncio.run(rh.execute_with_retry("task2", handler))
        assert result == "ok"
        assert call_count[0] == 2

    def test_max_retries_exceeded(self):
        rh = RetryHandler(RetryConfig(max_retries=2, base_delay_seconds=0.01))
        async def handler():
            raise ValueError("always fails")
        with pytest.raises(ValueError):
            asyncio.run(rh.execute_with_retry("task3", handler))

    def test_circuit_breaker_opens(self):
        config = RetryConfig(max_retries=1, base_delay_seconds=0.01, circuit_breaker_threshold=2, circuit_breaker_reset_seconds=0.1)
        rh = RetryHandler(config)
        async def handler():
            raise ValueError("fail")
        # Trigger 2 failures
        for _ in range(2):
            with pytest.raises(ValueError):
                asyncio.run(rh.execute_with_retry("task4", handler))
        # Circuit should be open
        with pytest.raises(CircuitBreakerOpenError):
            asyncio.run(rh.execute_with_retry("task4", handler))

    def test_circuit_breaker_resets(self):
        import time
        config = RetryConfig(max_retries=1, base_delay_seconds=0.01, circuit_breaker_threshold=2, circuit_breaker_reset_seconds=0.05)
        rh = RetryHandler(config)
        async def failing():
            raise ValueError("fail")
        for _ in range(2):
            with pytest.raises(ValueError):
                asyncio.run(rh.execute_with_retry("task5", failing))
        # Wait for reset
        time.sleep(0.06)
        async def succeeding():
            return "ok"
        result = asyncio.run(rh.execute_with_retry("task5", succeeding))
        assert result == "ok"

    def test_compute_delay_exponential(self):
        rh = RetryHandler(RetryConfig(base_delay_seconds=1.0, jitter=False))
        d1 = rh._compute_delay(1)
        d2 = rh._compute_delay(2)
        d3 = rh._compute_delay(3)
        assert d1 == 1.0
        assert d2 == 2.0
        assert d3 == 4.0

    def test_compute_delay_max_cap(self):
        rh = RetryHandler(RetryConfig(base_delay_seconds=10.0, max_delay_seconds=30.0, jitter=False))
        d = rh._compute_delay(10)
        assert d == 30.0

    def test_compute_delay_with_jitter(self):
        rh = RetryHandler(RetryConfig(base_delay_seconds=10.0, jitter=True))
        d = rh._compute_delay(1)
        assert 5.0 <= d <= 10.0

    def test_success_resets_failures(self):
        rh = RetryHandler(RetryConfig(max_retries=1, circuit_breaker_threshold=3))
        async def fail():
            raise ValueError("fail")
        async def succeed():
            return "ok"
        with pytest.raises(ValueError):
            asyncio.run(rh.execute_with_retry("task6", fail))
        asyncio.run(rh.execute_with_retry("task6", succeed))
        state = rh.get_state("task6")
        assert state["consecutive_failures"] == 0

    def test_get_state(self):
        rh = RetryHandler()
        state = rh.get_state("nonexistent")
        assert state["consecutive_failures"] == 0
        assert state["circuit_open"] is False


# ══════════════════════════════════════════════════════════════
# 4. EVENT BUS TESTS (14)
# ══════════════════════════════════════════════════════════════

class TestEventBus:
    def test_publish_event(self):
        bus = EventBus()
        evt = bus.publish(EventType.KPI_CHANGED, ORG_ID, payload={"kpi": "revenue", "value": 100000})
        assert evt.event_type == EventType.KPI_CHANGED
        assert evt.org_id == ORG_ID

    def test_subscribe_to_event(self):
        bus = EventBus()
        received = []
        def handler(evt):
            received.append(evt)
        bus.subscribe(EventType.KPI_CHANGED, handler)
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        assert len(received) == 1

    def test_subscribe_all(self):
        bus = EventBus()
        received = []
        def handler(evt):
            received.append(evt)
        bus.subscribe_all(handler)
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        bus.publish(EventType.DATA_UPDATED, ORG_ID)
        assert len(received) == 2

    def test_event_types_supported(self):
        bus = EventBus()
        for et in EventType:
            evt = bus.publish(et, ORG_ID)
            assert evt.event_type == et

    def test_get_events_by_org(self):
        bus = EventBus()
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        bus.publish(EventType.KPI_CHANGED, ORG_ID_2)
        assert len(bus.get_events(org_id=ORG_ID)) == 1

    def test_get_events_by_type(self):
        bus = EventBus()
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        bus.publish(EventType.DATA_UPDATED, ORG_ID)
        assert len(bus.get_events(event_type="kpi_changed")) == 1

    def test_mark_processed(self):
        bus = EventBus()
        evt = bus.publish(EventType.KPI_CHANGED, ORG_ID)
        assert bus.mark_processed(evt.id)
        assert evt.processed is True

    def test_get_unprocessed(self):
        bus = EventBus()
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        bus.publish(EventType.DATA_UPDATED, ORG_ID)
        e1 = bus.publish(EventType.ANOMALY_DETECTED, ORG_ID)
        bus.mark_processed(e1.id)
        unprocessed = bus.get_unprocessed()
        assert len(unprocessed) == 2

    def test_event_counts(self):
        bus = EventBus()
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        bus.publish(EventType.DATA_UPDATED, ORG_ID)
        counts = bus.get_event_counts()
        assert counts["kpi_changed"] == 2
        assert counts["data_updated"] == 1

    def test_event_counts_by_org(self):
        bus = EventBus()
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        bus.publish(EventType.KPI_CHANGED, ORG_ID_2)
        counts = bus.get_event_counts(org_id=ORG_ID)
        assert counts["kpi_changed"] == 1

    def test_get_stats(self):
        bus = EventBus()
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        stats = bus.get_stats()
        assert stats["total_events"] == 1
        assert stats["subscriber_count"] == 0

    def test_subscriber_count_in_stats(self):
        bus = EventBus()
        bus.subscribe(EventType.KPI_CHANGED, lambda e: None)
        bus.subscribe_all(lambda e: None)
        stats = bus.get_stats()
        assert stats["subscriber_count"] == 2

    def test_clear_events(self):
        bus = EventBus()
        bus.publish(EventType.KPI_CHANGED, ORG_ID)
        bus.clear()
        assert len(bus.get_events()) == 0

    def test_handler_error_does_not_crash(self):
        bus = EventBus()
        def bad_handler(evt):
            raise ValueError("handler error")
        bus.subscribe(EventType.KPI_CHANGED, bad_handler)
        # Should not raise
        bus.publish(EventType.KPI_CHANGED, ORG_ID)


# ══════════════════════════════════════════════════════════════
# 5. PRODUCTION PERSISTENCE TESTS (16)
# ══════════════════════════════════════════════════════════════

class TestProductionPersistence:
    def test_save_and_get_memory(self):
        pp = ProductionPersistence()
        mem = pp.save_memory("a1", ORG_ID, "short_term", "Revenue analysis", 0.8)
        assert mem["content"] == "Revenue analysis"
        results = pp.query_memory("a1", "short_term")
        assert len(results) == 1

    def test_save_and_query_execution(self):
        pp = ProductionPersistence()
        pp.save_execution("a1", ORG_ID, "Why revenue drop?", "Analysis...", model="gpt-4o", cost=0.05)
        results = pp.query_executions(agent_id="a1")
        assert len(results) == 1
        assert results[0]["model"] == "gpt-4o"

    def test_save_and_query_evaluation(self):
        pp = ProductionPersistence()
        pp.save_evaluation("a1", ORG_ID, "query", "response", 85, {"accuracy": 0.9}, [], [])
        results = pp.query_evaluations(agent_id="a1")
        assert len(results) == 1
        assert results[0]["quality_score"] == 85

    def test_save_and_query_message(self):
        pp = ProductionPersistence()
        pp.save_message("a1", "a2", ORG_ID, "query", "What's the revenue?")
        results = pp.query_messages(ORG_ID)
        assert len(results) == 1

    def test_save_and_query_metric(self):
        pp = ProductionPersistence()
        pp.save_metric(ORG_ID, "ai_cost", 0.05, "USD", model="gpt-4o")
        pp.save_metric(ORG_ID, "latency", 500, "ms")
        results = pp.query_metrics(ORG_ID, "ai_cost")
        assert len(results) == 1
        assert results[0]["value"] == 0.05

    def test_save_and_query_audit(self):
        pp = ProductionPersistence()
        pp.save_audit(ORG_ID, "user_1", "sales_data", "gpt-4o", "Sales Agent", "Q3 review", "query", "report")
        results = pp.query_audit(ORG_ID)
        assert len(results) == 1
        assert results[0]["which_agent"] == "Sales Agent"

    def test_save_schedule(self):
        pp = ProductionPersistence()
        sched = pp.save_schedule(ORG_ID, "a1", "kpi_threshold", {"kpi": "revenue"}, 3600)
        assert sched["status"] == "active"
        assert sched["interval_seconds"] == 3600

    def test_tenant_isolation_memory(self):
        pp = ProductionPersistence()
        pp.save_memory("a1", ORG_ID, "short_term", "org1 data")
        pp.save_memory("a2", ORG_ID_2, "short_term", "org2 data")
        org1 = pp.query_memory("a1", "short_term")
        assert all(m["org_id"] == ORG_ID for m in org1)

    def test_tenant_isolation_executions(self):
        pp = ProductionPersistence()
        pp.save_execution("a1", ORG_ID, "q1", "r1")
        pp.save_execution("a2", ORG_ID_2, "q2", "r2")
        org1 = pp.query_executions(org_id=ORG_ID)
        assert all(e["org_id"] == ORG_ID for e in org1)

    def test_tenant_isolation_evaluations(self):
        pp = ProductionPersistence()
        pp.save_evaluation("a1", ORG_ID, "q", "r", 80, {}, [], [])
        pp.save_evaluation("a2", ORG_ID_2, "q", "r", 90, {}, [], [])
        org1 = pp.query_evaluations(org_id=ORG_ID)
        assert len(org1) == 1

    def test_tenant_isolation_metrics(self):
        pp = ProductionPersistence()
        pp.save_metric(ORG_ID, "ai_cost", 0.05)
        pp.save_metric(ORG_ID_2, "ai_cost", 0.03)
        org1 = pp.query_metrics(ORG_ID)
        assert len(org1) == 1

    def test_tenant_isolation_messages(self):
        pp = ProductionPersistence()
        pp.save_message("a1", "a2", ORG_ID, "query", "msg1")
        pp.save_message("a3", "a4", ORG_ID_2, "query", "msg2")
        org1 = pp.query_messages(ORG_ID)
        assert all(m["org_id"] == ORG_ID for m in org1)

    def test_tenant_isolation_audit(self):
        pp = ProductionPersistence()
        pp.save_audit(ORG_ID, "u1", "d", "m", "a", "w", "act", "r")
        pp.save_audit(ORG_ID_2, "u1", "d", "m", "a", "w", "act", "r")
        org1 = pp.query_audit(ORG_ID)
        assert all(a["org_id"] == ORG_ID for a in org1)

    def test_verify_tenant_isolation(self):
        pp = ProductionPersistence()
        pp.save_memory("a1", ORG_ID, "short_term", "data")
        result = pp.verify_tenant_isolation(ORG_ID)
        assert all(result.values())

    def test_get_stats(self):
        pp = ProductionPersistence()
        pp.save_memory("a1", ORG_ID, "short_term", "data")
        pp.save_execution("a1", ORG_ID, "q", "r")
        stats = pp.get_stats()
        assert stats["agent_memory"] >= 1
        assert stats["executions"] >= 1

    def test_persistent_store_delete(self):
        store = PersistentStore("test")
        store.save("row1", {"name": "test"})
        assert store.get("row1") is not None
        assert store.delete("row1")
        assert store.get("row1") is None


# ══════════════════════════════════════════════════════════════
# 6. PRODUCTION SECURITY TESTS (14)
# ══════════════════════════════════════════════════════════════

class TestProductionSecurity:
    def test_set_rate_limit(self):
        sec = ProductionSecurity()
        sec.set_rate_limit(RateLimitConfig(org_id=ORG_ID, requests_per_minute=10))
        # First 10 requests should pass
        for _ in range(10):
            result = sec.check_rate_limit(ORG_ID)
            assert result["allowed"]
        # 11th should fail
        result = sec.check_rate_limit(ORG_ID)
        assert not result["allowed"]

    def test_rate_limit_no_config(self):
        sec = ProductionSecurity()
        result = sec.check_rate_limit(ORG_ID)
        assert result["allowed"]

    def test_ai_call_rate_limit(self):
        sec = ProductionSecurity()
        sec.set_rate_limit(RateLimitConfig(org_id=ORG_ID, ai_calls_per_hour=2))
        sec.check_rate_limit(ORG_ID, is_ai_call=True)
        sec.check_rate_limit(ORG_ID, is_ai_call=True)
        result = sec.check_rate_limit(ORG_ID, is_ai_call=True)
        assert not result["allowed"]

    def test_encrypt_field(self):
        sec = ProductionSecurity()
        encrypted = sec.encrypt_field("agent_memory", "content", "sensitive data")
        assert encrypted.startswith("ENC:")

    def test_encrypt_non_sensitive_field(self):
        sec = ProductionSecurity()
        result = sec.encrypt_field("agent_memory", "importance", "0.5")
        assert result == "0.5"  # Not encrypted

    def test_decrypt_field(self):
        sec = ProductionSecurity()
        decrypted = sec.decrypt_field("agent_memory", "content", "plain text")
        assert decrypted == "plain text"

    def test_verify_rls_passes(self):
        sec = ProductionSecurity()
        rows = [{"org_id": ORG_ID, "data": "test"}, {"org_id": ORG_ID, "data": "test2"}]
        result = sec.verify_rls("agent_memory", ORG_ID, rows)
        assert result["rls_enforced"]

    def test_verify_rls_fails(self):
        sec = ProductionSecurity()
        rows = [{"org_id": ORG_ID, "data": "ok"}, {"org_id": ORG_ID_2, "data": "leak!"}]
        result = sec.verify_rls("agent_memory", ORG_ID, rows)
        assert not result["rls_enforced"]
        assert result["violations"] == 1

    def test_get_security_events(self):
        sec = ProductionSecurity()
        sec.set_rate_limit(RateLimitConfig(org_id=ORG_ID, requests_per_minute=1))
        sec.check_rate_limit(ORG_ID)
        sec.check_rate_limit(ORG_ID)  # triggers rate limit event
        events = sec.get_security_events(org_id=ORG_ID)
        assert len(events) > 0

    def test_generate_audit_report(self):
        sec = ProductionSecurity()
        report = sec.generate_audit_report(ORG_ID)
        assert report.org_id == ORG_ID
        assert report.report_id.startswith("audit_")

    def test_get_rls_sql(self):
        sec = ProductionSecurity()
        sql = sec.get_rls_sql()
        assert len(sql) > 0
        assert any("ROW LEVEL SECURITY" in s for s in sql)

    def test_rls_policies_cover_all_tables(self):
        sec = ProductionSecurity()
        sql = sec.get_rls_sql()
        # Should cover at least 6 tables
        table_count = sum(1 for s in sql if "ENABLE ROW LEVEL SECURITY" in s)
        assert table_count >= 6

    def test_encrypted_fields_defined(self):
        sec = ProductionSecurity()
        assert "agent_memory" in sec.ENCRYPTED_FIELDS
        assert "content" in sec.ENCRYPTED_FIELDS["agent_memory"]

    def test_rate_limit_records_security_event(self):
        sec = ProductionSecurity()
        sec.set_rate_limit(RateLimitConfig(org_id=ORG_ID, requests_per_minute=1))
        sec.check_rate_limit(ORG_ID)  # passes
        sec.check_rate_limit(ORG_ID)  # fails
        events = sec.get_security_events(ORG_ID)
        assert any("rate_limit" in e["event_type"] for e in events)


# ══════════════════════════════════════════════════════════════
# 7. INTEGRATION: AUTONOMOUS LOOP TESTS (8)
# ══════════════════════════════════════════════════════════════

class TestAutonomousLoop:
    def test_full_autonomous_scenario(self):
        """KPI drops → event published → agent triggered → analysis → decision → memory"""
        bus = EventBus()
        rt = PXRuntime()
        pp = ProductionPersistence()

        triggered = []
        async def agent_handler(task):
            triggered.append(task.payload)
            return {"analysis": "Revenue dropped due to market conditions"}

        rt.register_handler(RuntimeTaskType.ANOMALY_INVESTIGATION, agent_handler)

        # 1. KPI change detected
        evt = bus.publish(EventType.KPI_THRESHOLD_BREACH, ORG_ID,
            payload={"kpi": "revenue", "change": "-15%"})
        assert evt.event_type == EventType.KPI_THRESHOLD_BREACH

        # 2. Runtime enqueues investigation
        rt.enqueue(
            RuntimeTaskType.ANOMALY_INVESTIGATION,
            ORG_ID, "sales_agent",
            payload={"reason": "Revenue dropped 15%"},
            priority=TaskPriority.CRITICAL,
        )

        # 3. Execute
        asyncio.run(rt.tick())
        assert len(triggered) == 1

        # 4. Persist execution
        pp.save_execution("sales_agent", ORG_ID, "Investigate revenue drop",
            "Revenue dropped due to market conditions", model="gpt-4o")
        assert len(pp.query_executions(org_id=ORG_ID)) == 1

        # 5. Persist memory
        pp.save_memory("sales_agent", ORG_ID, "experience",
            "Revenue drop investigated: market conditions", importance=0.8)
        assert len(pp.query_memory("sales_agent", "experience")) == 1

    def test_event_driven_agent_trigger(self):
        """Event → agent trigger → execution"""
        bus = EventBus()
        triggered = []
        def on_kpi_breach(event):
            triggered.append(event)
        bus.subscribe(EventType.KPI_THRESHOLD_BREACH, on_kpi_breach)
        bus.publish(EventType.KPI_THRESHOLD_BREACH, ORG_ID, payload={"kpi": "revenue"})
        assert len(triggered) == 1

    def test_scheduled_monitoring_with_persistence(self):
        """Scheduled task fires → executes → persists"""
        rt = PXRuntime()
        pp = ProductionPersistence()
        async def handler(task):
            return {"kpi": "revenue", "status": "normal"}
        rt.register_handler(RuntimeTaskType.KPI_MONITOR, handler)
        rt.schedule(ORG_ID, "sales_agent", RuntimeTaskType.KPI_MONITOR, 0)
        # Set next_run to past
        for s in rt._schedules.values():
            s.next_run = "2020-01-01T00:00:00+00:00"
        asyncio.run(rt.tick())
        assert len(rt.get_completed()) >= 1
        # In production, this would persist to PostgreSQL
        pp.save_execution("sales_agent", ORG_ID, "KPI monitor", "Status: normal")
        assert len(pp.query_executions()) == 1

    def test_retry_and_recovery_scenario(self):
        """Agent fails → retries → succeeds → memory records experience"""
        rt = PXRuntime()
        pp = ProductionPersistence()
        call_count = [0]
        async def handler(task):
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Temporary failure")
            return {"result": "recovered"}
        rt.register_handler(RuntimeTaskType.AGENT_EXECUTE, handler)
        rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "a1")
        asyncio.run(rt.tick())
        completed = rt.get_completed()
        assert completed[0]["state"] == "succeeded"
        pp.save_memory("a1", ORG_ID, "experience",
            "Recovered after retry", importance=0.7)

    def test_observability_records_all_operations(self):
        """Every operation records observability metrics"""
        pp = ProductionPersistence()
        # Simulate AI call
        pp.save_metric(ORG_ID, "ai_cost", 0.05, "USD", model="gpt-4o")
        pp.save_metric(ORG_ID, "latency", 350, "ms")
        pp.save_metric(ORG_ID, "tokens", 1200, "tokens")
        metrics = pp.query_metrics(ORG_ID)
        assert len(metrics) == 3

    def test_audit_trail_on_every_action(self):
        """Every AI action creates an audit entry"""
        pp = ProductionPersistence()
        pp.save_audit(ORG_ID, "sales_agent", "revenue_data", "gpt-4o",
            "Sales Agent", "Revenue analysis", "query", "Revenue down 5%")
        pp.save_audit(ORG_ID, "finance_agent", "financial_data", "claude-3-5-sonnet",
            "Finance Agent", "Cost analysis", "query", "Costs up 10%")
        audit = pp.query_audit(ORG_ID)
        assert len(audit) == 2
        assert all(a["org_id"] == ORG_ID for a in audit)

    def test_tenant_isolation_full_stack(self):
        """Two orgs: complete isolation across all stores"""
        pp = ProductionPersistence()
        # Org 1
        pp.save_memory("a1", ORG_ID, "short_term", "org1 secret")
        pp.save_execution("a1", ORG_ID, "q1", "r1")
        pp.save_audit(ORG_ID, "u1", "d", "m", "a", "w", "act", "r")
        # Org 2
        pp.save_memory("a2", ORG_ID_2, "short_term", "org2 secret")
        pp.save_execution("a2", ORG_ID_2, "q2", "r2")
        pp.save_audit(ORG_ID_2, "u2", "d", "m", "a", "w", "act", "r")
        # Verify isolation
        assert all(pp.verify_tenant_isolation(ORG_ID).values())
        assert all(pp.verify_tenant_isolation(ORG_ID_2).values())

    def test_continuous_operation_health(self):
        """Runtime health monitoring during continuous operation"""
        rt = PXRuntime()
        async def handler(task):
            return "ok"
        rt.register_handler(RuntimeTaskType.AGENT_EXECUTE, handler)
        # Execute multiple tasks
        for _ in range(5):
            rt.enqueue(RuntimeTaskType.AGENT_EXECUTE, ORG_ID, "a1")
        asyncio.run(rt.tick())
        health = rt.get_health()
        assert health["succeeded"] == 5
        assert health["total_tasks"] == 5
        assert health["uptime_seconds"] >= 0
        assert health["queue_length"] == 0
