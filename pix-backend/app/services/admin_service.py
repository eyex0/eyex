from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pix_backend.app.models.memory import ConversationMessage

logger = logging.getLogger("pix.services.admin")

_start_time = time.monotonic()


class AdminService:
    def __init__(self) -> None:
        self.workflows_completed = 0
        self.workflows_failed = 0
        self.total_response_time_ms = 0.0
        self.total_executions = 0
        self.tools_used: dict[str, int] = defaultdict(int)
        self.agents_used: dict[str, int] = defaultdict(int)
        self.agent_durations: dict[str, list[float]] = defaultdict(list)
        self.agent_errors: dict[str, int] = defaultdict(int)
        self.agent_last_execution: dict[str, float] = {}

    def record_workflow(self, success: bool, duration_ms: float) -> None:
        if success:
            self.workflows_completed += 1
        else:
            self.workflows_failed += 1
        self.total_response_time_ms += duration_ms
        self.total_executions += 1

    def record_agent_execution(self, agent_name: str, duration_ms: float, success: bool) -> None:
        self.agents_used[agent_name] += 1
        self.agent_durations[agent_name].append(duration_ms)
        if not success:
            self.agent_errors[agent_name] += 1
        self.agent_last_execution[agent_name] = time.time()

    def record_tool_use(self, tool_name: str) -> None:
        self.tools_used[tool_name] += 1

    @property
    def uptime_hours(self) -> float:
        return (time.monotonic() - _start_time) / 3600

    @property
    def average_response_time_ms(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_response_time_ms / self.total_executions

    async def get_overall_stats(self, db: AsyncSession | None = None) -> dict:
        stats: dict = {
            "total_sessions": 0,
            "total_messages": 0,
            "active_users": 0,
            "workflows_completed": self.workflows_completed,
            "workflows_failed": self.workflows_failed,
            "average_response_time_ms": round(self.average_response_time_ms, 2),
            "tools_used": dict(self.tools_used),
            "agents_used": dict(self.agents_used),
            "uptime_hours": round(self.uptime_hours, 2),
        }

        if db is not None:
            try:
                msg_count = await db.scalar(select(func.count(ConversationMessage.id)))
                stats["total_messages"] = msg_count or 0

                session_count = await db.scalar(
                    select(func.count(func.distinct(ConversationMessage.session_id)))
                )
                stats["total_sessions"] = session_count or 0

                thirty_min_ago = datetime.now(UTC) - timedelta(minutes=30)
                active_count = await db.scalar(
                    select(func.count(func.distinct(ConversationMessage.session_id)))
                    .where(ConversationMessage.created_at >= thirty_min_ago)
                )
                stats["active_users"] = active_count or 0
            except Exception as exc:
                logger.warning("Failed to query DB for stats: %s", exc)

        return stats

    async def get_sessions(
        self,
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        try:
            total = await db.scalar(
                select(func.count(func.distinct(ConversationMessage.session_id)))
            ) or 0

            subq = (
                select(
                    ConversationMessage.session_id,
                    func.count(ConversationMessage.id).label("message_count"),
                    func.max(ConversationMessage.created_at).label("last_activity"),
                )
                .group_by(ConversationMessage.session_id)
                .subquery()
            )

            query = (
                select(subq)
                .order_by(subq.c.last_activity.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            rows = await db.execute(query)

            sessions = []
            for row in rows:
                sessions.append({
                    "session_id": row.session_id,
                    "message_count": row.message_count,
                    "last_activity": row.last_activity.isoformat() if row.last_activity else None,
                    "agents_used": [],
                    "status": "active",
                })

            return {
                "sessions": sessions,
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        except Exception as exc:
            logger.warning("Failed to query DB for sessions: %s", exc)
            return {"sessions": [], "total": 0, "page": page, "per_page": per_page}

    async def get_agents_stats(self) -> dict:
        agents = []
        for name, count in self.agents_used.items():
            durations = self.agent_durations.get(name, [])
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            errors = self.agent_errors.get(name, 0)
            error_rate = errors / count if count > 0 else 0.0
            last_exec = self.agent_last_execution.get(name)
            agents.append({
                "name": name,
                "executions": count,
                "avg_duration_ms": round(avg_duration, 2),
                "last_execution": datetime.fromtimestamp(last_exec, tz=UTC).isoformat() if last_exec else None,
                "error_rate": round(error_rate, 4),
            })
        return {"agents": agents}

    async def get_detailed_health(self, db: AsyncSession | None = None, memory=None) -> dict:
        from app.config import get_settings

        settings = get_settings()
        health: dict = {}

        if db is not None:
            try:
                start = time.monotonic()
                await db.execute(select(1))
                latency = (time.monotonic() - start) * 1000
                health["postgresql"] = {"status": "ok", "latency_ms": round(latency, 2)}
            except Exception as exc:
                health["postgresql"] = {"status": "error", "latency_ms": 0, "error": str(exc)}
        else:
            health["postgresql"] = {"status": "unknown", "latency_ms": 0}

        try:
            from redis.asyncio import Redis

            from pix_backend.app.database import get_redis_pool

            pool = get_redis_pool()
            r = Redis(connection_pool=pool)
            start = time.monotonic()
            await r.ping()
            latency = (time.monotonic() - start) * 1000
            health["redis"] = {"status": "ok", "latency_ms": round(latency, 2)}
        except Exception as exc:
            health["redis"] = {"status": "error", "latency_ms": 0, "error": str(exc)}

        if settings.openai_api_key:
            try:
                import openai

                client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                start = time.monotonic()
                await client.models.list()
                latency = (time.monotonic() - start) * 1000
                health["openai"] = {"status": "ok", "latency_ms": round(latency, 2)}
            except Exception as exc:
                health["openai"] = {"status": "error", "latency_ms": 0, "error": str(exc)}
        else:
            health["openai"] = {"status": "disabled", "latency_ms": 0}

        if memory is not None:
            try:
                mem_health = await memory.health()
                health["memory"] = {"status": "ok" if mem_health.get("healthy") else "degraded"}
            except Exception as exc:
                health["memory"] = {"status": "error", "error": str(exc)}
        else:
            health["memory"] = {"status": "unknown"}

        return {
            **health,
            "version": settings.app_version,
            "uptime_hours": round(self.uptime_hours, 2),
        }


_admin_service: AdminService | None = None


def get_admin_service() -> AdminService:
    global _admin_service
    if _admin_service is None:
        _admin_service = AdminService()
    return _admin_service
