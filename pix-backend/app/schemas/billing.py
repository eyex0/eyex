from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SubscriptionPlanRead(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    price_monthly: float
    price_yearly: float
    currency: str
    max_users: int
    max_agents: int
    max_tasks_per_month: int
    features: dict | None
    is_active: bool
    sort_order: int

    model_config = {"from_attributes": True}


class SubscriptionPlanList(BaseModel):
    plans: list[SubscriptionPlanRead]


class SubscriptionCreate(BaseModel):
    plan_id: str
    billing_interval: str = Field("monthly", pattern=r"^(monthly|yearly)$")


class SubscriptionUpdate(BaseModel):
    billing_interval: str | None = Field(None, pattern=r"^(monthly|yearly)$")
    cancel_at_period_end: bool | None = None


class SubscriptionRead(BaseModel):
    id: str
    organization_id: str
    plan_id: str
    status: str
    billing_interval: str
    current_period_start: datetime
    current_period_end: datetime | None
    trial_end: datetime | None
    cancel_at_period_end: bool
    plan: SubscriptionPlanRead | None = None

    model_config = {"from_attributes": True}


class InvoiceRead(BaseModel):
    id: str
    subscription_id: str
    organization_id: str
    amount: float
    currency: str
    status: str
    description: str | None
    period_start: datetime | None
    period_end: datetime | None
    paid_at: datetime | None
    invoice_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceList(BaseModel):
    invoices: list[InvoiceRead]
    total: int


class UsageRead(BaseModel):
    metric: str
    value: float
    recorded_at: datetime


class UsageSummary(BaseModel):
    total_tasks: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    tasks_this_month: int = 0
    active_agents: int = 0
    active_members: int = 0


class DashboardStats(BaseModel):
    total_tasks: int = 0
    tasks_today: int = 0
    tasks_this_week: int = 0
    tasks_this_month: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    active_agents_count: int = 0
    members_count: int = 0
    recent_tasks: list = []
