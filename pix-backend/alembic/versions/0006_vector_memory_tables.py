"""Add pgvector extension and memory chunk/version tables."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "memory_chunks",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("ALTER TABLE memory_chunks ADD COLUMN embedding vector(1536)")
    op.create_index("ix_memory_chunks_org_id", "memory_chunks", ["org_id"])
    op.create_index("ix_memory_chunks_document_id", "memory_chunks", ["document_id"])
    op.execute(
        "CREATE INDEX ix_memory_chunks_embedding ON memory_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "memory_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("memory_id", sa.String(64), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_versions_memory_id", "memory_versions", ["memory_id"])


def downgrade() -> None:
    op.drop_table("memory_versions")
    op.drop_index("ix_memory_chunks_embedding", table_name="memory_chunks")
    op.drop_index("ix_memory_chunks_document_id", table_name="memory_chunks")
    op.drop_index("ix_memory_chunks_org_id", table_name="memory_chunks")
    op.drop_table("memory_chunks")
