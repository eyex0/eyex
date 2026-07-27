"""
Intelligence Profile System — Migration 0009

Creates the foundation for adaptive enterprise intelligence:
  - intelligence_profiles: Organization intelligence identity
  - profile_versions: Full version history with diff tracking
  - profile_ontology: Custom entities, relationships, business concepts
  - profile_kpis: Company KPIs with definitions, formulas, targets
  - profile_glossary: Company terminology, aliases, synonyms
  - profile_data_sources: Connected systems, datasets, metadata
  - profile_events: Event system for all profile lifecycle changes
  - profile_semantic_history: Semantic learning history (column→entity mappings over time)

Design principles:
  - JSONB for all flexible/adaptive fields (no hardcoded schemas)
  - Tenant isolation via organization_id on every table
  - Versioning via profile_versions with snapshot + diff
  - Event sourcing via profile_events for audit and replay
  - Confidence scores on all inferred intelligence
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ── intelligence_profiles ──────────────────────────────────────────
    # The core intelligence identity for an organization.
    op.create_table(
        "intelligence_profiles",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("business_model", sa.Text(), nullable=True),
        sa.Column("company_size", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("locations", sa.JSON(), nullable=False, server_default="[]"),
        # profile_config stores the full adaptive configuration:
        # departments, roles, workflows, processes, AI agents, policies,
        # preferred models, dashboard config — everything company-specific.
        sa.Column("profile_config", sa.JSON(), nullable=False, server_default="{}"),
        # Confidence of the overall profile (0.0–1.0), aggregated from
        # sub-component confidences.
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),  # draft|active|archived
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_intelligence_profiles_org"),
    )
    op.create_index("ix_intel_profiles_org_id", "intelligence_profiles", ["organization_id"])
    op.create_index("ix_intel_profiles_status", "intelligence_profiles", ["status"])
    op.create_index("ix_intel_profiles_industry", "intelligence_profiles", ["industry"])

    # ── profile_versions ──────────────────────────────────────────────
    # Full version history with JSONB snapshots for diff tracking.
    op.create_table(
        "profile_versions",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("profile_id", sa.UUID(), sa.ForeignKey("intelligence_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),  # full profile state at this version
        sa.Column("diff", sa.JSON(), nullable=False, server_default="{}"),  # changes from previous version
        sa.Column("changed_by", sa.UUID(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "version_number", name="uq_profile_version"),
    )
    op.create_index("ix_profile_versions_profile_id", "profile_versions", ["profile_id"])
    op.create_index("ix_profile_versions_org_id", "profile_versions", ["organization_id"])

    # ── profile_ontology ──────────────────────────────────────────────
    # Custom entities, relationships, and business concepts per organization.
    # Fully dynamic — no predefined entity types. Each org defines its own.
    op.create_table(
        "profile_ontology",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), sa.ForeignKey("intelligence_profiles.id", ondelete="CASCADE"), nullable=False),
        # entity_type is free-form: "customer", "store", "sku", "truck_route" — whatever the company needs
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_label", sa.Text(), nullable=True),  # human-readable label
        # properties_schema defines the shape of this entity (JSONB, not SQL DDL)
        # Example: {"fields": [{"name": "store_id", "type": "identifier"}, ...]}
        sa.Column("properties_schema", sa.JSON(), nullable=False, server_default="{}"),
        # relationships: [{"target_type": "product", "relation": "stocks", "cardinality": "one_to_many"}]
        sa.Column("relationships", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("aliases", sa.JSON(), nullable=False, server_default="[]"),  # ["cust", "client", "buyer"]
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("source", sa.Text(), nullable=False, server_default="inferred"),  # inferred|user_defined|template
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_ontology_org_id", "profile_ontology", ["organization_id"])
    op.create_index("ix_profile_ontology_profile_id", "profile_ontology", ["profile_id"])
    op.create_index("ix_profile_ontology_entity_type", "profile_ontology", ["entity_type"])

    # ── profile_kpis ──────────────────────────────────────────────────
    # Company KPIs with definitions, formulas, targets — fully adaptive.
    op.create_table(
        "profile_kpis",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), sa.ForeignKey("intelligence_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),  # revenue|operations|customer|growth|custom
        # definition: natural language description of what this KPI means
        sa.Column("definition", sa.Text(), nullable=True),
        # formula: structured formula (JSONB) for computation
        # Example: {"type": "sum", "field": "net_rev", "filter": {"region": "EMEA"}}
        sa.Column("formula", sa.JSON(), nullable=False, server_default="{}"),
        # target: {"value": 1000000, "unit": "EUR", "period": "monthly", "direction": "higher_better"}
        sa.Column("target", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("aliases", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("source", sa.Text(), nullable=False, server_default="inferred"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_kpis_org_id", "profile_kpis", ["organization_id"])
    op.create_index("ix_profile_kpis_profile_id", "profile_kpis", ["profile_id"])
    op.create_index("ix_profile_kpis_category", "profile_kpis", ["category"])

    # ── profile_glossary ──────────────────────────────────────────────
    # Company terminology, aliases, synonyms — the business language layer.
    op.create_table(
        "profile_glossary",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), sa.ForeignKey("intelligence_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("term", sa.Text(), nullable=False),  # canonical term
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("aliases", sa.JSON(), nullable=False, server_default="[]"),  # ["net_rev", "netrevenue", "net sales"]
        sa.Column("synonyms", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("category", sa.Text(), nullable=True),  # financial|operational|customer|custom
        sa.Column("maps_to_entity", sa.Text(), nullable=True),  # links to profile_ontology entity_type
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("source", sa.Text(), nullable=False, server_default="inferred"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_glossary_org_id", "profile_glossary", ["organization_id"])
    op.create_index("ix_profile_glossary_profile_id", "profile_glossary", ["profile_id"])

    # ── profile_data_sources ──────────────────────────────────────────
    # Connected systems, datasets, metadata — what data the company has.
    op.create_table(
        "profile_data_sources",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), sa.ForeignKey("intelligence_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),  # excel|csv|pdf|docx|database|api|webhook|image
        sa.Column("connection_config", sa.JSON(), nullable=False, server_default="{}"),  # connection details (encrypted)
        # schema_metadata: discovered schema from the data source
        # Example: {"columns": [{"name": "Cust Name", "semantic_type": "text", "entity_type": "customer", "confidence": 0.85}]}
        sa.Column("schema_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("semantic_mappings", sa.JSON(), nullable=False, server_default="[]"),  # column→entity mappings
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", sa.Text(), nullable=False, server_default="discovered"),  # discovered|connected|active|error
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_data_sources_org_id", "profile_data_sources", ["organization_id"])
    op.create_index("ix_profile_data_sources_profile_id", "profile_data_sources", ["profile_id"])
    op.create_index("ix_profile_data_sources_source_type", "profile_data_sources", ["source_type"])

    # ── profile_events ─────────────────────────────────────────────────
    # Event system for all profile lifecycle changes — audit, replay, triggers.
    op.create_table(
        "profile_events",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), sa.ForeignKey("intelligence_profiles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        # event types: profile.created, profile.activated, profile.updated, ontology.added,
        #   kpi.added, glossary.learned, datasource.connected, semantic.mapping.corrected,
        #   version.created, agent.suggested, confidence.recalculated
        sa.Column("event_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("entity_type", sa.Text(), nullable=True),  # which sub-entity was affected
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("triggered_by", sa.Text(), nullable=False, server_default="system"),  # system|user|agent
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_events_org_id", "profile_events", ["organization_id"])
    op.create_index("ix_profile_events_profile_id", "profile_events", ["profile_id"])
    op.create_index("ix_profile_events_event_type", "profile_events", ["event_type"])

    # ── profile_semantic_history ───────────────────────────────────────
    # Semantic learning history — tracks how column→entity mappings evolve over time.
    # Enables the system to learn from corrections and improve inference accuracy.
    op.create_table(
        "profile_semantic_history",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), sa.ForeignKey("intelligence_profiles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("column_name", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=True),  # file/API the column came from
        sa.Column("inferred_entity", sa.Text(), nullable=True),
        sa.Column("inferred_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("corrected_entity", sa.Text(), nullable=True),  # user correction (if any)
        sa.Column("corrected_by", sa.UUID(), nullable=True),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sample_values", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("semantic_type", sa.Text(), nullable=True),  # text|numeric|date|currency|identifier
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_semantic_history_org_id", "profile_semantic_history", ["organization_id"])
    op.create_index("ix_profile_semantic_history_profile_id", "profile_semantic_history", ["profile_id"])
    op.create_index("ix_profile_semantic_history_column", "profile_semantic_history", ["column_name"])


def downgrade() -> None:
    op.drop_table("profile_semantic_history")
    op.drop_table("profile_events")
    op.drop_table("profile_data_sources")
    op.drop_table("profile_glossary")
    op.drop_table("profile_kpis")
    op.drop_table("profile_ontology")
    op.drop_table("profile_versions")
    op.drop_table("intelligence_profiles")
