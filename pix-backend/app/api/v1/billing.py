from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_cache
from app.core.exceptions import NotFoundException, ValidationException
from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.models.workspace import (
    Invoice,
    Subscription,
    SubscriptionPlan,
    TaskExecution,
    Workspace,
    WorkspaceMember,
)
from app.schemas.billing import (
    DashboardStats,
    InvoiceList,
    InvoiceRead,
    SubscriptionCreate,
    SubscriptionPlanList,
    SubscriptionPlanRead,
    SubscriptionRead,
    SubscriptionUpdate,
    UsageSummary,
)

logger = logging.getLogger("pix.api.billing")

billing_router = APIRouter(prefix="/billing", tags=["Billing"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def _get_org_for_user(db: AsyncSession, user_id: str) -> Organization:
    result = await db.execute(
        select(Organization).join(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise NotFoundException("Organization")
    return org


@billing_router.get("/plans", response_model=SubscriptionPlanList)
async def list_plans(
    db: AsyncSession = Depends(get_db_session),
):
    cache = get_cache()
    cached = await cache.get("billing:plans")
    if cached is not None:
        return SubscriptionPlanList(plans=cached)
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.sort_order)
    )
    plans = [SubscriptionPlanRead.model_validate(p).model_dump() for p in result.scalars().all()]
    await cache.set("billing:plans", plans, ttl=600)
    return SubscriptionPlanList(plans=plans)


@billing_router.get("/subscription", response_model=SubscriptionRead | None)
async def get_subscription(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    org = await _get_org_for_user(db, str(user.id))
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == org.id).order_by(Subscription.created_at.desc())
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return None
    data = SubscriptionRead.model_validate(sub)
    if sub.plan_id:
        plan_result = await db.get(SubscriptionPlan, sub.plan_id)
        if plan_result:
            data.plan = SubscriptionPlanRead.model_validate(plan_result)
    return data


@billing_router.post("/subscription", response_model=SubscriptionRead, status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    org = await _get_org_for_user(db, str(user.id))

    existing = await db.execute(
        select(Subscription).where(Subscription.organization_id == org.id, Subscription.status == "active")
    )
    if existing.scalar_one_or_none():
        raise ValidationException("Organization already has an active subscription")

    plan = await db.get(SubscriptionPlan, body.plan_id)
    if not plan:
        raise NotFoundException("Plan")
    if not plan.is_active:
        raise ValidationException("Plan is not available")

    now = datetime.now(UTC)
    period_end = now + timedelta(days=30 if body.billing_interval == "monthly" else 365)

    sub = Subscription(
        organization_id=org.id,
        plan_id=plan.id,
        billing_interval=body.billing_interval,
        current_period_start=now,
        current_period_end=period_end,
        trial_end=now + timedelta(days=14),
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)

    data = SubscriptionRead.model_validate(sub)
    data.plan = SubscriptionPlanRead.model_validate(plan)
    return data


@billing_router.patch("/subscription", response_model=SubscriptionRead)
async def update_subscription(
    body: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    org = await _get_org_for_user(db, str(user.id))
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == org.id, Subscription.status == "active")
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundException("Active subscription")
    if body.billing_interval is not None:
        sub.billing_interval = body.billing_interval
    if body.cancel_at_period_end is not None:
        sub.cancel_at_period_end = body.cancel_at_period_end
    if body.cancel_at_period_end is True:
        sub.status = "canceling"
    await db.flush()
    await db.refresh(sub)
    data = SubscriptionRead.model_validate(sub)
    if sub.plan_id:
        plan = await db.get(SubscriptionPlan, sub.plan_id)
        if plan:
            data.plan = SubscriptionPlanRead.model_validate(plan)
    return data


@billing_router.get("/invoices", response_model=InvoiceList)
async def list_invoices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    org = await _get_org_for_user(db, str(user.id))
    query = (
        select(Invoice)
        .where(Invoice.organization_id == org.id)
        .order_by(Invoice.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    count_q = select(func.count()).select_from(Invoice).where(Invoice.organization_id == org.id)
    result = await db.execute(query)
    invoices = [InvoiceRead.model_validate(i) for i in result.scalars().all()]
    total = await db.scalar(count_q)
    return InvoiceList(invoices=invoices, total=total or 0)


@dashboard_router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    org = await _get_org_for_user(db, str(user.id))
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    ws_result = await db.execute(
        select(Workspace).where(Workspace.organization_id == org.id)
    )
    workspaces = ws_result.scalars().all()
    ws_ids = [ws.id for ws in workspaces]
    if not ws_ids:
        return DashboardStats()

    total_tasks = await db.scalar(
        select(func.count()).select_from(TaskExecution).where(TaskExecution.workspace_id.in_(ws_ids))
    )
    tasks_today = await db.scalar(
        select(func.count()).select_from(TaskExecution).where(
            TaskExecution.workspace_id.in_(ws_ids),
            TaskExecution.created_at >= today_start,
        )
    )
    tasks_this_week = await db.scalar(
        select(func.count()).select_from(TaskExecution).where(
            TaskExecution.workspace_id.in_(ws_ids),
            TaskExecution.created_at >= week_start,
        )
    )
    tasks_this_month = await db.scalar(
        select(func.count()).select_from(TaskExecution).where(
            TaskExecution.workspace_id.in_(ws_ids),
            TaskExecution.created_at >= month_start,
        )
    )

    success_result = await db.execute(
        select(
            func.count().filter(TaskExecution.status == "completed"),
            func.count(),
        ).select_from(TaskExecution).where(TaskExecution.workspace_id.in_(ws_ids))
    )
    success_count, total_count = success_result.one()
    success_rate = (success_count / total_count * 100) if total_count and total_count > 0 else 0.0

    avg_dur = await db.scalar(
        select(func.avg(TaskExecution.duration_ms)).where(
            TaskExecution.workspace_id.in_(ws_ids),
            TaskExecution.duration_ms.isnot(None),
        )
    )

    total_tokens = await db.scalar(
        select(func.coalesce(func.sum(TaskExecution.tokens_used), 0)).where(
            TaskExecution.workspace_id.in_(ws_ids),
        )
    )

    total_cost = await db.scalar(
        select(func.coalesce(func.sum(TaskExecution.cost), 0)).where(
            TaskExecution.workspace_id.in_(ws_ids),
        )
    )

    active_agents = await db.scalar(
        select(func.count()).select_from(TaskExecution).where(
            TaskExecution.workspace_id.in_(ws_ids),
            TaskExecution.status == "running",
        )
    )

    member_count = 0
    for ws_id in ws_ids:
        cnt = await db.scalar(
            select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_id)
        )
        member_count += cnt or 0

    recent = await db.execute(
        select(TaskExecution)
        .where(TaskExecution.workspace_id.in_(ws_ids))
        .order_by(TaskExecution.created_at.desc())
        .limit(10)
    )

    return DashboardStats(
        total_tasks=total_tasks or 0,
        tasks_today=tasks_today or 0,
        tasks_this_week=tasks_this_week or 0,
        tasks_this_month=tasks_this_month or 0,
        success_rate=round(float(success_rate), 1),
        avg_duration_ms=round(float(avg_dur or 0), 0),
        total_tokens_used=total_tokens or 0,
        total_cost=float(total_cost or 0),
        active_agents_count=active_agents or 0,
        members_count=member_count,
        recent_tasks=[{"id": str(t.id), "agent_role": t.agent_role, "status": t.status, "duration_ms": t.duration_ms, "created_at": t.created_at.isoformat() if t.created_at else None} for t in recent.scalars().all()],
    )


@dashboard_router.get("/usage", response_model=UsageSummary)
async def get_usage_summary(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    org = await _get_org_for_user(db, str(user.id))
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    ws_result = await db.execute(
        select(Workspace).where(Workspace.organization_id == org.id)
    )
    ws_ids = [ws.id for ws in ws_result.scalars().all()]
    if not ws_ids:
        return UsageSummary()

    total_tasks = await db.scalar(
        select(func.count()).select_from(TaskExecution).where(TaskExecution.workspace_id.in_(ws_ids))
    )
    month_tasks = await db.scalar(
        select(func.count()).select_from(TaskExecution).where(
            TaskExecution.workspace_id.in_(ws_ids),
            TaskExecution.created_at >= month_start,
        )
    )
    total_tokens = await db.scalar(
        select(func.coalesce(func.sum(TaskExecution.tokens_used), 0)).where(TaskExecution.workspace_id.in_(ws_ids))
    )
    total_cost = await db.scalar(
        select(func.coalesce(func.sum(TaskExecution.cost), 0)).where(TaskExecution.workspace_id.in_(ws_ids))
    )
    active_agents = await db.scalar(
        select(func.count()).select_from(TaskExecution).where(
            TaskExecution.workspace_id.in_(ws_ids),
            TaskExecution.status == "running",
        )
    )

    member_count = sum(
        (await db.scalar(
            select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_id)
        )) or 0
        for ws_id in ws_ids
    )

    return UsageSummary(
        total_tasks=total_tasks or 0,
        total_tokens=total_tokens or 0,
        total_cost=float(total_cost or 0),
        tasks_this_month=month_tasks or 0,
        active_agents=active_agents or 0,
        active_members=member_count,
    )
