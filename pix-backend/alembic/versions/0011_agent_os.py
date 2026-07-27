"""
Enterprise AI Agent OS — Migration 0011

Tables:
  - agent_instances: Created agents per org
  - agent_memory: 4-layer memory (short_term, long_term, experience, decision_history)
  - agent_evaluations: Evaluation loop records
  - agent_permissions: RBAC per agent
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0011"
down_revision: str | None = "0010"


def upgrade() -> None:
    op.create_table(
        "agent_instances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("agent_type", sa.String(64), nullable=False),
        sa.Column("label", sa.String(256), nullable=False),
        sa.Column("purpose", sa.Text),
        sa.Column("industry", sa.String(64)),
        sa.Column("role", sa.String(64)),
        sa.Column("tools", JSONB, nullable=False, default=list),
        sa.Column("knowledge_access", JSONB, nullable=False, default=list),
        sa.Column("data_access", JSONB, nullable=False, default=list),
        sa.Column("kpis_monitored", JSONB, nullable=False, default=list),
        sa.Column("goals", JSONB, nullable=False, default=list),
        sa.Column("policies", JSONB, nullable=False, default=dict),
        sa.Column("status", sa.String(32), nullable=False, default="active", index=True),
        sa.Column("conversation_count", sa.Integer, default=0),
        sa.Column("decision_count", sa.Integer, default=0),
        sa.Column("performance_score", sa.Float, default=0.0),
        sa.Column("last_active", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_inst_org", "agent_instances", ["org_id", "status"])

    op.create_table(
        "agent_memory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agent_instances.id"), nullable=False, index=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("memory_type", sa.String(32), nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=False, default=dict),
        sa.Column("importance", sa.Float, default=0.5),
        sa.Column("access_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("accessed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_mem_type", "agent_memory", ["agent_id", "memory_type"])

    op.create_table(
        "agent_evaluations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agent_instances.id"), nullable=False, index=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("accuracy", sa.Float, default=0.0),
        sa.Column("confidence", sa.Float, default=0.0),
        sa.Column("business_impact", sa.Float, default=0.0),
        sa.Column("human_approved", sa.Boolean, nullable=True),
        sa.Column("score", sa.Float, default=0.0),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agent_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agent_instances.id"), nullable=False, index=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("allowed_tools", JSONB, nullable=False, default=list),
        sa.Column("allowed_entities", JSONB, nullable=False, default=list),
        sa.Column("allowed_data_categories", JSONB, nullable=False, default=list),
        sa.Column("data_sensitivity_max", sa.String(32), default="standard"),
        sa.Column("can_create_decisions", sa.Boolean, default=False),
        sa.Column("can_send_notifications", sa.Boolean, default=False),
        sa.Column("can_modify_data", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("agent_id", name="uq_agent_perm"),
    )


def downgrade() -> None:
    op.drop_table("agent_permissions")
    op.drop_table("agent_evaluations")
    op.drop_table("agent_memory")
    op.drop_table("agent_instances")
