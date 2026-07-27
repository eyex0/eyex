from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.user import User
from app.services.admin_service import get_admin_service

logger = logging.getLogger("pix.api.admin")

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_admin(user: User) -> User:
    if not user.is_superuser:
        raise ForbiddenException("Admin access required")
    return user


@admin_router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    service = get_admin_service()
    return await service.get_overall_stats(db=db)


@admin_router.get("/sessions")
async def list_sessions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    service = get_admin_service()
    return await service.get_sessions(db=db, page=page, per_page=per_page)


@admin_router.get("/agents")
async def list_agents(
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    service = get_admin_service()
    return await service.get_agents_stats()


@admin_router.get("/health/detailed")
async def detailed_health(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    service = get_admin_service()
    memory = getattr(request.app.state, "memory", None)
    return await service.get_detailed_health(db=db, memory=memory)
