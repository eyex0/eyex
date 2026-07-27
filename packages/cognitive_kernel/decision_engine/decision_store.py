"""πX Decision Store — PostgreSQL persistence for decisions."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("pix.decision.store")


class DecisionStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def create(self, decision: dict) -> str:
        decision_id = decision.get("decision_id", str(uuid.uuid4()))
        async with self.session_factory() as db:
            await db.execute(
                text(
                    "INSERT INTO decisions (id, org_id, title, category, status, problem_definition, "
                    "business_context, evidence, alternatives, reasoning, risk_analysis, "
                    "recommendation, confidence_score, created_by) "
                    "VALUES (:id, :org_id, :title, :category, :status, :problem, :ctx, :evidence, "
                    ":alternatives, :reasoning, :risks, :recommendation, :confidence, :created_by)"
                ),
                {
                    "id": decision_id,
                    "org_id": decision.get("org_id", ""),
                    "title": decision.get("question", "")[:256],
                    "category": decision.get("category", "general"),
                    "status": "pending",
                    "problem": decision.get("question", ""),
                    "ctx": json.dumps(decision.get("context_summary", {})),
                    "evidence": json.dumps(decision.get("evidence", [])),
                    "alternatives": json.dumps(decision.get("alternatives", [])),
                    "reasoning": json.dumps(decision.get("reasoning_chain", [])),
                    "risks": json.dumps(decision.get("risks", [])),
                    "recommendation": decision.get("recommendation", ""),
                    "confidence": decision.get("confidence", 0.0),
                    "created_by": decision.get("created_by"),
                },
            )
            await db.commit()
        return decision_id

    async def get(self, decision_id: str) -> dict | None:
        async with self.session_factory() as db:
            result = await db.execute(
                text("SELECT * FROM decisions WHERE id = :id"), {"id": decision_id}
            )
            row = result.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    async def list(self, org_id: str, status: str | None = None, limit: int = 20, offset: int = 0) -> list[dict]:
        conditions = ["org_id = :org_id"]
        params: dict[str, Any] = {"org_id": org_id, "limit": limit, "offset": offset}
        if status:
            conditions.append("status = :status")
            params["status"] = status
        where = " AND ".join(conditions)
        async with self.session_factory() as db:
            result = await db.execute(
                text(f"SELECT * FROM decisions WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
                params,
            )
            return [self._row_to_dict(r) for r in result.fetchall()]

    async def update_status(self, decision_id: str, status: str, approved_by: str | None = None) -> dict | None:
        async with self.session_factory() as db:
            if approved_by and status in ("approved", "rejected"):
                await db.execute(
                    text("UPDATE decisions SET status = :status, approved_by = :ab, approved_at = CURRENT_TIMESTAMP WHERE id = :id"),
                    {"status": status, "ab": approved_by, "id": decision_id},
                )
            else:
                await db.execute(
                    text("UPDATE decisions SET status = :status WHERE id = :id"),
                    {"status": status, "id": decision_id},
                )
            await db.commit()
            result = await db.execute(text("SELECT * FROM decisions WHERE id = :id"), {"id": decision_id})
            row = result.fetchone()
            return self._row_to_dict(row) if row else None

    async def get_outcomes(self, org_id: str) -> dict:
        async with self.session_factory() as db:
            total = await db.execute(text("SELECT COUNT(*) FROM decisions WHERE org_id = :oid"), {"oid": org_id})
            approved = await db.execute(text("SELECT COUNT(*) FROM decisions WHERE org_id = :oid AND status='approved'"), {"oid": org_id})
            rejected = await db.execute(text("SELECT COUNT(*) FROM decisions WHERE org_id = :oid AND status='rejected'"), {"oid": org_id})
            pending = await db.execute(text("SELECT COUNT(*) FROM decisions WHERE org_id = :oid AND status='pending'"), {"oid": org_id})
            avg_conf = await db.execute(text("SELECT AVG(confidence_score) FROM decisions WHERE org_id = :oid"), {"oid": org_id})
            by_cat = await db.execute(text("SELECT category, COUNT(*) FROM decisions WHERE org_id = :oid GROUP BY category"), {"oid": org_id})
        return {
            "total": total.scalar() or 0,
            "approved": approved.scalar() or 0,
            "rejected": rejected.scalar() or 0,
            "pending": pending.scalar() or 0,
            "avg_confidence": float(avg_conf.scalar() or 0),
            "by_category": {r[0]: r[1] for r in by_cat.fetchall()},
        }

    @staticmethod
    def _row_to_dict(row) -> dict:
        cols = ["id", "org_id", "title", "category", "status", "problem_definition",
                "business_context", "evidence", "alternatives", "reasoning", "risk_analysis",
                "recommendation", "confidence_score", "chosen_option", "created_by",
                "approved_by", "approved_at", "created_at", "updated_at"]
        result = {}
        for i, col in enumerate(cols):
            val = row[i] if i < len(row) else None
            if col in ("business_context", "evidence", "alternatives", "reasoning", "risk_analysis", "chosen_option") and isinstance(val, str):
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
            if val is not None:
                result[col] = str(val) if hasattr(val, 'isoformat') else val
        return result
