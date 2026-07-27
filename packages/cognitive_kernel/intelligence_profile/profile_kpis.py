"""
πX KPI Manager — Company KPIs with definitions, formulas, targets.

KPIs are fully adaptive: each organization defines its own metrics.
Formulas are stored as structured JSONB for computation.
Targets include value, unit, period, and direction.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.intelligence_profile.kpis")


class KPIManager:
    """Manages company KPIs for an intelligence profile."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def add_kpi(
        self, organization_id: str, profile_id: str,
        name: str, label: str | None = None,
        category: str | None = None,
        definition: str | None = None,
        formula: dict | None = None,
        target: dict | None = None,
        unit: str | None = None,
        aliases: list | None = None,
        confidence: float = 0.5, source: str = "inferred",
    ) -> dict:
        kpi_id = str(uuid.uuid4())
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO profile_kpis "
                    "(id, organization_id, profile_id, name, label, category, definition, "
                    "formula, target, unit, aliases, confidence, source) "
                    "VALUES (:id, :org_id, :pid, :name, :label, :category, :def, "
                    ":formula, :target, :unit, :aliases, :conf, :source)"
                ),
                {
                    "id": kpi_id, "org_id": organization_id, "pid": profile_id,
                    "name": name, "label": label, "category": category,
                    "def": definition,
                    "formula": json.dumps(formula or {}),
                    "target": json.dumps(target or {}),
                    "unit": unit,
                    "aliases": json.dumps(aliases or []),
                    "conf": confidence, "source": source,
                },
            )
            await db.commit()
        return {"id": kpi_id, "name": name, "confidence": confidence}

    async def get_kpis(
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
                text(f"SELECT * FROM profile_kpis WHERE {where} ORDER BY confidence DESC"),
                params,
            )
            return [self._row_to_dict(r) for r in result.fetchall()]

    async def update_kpi(self, organization_id: str, kpi_id: str, updates: dict) -> dict | None:
        allowed = {"name", "label", "category", "definition", "formula", "target", "unit", "aliases", "confidence", "source"}
        set_clauses = []
        params: dict[str, Any] = {"id": kpi_id, "org_id": organization_id}
        for key, value in updates.items():
            if key in allowed:
                set_clauses.append(f"{key} = :{key}")
                params[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
        if not set_clauses:
            return None
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")

        async with self.session_factory() as db:
            await db.execute(
                text(f"UPDATE profile_kpis SET {', '.join(set_clauses)} WHERE id = :id AND organization_id = :org_id"),
                params,
            )
            await db.commit()
        async with self.session_factory() as db:
            result = await db.execute(
                text("SELECT * FROM profile_kpis WHERE id = :id AND organization_id = :org_id"),
                {"id": kpi_id, "org_id": organization_id},
            )
            row = result.fetchone()
            return self._row_to_dict(row) if row else None

    async def delete_kpi(self, organization_id: str, kpi_id: str) -> bool:
        async with self.session_factory() as db:
            result = await db.execute(
                text("DELETE FROM profile_kpis WHERE id = :id AND organization_id = :org_id"),
                {"id": kpi_id, "org_id": organization_id},
            )
            await db.commit()
            return result.rowcount > 0

    async def find_by_alias(self, organization_id: str, profile_id: str, term: str) -> dict | None:
        term_lower = term.lower().strip()
        kpis = await self.get_kpis(organization_id, profile_id)
        for kpi in kpis:
            if kpi["name"].lower() == term_lower:
                return kpi
            for alias in kpi.get("aliases", []):
                if alias.lower() == term_lower:
                    return kpi
        return None

    @staticmethod
    def _row_to_dict(row: Any) -> dict:
        return {
            "id": str(row[0]),
            "organization_id": str(row[1]),
            "profile_id": str(row[2]),
            "name": row[3],
            "label": row[4],
            "category": row[5],
            "definition": row[6],
            "formula": row[7] if isinstance(row[7], dict) else json.loads(row[7] or "{}"),
            "target": row[8] if isinstance(row[8], dict) else json.loads(row[8] or "{}"),
            "unit": row[9],
            "aliases": row[10] if isinstance(row[10], list) else json.loads(row[10] or "[]"),
            "confidence": float(row[11] or 0.5),
            "source": row[12],
            "created_at": str(row[13]) if row[13] else None,
            "updated_at": str(row[14]) if row[14] else None,
        }
