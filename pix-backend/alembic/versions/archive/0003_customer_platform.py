"""Create workspace, task, billing, and API key tables."""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("settings", postgresql.JSONB(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspaces_id"), "workspaces", ["id"])
    op.create_index(op.f("ix_workspaces_organization_id"), "workspaces", ["organization_id"])
    op.create_index(op.f("ix_workspaces_slug"), "workspaces", ["slug"])

    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(64), nullable=False, server_default=sa.text("'member'")),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspace_members_id"), "workspace_members", ["id"])

    op.create_table(
        "agent_configs",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("agent_role", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_configs_id"), "agent_configs", ["id"])
    op.create_index(op.f("ix_agent_configs_workspace_id"), "agent_configs", ["workspace_id"])

    op.create_table(
        "task_executions",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("agent_role", sa.String(100), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=True),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("steps", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_executions_id"), "task_executions", ["id"])
    op.create_index(op.f("ix_task_executions_workspace_id"), "task_executions", ["workspace_id"])
    op.create_index(op.f("ix_task_executions_session_id"), "task_executions", ["session_id"])
    op.create_index(op.f("ix_task_executions_status"), "task_executions", ["status"])

    op.create_table(
        "api_keys",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("key_hash", sa.String(256), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("permissions", postgresql.JSONB(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(op.f("ix_api_keys_id"), "api_keys", ["id"])
    op.create_index(op.f("ix_api_keys_workspace_id"), "api_keys", ["workspace_id"])

    op.create_table(
        "usage_records",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("metric", sa.String(100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_records_id"), "usage_records", ["id"])
    op.create_index(op.f("ix_usage_records_workspace_id"), "usage_records", ["workspace_id"])
    op.create_index(op.f("ix_usage_records_recorded_at"), "usage_records", ["recorded_at"])

    op.create_table(
        "subscription_plans",
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_monthly", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("price_yearly", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("max_agents", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("max_tasks_per_month", sa.Integer(), nullable=False, server_default=sa.text("1000")),
        sa.Column("features", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_subscription_plans_id"), "subscription_plans", ["id"])
    op.create_index(op.f("ix_subscription_plans_slug"), "subscription_plans", ["slug"])

    op.create_table(
        "subscriptions",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'active'")),
        sa.Column("billing_interval", sa.String(20), nullable=False, server_default=sa.text("'monthly'")),
        sa.Column("current_period_start", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("provider", sa.String(50), nullable=False, server_default=sa.text("'stripe'")),
        sa.Column("provider_subscription_id", sa.String(256), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subscriptions_id"), "subscriptions", ["id"])
    op.create_index(op.f("ix_subscriptions_organization_id"), "subscriptions", ["organization_id"])

    op.create_table(
        "invoices",
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False, server_default=sa.text("'stripe'")),
        sa.Column("provider_invoice_id", sa.String(256), nullable=True),
        sa.Column("invoice_url", sa.String(1024), nullable=True),
        sa.Column("invoice_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoices_id"), "invoices", ["id"])
    op.create_index(op.f("ix_invoices_subscription_id"), "invoices", ["subscription_id"])
    op.create_index(op.f("ix_invoices_organization_id"), "invoices", ["organization_id"])


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("subscriptions")
    op.drop_table("subscription_plans")
    op.drop_table("usage_records")
    op.drop_table("api_keys")
    op.drop_table("task_executions")
    op.drop_table("agent_configs")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
