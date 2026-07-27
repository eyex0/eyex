"""
πX Profile Event System — Event sourcing for all profile lifecycle changes.

Every change to the intelligence profile, ontology, KPIs, glossary, data sources,
or semantic mappings generates an event. Events enable:
  - Full audit trail
  - Replay/reconstruction of profile state
  - Triggers for downstream engines (memory, knowledge graph, decisions)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.intelligence_profile.events")

# Event type constants
class ProfileEventType:
    PROFILE_CREATED = "profile.created"
    PROFILE_ACTIVATED = "profile.activated"
    PROFILE_UPDATED = "profile.updated"
    PROFILE_ARCHIVED = "profile.archived"
    ONTOLOGY_ADDED = "ontology.added"
    ONTOLOGY_UPDATED = "ontology.updated"
    ONTOLOGY_DELETED = "ontology.deleted"
    KPI_ADDED = "kpi.added"
    KPI_UPDATED = "kpi.updated"
    KPI_DELETED = "kpi.deleted"
    GLOSSARY_LEARNED = "glossary.learned"
    GLOSSARY_UPDATED = "glossary.updated"
    DATASOURCE_CONNECTED = "datasource.connected"
    DATASOURCE_UPDATED = "datasource.updated"
    SEMANTIC_MAPPING_INFERRED = "semantic.mapping.inferred"
    SEMANTIC_MAPPING_CORRECTED = "semantic.mapping.corrected"
    VERSION_CREATED = "version.created"
    AGENT_SUGGESTED = "agent.suggested"
    CONFIDENCE_RECALCULATED = "confidence.recalculated"
    TEMPLATE_APPLIED = "template.applied"


class EventManager:
    """Event system for the intelligence profile lifecycle."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def emit(
        self,
        organization_id: str,
        event_type: str,
        profile_id: str | None = None,
        event_data: dict | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        triggered_by: str = "system",
        user_id: str | None = None,
    ) -> dict:
        event_id = str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO profile_events "
                    "(id, organization_id, profile_id, event_type, event_data, "
                    "entity_type, entity_id, triggered_by, user_id) "
                    "VALUES (:id, :org_id, :pid, :etype, :data, :ent_type, :ent_id, :by, :uid)"
                ),
                {
                    "id": event_id, "org_id": organization_id,
                    "pid": profile_id, "etype": event_type,
                    "data": json.dumps(event_data or {}),
                    "ent_type": entity_type, "ent_id": entity_id,
                    "by": triggered_by, "uid": user_id,
                },
            )
            await db.commit()
        logger.debug("Emitted event %s for org %s", event_type, organization_id)
        return {"id": event_id, "event_type": event_type}

    async def get_events(
        self,
        organization_id: str,
        profile_id: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        conditions = ["organization_id = :org_id"]
        params: dict[str, Any] = {"org_id": organization_id, "limit": limit, "offset": offset}
        if profile_id:
            conditions.append("profile_id = :pid")
            params["pid"] = profile_id
        if event_type:
            conditions.append("event_type = :etype")
            params["etype"] = event_type
        where = " AND ".join(conditions)

        async with self.session_factory() as db:
            result = await db.execute(
                text(
                    f"SELECT id, profile_id, event_type, event_data, entity_type, entity_id, "
                    f"triggered_by, user_id, created_at FROM profile_events "
                    f"WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ),
                params,
            )
            return [
                {
                    "id": str(r[0]),
                    "profile_id": str(r[1]) if r[1] else None,
                    "event_type": r[2],
                    "event_data": r[3] if isinstance(r[3], dict) else json.loads(r[3] or "{}"),
                    "entity_type": r[4],
                    "entity_id": str(r[5]) if r[5] else None,
                    "triggered_by": r[6],
                    "user_id": str(r[7]) if r[7] else None,
                    "created_at": str(r[8]),
                }
                for r in result.fetchall()
            ]

    async def get_event_timeline(self, organization_id: str, profile_id: str, limit: int = 100) -> list[dict]:
        """Get a chronological event timeline for a profile."""
        return await self.get_events(organization_id, profile_id, limit=limit)
