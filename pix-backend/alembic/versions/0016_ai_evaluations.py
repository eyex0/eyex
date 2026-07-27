"""Migration 0016 — AI quality evaluations and persistent memory objects."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0016"
down_revision: str | None = "0015"

def upgrade() -> None:
    op.create_table(
        "ai_quality_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agent_instances.id"), nullable=False, index=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("response", sa.Text, nullable=False),
        sa.Column("factors", JSONB, nullable=False, default=dict),
        sa.Column("quality_score", sa.Integer, nullable=False, default=0),
        sa.Column("hallucination_flags", JSONB, default=list),
        sa.Column("sources_cited", JSONB, default=list),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("approved", sa.Boolean, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_qa_org_agent", "ai_quality_assessments", ["org_id", "agent_id"])

    op.create_table(
        "persistent_agent_memory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agent_instances.id"), nullable=False, index=True),
        sa.Column("memory_type", sa.String(32), nullable=False, index=True),
        sa.Column("agent_label", sa.String(256)),
        sa.Column("context", sa.Text),
        sa.Column("action", sa.Text),
        sa.Column("reasoning", sa.Text),
        sa.Column("result", sa.Text),
        sa.Column("confidence", sa.Float, default=0.0),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, default=dict),
        sa.Column("importance", sa.Float, default=0.5),
        sa.Column("access_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("accessed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pmem_org_type", "persistent_agent_memory", ["org_id", "memory_type"])

    op.create_table(
        "ai_audit_trail",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("who", sa.String(128), nullable=False),
        sa.Column("when", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("which_data", sa.Text),
        sa.Column("which_model", sa.String(128)),
        sa.Column("which_agent", sa.String(256)),
        sa.Column("why", sa.Text),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("result", sa.Text),
        sa.Column("metadata", JSONB, default=dict),
    )

def downgrade() -> None:
    op.drop_table("ai_audit_trail")
    op.drop_table("persistent_agent_memory")
    op.drop_table("ai_quality_assessments")
