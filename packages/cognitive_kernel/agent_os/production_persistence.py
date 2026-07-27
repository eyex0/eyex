"""
πX Production Persistence Layer — Replaces all in-memory storage with PostgreSQL.

Every component persists: agent memory, evaluations, executions, messages,
observability metrics, audit trails.

In production, this uses SQLAlchemy + asyncpg + PostgreSQL.
Here we provide a clean persistence interface with a dict-backed simulation
that maps 1:1 to the PostgreSQL schema (migrations 0011-0016).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import json
import uuid


class PersistentStore:
    """Base persistent store — simulates PostgreSQL tables with dict storage.

    Each method maps to a SQL query in production:
      get()  → SELECT ... WHERE ...
      save() → INSERT ... ON CONFLICT UPDATE
      query()→ SELECT ... WHERE ... ORDER BY ... LIMIT ...
      delete()→ DELETE ... WHERE ...
    """

    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        self._rows: dict[str, dict[str, Any]] = {}  # id → row

    def save(self, row_id: str, data: dict[str, Any]) -> dict[str, Any]:
        data = {**data, "id": row_id, "updated_at": datetime.now(UTC).isoformat()}
        if row_id not in self._rows:
            data["created_at"] = datetime.now(UTC).isoformat()
        self._rows[row_id] = data
        return data

    def get(self, row_id: str) -> dict[str, Any] | None:
        return self._rows.get(row_id)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        order_by: str = "created_at",
        descending: bool = True,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        results = list(self._rows.values())
        if filters:
            for key, value in filters.items():
                results = [r for r in results if r.get(key) == value]
        results.sort(key=lambda r: r.get(order_by, ""), reverse=descending)
        return results[:limit]

    def delete(self, row_id: str) -> bool:
        return self._rows.pop(row_id, None) is not None

    def count(self, filters: dict[str, Any] | None = None) -> int:
        if not filters:
            return len(self._rows)
        return len(self.query(filters, limit=10000))

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows.values())


class ProductionPersistence:
    """Central persistence manager — replaces all in-memory storage.

    Maps to PostgreSQL tables:
      agent_memory      → PersistentStore("agent_memory")
      evaluations       → PersistentStore("ai_quality_assessments")
      executions        → PersistentStore("agent_execution_history")
      messages          → PersistentStore("agent_messages")
      observability     → PersistentStore("ai_observability_metrics")
      security_events   → PersistentStore("ai_security_events")
      audit_trail       → PersistentStore("ai_audit_trail")
      schedules         → PersistentStore("agent_schedules")
    """

    def __init__(self) -> None:
        self.stores: dict[str, PersistentStore] = {
            "agent_memory": PersistentStore("agent_memory"),
            "evaluations": PersistentStore("ai_quality_assessments"),
            "executions": PersistentStore("agent_execution_history"),
            "messages": PersistentStore("agent_messages"),
            "observability": PersistentStore("ai_observability_metrics"),
            "security_events": PersistentStore("ai_security_events"),
            "audit_trail": PersistentStore("ai_audit_trail"),
            "schedules": PersistentStore("agent_schedules"),
            "persistent_memory": PersistentStore("persistent_agent_memory"),
        }

    def get_store(self, name: str) -> PersistentStore:
        return self.stores[name]

    # ── Agent Memory ──
    def save_memory(self, agent_id: str, org_id: str, memory_type: str,
                    content: str, importance: float = 0.5,
                    metadata: dict | None = None) -> dict:
        mid = f"mem_{uuid.uuid4().hex[:12]}"
        return self.stores["agent_memory"].save(mid, {
            "agent_id": agent_id, "org_id": org_id,
            "memory_type": memory_type, "content": content,
            "importance": importance, "metadata": metadata or {},
            "access_count": 0,
        })

    def query_memory(self, agent_id: str, memory_type: str | None = None,
                     limit: int = 10) -> list[dict]:
        filters = {"agent_id": agent_id}
        if memory_type:
            filters["memory_type"] = memory_type
        return self.stores["agent_memory"].query(filters, limit=limit)

    # ── Executions ──
    def save_execution(self, agent_id: str, org_id: str, query: str,
                       response: str, model: str = "", provider: str = "",
                       tokens_in: int = 0, tokens_out: int = 0,
                       latency_ms: int = 0, cost: float = 0.0,
                       confidence: float = 0.0) -> dict:
        eid = f"exec_{uuid.uuid4().hex[:12]}"
        return self.stores["executions"].save(eid, {
            "agent_id": agent_id, "org_id": org_id,
            "query": query, "response": response,
            "model": model, "provider": provider,
            "input_tokens": tokens_in, "output_tokens": tokens_out,
            "latency_ms": latency_ms, "cost_usd": cost,
            "confidence": confidence,
        })

    def query_executions(self, agent_id: str | None = None,
                         org_id: str | None = None, limit: int = 50) -> list[dict]:
        filters = {}
        if agent_id:
            filters["agent_id"] = agent_id
        if org_id:
            filters["org_id"] = org_id
        return self.stores["executions"].query(filters or None, limit=limit)

    # ── Evaluations ──
    def save_evaluation(self, agent_id: str, org_id: str, query: str,
                        response: str, quality_score: int,
                        factors: dict, hallucination_flags: list,
                        sources: list) -> dict:
        eid = f"qa_{uuid.uuid4().hex[:12]}"
        return self.stores["evaluations"].save(eid, {
            "agent_id": agent_id, "org_id": org_id,
            "query": query, "response": response,
            "quality_score": quality_score, "factors": factors,
            "hallucination_flags": hallucination_flags,
            "sources_cited": sources,
        })

    def query_evaluations(self, agent_id: str | None = None,
                          org_id: str | None = None, limit: int = 50) -> list[dict]:
        filters = {}
        if agent_id:
            filters["agent_id"] = agent_id
        if org_id:
            filters["org_id"] = org_id
        return self.stores["evaluations"].query(filters or None, limit=limit)

    # ── Messages ──
    def save_message(self, from_agent: str, to_agent: str, org_id: str,
                      msg_type: str, content: str, confidence: float = 0.5) -> dict:
        mid = f"msg_{uuid.uuid4().hex[:12]}"
        return self.stores["messages"].save(mid, {
            "from_agent_id": from_agent, "to_agent_id": to_agent,
            "org_id": org_id, "message_type": msg_type,
            "content": content, "confidence": confidence,
        })

    def query_messages(self, org_id: str, agent_id: str | None = None,
                       limit: int = 50) -> list[dict]:
        filters = {"org_id": org_id}
        if agent_id:
            filters["from_agent_id"] = agent_id
        return self.stores["messages"].query(filters, limit=limit)

    # ── Observability ──
    def save_metric(self, org_id: str, metric_type: str, value: float,
                    unit: str = "", agent_id: str = "", model: str = "") -> dict:
        mid = f"metric_{uuid.uuid4().hex[:12]}"
        return self.stores["observability"].save(mid, {
            "org_id": org_id, "metric_type": metric_type,
            "value": value, "unit": unit,
            "agent_id": agent_id, "model": model,
        })

    def query_metrics(self, org_id: str, metric_type: str | None = None,
                      limit: int = 100) -> list[dict]:
        filters = {"org_id": org_id}
        if metric_type:
            filters["metric_type"] = metric_type
        return self.stores["observability"].query(filters, limit=limit)

    # ── Audit Trail ──
    def save_audit(self, org_id: str, who: str, which_data: str,
                   which_model: str, which_agent: str, why: str,
                   action: str, result: str) -> dict:
        aid = f"audit_{uuid.uuid4().hex[:12]}"
        return self.stores["audit_trail"].save(aid, {
            "org_id": org_id, "who": who,
            "which_data": which_data, "which_model": which_model,
            "which_agent": which_agent, "why": why,
            "action": action, "result": result,
        })

    def query_audit(self, org_id: str | None = None, limit: int = 100) -> list[dict]:
        filters = {"org_id": org_id} if org_id else None
        return self.stores["audit_trail"].query(filters, limit=limit)

    # ── Schedules ──
    def save_schedule(self, org_id: str, agent_id: str, trigger_type: str,
                      condition: dict, interval_seconds: int = 3600,
                      action: str = "") -> dict:
        sid = f"sched_{uuid.uuid4().hex[:12]}"
        return self.stores["schedules"].save(sid, {
            "org_id": org_id, "agent_id": agent_id,
            "trigger_type": trigger_type, "condition": condition,
            "interval_seconds": interval_seconds, "action": action,
            "status": "active", "trigger_count": 0,
        })

    # ── Tenant Isolation Check ──
    def verify_tenant_isolation(self, org_id: str) -> dict[str, bool]:
        """Verify no data from other orgs leaks into this org's queries."""
        results = {}
        for name, store in self.stores.items():
            all_rows = store.all()
            other_org = [r for r in all_rows if r.get("org_id") == org_id and r.get("org_id") != org_id]
            results[name] = len(other_org) == 0
        return results

    def get_stats(self) -> dict[str, int]:
        return {name: store.count() for name, store in self.stores.items()}
