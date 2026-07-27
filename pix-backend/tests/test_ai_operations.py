from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.core.ai_operations import (
    AIOperationsManager,
    AgentExecutionEvent,
    AgentMonitor,
    CostTracker,
    FailureRecoveryManager,
    FailureRecoveryPolicy,
    get_ai_operations_manager,
)


class TestAgentMonitor:
    def test_record_and_overview(self):
        monitor = AgentMonitor()
        monitor.record_execution(AgentExecutionEvent(
            agent_name="coder", workspace_id="ws1", org_id="org1",
            status="success", duration_ms=150.0, tokens_used=500, cost=0.01, model="gpt-4o",
        ))
        overview = monitor.get_overview()
        assert overview["total_executions"] == 1
        assert overview["success"] == 1
        assert overview["success_rate"] == 1.0

    def test_get_agent_stats(self):
        monitor = AgentMonitor()
        monitor.record_execution(AgentExecutionEvent("coder", "ws1", "org1", "success", 100.0))
        monitor.record_execution(AgentExecutionEvent("coder", "ws1", "org1", "failed", 50.0, error="timeout"))
        stats = monitor.get_agent_stats("coder")
        assert stats["total"] == 2
        assert stats["success"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.5

    def test_get_agent_stats_empty(self):
        monitor = AgentMonitor()
        stats = monitor.get_agent_stats("nonexistent")
        assert stats["total"] == 0
        assert stats["success_rate"] == 1.0

    def test_get_workspace_stats(self):
        monitor = AgentMonitor()
        monitor.record_execution(AgentExecutionEvent("coder", "ws1", "org1", "success", 100.0, tokens_used=100, cost=0.01))
        monitor.record_execution(AgentExecutionEvent("planner", "ws2", "org1", "success", 200.0, tokens_used=200, cost=0.02))
        ws_stats = monitor.get_workspace_stats("ws1")
        assert ws_stats["total"] == 1
        assert ws_stats["total_tokens"] == 100

    def test_workspace_stats_empty(self):
        monitor = AgentMonitor()
        assert monitor.get_workspace_stats("nonexistent")["total"] == 0

    def test_recent_failures(self):
        monitor = AgentMonitor()
        monitor.record_execution(AgentExecutionEvent("coder", "ws1", "org1", "failed", 50.0, error="timeout"))
        monitor.record_execution(AgentExecutionEvent("coder", "ws1", "org1", "success", 100.0))
        failures = monitor.get_recent_failures()
        assert len(failures) == 1
        assert failures[0]["error"] == "timeout"

    def test_events_capped(self):
        monitor = AgentMonitor()
        for i in range(12000):
            monitor.record_execution(AgentExecutionEvent(f"agent{i}", "ws1", "org1", "success", 10.0))
        assert len(monitor._events) <= 7000

    def test_add_listener(self):
        monitor = AgentMonitor()
        received = []
        monitor.add_listener(lambda e: received.append(e.agent_name))
        monitor.record_execution(AgentExecutionEvent("coder", "ws1", "org1", "success", 10.0))
        assert received == ["coder"]

    def test_check_alerts_triggers_on_high_errors(self):
        monitor = AgentMonitor()
        now = datetime.now(UTC)
        for _ in range(10):
            monitor.record_execution(AgentExecutionEvent("failing-agent", "ws1", "org1", "failed", 50.0, error="err", timestamp=now.isoformat()))
        alerts = monitor.check_alerts()
        assert len(alerts) >= 1
        assert alerts[0]["severity"] == "critical"

    def test_get_alerts(self):
        monitor = AgentMonitor()
        monitor._alerts.append({"type": "test", "message": "test alert", "severity": "info", "timestamp": datetime.now(UTC).isoformat()})
        alerts = monitor.get_alerts()
        assert len(alerts) == 1


class TestCostTracker:
    def test_calculate_cost_known_model(self):
        tracker = CostTracker()
        cost = tracker.calculate_cost("gpt-4o-mini", input_tokens=1000, output_tokens=500)
        assert cost > 0
        assert cost == pytest.approx(0.00015 + 0.0003, rel=0.01)

    def test_calculate_cost_unknown_model(self):
        tracker = CostTracker()
        cost = tracker.calculate_cost("unknown-model", 1000, 500)
        assert cost == 0.0

    def test_record_and_get_org_costs(self):
        tracker = CostTracker()
        tracker.record_cost("org1", "ws1", "coder", "gpt-4o-mini", input_tokens=1000, output_tokens=500)
        stats = tracker.get_org_costs("org1")
        assert stats["total_records"] == 1
        assert stats["total_cost"] > 0

    def test_get_workspace_costs(self):
        tracker = CostTracker()
        tracker.record_cost("org1", "ws1", "coder", "gpt-4o-mini", 1000, 500)
        tracker.record_cost("org1", "ws2", "planner", "gpt-4o", 2000, 1000)
        ws_stats = tracker.get_workspace_costs("ws1")
        assert ws_stats["total_records"] == 1

    def test_aggregate_empty(self):
        tracker = CostTracker()
        stats = tracker.get_org_costs("nonexistent")
        assert stats["total_cost"] == 0.0
        assert stats["total_records"] == 0

    def test_set_and_get_budget(self):
        tracker = CostTracker()
        tracker.set_budget("org1", monthly_budget=100.0, alert_threshold=0.8)
        status = tracker.get_budget_status("org1")
        assert status["has_budget"] is True
        assert status["monthly_budget"] == 100.0

    def test_budget_near_limit(self):
        tracker = CostTracker()
        tracker.set_budget("org1", monthly_budget=10.0, alert_threshold=0.8)
        for _ in range(500):
            tracker.record_cost("org1", "ws1", "coder", "gpt-4o", 10000, 5000)
        status = tracker.get_budget_status("org1")
        assert status["near_limit"] is True

    def test_budget_no_budget(self):
        tracker = CostTracker()
        status = tracker.get_budget_status("nonexistent")
        assert status["has_budget"] is False

    def test_get_overview(self):
        tracker = CostTracker()
        tracker.record_cost("org1", "ws1", "coder", "gpt-4o-mini", 1000, 500)
        overview = tracker.get_overview()
        assert overview["total_records"] == 1
        assert overview["total_cost"] > 0

    def test_costs_capped(self):
        tracker = CostTracker()
        for i in range(110000):
            tracker.record_cost(f"org{i}", "ws1", "agent", "gpt-4o-mini", 100, 50)
        assert len(tracker._costs) <= 60000

    def test_by_agent_breakdown(self):
        tracker = CostTracker()
        tracker.record_cost("org1", "ws1", "coder", "gpt-4o-mini", 1000, 500)
        tracker.record_cost("org1", "ws1", "planner", "gpt-4o", 2000, 1000)
        stats = tracker.get_org_costs("org1")
        assert "coder" in stats["by_agent"]
        assert "planner" in stats["by_agent"]


class TestFailureRecoveryManager:
    @pytest.mark.asyncio
    async def test_execute_success(self):
        mgr = FailureRecoveryManager()

        async def succeed():
            return "ok"

        result, info = await mgr.execute_with_recovery("test-agent", succeed)
        assert result == "ok"
        assert info["status"] == "success"
        assert info["attempts"] == 1

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        mgr = FailureRecoveryManager()
        mgr.register_policy("flaky", FailureRecoveryPolicy(max_retries=3, base_delay=0.01))
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not ready yet")
            return "finally"

        result, info = await mgr.execute_with_recovery("flaky", flaky)
        assert result == "finally"
        assert info["attempts"] == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_fail(self):
        mgr = FailureRecoveryManager()
        mgr.register_policy("always-fail", FailureRecoveryPolicy(max_retries=2, base_delay=0.01))

        async def always_fail():
            raise ValueError("persistent error")

        result, info = await mgr.execute_with_recovery("always-fail", always_fail)
        assert result is None
        assert info["status"] == "fallback_default"

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        mgr = FailureRecoveryManager()
        mgr.register_policy("slow", FailureRecoveryPolicy(max_retries=2, base_delay=0.01, timeout_seconds=0.1))

        async def slow():
            await asyncio.sleep(10)
            return "too late"

        result, info = await mgr.execute_with_recovery("slow", slow)
        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_raise(self):
        mgr = FailureRecoveryManager()
        mgr.register_policy("no-fallback", FailureRecoveryPolicy(max_retries=1, base_delay=0.01, fallback_action="raise"))

        async def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await mgr.execute_with_recovery("no-fallback", fail)

    @pytest.mark.asyncio
    async def test_get_stats(self):
        mgr = FailureRecoveryManager()

        async def ok():
            return "ok"

        await mgr.execute_with_recovery("agent1", ok)
        stats = mgr.get_stats()
        assert stats["total"] == 1
        assert stats["success"] == 1

    def test_default_policy(self):
        mgr = FailureRecoveryManager()
        policy = mgr.get_policy("unknown")
        assert policy.max_retries == 3
        assert policy.base_delay == 1.0

    def test_register_policy(self):
        mgr = FailureRecoveryManager()
        policy = FailureRecoveryPolicy(max_retries=5, fallback_action="raise")
        mgr.register_policy("critical-agent", policy)
        assert mgr.get_policy("critical-agent").max_retries == 5


class TestAIOperationsManager:
    def test_singleton(self):
        m1 = get_ai_operations_manager()
        m2 = get_ai_operations_manager()
        assert m1 is m2

    def test_get_operations_status(self):
        mgr = AIOperationsManager()
        status = mgr.get_operations_status()
        assert "monitor" in status
        assert "cost_tracker" in status
        assert "failure_recovery" in status

    def test_all_components_accessible(self):
        mgr = AIOperationsManager()
        assert mgr.monitor is not None
        assert mgr.cost_tracker is not None
        assert mgr.failure_recovery is not None
