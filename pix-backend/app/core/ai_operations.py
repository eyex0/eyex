from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("pix.core.ai_operations")


@dataclass
class AgentExecutionEvent:
    agent_name: str
    workspace_id: str
    org_id: str
    status: str
    duration_ms: float
    tokens_used: int = 0
    cost: float = 0.0
    error: str | None = None
    model: str = ""
    timestamp: str = ""


class AgentMonitor:
    def __init__(self) -> None:
        self._events: list[AgentExecutionEvent] = []
        self._alerts: list[dict[str, Any]] = []
        self._error_counts: dict[str, int] = defaultdict(int)
        self._event_listeners: list[Callable[[AgentExecutionEvent], None]] = []

    def record_execution(self, event: AgentExecutionEvent) -> None:
        self._events.append(event)
        if len(self._events) > 10000:
            self._events = self._events[-5000:]
        if event.status == "failed":
            self._error_counts[event.agent_name] += 1
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception:
                logger.exception("Event listener error")

    def add_listener(self, listener: Callable[[AgentExecutionEvent], None]) -> None:
        self._event_listeners.append(listener)

    def get_agent_stats(self, agent_name: str, since: datetime | None = None) -> dict[str, Any]:
        events = self._events
        if since:
            events = [e for e in events if e.timestamp >= since.isoformat()]
        agent_events = [e for e in events if e.agent_name == agent_name]
        total = len(agent_events)
        if total == 0:
            return {"agent": agent_name, "total": 0, "success_rate": 1.0, "avg_duration_ms": 0, "total_cost": 0.0, "total_tokens": 0}
        success = sum(1 for e in agent_events if e.status == "success")
        avg_duration = sum(e.duration_ms for e in agent_events) / total
        total_cost = sum(e.cost for e in agent_events)
        total_tokens = sum(e.tokens_used for e in agent_events)
        return {
            "agent": agent_name,
            "total": total,
            "success": success,
            "failed": total - success,
            "success_rate": round(success / total, 4),
            "avg_duration_ms": round(avg_duration, 2),
            "total_cost": round(total_cost, 4),
            "total_tokens": total_tokens,
            "error_rate": round(self._error_counts.get(agent_name, 0) / max(total, 1), 4),
        }

    def get_workspace_stats(self, workspace_id: str, since: datetime | None = None) -> dict[str, Any]:
        events = self._events
        if since:
            events = [e for e in events if e.timestamp >= since.isoformat()]
        ws_events = [e for e in events if e.workspace_id == workspace_id]
        total = len(ws_events)
        if total == 0:
            return {"workspace_id": workspace_id, "total": 0, "total_cost": 0.0, "total_tokens": 0}
        success = sum(1 for e in ws_events if e.status == "success")
        return {
            "workspace_id": workspace_id,
            "total": total,
            "success": success,
            "failed": total - success,
            "success_rate": round(success / total, 4),
            "total_cost": round(sum(e.cost for e in ws_events), 4),
            "total_tokens": sum(e.tokens_used for e in ws_events),
            "avg_duration_ms": round(sum(e.duration_ms for e in ws_events) / total, 2),
        }

    def get_recent_failures(self, limit: int = 20) -> list[dict[str, Any]]:
        return [
            {"agent": e.agent_name, "error": e.error, "duration_ms": e.duration_ms, "timestamp": e.timestamp, "workspace_id": e.workspace_id}
            for e in self._events if e.status == "failed"
        ][-limit:]

    def check_alerts(self) -> list[dict[str, Any]]:
        alerts = []
        for agent, count in self._error_counts.items():
            recent = self.get_agent_stats(agent, since=datetime.now(UTC) - timedelta(minutes=5))
            if recent["total"] >= 5 and recent["success_rate"] < 0.5:
                alert = {
                    "type": "high_error_rate",
                    "agent": agent,
                    "message": f"Agent {agent} has {recent['success_rate']:.0%} success rate in last 5 minutes",
                    "severity": "critical",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                alerts.append(alert)
                self._alerts.append(alert)
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-50:]
        return alerts

    def get_alerts(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._alerts[-limit:]

    def get_overview(self) -> dict[str, Any]:
        total = len(self._events)
        if total == 0:
            return {"total_executions": 0, "success_rate": 1.0, "total_cost": 0.0, "total_tokens": 0}
        success = sum(1 for e in self._events if e.status == "success")
        return {
            "total_executions": total,
            "success": success,
            "failed": total - success,
            "success_rate": round(success / total, 4),
            "total_cost": round(sum(e.cost for e in self._events), 4),
            "total_tokens": sum(e.tokens_used for e in self._events),
            "unique_agents": len(set(e.agent_name for e in self._events)),
            "unique_workspaces": len(set(e.workspace_id for e in self._events)),
            "active_alerts": len(self._alerts),
        }


class CostTracker:
    MODEL_COSTS: dict[str, dict[str, float]] = {
        "gpt-4o": {"input_per_1k": 0.01, "output_per_1k": 0.03},
        "gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
        "gpt-4": {"input_per_1k": 0.03, "output_per_1k": 0.06},
        "gpt-3.5-turbo": {"input_per_1k": 0.0005, "output_per_1k": 0.0015},
        "claude-3-opus": {"input_per_1k": 0.015, "output_per_1k": 0.075},
        "claude-3-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015},
        "claude-3-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
        "gemini-2.5-flash": {"input_per_1k": 0.000075, "output_per_1k": 0.0003},
    }

    def __init__(self) -> None:
        self._costs: list[dict[str, Any]] = []
        self._budgets: dict[str, dict[str, Any]] = {}

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        costs = self.MODEL_COSTS.get(model)
        if not costs:
            return 0.0
        input_cost = (input_tokens / 1000) * costs["input_per_1k"]
        output_cost = (output_tokens / 1000) * costs["output_per_1k"]
        return round(input_cost + output_cost, 6)

    def record_cost(self, org_id: str, workspace_id: str, agent: str, model: str, input_tokens: int, output_tokens: int, duration_ms: float = 0) -> dict[str, Any]:
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        record = {
            "org_id": org_id,
            "workspace_id": workspace_id,
            "agent": agent,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._costs.append(record)
        if len(self._costs) > 100000:
            self._costs = self._costs[-50000:]
        return record

    def get_org_costs(self, org_id: str, since: datetime | None = None) -> dict[str, Any]:
        records = self._costs
        if since:
            records = [r for r in records if r["timestamp"] >= since.isoformat()]
        org_records = [r for r in records if r["org_id"] == org_id]
        return self._aggregate(org_records)

    def get_workspace_costs(self, workspace_id: str, since: datetime | None = None) -> dict[str, Any]:
        records = self._costs
        if since:
            records = [r for r in records if r["timestamp"] >= since.isoformat()]
        ws_records = [r for r in records if r["workspace_id"] == workspace_id]
        return self._aggregate(ws_records)

    def _aggregate(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(records)
        if total == 0:
            return {"total_cost": 0.0, "total_tokens": 0, "total_records": 0, "by_agent": {}, "by_model": {}}
        by_agent: dict[str, float] = defaultdict(float)
        by_model: dict[str, float] = defaultdict(float)
        total_cost = 0.0
        total_tokens = 0
        for r in records:
            total_cost += r["cost"]
            total_tokens += r["total_tokens"]
            by_agent[r["agent"]] += r["cost"]
            by_model[r["model"]] += r["cost"]
        return {
            "total_cost": round(total_cost, 4),
            "total_tokens": total_tokens,
            "total_records": total,
            "by_agent": dict(by_agent),
            "by_model": dict(by_model),
        }

    def set_budget(self, org_id: str, monthly_budget: float, alert_threshold: float = 0.8) -> None:
        self._budgets[org_id] = {"monthly_budget": monthly_budget, "alert_threshold": alert_threshold, "set_at": datetime.now(UTC).isoformat()}

    def get_budget_status(self, org_id: str) -> dict[str, Any]:
        budget = self._budgets.get(org_id)
        if not budget:
            return {"has_budget": False}
        since = datetime.now(UTC) - timedelta(days=30)
        usage = self.get_org_costs(org_id, since=since)
        monthly = budget["monthly_budget"]
        spent = usage["total_cost"]
        return {
            "has_budget": True,
            "monthly_budget": monthly,
            "spent": round(spent, 4),
            "remaining": round(monthly - spent, 4),
            "usage_pct": round(spent / monthly * 100, 1) if monthly > 0 else 0,
            "alert_threshold": budget["alert_threshold"],
            "near_limit": spent >= monthly * budget["alert_threshold"],
        }

    def get_overview(self) -> dict[str, Any]:
        total = len(self._costs)
        if total == 0:
            return {"total_cost": 0.0, "total_tokens": 0, "total_records": 0}
        return {
            "total_cost": round(sum(r["cost"] for r in self._costs), 4),
            "total_tokens": sum(r["total_tokens"] for r in self._costs),
            "total_records": total,
            "unique_orgs": len(set(r["org_id"] for r in self._costs)),
            "budgets_configured": len(self._budgets),
        }


class FailureRecoveryPolicy:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0, backoff_factor: float = 2.0, fallback_action: str = "return_default", timeout_seconds: float = 30.0) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.fallback_action = fallback_action
        self.timeout_seconds = timeout_seconds


class FailureRecoveryManager:
    def __init__(self) -> None:
        self._policies: dict[str, FailureRecoveryPolicy] = {}
        self._recovery_records: list[dict[str, Any]] = []

    def register_policy(self, agent_name: str, policy: FailureRecoveryPolicy) -> None:
        self._policies[agent_name] = policy

    def get_policy(self, agent_name: str) -> FailureRecoveryPolicy:
        return self._policies.get(agent_name, FailureRecoveryPolicy())

    async def execute_with_recovery(self, agent_name: str, func: Callable, *args: Any, **kwargs: Any) -> tuple[Any, dict[str, Any]]:
        policy = self.get_policy(agent_name)
        last_error: Exception | None = None
        attempts = 0

        for attempt in range(1, policy.max_retries + 1):
            attempts = attempt
            start = time.perf_counter()
            try:
                async with asyncio.timeout(policy.timeout_seconds):
                    result = func(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        result = await result
                elapsed = (time.perf_counter() - start) * 1000
                self._record_recovery(agent_name, "success", attempt, elapsed)
                return result, {"status": "success", "attempts": attempt, "duration_ms": round(elapsed, 2)}
            except TimeoutError:
                last_error = TimeoutError(f"Agent {agent_name} timed out after {policy.timeout_seconds}s")
                elapsed = (time.perf_counter() - start) * 1000
                self._record_recovery(agent_name, "timeout" if attempt < policy.max_retries else "failed", attempt, elapsed, str(last_error))
                if attempt < policy.max_retries:
                    delay = min(policy.base_delay * (policy.backoff_factor ** (attempt - 1)), policy.max_delay)
                    await asyncio.sleep(delay)
            except Exception as exc:
                last_error = exc
                elapsed = (time.perf_counter() - start) * 1000
                self._record_recovery(agent_name, "retry" if attempt < policy.max_retries else "failed", attempt, elapsed, str(exc))
                if attempt < policy.max_retries:
                    delay = min(policy.base_delay * (policy.backoff_factor ** (attempt - 1)), policy.max_delay)
                    await asyncio.sleep(delay)

        return self._execute_fallback(agent_name, policy, last_error, attempts)

    def _execute_fallback(self, agent_name: str, policy: FailureRecoveryPolicy, error: Exception | None, attempts: int) -> tuple[Any, dict[str, Any]]:
        if policy.fallback_action == "return_default":
            self._record_recovery(agent_name, "fallback_default", attempts, 0, str(error) if error else None)
            return None, {"status": "fallback_default", "attempts": attempts, "error": str(error) if error else "Unknown error"}
        if policy.fallback_action == "raise":
            raise error or RuntimeError(f"{agent_name} failed after {attempts} attempts")
        return None, {"status": "fallback_default", "attempts": attempts, "error": str(error) if error else "Unknown error"}

    def _record_recovery(self, agent_name: str, status: str, attempt: int, duration_ms: float, error: str | None = None) -> None:
        self._recovery_records.append({
            "agent": agent_name,
            "status": status,
            "attempt": attempt,
            "duration_ms": round(duration_ms, 2),
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        if len(self._recovery_records) > 10000:
            self._recovery_records = self._recovery_records[-5000:]

    def get_stats(self) -> dict[str, Any]:
        total = len(self._recovery_records)
        if total == 0:
            return {"total": 0, "success_rate": 1.0}
        success = sum(1 for r in self._recovery_records if r["status"] == "success")
        return {
            "total": total,
            "success": success,
            "failed": total - success,
            "success_rate": round(success / total, 4),
            "agents_with_policies": list(self._policies.keys()),
        }


class AIOperationsManager:
    def __init__(self) -> None:
        self.monitor = AgentMonitor()
        self.cost_tracker = CostTracker()
        self.failure_recovery = FailureRecoveryManager()

    def get_operations_status(self) -> dict[str, Any]:
        return {
            "monitor": self.monitor.get_overview(),
            "cost_tracker": self.cost_tracker.get_overview(),
            "failure_recovery": self.failure_recovery.get_stats(),
        }


_ai_ops_manager: AIOperationsManager | None = None


def get_ai_operations_manager() -> AIOperationsManager:
    global _ai_ops_manager
    if _ai_ops_manager is None:
        _ai_ops_manager = AIOperationsManager()
    return _ai_ops_manager
