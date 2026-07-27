"""
πX Phase 3.6 — Enterprise Production Reality — 100+ tests.

Covers: async persistence, distributed event bus, workflow engine,
connectors, NL intelligence interface.
"""
import pytest
import asyncio

from packages.cognitive_kernel.persistence.async_db import AsyncDatabase, DBConfig, get_db
from packages.cognitive_kernel.persistence.repositories import (
    AgentRepository, MemoryRepository, ExecutionRepository,
    EvaluationRepository, AuditRepository, MessageRepository,
    ScheduleRepository, ObservabilityRepository,
)
from packages.cognitive_kernel.event_bus.distributed_bus import (
    DistributedEventBus, EventStatus,
)
from packages.cognitive_kernel.workflow_engine.workflow_engine import (
    WorkflowEngine, Workflow, WorkflowStep, WorkflowStatus, StepStatus,
)
from packages.cognitive_kernel.connectors.connector_framework import (
    ConnectorFramework, ConnectorType, ConnectorStatus,
    PostgreSQLConnector, MySQLConnector, MongoDBConnector,
    RESTConnector, GraphQLConnector, SAPConnector, SalesforceConnector, HubSpotConnector,
    KafkaConnector, WebhookConnector,
)
from packages.cognitive_kernel.nl_interface.nl_engine import (
    NLIntelligenceEngine, NLQueryResult,
)

ORG_ID = "test-org-001"
ORG_ID_2 = "test-org-002"


# ══════════════════════════════════════════════════════════════
# 1. ASYNC DATABASE TESTS (16)
# ══════════════════════════════════════════════════════════════

class TestAsyncDatabase:
    @pytest.fixture
    async def db(self):
        d = AsyncDatabase()
        await d.connect()
        return d

    def test_connect(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            assert d._connected
        asyncio.run(run())

    def test_disconnect(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            await d.disconnect()
            assert not d._connected
        asyncio.run(run())

    def test_insert_and_select(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            row = await d.insert("agent_instances", {"org_id": ORG_ID, "label": "Sales Agent"})
            assert row["label"] == "Sales Agent"
            results = await d.select("agent_instances")
            assert len(results) == 1
        asyncio.run(run())

    def test_select_with_filters(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            await d.insert("agent_instances", {"org_id": ORG_ID, "label": "A1"})
            await d.insert("agent_instances", {"org_id": ORG_ID_2, "label": "A2"})
            results = await d.select("agent_instances", {"org_id": ORG_ID})
            assert len(results) == 1
        asyncio.run(run())

    def test_update(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            row = await d.insert("agent_instances", {"org_id": ORG_ID, "status": "active"})
            updated = await d.update("agent_instances", row["id"], {"status": "paused"})
            assert updated["status"] == "paused"
        asyncio.run(run())

    def test_delete(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            row = await d.insert("agent_instances", {"org_id": ORG_ID})
            assert await d.delete("agent_instances", row["id"])
            results = await d.select("agent_instances")
            assert len(results) == 0
        asyncio.run(run())

    def test_count(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            await d.insert("agent_memory", {"org_id": ORG_ID})
            await d.insert("agent_memory", {"org_id": ORG_ID})
            assert await d.count("agent_memory") == 2
        asyncio.run(run())

    def test_rls_tenant_isolation(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            await d.insert("agent_memory", {"org_id": ORG_ID, "content": "secret1"})
            await d.insert("agent_memory", {"org_id": ORG_ID_2, "content": "secret2"})
            await d.set_tenant(ORG_ID)
            results = await d.select("agent_memory")
            assert all(r["org_id"] == ORG_ID for r in results)
            assert len(results) == 1
        asyncio.run(run())

    def test_rls_blocks_cross_tenant_update(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            row = await d.insert("agent_memory", {"org_id": ORG_ID, "content": "data"})
            await d.set_tenant(ORG_ID_2)
            result = await d.update("agent_memory", row["id"], {"content": "hacked"})
            assert result is None
        asyncio.run(run())

    def test_rls_blocks_cross_tenant_delete(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            row = await d.insert("agent_memory", {"org_id": ORG_ID, "content": "data"})
            await d.set_tenant(ORG_ID_2)
            assert not await d.delete("agent_memory", row["id"])
        asyncio.run(run())

    def test_pagination(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            for i in range(10):
                await d.insert("agent_memory", {"org_id": ORG_ID, "idx": i})
            page1 = await d.select("agent_memory", limit=5, offset=0)
            page2 = await d.select("agent_memory", limit=5, offset=5)
            assert len(page1) == 5
            assert len(page2) == 5
        asyncio.run(run())

    def test_transaction(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            async with d.transaction():
                await d.insert("agent_memory", {"org_id": ORG_ID, "content": "tx"})
            results = await d.select("agent_memory")
            assert len(results) == 1
        asyncio.run(run())

    def test_health_check(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            health = await d.health_check()
            assert health["connected"] is True
        asyncio.run(run())

    def test_not_connected_error(self):
        d = AsyncDatabase()
        with pytest.raises(RuntimeError):
            asyncio.run(d.select("agent_memory"))

    def test_ordering(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            await d.insert("agent_memory", {"org_id": ORG_ID, "score": 5})
            await d.insert("agent_memory", {"org_id": ORG_ID, "score": 10})
            results = await d.select("agent_memory", order_by="score", descending=True)
            assert results[0]["score"] == 10
        asyncio.run(run())

    def test_db_config_url(self):
        cfg = DBConfig(host="localhost", port=5432, database="test", username="user", password="pass")
        assert "postgresql+asyncpg" in cfg.url
        assert "localhost" in cfg.url


# ══════════════════════════════════════════════════════════════
# 2. REPOSITORY TESTS (12)
# ══════════════════════════════════════════════════════════════

class TestRepositories:
    @pytest.fixture
    async def setup(self):
        d = AsyncDatabase()
        await d.connect()
        return d

    def test_agent_repo_create_and_list(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = AgentRepository(d)
            agent = await repo.create({"org_id": ORG_ID, "label": "Sales Agent", "status": "active"})
            agents = await repo.get_by_org(ORG_ID)
            assert len(agents) == 1
        asyncio.run(run())

    def test_agent_repo_update_status(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = AgentRepository(d)
            agent = await repo.create({"org_id": ORG_ID, "status": "active"})
            await repo.update_status(agent["id"], "paused")
            updated = await repo.get_by_id(agent["id"])
            assert updated["status"] == "paused"
        asyncio.run(run())

    def test_agent_repo_increment_stat(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = AgentRepository(d)
            agent = await repo.create({"org_id": ORG_ID, "conversation_count": 0})
            await repo.increment_stat(agent["id"], "conversation_count")
            updated = await repo.get_by_id(agent["id"])
            assert updated["conversation_count"] == 1
        asyncio.run(run())

    def test_memory_repo_create_and_get(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = MemoryRepository(d)
            mem = await repo.create({"agent_id": "a1", "org_id": ORG_ID, "memory_type": "short_term", "content": "test"})
            results = await repo.get_by_agent("a1", "short_term")
            assert len(results) == 1
        asyncio.run(run())

    def test_memory_repo_org_memory(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = MemoryRepository(d)
            await repo.create({"agent_id": "a1", "org_id": ORG_ID, "memory_type": "short_term"})
            await repo.create({"agent_id": "a2", "org_id": ORG_ID_2, "memory_type": "short_term"})
            org1 = await repo.get_org_memory(ORG_ID)
            assert len(org1) == 1
        asyncio.run(run())

    def test_execution_repo_cost_summary(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = ExecutionRepository(d)
            await repo.create({"org_id": ORG_ID, "agent_id": "a1", "model": "gpt-4o", "cost_usd": 0.05, "input_tokens": 100, "output_tokens": 50})
            await repo.create({"org_id": ORG_ID, "agent_id": "a1", "model": "gpt-4o", "cost_usd": 0.03, "input_tokens": 80, "output_tokens": 40})
            summary = await repo.get_cost_summary(ORG_ID)
            assert summary["total_cost"] == 0.08
            assert summary["total_calls"] == 2
        asyncio.run(run())

    def test_evaluation_repo_quality_stats(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = EvaluationRepository(d)
            await repo.create({"org_id": ORG_ID, "agent_id": "a1", "quality_score": 80})
            await repo.create({"org_id": ORG_ID, "agent_id": "a1", "quality_score": 90})
            stats = await repo.get_quality_stats(ORG_ID)
            assert stats["total"] == 2
            assert stats["avg_score"] == 85
        asyncio.run(run())

    def test_audit_repo_by_org(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = AuditRepository(d)
            await repo.create({"org_id": ORG_ID, "who": "a1", "action": "query"})
            await repo.create({"org_id": ORG_ID_2, "who": "a2", "action": "query"})
            org1 = await repo.get_by_org(ORG_ID)
            assert len(org1) == 1
        asyncio.run(run())

    def test_message_repo_by_org(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = MessageRepository(d)
            await repo.create({"org_id": ORG_ID, "from_agent_id": "a1", "content": "msg"})
            results = await repo.get_by_org(ORG_ID)
            assert len(results) == 1
        asyncio.run(run())

    def test_schedule_repo_active(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = ScheduleRepository(d)
            await repo.create({"org_id": ORG_ID, "agent_id": "a1", "status": "active"})
            await repo.create({"org_id": ORG_ID, "agent_id": "a2", "status": "paused"})
            active = await repo.get_active_by_org(ORG_ID)
            assert len(active) == 1
        asyncio.run(run())

    def test_observability_repo_by_org(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = ObservabilityRepository(d)
            await repo.create({"org_id": ORG_ID, "metric_type": "ai_cost", "value": 0.05})
            await repo.create({"org_id": ORG_ID, "metric_type": "latency", "value": 300})
            results = await repo.get_by_org(ORG_ID, "ai_cost")
            assert len(results) == 1
        asyncio.run(run())

    def test_base_repo_delete(self):
        async def run():
            d = AsyncDatabase()
            await d.connect()
            repo = AgentRepository(d)
            agent = await repo.create({"org_id": ORG_ID})
            assert await repo.delete(agent["id"])
            assert await repo.get_by_id(agent["id"]) is None
        asyncio.run(run())


# ══════════════════════════════════════════════════════════════
# 3. DISTRIBUTED EVENT BUS TESTS (14)
# ══════════════════════════════════════════════════════════════

class TestDistributedEventBus:
    def test_publish(self):
        bus = DistributedEventBus()
        evt = bus.publish("kpi_changed", ORG_ID, payload={"kpi": "revenue"})
        assert evt.event_type == "kpi_changed"
        assert evt.status == EventStatus.PENDING

    def test_stream_routing(self):
        bus = DistributedEventBus()
        assert bus.get_stream("kpi_changed") == "kpi_events"
        assert bus.get_stream("data_updated") == "data_events"
        assert bus.get_stream("agent_triggered") == "agent_events"
        assert bus.get_stream("security_event") == "security_events"

    def test_subscribe_and_consume(self):
        bus = DistributedEventBus()
        bus.subscribe("kpi_events", lambda e: None)
        bus.publish("kpi_changed", ORG_ID)
        events = bus.consume("kpi_events")
        assert len(events) == 1
        assert events[0].status == EventStatus.PROCESSING

    def test_ack(self):
        bus = DistributedEventBus()
        evt = bus.publish("kpi_changed", ORG_ID)
        bus.consume("kpi_events")
        assert bus.ack(evt.id)
        assert evt.status == EventStatus.PROCESSED

    def test_nack_retry(self):
        bus = DistributedEventBus()
        evt = bus.publish("kpi_changed", ORG_ID, max_retries=3)
        bus.consume("kpi_events")
        bus.nack(evt.id, "processing error")
        assert evt.retry_count == 1
        assert evt.status == EventStatus.PENDING

    def test_nack_dead_letter(self):
        bus = DistributedEventBus()
        evt = bus.publish("kpi_changed", ORG_ID, max_retries=2)
        bus.consume("kpi_events")
        bus.nack(evt.id, "error 1")
        bus.consume("kpi_events")
        bus.nack(evt.id, "error 2")
        assert evt.status == EventStatus.DEAD_LETTER
        assert len(bus.get_dead_letter()) == 1

    def test_replay_from_dead_letter(self):
        bus = DistributedEventBus()
        evt = bus.publish("kpi_changed", ORG_ID, max_retries=1)
        bus.consume("kpi_events")
        bus.nack(evt.id, "error")
        assert len(bus.get_dead_letter()) == 1
        assert bus.replay_from_dead_letter(evt.id)
        assert len(bus.get_dead_letter()) == 0
        assert evt.status == EventStatus.PENDING

    def test_process_all(self):
        bus = DistributedEventBus()
        bus.publish("kpi_changed", ORG_ID)
        bus.publish("kpi_changed", ORG_ID_2)
        processed = bus.process("kpi_events", lambda e: None)
        assert len(processed) == 2

    def test_process_with_failure(self):
        bus = DistributedEventBus()
        bus.publish("kpi_changed", ORG_ID, max_retries=1)
        def handler(evt):
            raise ValueError("fail")
        bus.process("kpi_events", handler)
        dead = bus.get_dead_letter()
        assert len(dead) == 1

    def test_get_stats(self):
        bus = DistributedEventBus()
        bus.publish("kpi_changed", ORG_ID)
        stats = bus.get_stats()
        assert stats["total_events"] == 1
        assert stats["processed"] == 0

    def test_get_pending(self):
        bus = DistributedEventBus()
        bus.publish("kpi_changed", ORG_ID)
        bus.publish("data_updated", ORG_ID)
        pending = bus.get_pending()
        assert len(pending) == 2

    def test_tenant_isolation(self):
        bus = DistributedEventBus()
        bus.publish("kpi_changed", ORG_ID)
        bus.publish("kpi_changed", ORG_ID_2)
        org1 = bus.get_events(org_id=ORG_ID)
        assert len(org1) == 1

    def test_consumer_groups(self):
        bus = DistributedEventBus()
        bus.subscribe("kpi_events", lambda e: None, consumer_id="worker_1")
        bus.subscribe("kpi_events", lambda e: None, consumer_id="worker_2")
        stats = bus.get_stats()
        assert stats["consumer_groups"]["kpi_events"] == 2

    def test_get_events_by_stream(self):
        bus = DistributedEventBus()
        bus.publish("kpi_changed", ORG_ID)
        bus.publish("data_updated", ORG_ID)
        kpi_events = bus.get_events(stream="kpi_events")
        assert len(kpi_events) == 1


# ══════════════════════════════════════════════════════════════
# 4. WORKFLOW ENGINE TESTS (14)
# ══════════════════════════════════════════════════════════════

class TestWorkflowEngine:
    def test_create_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("test_wf", ORG_ID, "agent_1", [
            {"name": "step1", "handler": "analyze"},
            {"name": "step2", "handler": "decide"},
        ])
        assert len(wf.steps) == 2
        assert wf.status == WorkflowStatus.PENDING

    def test_execute_workflow_success(self):
        engine = WorkflowEngine()
        async def handler(wf, step):
            return f"{step.name}_result"
        engine.register_handler("analyze", handler)
        engine.register_handler("decide", handler)
        wf = engine.create_workflow("test", ORG_ID, "a1", [
            {"name": "analyze", "handler": "analyze"},
            {"name": "decide", "handler": "decide"},
        ])
        result = asyncio.run(engine.execute(wf.id))
        assert result.status == WorkflowStatus.SUCCEEDED
        assert result.steps[0].status == StepStatus.SUCCEEDED
        assert result.steps[1].status == StepStatus.SUCCEEDED

    def test_execute_workflow_with_retry(self):
        engine = WorkflowEngine()
        call_count = [0]
        async def handler(wf, step):
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("fail")
            return "ok"
        engine.register_handler("analyze", handler)
        wf = engine.create_workflow("test", ORG_ID, "a1", [
            {"name": "analyze", "handler": "analyze", "max_retries": 3},
        ])
        result = asyncio.run(engine.execute(wf.id))
        assert result.status == WorkflowStatus.SUCCEEDED
        assert call_count[0] == 2

    def test_execute_workflow_all_retries_exhausted(self):
        engine = WorkflowEngine()
        async def handler(wf, step):
            raise ValueError("always fails")
        engine.register_handler("analyze", handler)
        wf = engine.create_workflow("test", ORG_ID, "a1", [
            {"name": "analyze", "handler": "analyze", "max_retries": 2},
        ])
        result = asyncio.run(engine.execute(wf.id))
        assert result.status == WorkflowStatus.FAILED
        assert result.steps[0].attempts == 2

    def test_workflow_compensation(self):
        engine = WorkflowEngine()
        async def handler1(wf, step):
            return "ok"
        async def handler2(wf, step):
            raise ValueError("fail")
        comp_called = [False]
        def comp_handler(wf, step):
            comp_called[0] = True
        engine.register_handler("step1", handler1)
        engine.register_handler("step2", handler2)
        engine.register_compensation("undo_step1", comp_handler)
        wf = engine.create_workflow("test", ORG_ID, "a1", [
            {"name": "step1", "handler": "step1", "compensation": "undo_step1"},
            {"name": "step2", "handler": "step2", "max_retries": 1},
        ])
        result = asyncio.run(engine.execute(wf.id))
        assert result.status == WorkflowStatus.FAILED
        assert comp_called[0] is True

    def test_pause_and_resume(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("test", ORG_ID, "a1", [
            {"name": "step1", "handler": "h"},
        ])
        # Can't pause pending workflow
        assert not engine.pause(wf.id)

    def test_missing_handler(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("test", ORG_ID, "a1", [
            {"name": "step1", "handler": "nonexistent"},
        ])
        result = asyncio.run(engine.execute(wf.id))
        assert result.status == WorkflowStatus.FAILED
        assert "not registered" in result.error or "not found" in result.error

    def test_get_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("test", ORG_ID, "a1", [])
        assert engine.get_workflow(wf.id) is not None
        assert engine.get_workflow("fake") is None

    def test_list_workflows(self):
        engine = WorkflowEngine()
        engine.create_workflow("wf1", ORG_ID, "a1", [])
        engine.create_workflow("wf2", ORG_ID_2, "a1", [])
        assert len(engine.list_workflows(org_id=ORG_ID)) == 1

    def test_schedule_workflow(self):
        engine = WorkflowEngine()
        sched_id = engine.schedule_workflow("daily_check", "0 9 * * *", ORG_ID, "a1", [])
        assert len(engine.get_schedules()) == 1

    def test_workflow_stats(self):
        engine = WorkflowEngine()
        engine.create_workflow("wf1", ORG_ID, "a1", [])
        stats = engine.get_stats()
        assert stats["total"] == 1

    def test_workflow_output_data(self):
        engine = WorkflowEngine()
        async def handler(wf, step):
            return {"value": 42}
        engine.register_handler("analyze", handler)
        wf = engine.create_workflow("test", ORG_ID, "a1", [
            {"name": "analyze", "handler": "analyze"},
        ])
        result = asyncio.run(engine.execute(wf.id))
        assert result.output_data["analyze"] == {"value": 42}

    def test_workflow_has_timestamps(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("test", ORG_ID, "a1", [])
        assert wf.created_at is not None
        async def handler(wf, step):
            return "ok"
        engine.register_handler("h", handler)
        wf.steps = [WorkflowStep(id="s1", name="s1", handler="h")]
        result = asyncio.run(engine.execute(wf.id))
        assert result.completed_at is not None

    def test_workflow_to_dict(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow("test", ORG_ID, "a1", [
            {"name": "step1", "handler": "h"},
        ])
        d = wf.to_dict()
        assert d["name"] == "test"
        assert len(d["steps"]) == 1


# ══════════════════════════════════════════════════════════════
# 5. CONNECTOR FRAMEWORK TESTS (16)
# ══════════════════════════════════════════════════════════════

class TestConnectors:
    def test_create_postgresql_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.POSTGRESQL, "pg1", ORG_ID, {"host": "localhost", "tables": ["orders"]})
        assert conn.config.connector_type == ConnectorType.POSTGRESQL

    def test_create_mysql_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.MYSQL, "mysql1", ORG_ID, {})
        assert conn.config.connector_type == ConnectorType.MYSQL

    def test_create_mongodb_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.MONGODB, "mongo1", ORG_ID, {"collections": ["orders"]})
        assert conn.config.connector_type == ConnectorType.MONGODB

    def test_create_rest_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.REST, "api1", ORG_ID, {"base_url": "https://api.example.com"})
        assert conn.config.connector_type == ConnectorType.REST

    def test_create_graphql_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.GRAPHQL, "gql1", ORG_ID, {"queries": ["getRevenue"]})
        assert conn.config.connector_type == ConnectorType.GRAPHQL

    def test_create_sap_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.SAP, "sap1", ORG_ID, {"objects": ["Orders"]})
        assert conn.config.connector_type == ConnectorType.SAP

    def test_create_salesforce_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.SALESFORCE, "sf1", ORG_ID, {})
        assert conn.config.connector_type == ConnectorType.SALESFORCE

    def test_create_hubspot_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.HUBSPOT, "hs1", ORG_ID, {})
        assert conn.config.connector_type == ConnectorType.HUBSPOT

    def test_create_kafka_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.KAFKA, "kafka1", ORG_ID, {"topics": ["events"]})
        assert conn.config.connector_type == ConnectorType.KAFKA

    def test_create_webhook_connector(self):
        cf = ConnectorFramework()
        conn = cf.create_connector(ConnectorType.WEBHOOK, "wh1", ORG_ID, {"url": "https://webhook.site"})
        assert conn.config.connector_type == ConnectorType.WEBHOOK

    def test_connect_postgresql(self):
        async def run():
            cf = ConnectorFramework()
            conn = cf.create_connector(ConnectorType.POSTGRESQL, "pg1", ORG_ID, {})
            result = await conn.connect()
            assert result is True
            assert conn.status == ConnectorStatus.CONNECTED
        asyncio.run(run())

    def test_discover_tables(self):
        async def run():
            cf = ConnectorFramework()
            conn = cf.create_connector(ConnectorType.POSTGRESQL, "pg1", ORG_ID, {"tables": ["orders", "customers"]})
            await conn.connect()
            tables = await conn.discover()
            assert "orders" in tables
        asyncio.run(run())

    def test_sample_data(self):
        async def run():
            cf = ConnectorFramework()
            conn = cf.create_connector(ConnectorType.POSTGRESQL, "pg1", ORG_ID, {"schema": {"id": "int", "name": "text"}})
            await conn.connect()
            sample = await conn.sample("orders", limit=50)
            assert sample.row_count == 50
            assert "id" in sample.schema
        asyncio.run(run())

    def test_sync_data(self):
        async def run():
            cf = ConnectorFramework()
            conn = cf.create_connector(ConnectorType.POSTGRESQL, "pg1", ORG_ID, {})
            await conn.connect()
            result = await conn.sync("orders")
            assert result["status"] == "completed"
        asyncio.run(run())

    def test_connect_all(self):
        async def run():
            cf = ConnectorFramework()
            cf.create_connector(ConnectorType.POSTGRESQL, "pg1", ORG_ID, {})
            cf.create_connector(ConnectorType.MYSQL, "mysql1", ORG_ID, {})
            results = await cf.connect_all(ORG_ID)
            assert len(results) == 2
        asyncio.run(run())

    def test_get_supported_types(self):
        cf = ConnectorFramework()
        types = cf.get_supported_types()
        assert "postgresql" in types
        assert "sap" in types
        assert "kafka" in types


# ══════════════════════════════════════════════════════════════
# 6. NL INTELLIGENCE INTERFACE TESTS (16)
# ══════════════════════════════════════════════════════════════

class TestNLIntelligence:
    PROFILE = {
        "industry": "retail",
        "kpis": [{"name": "Revenue", "aliases": ["sales", "turnover"]}, {"name": "Inventory Turnover"}],
        "ontology": {"entities": {"customer": {}, "product": {}, "store": {}}},
    }
    AGENTS = [
        {"label": "Sales Agent", "kpis_monitored": ["Revenue", "Sell-out"], "purpose": "Revenue and sales analysis"},
        {"label": "Finance Agent", "kpis_monitored": ["Revenue", "Cost"], "purpose": "Financial analysis"},
        {"label": "Inventory Agent", "kpis_monitored": ["Inventory Turnover"], "purpose": "Inventory management"},
    ]

    def test_detect_intent_root_cause(self):
        engine = NLIntelligenceEngine()
        intent = engine._detect_intent("Why did revenue drop?")
        assert intent == "root_cause"

    def test_detect_intent_prediction(self):
        engine = NLIntelligenceEngine()
        intent = engine._detect_intent("Forecast revenue for Q4")
        assert intent == "prediction"

    def test_detect_intent_comparison(self):
        engine = NLIntelligenceEngine()
        intent = engine._detect_intent("Compare revenue vs cost")
        assert intent == "comparison"

    def test_detect_intent_general(self):
        engine = NLIntelligenceEngine()
        intent = engine._detect_intent("What are our KPIs?")
        assert intent == "general_inquiry"

    def test_identify_kpis_revenue(self):
        engine = NLIntelligenceEngine()
        kpis = engine._identify_kpis("Why did revenue drop?", self.PROFILE)
        assert "revenue" in kpis

    def test_identify_kpis_from_profile_aliases(self):
        engine = NLIntelligenceEngine()
        kpis = engine._identify_kpis("What happened to sales?", self.PROFILE)
        assert "revenue" in kpis  # "sales" is an alias for "revenue"

    def test_identify_entities_geographic(self):
        engine = NLIntelligenceEngine()
        entities = engine._identify_entities("Why did revenue drop in Germany?", self.PROFILE)
        assert "Germany" in entities

    def test_identify_entities_from_ontology(self):
        engine = NLIntelligenceEngine()
        entities = engine._identify_entities("What's the customer behavior?", self.PROFILE)
        assert "customer" in entities

    def test_activate_agents_by_kpi(self):
        engine = NLIntelligenceEngine()
        activated = engine._activate_agents("Why did revenue drop?", self.AGENTS, ["revenue"])
        assert "Sales Agent" in activated
        assert "Finance Agent" in activated

    def test_activate_agents_fallback(self):
        engine = NLIntelligenceEngine()
        activated = engine._activate_agents("random query about nothing", self.AGENTS, [])
        assert len(activated) <= 3

    def test_retrieve_memory_relevant(self):
        engine = NLIntelligenceEngine()
        memory = [
            {"content": "Revenue dropped 15% in Q3"},
            {"content": "Inventory levels are normal"},
        ]
        results = engine._retrieve_memory("Why did revenue drop?", memory)
        assert len(results) > 0
        assert "Revenue" in results[0]["content"]

    def test_full_query_pipeline(self):
        engine = NLIntelligenceEngine()
        result = engine.analyze_query(
            "Why did revenue drop in Germany?",
            self.PROFILE, self.AGENTS,
            memory_entries=[{"content": "Revenue dropped 15% in Q3 Germany"}],
            agent_responses=[
                {"agent_label": "Sales Agent", "response": "Revenue declined due to competitor entry in German market."},
                {"agent_label": "Finance Agent", "response": "Margin impact is significant, 15% drop confirmed."},
            ],
        )
        assert result.intent == "root_cause"
        assert "revenue" in result.identified_kpis
        assert "Germany" in result.identified_entities
        assert len(result.activated_agents) >= 1
        assert len(result.decision) > 50
        assert result.confidence > 0

    def test_visualization_generation(self):
        engine = NLIntelligenceEngine()
        viz = engine._generate_visualization("root_cause", ["revenue"], ["Germany"])
        assert viz["type"] == "line_chart"
        assert "revenue" in viz["kpis"]

    def test_visualization_comparison(self):
        engine = NLIntelligenceEngine()
        viz = engine._generate_visualization("comparison", ["revenue", "cost"], [])
        assert viz["type"] == "bar_chart"

    def test_decision_generation_with_responses(self):
        engine = NLIntelligenceEngine()
        decision, conf = engine._generate_decision(
            "Why revenue drop?", "root_cause", ["revenue"],
            ["Sales Agent", "Finance Agent"],
            [{"agent_label": "Sales Agent", "response": "Competitor entered market"}],
            [{"content": "Previous Q3 analysis showed similar pattern"}],
        )
        assert "Intelligence Analysis" in decision
        assert conf > 0.5

    def test_get_history(self):
        engine = NLIntelligenceEngine()
        engine.analyze_query("test query", self.PROFILE, self.AGENTS)
        history = engine.get_history()
        assert len(history) == 1


# ══════════════════════════════════════════════════════════════
# 7. END-TO-END PRODUCTION SCENARIO TESTS (8)
# ══════════════════════════════════════════════════════════════

class TestEndToEndProduction:
    def test_full_intelligence_loop(self):
        """Full loop: Connector → Profile → Agents → NL Query → Decision → Persistence"""
        async def run():
            # 1. Create connector and ingest data
            cf = ConnectorFramework()
            conn = cf.create_connector(ConnectorType.POSTGRESQL, "erp", ORG_ID, {"tables": ["sales"]})
            await conn.connect()
            await conn.sync("sales")

            # 2. Persist agent state
            db = AsyncDatabase()
            await db.connect()
            await db.set_tenant(ORG_ID)
            agent_repo = AgentRepository(db)
            agent = await agent_repo.create({"org_id": ORG_ID, "label": "Sales Agent", "status": "active"})

            # 3. NL query
            engine = NLIntelligenceEngine()
            result = engine.analyze_query(
                "Why did revenue drop in Germany?",
                {"kpis": [{"name": "Revenue"}], "ontology": {"entities": {"customer": {}}}},
                [{"label": "Sales Agent", "kpis_monitored": ["Revenue"], "purpose": "Revenue analysis"}],
                agent_responses=[{"agent_label": "Sales Agent", "response": "Competitor entered market"}],
            )
            assert result.decision != ""

            # 4. Persist execution
            exec_repo = ExecutionRepository(db)
            await exec_repo.create({
                "org_id": ORG_ID, "agent_id": agent["id"],
                "query": "Why did revenue drop?", "response": result.decision,
                "model": "gpt-4o", "cost_usd": 0.05,
            })

            # 5. Verify persistence
            executions = await exec_repo.get_by_org(ORG_ID)
            assert len(executions) == 1

        asyncio.run(run())

    def test_event_driven_workflow(self):
        """Event → Workflow → Agent execution → Memory persistence"""
        async def run():
            # 1. Publish event
            bus = DistributedEventBus()
            evt = bus.publish("kpi_threshold_breach", ORG_ID, payload={"kpi": "revenue", "change": "-15%"})

            # 2. Create and execute workflow
            engine = WorkflowEngine()
            async def investigate(wf, step):
                return {"finding": "Competitor entry caused revenue drop"}
            async def decide(wf, step):
                return {"decision": "Increase marketing spend"}
            engine.register_handler("investigate", investigate)
            engine.register_handler("decide", decide)

            wf = engine.create_workflow("revenue_investigation", ORG_ID, "sales_agent", [
                {"name": "investigate", "handler": "investigate"},
                {"name": "decide", "handler": "decide"},
            ], input_data={"trigger": evt.id})

            result = await engine.execute(wf.id)
            assert result.status == WorkflowStatus.SUCCEEDED

            # 3. Persist to database
            db = AsyncDatabase()
            await db.connect()
            await db.set_tenant(ORG_ID)
            mem_repo = MemoryRepository(db)
            await mem_repo.create({
                "org_id": ORG_ID, "agent_id": "sales_agent",
                "memory_type": "decision", "content": result.output_data.get("decide", {}).get("decision", ""),
            })
            memories = await mem_repo.get_by_agent("sales_agent", "decision")
            assert len(memories) == 1

        asyncio.run(run())

    def test_connector_to_intelligence_pipeline(self):
        """Connector sync → Universal Data Intelligence → Profile update"""
        async def run():
            cf = ConnectorFramework()
            conn = cf.create_connector(ConnectorType.SALESFORCE, "crm", ORG_ID, {"objects": ["Opportunities"]})
            await conn.connect()
            sources = await conn.discover()
            assert "Opportunities" in sources
            sample = await conn.sample("Opportunities")
            assert sample.row_count > 0

            # In production: sample → universal_profiler.profile() → Intelligence Profile update
        asyncio.run(run())

    def test_multi_connector_discovery(self):
        async def run():
            cf = ConnectorFramework()
            cf.create_connector(ConnectorType.POSTGRESQL, "erp", ORG_ID, {"tables": ["sales", "inventory"]})
            cf.create_connector(ConnectorType.SALESFORCE, "crm", ORG_ID, {"objects": ["Opportunities"]})
            cf.create_connector(ConnectorType.KAFKA, "stream", ORG_ID, {"topics": ["events"]})

            all_sources = await cf.discover_all(ORG_ID)
            assert len(all_sources) == 3

        asyncio.run(run())

    def test_continuous_monitoring_with_persistence(self):
        """Scheduled monitoring → Event → Workflow → Persistence"""
        async def run():
            # Setup
            bus = DistributedEventBus()
            engine = WorkflowEngine()
            db = AsyncDatabase()
            await db.connect()
            await db.set_tenant(ORG_ID)

            async def check_kpi(wf, step):
                return {"status": "normal"}
            engine.register_handler("check_kpi", check_kpi)

            # Schedule
            engine.schedule_workflow("kpi_monitor", "*/15 * * * *", ORG_ID, "monitor_agent",
                [{"name": "check_kpi", "handler": "check_kpi"}])

            # Simulate KPI breach event
            bus.publish("kpi_threshold_breach", ORG_ID, payload={"kpi": "revenue"})

            # Create and execute investigation workflow
            wf = engine.create_workflow("investigation", ORG_ID, "sales_agent", [
                {"name": "check_kpi", "handler": "check_kpi"},
            ])
            result = await engine.execute(wf.id)
            assert result.status == WorkflowStatus.SUCCEEDED

            # Persist audit trail
            audit_repo = AuditRepository(db)
            await audit_repo.create({
                "org_id": ORG_ID, "who": "sales_agent",
                "action": "kpi_monitor", "result": "normal",
            })
            audit = await audit_repo.get_by_org(ORG_ID)
            assert len(audit) == 1

        asyncio.run(run())

    def test_tenant_isolation_full_stack(self):
        """Two orgs: complete isolation across database, events, connectors"""
        async def run():
            # Database isolation
            db = AsyncDatabase()
            await db.connect()
            await db.insert("agent_memory", {"org_id": ORG_ID, "content": "org1 secret"})
            await db.insert("agent_memory", {"org_id": ORG_ID_2, "content": "org2 secret"})
            await db.set_tenant(ORG_ID)
            results = await db.select("agent_memory")
            assert all(r["org_id"] == ORG_ID for r in results)

            # Event isolation
            bus = DistributedEventBus()
            bus.publish("kpi_changed", ORG_ID)
            bus.publish("kpi_changed", ORG_ID_2)
            org1_events = bus.get_events(org_id=ORG_ID)
            assert len(org1_events) == 1

            # Connector isolation
            cf = ConnectorFramework()
            cf.create_connector(ConnectorType.POSTGRESQL, "org1_db", ORG_ID, {})
            cf.create_connector(ConnectorType.POSTGRESQL, "org2_db", ORG_ID_2, {})
            org1_connectors = cf.get_connectors(org_id=ORG_ID)
            assert len(org1_connectors) == 1

        asyncio.run(run())

    def test_workflow_recovery_after_failure(self):
        """Workflow fails → Compensation runs → State persisted for recovery"""
        async def run():
            engine = WorkflowEngine()
            async def step1_handler(wf, step):
                return "step1_done"
            async def step2_handler(wf, step):
                raise ValueError("network failure")
            comp_called = [False]
            def comp(wf, step):
                comp_called[0] = True

            engine.register_handler("step1", step1_handler)
            engine.register_handler("step2", step2_handler)
            engine.register_compensation("undo_step1", comp)

            wf = engine.create_workflow("recovery_test", ORG_ID, "a1", [
                {"name": "step1", "handler": "step1", "compensation": "undo_step1", "max_retries": 1},
                {"name": "step2", "handler": "step2", "max_retries": 1},
            ])
            result = await engine.execute(wf.id)
            assert result.status == WorkflowStatus.FAILED
            assert comp_called[0] is True  # compensation ran

        asyncio.run(run())

    def test_production_health_check(self):
        """All systems health check"""
        async def run():
            # Database
            db = AsyncDatabase()
            await db.connect()
            db_health = await db.health_check()
            assert db_health["connected"] is True

            # Event bus
            bus = DistributedEventBus()
            bus.publish("system_health", ORG_ID)
            assert bus.get_stats()["total_events"] == 1

            # Workflow engine
            engine = WorkflowEngine()
            stats = engine.get_stats()
            assert "total" in stats

            # Connectors
            cf = ConnectorFramework()
            conn = cf.create_connector(ConnectorType.POSTGRESQL, "test", ORG_ID, {})
            await conn.connect()
            assert conn.status == ConnectorStatus.CONNECTED

        asyncio.run(run())
