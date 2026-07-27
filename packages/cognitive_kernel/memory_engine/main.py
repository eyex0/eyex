from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.context import org_id_ctx
from app.models.memory import AgentMemoryRecord, ConversationMessage, LongTermMemory
from app.database import get_redis_pool

logger = logging.getLogger("pix.db.memory")


def _current_org_id(org_id: str | None) -> str | None:
    return org_id if org_id is not None else org_id_ctx.get()

SHORT_TERM_TTL = 3600
WORKING_TTL = 86400
LOCK_TTL = 30
MAX_CONVERSATION_LIMIT = 100
DEFAULT_CONVERSATION_LIMIT = 50
MAX_LONG_TERM_LIMIT = 200
DEFAULT_LONG_TERM_MIN_IMPORTANCE = 0.3


class PersistentMemory:
    """Multi-layer persistent memory backed by PostgreSQL and Redis.

    Layers:
      - Conversation History  (PostgreSQL):  Full message log per session
      - Long-term Memory      (PostgreSQL):  Persistent facts, preferences, learnings
      - Agent-specific Memory (PostgreSQL):  Per-agent output, state, context
      - Short-term Memory     (Redis):       Ephemeral context with TTL
      - Working State         (Redis):       Current workflow state with 24h TTL
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        redis_client: Redis | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.redis = redis_client or Redis(connection_pool=get_redis_pool())

    # ------------------------------------------------------------------ #
    #  Conversation History (PostgreSQL)
    # ------------------------------------------------------------------ #

    async def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: str | None = None,
        metadata: dict | None = None,
        org_id: str | None = None,
    ) -> str:
        org_id = _current_org_id(org_id) or "default"
        async with self.session_factory() as db:  # type: ignore[union-attr]
            msg = ConversationMessage(
                session_id=session_id,
                org_id=org_id,
                role=role,
                content=content,
                agent_name=agent_name,
                metadata_=metadata or {},
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)
            logger.debug("Stored %s message for session %s (%d chars)", role, session_id, len(content))
            return str(msg.id)

    async def get_conversation(
        self,
        session_id: str,
        limit: int = DEFAULT_CONVERSATION_LIMIT,
        offset: int = 0,
        since: datetime | None = None,
        org_id: str | None = None,
    ) -> list[dict[str, Any]]:
        org_id = _current_org_id(org_id)
        limit = max(1, min(limit, MAX_CONVERSATION_LIMIT))
        offset = max(0, offset)
        async with self.session_factory() as db:  # type: ignore[union-attr]
            query = (
                select(ConversationMessage)
                .where(ConversationMessage.session_id == session_id)
                .order_by(ConversationMessage.created_at.asc())
                .offset(offset)
                .limit(limit)
            )
            if org_id:
                query = query.where(ConversationMessage.org_id == org_id)
            if since:
                query = query.where(ConversationMessage.created_at >= since)

            result = await db.execute(query)
            messages = result.scalars().all()

            return [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "agent_name": m.agent_name,
                    "metadata": m.metadata_ or {},
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ]

    async def delete_conversation(
        self,
        session_id: str,
        org_id: str | None = None,
    ) -> int:
        org_id = _current_org_id(org_id)
        async with self.session_factory() as db:  # type: ignore[union-attr]
            stmt = delete(ConversationMessage).where(ConversationMessage.session_id == session_id)
            if org_id:
                stmt = stmt.where(ConversationMessage.org_id == org_id)
            result = await db.execute(stmt)
            await db.commit()
            count = result.rowcount
            logger.info("Deleted %d conversation messages for session %s", count, session_id)
            return count

    async def count_conversation_messages(
        self,
        session_id: str,
        org_id: str | None = None,
    ) -> int:
        org_id = _current_org_id(org_id)
        async with self.session_factory() as db:  # type: ignore[union-attr]
            from sqlalchemy import func
            query = (
                select(func.count())
                .select_from(ConversationMessage)
                .where(ConversationMessage.session_id == session_id)
            )
            if org_id:
                query = query.where(ConversationMessage.org_id == org_id)
            result = await db.execute(query)
            return result.scalar() or 0

    # ------------------------------------------------------------------ #
    #  Long-term Memory (PostgreSQL)
    # ------------------------------------------------------------------ #

    async def remember(
        self,
        session_id: str,
        key: str,
        value: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: dict | None = None,
        ttl_seconds: int | None = None,
        org_id: str | None = None,
    ) -> None:
        org_id = _current_org_id(org_id) or "default"
        async with self.session_factory() as db:  # type: ignore[union-attr]
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds) if ttl_seconds else None

            where_clause = [
                LongTermMemory.session_id == session_id,
                LongTermMemory.key == key,
            ]
            if org_id:
                where_clause.append(LongTermMemory.org_id == org_id)
            existing = await db.execute(select(LongTermMemory).where(*where_clause))
            record = existing.scalar_one_or_none()

            if record:
                record.value = value
                record.memory_type = memory_type
                record.importance = importance
                record.metadata_ = metadata or {}
                record.expires_at = expires_at
                record.updated_at = datetime.now(UTC)
            else:
                db.add(LongTermMemory(
                    session_id=session_id,
                    org_id=org_id,
                    key=key,
                    value=value,
                    memory_type=memory_type,
                    importance=importance,
                    metadata_=metadata or {},
                    expires_at=expires_at,
                ))
            await db.commit()
            logger.debug("Remembered %s[%s] = %s (%.1f)", memory_type, key, value[:80], importance)

    async def recall(
        self,
        session_id: str,
        key: str,
        org_id: str | None = None,
    ) -> str | None:
        org_id = _current_org_id(org_id)
        async with self.session_factory() as db:  # type: ignore[union-attr]
            where_clause = [
                LongTermMemory.session_id == session_id,
                LongTermMemory.key == key,
            ]
            if org_id:
                where_clause.append(LongTermMemory.org_id == org_id)
            result = await db.execute(select(LongTermMemory).where(*where_clause))
            record = result.scalar_one_or_none()
            if record is None:
                return None
            if record.expires_at and record.expires_at < datetime.now(UTC):
                await db.delete(record)
                await db.commit()
                return None
            return record.value

    async def recall_all(
        self,
        session_id: str,
        memory_type: str | None = None,
        min_importance: float = DEFAULT_LONG_TERM_MIN_IMPORTANCE,
        limit: int = MAX_LONG_TERM_LIMIT,
        org_id: str | None = None,
    ) -> dict[str, str]:
        org_id = _current_org_id(org_id)
        limit = max(1, min(limit, MAX_LONG_TERM_LIMIT))
        async with self.session_factory() as db:  # type: ignore[union-attr]
            where_clause = [
                LongTermMemory.session_id == session_id,
                LongTermMemory.importance >= min_importance,
            ]
            if org_id:
                where_clause.append(LongTermMemory.org_id == org_id)
            query = (
                select(LongTermMemory)
                .where(*where_clause)
                .order_by(LongTermMemory.importance.desc())
                .limit(limit)
            )
            if memory_type:
                query = query.where(LongTermMemory.memory_type == memory_type)

            result = await db.execute(query)
            records = result.scalars().all()

            results: dict[str, str] = {}
            now = datetime.now(UTC)
            for r in records:
                if r.expires_at and r.expires_at < now:
                    await db.delete(r)
                    continue
                results[r.key] = r.value
            await db.commit()

            return results

    async def recall_by_type(
        self,
        session_id: str,
        memory_type: str,
        limit: int = MAX_LONG_TERM_LIMIT,
        org_id: str | None = None,
    ) -> list[dict[str, Any]]:
        org_id = _current_org_id(org_id)
        limit = max(1, min(limit, MAX_LONG_TERM_LIMIT))
        async with self.session_factory() as db:  # type: ignore[union-attr]
            where_clause = [
                LongTermMemory.session_id == session_id,
                LongTermMemory.memory_type == memory_type,
            ]
            if org_id:
                where_clause.append(LongTermMemory.org_id == org_id)
            result = await db.execute(
                select(LongTermMemory)
                .where(*where_clause)
                .order_by(LongTermMemory.importance.desc())
                .limit(limit)
            )
            return [
                {"key": r.key, "value": r.value, "importance": r.importance, "updated_at": r.updated_at.isoformat()}
                for r in result.scalars().all()
            ]

    async def forget(
        self,
        session_id: str,
        key: str,
        org_id: str | None = None,
    ) -> bool:
        org_id = _current_org_id(org_id)
        async with self.session_factory() as db:  # type: ignore[union-attr]
            stmt = delete(LongTermMemory).where(
                LongTermMemory.session_id == session_id,
                LongTermMemory.key == key,
            )
            if org_id:
                stmt = stmt.where(LongTermMemory.org_id == org_id)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount > 0

    async def clear_long_term(
        self,
        session_id: str,
        org_id: str | None = None,
    ) -> int:
        org_id = _current_org_id(org_id)
        async with self.session_factory() as db:  # type: ignore[union-attr]
            stmt = delete(LongTermMemory).where(LongTermMemory.session_id == session_id)
            if org_id:
                stmt = stmt.where(LongTermMemory.org_id == org_id)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

    # ------------------------------------------------------------------ #
    #  Agent-specific Memory (PostgreSQL)
    # ------------------------------------------------------------------ #

    async def set_agent_memory(
        self,
        session_id: str,
        agent_name: str,
        key: str,
        value: str,
        memory_type: str = "output",
        metadata: dict | None = None,
        org_id: str | None = None,
    ) -> None:
        org_id = _current_org_id(org_id) or "default"
        async with self.session_factory() as db:  # type: ignore[union-attr]
            where_clause = [
                AgentMemoryRecord.session_id == session_id,
                AgentMemoryRecord.agent_name == agent_name,
                AgentMemoryRecord.key == key,
            ]
            if org_id:
                where_clause.append(AgentMemoryRecord.org_id == org_id)
            existing = await db.execute(select(AgentMemoryRecord).where(*where_clause))
            record = existing.scalar_one_or_none()
            if record:
                record.value = value
                record.memory_type = memory_type
                record.metadata_ = metadata or {}
                record.updated_at = datetime.now(UTC)
            else:
                db.add(AgentMemoryRecord(
                    session_id=session_id,
                    org_id=org_id,
                    agent_name=agent_name,
                    key=key,
                    value=value,
                    memory_type=memory_type,
                    metadata_=metadata or {},
                ))
            await db.commit()

    async def get_agent_memory(
        self,
        session_id: str,
        agent_name: str,
        key: str,
        org_id: str | None = None,
    ) -> str | None:
        org_id = _current_org_id(org_id)
        async with self.session_factory() as db:  # type: ignore[union-attr]
            where_clause = [
                AgentMemoryRecord.session_id == session_id,
                AgentMemoryRecord.agent_name == agent_name,
                AgentMemoryRecord.key == key,
            ]
            if org_id:
                where_clause.append(AgentMemoryRecord.org_id == org_id)
            result = await db.execute(select(AgentMemoryRecord).where(*where_clause))
            record = result.scalar_one_or_none()
            return record.value if record else None

    async def get_all_agent_memory(
        self,
        session_id: str,
        agent_name: str,
        limit: int = 100,
        org_id: str | None = None,
    ) -> dict[str, str]:
        org_id = _current_org_id(org_id)
        limit = max(1, min(limit, 200))
        async with self.session_factory() as db:  # type: ignore[union-attr]
            where_clause = [
                AgentMemoryRecord.session_id == session_id,
                AgentMemoryRecord.agent_name == agent_name,
            ]
            if org_id:
                where_clause.append(AgentMemoryRecord.org_id == org_id)
            result = await db.execute(
                select(AgentMemoryRecord).where(*where_clause).limit(limit)
            )
            return {r.key: r.value for r in result.scalars().all()}

    async def clear_agent_memory(
        self,
        session_id: str,
        agent_name: str | None = None,
        org_id: str | None = None,
    ) -> int:
        org_id = _current_org_id(org_id)
        async with self.session_factory() as db:  # type: ignore[union-attr]
            stmt = delete(AgentMemoryRecord).where(AgentMemoryRecord.session_id == session_id)
            if agent_name:
                stmt = stmt.where(AgentMemoryRecord.agent_name == agent_name)
            if org_id:
                stmt = stmt.where(AgentMemoryRecord.org_id == org_id)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

    async def get_agent_memory_by_type(
        self,
        session_id: str,
        agent_name: str,
        memory_type: str,
        org_id: str | None = None,
    ) -> dict[str, str]:
        org_id = _current_org_id(org_id)
        async with self.session_factory() as db:  # type: ignore[union-attr]
            where_clause = [
                AgentMemoryRecord.session_id == session_id,
                AgentMemoryRecord.agent_name == agent_name,
                AgentMemoryRecord.memory_type == memory_type,
            ]
            if org_id:
                where_clause.append(AgentMemoryRecord.org_id == org_id)
            result = await db.execute(select(AgentMemoryRecord).where(*where_clause))
            return {r.key: r.value for r in result.scalars().all()}

    # ------------------------------------------------------------------ #
    #  Short-term / Working Memory (Redis)
    # ------------------------------------------------------------------ #

    async def set_short_term(self, session_id: str, key: str, value: str, ttl: int = SHORT_TERM_TTL) -> None:
        redis_key = f"st:{session_id}:{key}"
        await self.redis.setex(redis_key, ttl, value)

    async def get_short_term(self, session_id: str, key: str) -> str | None:
        redis_key = f"st:{session_id}:{key}"
        val = await self.redis.get(redis_key)
        return val

    async def delete_short_term(self, session_id: str, key: str) -> None:
        redis_key = f"st:{session_id}:{key}"
        await self.redis.delete(redis_key)

    async def clear_short_term(self, session_id: str) -> None:
        pattern = f"st:{session_id}:*"
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        if deleted:
            logger.debug("Cleared %d short-term keys for session %s", deleted, session_id)

    async def set_working_state(self, session_id: str, state: dict[str, Any], ttl: int = WORKING_TTL) -> None:
        redis_key = f"work:{session_id}"
        await self.redis.setex(redis_key, ttl, json.dumps(state, default=str))

    async def get_working_state(self, session_id: str) -> dict[str, Any] | None:
        redis_key = f"work:{session_id}"
        val = await self.redis.get(redis_key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return None

    async def clear_working_state(self, session_id: str) -> None:
        await self.redis.delete(f"work:{session_id}")

    # ------------------------------------------------------------------ #
    #  Distributed Lock (Redis)
    # ------------------------------------------------------------------ #

    async def acquire_lock(self, resource: str, ttl: int = LOCK_TTL) -> bool:
        lock_key = f"lock:{resource}"
        result = await self.redis.setnx(lock_key, "1")
        if result:
            await self.redis.expire(lock_key, ttl)
        return bool(result)

    async def release_lock(self, resource: str) -> None:
        await self.redis.delete(f"lock:{resource}")

    # ------------------------------------------------------------------ #
    #  Health Check
    # ------------------------------------------------------------------ #

    async def health(self) -> dict[str, Any]:
        results: dict[str, Any] = {"postgresql": False, "redis": False}
        try:
            async with asyncio.timeout(3):
                async with self.session_factory() as db:  # type: ignore[union-attr]
                    await db.execute(select(ConversationMessage).limit(1))
                    results["postgresql"] = True
        except TimeoutError:
            results["postgresql_error"] = "Health check timed out after 3s"
        except Exception as exc:
            results["postgresql_error"] = str(exc)

        try:
            async with asyncio.timeout(3):
                await self.redis.ping()
                results["redis"] = True
        except TimeoutError:
            results["redis_error"] = "Health check timed out after 3s"
        except Exception as exc:
            results["redis_error"] = str(exc)

        results["healthy"] = results["postgresql"] and results["redis"]
        return results

    # ------------------------------------------------------------------ #
    #  Utility: Store conversation + extract long-term facts
    # ------------------------------------------------------------------ #

    async def store_interaction(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        agent_name: str | None = None,
        facts: list[tuple[str, str, float]] | None = None,
        org_id: str | None = None,
    ) -> None:
        org_id = _current_org_id(org_id)
        await self.add_conversation_message(
            session_id, "user", user_message, agent_name=agent_name, org_id=org_id
        )
        await self.add_conversation_message(
            session_id, "assistant", assistant_message, agent_name=agent_name, org_id=org_id
        )
        await self.set_short_term(session_id, "last_user_input", user_message[:500])
        await self.set_short_term(session_id, "last_assistant_output", assistant_message[:500])

        if facts:
            for key, value, importance in facts:
                await self.remember(
                    session_id, key, value, memory_type="fact", importance=importance, org_id=org_id
                )
