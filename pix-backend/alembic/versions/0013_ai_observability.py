"""Migration 0013 — AI observability metrics and security events."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0013"
down_revision: str | None = "0012"

def upgrade() -> None:
    op.create_table(
        "ai_observability_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("metric_type", sa.String(64), nullable=False, index=True),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("metadata", JSONB, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_obs_org_type", "ai_observability_metrics", ["org_id", "metric_type"])

    op.create_table(
        "ai_security_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, default="low"),
        sa.Column("metadata", JSONB, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade() -> None:
    op.drop_table("ai_security_events")
    op.drop_table("ai_observability_metrics")
