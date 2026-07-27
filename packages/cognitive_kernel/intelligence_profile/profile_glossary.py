"""
πX Glossary Manager — Company terminology, aliases, synonyms.

The business language layer. When a user says "net_rev" or "sell-out",
the glossary maps it to the canonical term and entity.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.intelligence_profile.glossary")


class GlossaryManager:
    """Manages company-specific terminology for an intelligence profile."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def add_term(
        self, organization_id: str, profile_id: str,
        term: str, definition: str | None = None,
        aliases: list | None = None, synonyms: list | None = None,
        category: str | None = None, maps_to_entity: str | None = None,
        confidence: float = 0.5, source: str = "inferred",
    ) -> dict:
        term_id = str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO profile_glossary "
                    "(id, organization_id, profile_id, term, definition, aliases, synonyms, "
                    "category, maps_to_entity, confidence, source) "
                    "VALUES (:id, :org_id, :pid, :term, :def, :aliases, :synonyms, "
                    ":category, :entity, :conf, :source)"
                ),
                {
                    "id": term_id, "org_id": organization_id, "pid": profile_id,
                    "term": term, "def": definition,
                    "aliases": json.dumps(aliases or []),
                    "synonyms": json.dumps(synonyms or []),
                    "category": category, "entity": maps_to_entity,
                    "conf": confidence, "source": source,
                },
            )
            await db.commit()
        return {"id": term_id, "term": term, "confidence": confidence}

    async def get_terms(
        self, organization_id: str, profile_id: str,
        category: str | None = None,
    ) -> list[dict]:
        conditions = ["organization_id = :org_id", "profile_id = :pid"]
        params: dict[str, Any] = {"org_id": organization_id, "pid": profile_id}
        if category:
            conditions.append("category = :category")
            params["category"] = category
        where = " AND ".join(conditions)

        async with self.session_factory() as db:
            result = await db.execute(
                text(f"SELECT * FROM profile_glossary WHERE {where} ORDER BY term"),
                params,
            )
            return [self._row_to_dict(r) for r in result.fetchall()]

    async def update_term(self, organization_id: str, term_id: str, updates: dict) -> dict | None:
        allowed = {"term", "definition", "aliases", "synonyms", "category", "maps_to_entity", "confidence", "source"}
        set_clauses = []
        params: dict[str, Any] = {"id": term_id, "org_id": organization_id}
        for key, value in updates.items():
            if key in allowed:
                set_clauses.append(f"{key} = :{key}")
                params[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
        if not set_clauses:
            return None
        set_clauses.append("updated_at = now()")

        async with self.session_factory() as db:
            await db.execute(
                text(f"UPDATE profile_glossary SET {', '.join(set_clauses)} WHERE id = :id AND organization_id = :org_id"),
                params,
            )
            await db.commit()
            result = await db.execute(
                text("SELECT * FROM profile_glossary WHERE id = :id AND organization_id = :org_id"),
                {"id": term_id, "org_id": organization_id},
            )
            row = result.fetchone()
            return self._row_to_dict(row) if row else None

    async def delete_term(self, organization_id: str, term_id: str) -> bool:
        async with self.session_factory() as db:
            result = await db.execute(
                text("DELETE FROM profile_glossary WHERE id = :id AND organization_id = :org_id"),
                {"id": term_id, "org_id": organization_id},
            )
            await db.commit()
            return result.rowcount > 0

    async def resolve_term(self, organization_id: str, profile_id: str, raw_term: str) -> dict | None:
        """Resolve a raw business term to its canonical form."""
        raw_lower = raw_term.lower().strip()
        terms = await self.get_terms(organization_id, profile_id)
        for t in terms:
            if t["term"].lower() == raw_lower:
                return t
            for alias in t.get("aliases", []):
                if alias.lower() == raw_lower:
                    return t
            for synonym in t.get("synonyms", []):
                if synonym.lower() == raw_lower:
                    return t
        return None

    @staticmethod
    def _row_to_dict(row: Any) -> dict:
        return {
            "id": str(row[0]),
            "organization_id": str(row[1]),
            "profile_id": str(row[2]),
            "term": row[3],
            "definition": row[4],
            "aliases": row[5] if isinstance(row[5], list) else json.loads(row[5] or "[]"),
            "synonyms": row[6] if isinstance(row[6], list) else json.loads(row[6] or "[]"),
            "category": row[7],
            "maps_to_entity": row[8],
            "confidence": float(row[9] or 0.5),
            "source": row[10],
            "created_at": str(row[11]) if row[11] else None,
            "updated_at": str(row[12]) if row[12] else None,
        }
