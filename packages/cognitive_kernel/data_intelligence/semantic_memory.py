"""
πX Semantic Memory — Learns from corrections and remembers company-specific mappings.

When a user says "REV means Net Revenue", πX stores it and automatically
understands REV in all future files.

Integrates with the existing profile_semantic_history table and profile_glossary.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.data_intelligence.semantic_memory")


class SemanticMemory:
    """Company-specific semantic memory — learns and remembers mappings."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def learn_correction(
        self,
        organization_id: str,
        column_name: str,
        correct_entity: str,
        correct_meaning: str | None = None,
        corrected_by: str | None = None,
        profile_id: str | None = None,
    ) -> dict:
        """
        Learn from a user correction: "REV means Net Revenue"
        Stores in profile_semantic_history and updates profile_glossary.
        """
        # Record in semantic history
        record_id = str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO profile_semantic_history "
                    "(id, organization_id, profile_id, column_name, inferred_entity, inferred_confidence, "
                    "corrected_entity, corrected_by, corrected_at) "
                    "VALUES (:id, :org_id, :pid, :col, NULL, 0.0, :cent, :cby, now())"
                ),
                {
                    "id": record_id, "org_id": organization_id, "pid": profile_id,
                    "col": column_name, "cent": correct_entity, "cby": corrected_by,
                },
            )
            await db.commit()

        logger.info("Learned correction: '%s' → '%s' for org %s", column_name, correct_entity, organization_id)
        return {"learned": True, "column": column_name, "entity": correct_entity}

    async def add_glossary_term(
        self,
        organization_id: str,
        profile_id: str,
        term: str,
        definition: str | None = None,
        aliases: list | None = None,
        maps_to_entity: str | None = None,
    ) -> dict:
        """Add a company-specific glossary term (e.g., "REV" = "Net Revenue")."""
        term_id = str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO profile_glossary "
                    "(id, organization_id, profile_id, term, definition, aliases, synonyms, "
                    "category, maps_to_entity, confidence, source) "
                    "VALUES (:id, :org_id, :pid, :term, :def, :aliases, '[]', 'user_defined', :entity, 1.0, 'user_defined')"
                ),
                {
                    "id": term_id, "org_id": organization_id, "pid": profile_id,
                    "term": term, "def": definition,
                    "aliases": json.dumps(aliases or []),
                    "entity": maps_to_entity,
                },
            )
            await db.commit()
        return {"id": term_id, "term": term, "confidence": 1.0}

    async def get_learned_mappings(self, organization_id: str, limit: int = 100) -> list[dict]:
        """Get all user-corrected mappings for an organization."""
        async with self.session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT column_name, corrected_entity, corrected_by, corrected_at "
                    "FROM profile_semantic_history WHERE organization_id = :org_id "
                    "AND corrected_entity IS NOT NULL ORDER BY corrected_at DESC LIMIT :limit"
                ),
                {"org_id": organization_id, "limit": limit},
            )
            return [
                {"column_name": r[0], "entity": r[1], "corrected_by": str(r[2]) if r[2] else None, "corrected_at": str(r[3])}
                for r in result.fetchall()
            ]

    async def lookup_mapping(self, organization_id: str, column_name: str) -> dict | None:
        """Look up a previously learned mapping for a column."""
        async with self.session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT corrected_entity FROM profile_semantic_history "
                    "WHERE organization_id = :org_id AND column_name = :col "
                    "AND corrected_entity IS NOT NULL ORDER BY corrected_at DESC LIMIT 1"
                ),
                {"org_id": organization_id, "col": column_name},
            )
            row = result.fetchone()
            if row:
                return {"column_name": column_name, "entity": row[0], "source": "learned"}
            return None

    async def get_learning_stats(self, organization_id: str) -> dict:
        """Get statistics about what πX has learned about this company."""
        async with self.session_factory() as db:
            total = await db.execute(
                text("SELECT COUNT(*) FROM profile_semantic_history WHERE organization_id = :org_id"),
                {"org_id": organization_id},
            )
            corrected = await db.execute(
                text("SELECT COUNT(*) FROM profile_semantic_history WHERE organization_id = :org_id AND corrected_entity IS NOT NULL"),
                {"org_id": organization_id},
            )
            glossary_count = await db.execute(
                text("SELECT COUNT(*) FROM profile_glossary WHERE organization_id = :org_id AND source = 'user_defined'"),
                {"org_id": organization_id},
            )
        return {
            "total_mappings_seen": total.scalar() or 0,
            "user_corrections": corrected.scalar() or 0,
            "custom_glossary_terms": glossary_count.scalar() or 0,
        }
