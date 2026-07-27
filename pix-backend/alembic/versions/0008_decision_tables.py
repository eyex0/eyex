"""Add decisions table."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("problem_definition", sa.Text(), nullable=True),
        sa.Column("business_context", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("alternatives", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("reasoning", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("risk_analysis", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("chosen_option", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decisions_org_id", "decisions", ["org_id"])
    op.create_index("ix_decisions_status", "decisions", ["status"])
    op.create_index("ix_decisions_category", "decisions", ["category"])
    op.create_index("ix_decisions_created_at", "decisions", ["created_at"])


def downgrade() -> None:
    op.drop_table("decisions")
