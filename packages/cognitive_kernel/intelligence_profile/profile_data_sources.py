"""
πX Data Source Manager — Connected systems, datasets, metadata.

Tracks every data source an organization connects to πX.
Stores discovered schemas and semantic mappings (column→entity).
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.intelligence_profile.data_sources")


class DataSourceManager:
    """Manages connected data sources for an intelligence profile."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def add_source(
        self, organization_id: str, profile_id: str,
        name: str, source_type: str,
        connection_config: dict | None = None,
        schema_metadata: dict | None = None,
        semantic_mappings: list | None = None,
        confidence: float = 0.5, status: str = "discovered",
    ) -> dict:
        source_id = str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO profile_data_sources "
                    "(id, organization_id, profile_id, name, source_type, "
                    "connection_config, schema_metadata, semantic_mappings, confidence, status) "
                    "VALUES (:id, :org_id, :pid, :name, :stype, "
                    ":config, :schema, :mappings, :conf, :status)"
                ),
                {
                    "id": source_id, "org_id": organization_id, "pid": profile_id,
                    "name": name, "stype": source_type,
                    "config": json.dumps(connection_config or {}),
                    "schema": json.dumps(schema_metadata or {}),
                    "mappings": json.dumps(semantic_mappings or []),
                    "conf": confidence, "status": status,
                },
            )
            await db.commit()
        return {"id": source_id, "name": name, "source_type": source_type}

    async def get_sources(
        self, organization_id: str, profile_id: str,
        source_type: str | None = None,
    ) -> list[dict]:
        conditions = ["organization_id = :org_id", "profile_id = :pid"]
        params: dict[str, Any] = {"org_id": organization_id, "pid": profile_id}
        if source_type:
            conditions.append("source_type = :stype")
            params["stype"] = source_type
        where = " AND ".join(conditions)

        async with self.session_factory() as db:
            result = await db.execute(
                text(f"SELECT * FROM profile_data_sources WHERE {where} ORDER BY created_at DESC"),
                params,
            )
            return [self._row_to_dict(r) for r in result.fetchall()]

    async def update_source(self, organization_id: str, source_id: str, updates: dict) -> dict | None:
        allowed = {"name", "source_type", "connection_config", "schema_metadata", "semantic_mappings", "confidence", "status"}
        set_clauses = []
        params: dict[str, Any] = {"id": source_id, "org_id": organization_id}
        for key, value in updates.items():
            if key in allowed:
                set_clauses.append(f"{key} = :{key}")
                params[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
        if not set_clauses:
            return None
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")

        async with self.session_factory() as db:
            await db.execute(
                text(f"UPDATE profile_data_sources SET {', '.join(set_clauses)} WHERE id = :id AND organization_id = :org_id"),
                params,
            )
            await db.commit()
            result = await db.execute(
                text("SELECT * FROM profile_data_sources WHERE id = :id AND organization_id = :org_id"),
                {"id": source_id, "org_id": organization_id},
            )
            row = result.fetchone()
            return self._row_to_dict(row) if row else None

    async def delete_source(self, organization_id: str, source_id: str) -> bool:
        async with self.session_factory() as db:
            result = await db.execute(
                text("DELETE FROM profile_data_sources WHERE id = :id AND organization_id = :org_id"),
                {"id": source_id, "org_id": organization_id},
            )
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    def _row_to_dict(row: Any) -> dict:
        return {
            "id": str(row[0]),
            "organization_id": str(row[1]),
            "profile_id": str(row[2]),
            "name": row[3],
            "source_type": row[4],
            "connection_config": row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
            "schema_metadata": row[6] if isinstance(row[6], dict) else json.loads(row[6] or "{}"),
            "semantic_mappings": row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]"),
            "confidence": float(row[8] or 0.5),
            "status": row[9],
            "created_at": str(row[10]) if row[10] else None,
            "updated_at": str(row[11]) if row[11] else None,
        }
