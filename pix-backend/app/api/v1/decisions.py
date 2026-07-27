"""πX Decision Intelligence API."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_org_id, get_current_user
from app.models.user import User

logger = logging.getLogger("pix.api.decisions")

decisions_router = APIRouter(prefix="/decisions", tags=["Decisions"])


class DecisionCreate(BaseModel):
    question: str
    context: dict = {}
    category: str = "general"


class StatusUpdate(BaseModel):
    status: str  # pending, approved, rejected, reviewed
    approved_by: str | None = None


class OutcomeRecord(BaseModel):
    outcome: str
    success_score: float = 0.0


@decisions_router.post("/")
async def create_decision(
    body: DecisionCreate,
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    from packages.cognitive_kernel.decision_engine.decision_engine import DecisionEngine
    from packages.cognitive_kernel.decision_engine.decision_store import DecisionStore
    from app.database import async_session_factory

    engine = DecisionEngine()
    result = await engine.decide(body.question, org_id, body.context)
    result["org_id"] = org_id
    result["category"] = body.category
    result["created_by"] = str(user.id) if hasattr(user, "id") else None

    store = DecisionStore(async_session_factory)
    decision_id = await store.create(result)
    result["decision_id"] = decision_id
    return result


@decisions_router.get("/")
async def list_decisions(
    status: str | None = None,
    category: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    from packages.cognitive_kernel.decision_engine.decision_store import DecisionStore
    from app.database import async_session_factory
    store = DecisionStore(async_session_factory)
    decisions = await store.list(org_id, status=status, limit=limit, offset=offset)
    return {"decisions": decisions, "total": len(decisions)}


@decisions_router.get("/{decision_id}")
async def get_decision(
    decision_id: str,
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    from packages.cognitive_kernel.decision_engine.decision_store import DecisionStore
    from app.database import async_session_factory
    store = DecisionStore(async_session_factory)
    decision = await store.get(decision_id)
    if not decision:
        return {"error": "Decision not found"}, 404
    return decision


@decisions_router.patch("/{decision_id}/status")
async def update_status(
    decision_id: str,
    body: StatusUpdate,
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    from packages.cognitive_kernel.decision_engine.decision_store import DecisionStore
    from app.database import async_session_factory
    store = DecisionStore(async_session_factory)
    result = await store.update_status(decision_id, body.status, body.approved_by)
    if not result:
        return {"error": "Decision not found"}, 404
    return result


@decisions_router.get("/analytics/summary")
async def decision_analytics(
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org_id),
):
    from packages.cognitive_kernel.decision_engine.decision_store import DecisionStore
    from app.database import async_session_factory
    store = DecisionStore(async_session_factory)
    return await store.get_outcomes(org_id)
