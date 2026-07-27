"""
πX Semantic Learning History — Tracks how column→entity mappings evolve over time.

Enables the system to:
  - Learn from user corrections (if user corrects "Cust Name" from "vendor" to "customer",
    the system records this and uses it for future inference)
  - Improve inference accuracy over time
  - Provide explainability for why a mapping was made
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.intelligence_profile.semantic_history")


class SemanticHistoryManager:
    """Tracks semantic mapping history for continuous learning."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def record_mapping(
        self,
        organization_id: str,
        column_name: str,
        inferred_entity: str | None = None,
        inferred_confidence: float = 0.0,
        source_name: str | None = None,
        sample_values: list | None = None,
        semantic_type: str | None = None,
        profile_id: str | None = None,
    ) -> dict:
        record_id = str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO profile_semantic_history "
                    "(id, organization_id, profile_id, column_name, source_name, "
                    "inferred_entity, inferred_confidence, sample_values, semantic_type) "
                    "VALUES (:id, :org_id, :pid, :col, :src, :entity, :conf, :samples, :stype)"
                ),
                {
                    "id": record_id, "org_id": organization_id, "pid": profile_id,
                    "col": column_name, "src": source_name,
                    "entity": inferred_entity, "conf": inferred_confidence,
                    "samples": json.dumps(sample_values or []),
                    "stype": semantic_type,
                },
            )
            await db.commit()
        return {"id": record_id, "column_name": column_name, "inferred_entity": inferred_entity}

    async def record_correction(
        self,
        organization_id: str,
        record_id: str,
        corrected_entity: str,
        corrected_by: str,
    ) -> dict | None:
        """Record a user correction for a semantic mapping."""
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "UPDATE profile_semantic_history "
                    "SET corrected_entity = :entity, corrected_by = :by, corrected_at = now() "
                    "WHERE id = :id AND organization_id = :org_id"
                ),
                {"id": record_id, "org_id": organization_id, "entity": corrected_entity, "by": corrected_by},
            )
            await db.commit()
            result = await db.execute(
                text("SELECT * FROM profile_semantic_history WHERE id = :id AND organization_id = :org_id"),
                {"id": record_id, "org_id": organization_id},
            )
            row = result.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    async def get_history(
        self,
        organization_id: str,
        column_name: str | None = None,
        profile_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conditions = ["organization_id = :org_id"]
        params: dict[str, Any] = {"org_id": organization_id, "limit": limit}
        if column_name:
            conditions.append("column_name = :col")
            params["col"] = column_name
        if profile_id:
            conditions.append("profile_id = :pid")
            params["pid"] = profile_id
        where = " AND ".join(conditions)

        async with self.session_factory() as db:
            result = await db.execute(
                text(f"SELECT * FROM profile_semantic_history WHERE {where} ORDER BY created_at DESC LIMIT :limit"),
                params,
            )
            return [self._row_to_dict(r) for r in result.fetchall()]

    async def get_corrections(self, organization_id: str, limit: int = 100) -> list[dict]:
        """Get all user corrections — used for training/improving inference."""
        async with self.session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT * FROM profile_semantic_history "
                    "WHERE organization_id = :org_id AND corrected_entity IS NOT NULL "
                    "ORDER BY corrected_at DESC LIMIT :limit"
                ),
                {"org_id": organization_id, "limit": limit},
            )
            return [self._row_to_dict(r) for r in result.fetchall()]

    async def get_learning_stats(self, organization_id: str) -> dict:
        """Get statistics about semantic learning for an organization."""
        async with self.session_factory() as db:
            total = await db.execute(
                text("SELECT COUNT(*) FROM profile_semantic_history WHERE organization_id = :org_id"),
                {"org_id": organization_id},
            )
            corrected = await db.execute(
                text("SELECT COUNT(*) FROM profile_semantic_history WHERE organization_id = :org_id AND corrected_entity IS NOT NULL"),
                {"org_id": organization_id},
            )
            avg_conf = await db.execute(
                text("SELECT AVG(inferred_confidence) FROM profile_semantic_history WHERE organization_id = :org_id"),
                {"org_id": organization_id},
            )
        return {
            "total_mappings": total.scalar() or 0,
            "user_corrections": corrected.scalar() or 0,
            "avg_inference_confidence": float(avg_conf.scalar() or 0),
            "correction_rate": (corrected.scalar() or 0) / max(total.scalar() or 1, 1),
        }

    @staticmethod
    def _row_to_dict(row: Any) -> dict:
        return {
            "id": str(row[0]),
            "organization_id": str(row[1]),
            "profile_id": str(row[2]) if row[2] else None,
            "column_name": row[3],
            "source_name": row[4],
            "inferred_entity": row[5],
            "inferred_confidence": float(row[6] or 0.0),
            "corrected_entity": row[7],
            "corrected_by": str(row[8]) if row[8] else None,
            "corrected_at": str(row[9]) if row[9] else None,
            "sample_values": row[10] if isinstance(row[10], list) else json.loads(row[10] or "[]"),
            "semantic_type": row[11],
            "created_at": str(row[12]),
        }
