"""
πX Ontology Manager — Custom entities, relationships, and business concepts.

Each organization defines its own entity types dynamically. No predefined schemas.
The ontology stores entity_type (free-form), properties_schema (JSONB), relationships,
and aliases — all with confidence scores and source tracking.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.intelligence_profile.ontology")


class OntologyManager:
    """Manages custom entity types for an organization's intelligence profile."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def add_entity(
        self, organization_id: str, profile_id: str,
        entity_type: str, entity_label: str | None = None,
        properties_schema: dict | None = None,
        relationships: list | None = None,
        aliases: list | None = None,
        confidence: float = 0.5, source: str = "inferred",
    ) -> dict:
        entity_id = str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO profile_ontology "
                    "(id, organization_id, profile_id, entity_type, entity_label, "
                    "properties_schema, relationships, aliases, confidence, source) "
                    "VALUES (:id, :org_id, :pid, :etype, :elabel, "
                    ":pschema, :rels, :aliases, :conf, :source)"
                ),
                {
                    "id": entity_id, "org_id": organization_id, "pid": profile_id,
                    "etype": entity_type, "elabel": entity_label,
                    "pschema": json.dumps(properties_schema or {}),
                    "rels": json.dumps(relationships or []),
                    "aliases": json.dumps(aliases or []),
                    "conf": confidence, "source": source,
                },
            )
            await db.commit()
        logger.info("Added entity '%s' to profile %s", entity_type, profile_id)
        return {"id": entity_id, "entity_type": entity_type, "confidence": confidence}

    async def get_entities(
        self, organization_id: str, profile_id: str,
        entity_type: str | None = None,
    ) -> list[dict]:
        conditions = ["organization_id = :org_id", "profile_id = :pid"]
        params: dict[str, Any] = {"org_id": organization_id, "pid": profile_id}
        if entity_type:
            conditions.append("entity_type = :etype")
            params["etype"] = entity_type
        where = " AND ".join(conditions)

        async with self.session_factory() as db:
            result = await db.execute(
                text(f"SELECT * FROM profile_ontology WHERE {where} ORDER BY confidence DESC"),
                params,
            )
            return [self._row_to_dict(r) for r in result.fetchall()]

    async def update_entity(
        self, organization_id: str, entity_id: str, updates: dict,
    ) -> dict | None:
        allowed = {"entity_label", "properties_schema", "relationships", "aliases", "confidence", "source"}
        set_clauses = []
        params: dict[str, Any] = {"id": entity_id, "org_id": organization_id}
        for key, value in updates.items():
            if key in allowed:
                set_clauses.append(f"{key} = :{key}")
                params[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
        if not set_clauses:
            return None
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")

        async with self.session_factory() as db:
            await db.execute(
                text(f"UPDATE profile_ontology SET {', '.join(set_clauses)} WHERE id = :id AND organization_id = :org_id"),
                params,
            )
            await db.commit()
        return await self.get_entity_by_id(organization_id, entity_id)

    async def delete_entity(self, organization_id: str, entity_id: str) -> bool:
        async with self.session_factory() as db:
            result = await db.execute(
                text("DELETE FROM profile_ontology WHERE id = :id AND organization_id = :org_id"),
                {"id": entity_id, "org_id": organization_id},
            )
            await db.commit()
            return result.rowcount > 0

    async def get_entity_by_id(self, organization_id: str, entity_id: str) -> dict | None:
        async with self.session_factory() as db:
            result = await db.execute(
                text("SELECT * FROM profile_ontology WHERE id = :id AND organization_id = :org_id"),
                {"id": entity_id, "org_id": organization_id},
            )
            row = result.fetchone()
            return self._row_to_dict(row) if row else None

    async def find_by_alias(self, organization_id: str, profile_id: str, term: str) -> dict | None:
        """Find an entity by matching a term against its aliases or type."""
        term_lower = term.lower().strip()
        entities = await self.get_entities(organization_id, profile_id)
        for entity in entities:
            if entity["entity_type"].lower() == term_lower:
                return entity
            for alias in entity.get("aliases", []):
                if alias.lower() == term_lower:
                    return entity
        return None

    @staticmethod
    def _row_to_dict(row: Any) -> dict:
        return {
            "id": str(row[0]),
            "organization_id": str(row[1]),
            "profile_id": str(row[2]),
            "entity_type": row[3],
            "entity_label": row[4],
            "properties_schema": row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
            "relationships": row[6] if isinstance(row[6], list) else json.loads(row[6] or "[]"),
            "aliases": row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]"),
            "confidence": float(row[8] or 0.5),
            "source": row[9],
            "created_at": str(row[10]) if row[10] else None,
            "updated_at": str(row[11]) if row[11] else None,
        }
