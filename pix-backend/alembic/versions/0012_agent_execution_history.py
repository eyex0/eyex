"""Migration 0012 — Agent execution history with full traceability."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0012"
down_revision: str | None = "0011"

def upgrade() -> None:
    op.create_table(
        "agent_execution_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agent_instances.id"), nullable=False, index=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("response", sa.Text, nullable=False),
        sa.Column("model", sa.String(128)),
        sa.Column("provider", sa.String(64)),
        sa.Column("tools_used", JSONB, default=list),
        sa.Column("input_tokens", sa.Integer, default=0),
        sa.Column("output_tokens", sa.Integer, default=0),
        sa.Column("latency_ms", sa.Integer, default=0),
        sa.Column("cost_usd", sa.Float, default=0.0),
        sa.Column("confidence", sa.Float, default=0.0),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_exec_org_agent", "agent_execution_history", ["org_id", "agent_id"])

def downgrade() -> None:
    op.drop_table("agent_execution_history")
