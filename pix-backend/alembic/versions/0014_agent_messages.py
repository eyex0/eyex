"""Migration 0014 — Agent-to-agent communication messages."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0014"
down_revision: str | None = "0013"

def upgrade() -> None:
    op.create_table(
        "agent_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("from_agent_id", UUID(as_uuid=True), sa.ForeignKey("agent_instances.id"), nullable=False),
        sa.Column("to_agent_id", sa.String(128), nullable=False),  # agent_id or "supervisor"
        sa.Column("message_type", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, default=0.5),
        sa.Column("metadata", JSONB, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_msg_org_session", "agent_messages", ["org_id", "session_id"])

def downgrade() -> None:
    op.drop_table("agent_messages")
