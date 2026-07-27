from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    organization = relationship("Organization", backref="workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", lazy="selectin", cascade="all, delete-orphan")
    agent_configs = relationship("AgentConfig", back_populates="workspace", lazy="selectin", cascade="all, delete-orphan")
    task_executions = relationship("TaskExecution", back_populates="workspace", lazy="selectin", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="member")

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", backref="workspace_members")


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    agent_role: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    workspace = relationship("Workspace", back_populates="agent_configs")


class TaskExecution(Base):
    __tablename__ = "task_executions"

    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    agent_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steps: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    workspace = relationship("Workspace", back_populates="task_executions")
    user = relationship("User", backref="task_executions")


class ApiKey(Base):
    __tablename__ = "api_keys"

    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    permissions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    workspace = relationship("Workspace", backref="api_keys")
    user = relationship("User", backref="api_keys")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    workspace = relationship("Workspace", backref="usage_records")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_monthly: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    price_yearly: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_agents: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_tasks_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    max_api_calls_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    max_storage_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_model_access: Mapped[list[str] | None] = mapped_column(JSONB, default=list)
    support_level: Mapped[str] = mapped_column(String(50), default="email")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    plan_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="stripe")
    provider_subscription_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    organization = relationship("Organization", backref="subscriptions")
    plan = relationship("SubscriptionPlan", backref="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", lazy="selectin", cascade="all, delete-orphan")


class Invoice(Base):
    __tablename__ = "invoices"

    subscription_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="stripe")
    provider_invoice_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    invoice_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    invoice_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    subscription = relationship("Subscription", back_populates="invoices")
    organization = relationship("Organization", backref="invoices")
