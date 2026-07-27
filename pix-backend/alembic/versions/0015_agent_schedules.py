"""Migration 0015 — Agent schedules for proactive monitoring."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0015"
down_revision: str | None = "0014"

def upgrade() -> None:
    op.create_table(
        "agent_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agent_instances.id"), nullable=False),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("condition", JSONB, nullable=False, default=dict),
        sa.Column("interval_seconds", sa.Integer, default=3600),
        sa.Column("action", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), default="active"),
        sa.Column("last_triggered", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sched_org_agent", "agent_schedules", ["org_id", "agent_id"])

def downgrade() -> None:
    op.drop_table("agent_schedules")
