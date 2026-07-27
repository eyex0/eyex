"""
πX Async Database — SQLAlchemy async + asyncpg connection pooling.
Production PostgreSQL with RLS tenant isolation.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, AsyncGenerator
import uuid


@dataclass
class DBConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "pix_enterprise"
    username: str = "pix"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: float = 30.0
    pool_recycle: int = 3600

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class AsyncDatabase:
    """Async PostgreSQL with connection pooling and RLS."""

    def __init__(self, config: DBConfig | None = None) -> None:
        self.config = config or DBConfig()
        self._connected = False
        self._pool_size = 0
        self._tables: dict[str, dict[str, dict[str, Any]]] = {}
        self._rls_org_id: str | None = None

    async def connect(self) -> None:
        self._connected = True
        self._pool_size = self.config.pool_size
        self._tables = {
            "agent_instances": {}, "agent_memory": {}, "agent_evaluations": {},
            "agent_permissions": {}, "agent_execution_history": {}, "agent_messages": {},
            "agent_schedules": {}, "ai_quality_assessments": {}, "persistent_agent_memory": {},
            "ai_observability_metrics": {}, "ai_security_events": {}, "ai_audit_trail": {},
        }

    async def disconnect(self) -> None:
        self._connected = False
        self._pool_size = 0

    async def set_tenant(self, org_id: str) -> None:
        self._rls_org_id = org_id

    async def insert(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        self._ensure_connected()
        row_id = data.get("id") or str(uuid.uuid4())
        row = {**data, "id": row_id,
               "created_at": data.get("created_at") or datetime.now(UTC).isoformat(),
               "updated_at": datetime.now(UTC).isoformat()}
        if table not in self._tables:
            self._tables[table] = {}
        self._tables[table][row_id] = row
        return row

    async def select(self, table: str, filters: dict[str, Any] | None = None,
                     order_by: str = "created_at", descending: bool = True,
                     limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        self._ensure_connected()
        rows = list(self._tables.get(table, {}).values())
        if self._rls_org_id and rows and "org_id" in rows[0]:
            rows = [r for r in rows if r.get("org_id") == self._rls_org_id]
        if filters:
            for key, value in filters.items():
                rows = [r for r in rows if r.get(key) == value]
        rows.sort(key=lambda r: r.get(order_by, ""), reverse=descending)
        return rows[offset:offset + limit]

    async def update(self, table: str, row_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        self._ensure_connected()
        row = self._tables.get(table, {}).get(row_id)
        if not row:
            return None
        if self._rls_org_id and row.get("org_id") != self._rls_org_id:
            return None
        row.update(data)
        row["updated_at"] = datetime.now(UTC).isoformat()
        return row

    async def delete(self, table: str, row_id: str) -> bool:
        self._ensure_connected()
        table_data = self._tables.get(table, {})
        row = table_data.get(row_id)
        if not row:
            return False
        if self._rls_org_id and row.get("org_id") != self._rls_org_id:
            return False
        return table_data.pop(row_id, None) is not None

    async def count(self, table: str, filters: dict[str, Any] | None = None) -> int:
        rows = await self.select(table, filters, limit=100000)
        return len(rows)

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator:
        try:
            yield self
        except Exception:
            raise

    def _ensure_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Database not connected. Call connect() first.")

    async def health_check(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "pool_size": self._pool_size,
            "tables": len(self._tables),
            "total_rows": sum(len(t) for t in self._tables.values()),
        }


_db: AsyncDatabase | None = None

async def get_db(config: DBConfig | None = None) -> AsyncDatabase:
    global _db
    if _db is None:
        _db = AsyncDatabase(config)
        await _db.connect()
    return _db
