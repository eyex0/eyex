"""Add knowledge graph tables."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_nodes_org_id", "knowledge_nodes", ["org_id"])
    op.create_index("ix_knowledge_nodes_type", "knowledge_nodes", ["type"])

    op.create_table(
        "knowledge_edges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("relation_type", sa.Text(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_edges_org_id", "knowledge_edges", ["org_id"])
    op.create_index("ix_knowledge_edges_source_id", "knowledge_edges", ["source_id"])
    op.create_index("ix_knowledge_edges_target_id", "knowledge_edges", ["target_id"])
    op.create_index("ix_knowledge_edges_relation_type", "knowledge_edges", ["relation_type"])


def downgrade() -> None:
    op.drop_table("knowledge_edges")
    op.drop_table("knowledge_nodes")
