"""
πX Repositories — Async CRUD for all entities via AsyncDatabase.
"""
from __future__ import annotations

from typing import Any
from .async_db import AsyncDatabase


class BaseRepository:
    """Base async repository with RLS enforcement."""
    def __init__(self, db: AsyncDatabase, table: str) -> None:
        self.db = db
        self.table = table

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self.db.insert(self.table, data)

    async def get_by_id(self, row_id: str) -> dict[str, Any] | None:
        rows = await self.db.select(self.table, {"id": row_id}, limit=1)
        return rows[0] if rows else None

    async def list(self, filters: dict[str, Any] | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        return await self.db.select(self.table, filters, limit=limit, offset=offset)

    async def update(self, row_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        return await self.db.update(self.table, row_id, data)

    async def delete(self, row_id: str) -> bool:
        return await self.db.delete(self.table, row_id)

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        return await self.db.count(self.table, filters)


class AgentRepository(BaseRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        super().__init__(db, "agent_instances")

    async def get_by_org(self, org_id: str) -> list[dict]:
        return await self.list({"org_id": org_id}, limit=500)

    async def update_status(self, agent_id: str, status: str) -> dict | None:
        return await self.update(agent_id, {"status": status})

    async def increment_stat(self, agent_id: str, field: str, amount: int = 1) -> dict | None:
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        current = agent.get(field, 0)
        return await self.update(agent_id, {field: current + amount})


class MemoryRepository(BaseRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        super().__init__(db, "persistent_agent_memory")

    async def get_by_agent(self, agent_id: str, memory_type: str | None = None, limit: int = 20) -> list[dict]:
        filters = {"agent_id": agent_id}
        if memory_type:
            filters["memory_type"] = memory_type
        return await self.list(filters, limit=limit)

    async def get_org_memory(self, org_id: str, limit: int = 100) -> list[dict]:
        return await self.list({"org_id": org_id}, limit=limit)


class ExecutionRepository(BaseRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        super().__init__(db, "agent_execution_history")

    async def get_by_agent(self, agent_id: str, limit: int = 50) -> list[dict]:
        return await self.list({"agent_id": agent_id}, limit=limit)

    async def get_by_org(self, org_id: str, limit: int = 100) -> list[dict]:
        return await self.list({"org_id": org_id}, limit=limit)

    async def get_cost_summary(self, org_id: str) -> dict[str, Any]:
        executions = await self.list({"org_id": org_id}, limit=10000)
        total_cost = sum(e.get("cost_usd", 0) for e in executions)
        total_tokens = sum(e.get("input_tokens", 0) + e.get("output_tokens", 0) for e in executions)
        by_model: dict[str, float] = {}
        for e in executions:
            model = e.get("model", "unknown")
            by_model[model] = by_model.get(model, 0) + e.get("cost_usd", 0)
        return {
            "total_cost": round(total_cost, 4),
            "total_tokens": total_tokens,
            "total_calls": len(executions),
            "by_model": by_model,
        }


class EvaluationRepository(BaseRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        super().__init__(db, "ai_quality_assessments")

    async def get_by_agent(self, agent_id: str, limit: int = 50) -> list[dict]:
        return await self.list({"agent_id": agent_id}, limit=limit)

    async def get_quality_stats(self, org_id: str) -> dict[str, Any]:
        evals = await self.list({"org_id": org_id}, limit=10000)
        if not evals:
            return {"total": 0, "avg_score": 0}
        scores = [e.get("quality_score", 0) for e in evals]
        return {
            "total": len(evals),
            "avg_score": sum(scores) // len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
        }


class AuditRepository(BaseRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        super().__init__(db, "ai_audit_trail")

    async def get_by_org(self, org_id: str, limit: int = 100) -> list[dict]:
        return await self.list({"org_id": org_id}, limit=limit)


class MessageRepository(BaseRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        super().__init__(db, "agent_messages")

    async def get_by_org(self, org_id: str, limit: int = 50) -> list[dict]:
        return await self.list({"org_id": org_id}, limit=limit)


class ScheduleRepository(BaseRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        super().__init__(db, "agent_schedules")

    async def get_active_by_org(self, org_id: str) -> list[dict]:
        all_schedules = await self.list({"org_id": org_id}, limit=500)
        return [s for s in all_schedules if s.get("status") == "active"]


class ObservabilityRepository(BaseRepository):
    def __init__(self, db: AsyncDatabase) -> None:
        super().__init__(db, "ai_observability_metrics")

    async def get_by_org(self, org_id: str, metric_type: str | None = None, limit: int = 100) -> list[dict]:
        filters = {"org_id": org_id}
        if metric_type:
            filters["metric_type"] = metric_type
        return await self.list(filters, limit=limit)
