"""Create memory tables: conversation_messages, long_term_memory, agent_memory."""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=True),
        sa.Column("metadata", sa.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversation_messages_session_id"), "conversation_messages", ["session_id"])
    op.create_index("idx_conv_session_created", "conversation_messages", ["session_id", "created_at"])

    op.create_table(
        "long_term_memory",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False, server_default=sa.text("'fact'")),
        sa.Column("importance", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("metadata", sa.JSONB(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "key", name="uq_long_term_memory_key"),
    )
    op.create_index(op.f("ix_long_term_memory_session_id"), "long_term_memory", ["session_id"])
    op.create_index("idx_ltm_session_type", "long_term_memory", ["session_id", "memory_type"])

    op.create_table(
        "agent_memory",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False, server_default=sa.text("'output'")),
        sa.Column("metadata", sa.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "agent_name", "key", name="uq_agent_memory_key"),
    )
    op.create_index(op.f("ix_agent_memory_session_id"), "agent_memory", ["session_id"])
    op.create_index("idx_agent_mem_lookup", "agent_memory", ["session_id", "agent_name"])


def downgrade() -> None:
    op.drop_table("agent_memory")
    op.drop_table("long_term_memory")
    op.drop_table("conversation_messages")
