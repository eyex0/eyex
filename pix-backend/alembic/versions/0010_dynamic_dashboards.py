"""
Dynamic Dashboard Engine — Migration 0010

Tables:
  - dashboard_definitions: Generated dashboard layouts per org/role
  - dashboard_preferences: User customization (hidden widgets, layout overrides)
  - dashboard_events: Event log for real-time updates
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0010"
down_revision: str | None = "0009"


def upgrade() -> None:
    op.create_table(
        "dashboard_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("role", sa.String(64), nullable=False, index=True),
        sa.Column("industry", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("subtitle", sa.Text, nullable=True),
        sa.Column("layout", JSONB, nullable=False, default=list),
        sa.Column("metadata", JSONB, nullable=False, default=dict),
        sa.Column("is_auto_generated", sa.Boolean, default=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dash_def_org_role", "dashboard_definitions", ["org_id", "role"])

    op.create_table(
        "dashboard_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("hidden_widgets", JSONB, nullable=False, default=list),
        sa.Column("custom_widgets", JSONB, nullable=False, default=list),
        sa.Column("layout_overrides", JSONB, nullable=False, default=dict),
        sa.Column("size_overrides", JSONB, nullable=False, default=dict),
        sa.Column("custom_title", sa.String(256), nullable=True),
        sa.Column("pinned_widgets", JSONB, nullable=False, default=list),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("org_id", "user_id", name="uq_dash_prefs_org_user"),
    )

    op.create_table(
        "dashboard_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("payload", JSONB, nullable=False, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dash_events_org_type", "dashboard_events", ["org_id", "event_type"])


def downgrade() -> None:
    op.drop_table("dashboard_events")
    op.drop_table("dashboard_preferences")
    op.drop_table("dashboard_definitions")
