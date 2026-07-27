"""Add GTM and Growth System tables."""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("company", sa.String(256)),
        sa.Column("title", sa.String(200)),
        sa.Column("phone", sa.String(50)),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("industry", sa.String(50)),
        sa.Column("employee_count", sa.Integer()),
        sa.Column("annual_revenue", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.Column("assigned_to", sa.UUID()),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True)),
        sa.Column("next_followup_at", sa.DateTime(timezone=True)),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_leads_email"), "leads", ['email'])
    op.create_index(op.f("ix_leads_id"), "leads", ['id'])
    op.create_index(op.f("ix_leads_status"), "leads", ['status'])

    op.create_table(
        "pipeline_deals",
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID()),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("expected_close_date", sa.DateTime(timezone=True)),
        sa.Column("actual_close_date", sa.DateTime(timezone=True)),
        sa.Column("assigned_to", sa.UUID()),
        sa.Column("competitor", sa.String(200)),
        sa.Column("loss_reason", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_pipeline_deals_org_id"), "pipeline_deals", ['org_id'])
    op.create_index(op.f("ix_pipeline_deals_status"), "pipeline_deals", ['status'])
    op.create_index(op.f("ix_pipeline_deals_stage"), "pipeline_deals", ['stage'])
    op.create_index(op.f("ix_pipeline_deals_id"), "pipeline_deals", ['id'])
    op.create_index(op.f("ix_pipeline_deals_lead_id"), "pipeline_deals", ['lead_id'])

    op.create_table(
        "deal_activities",
        sa.Column("deal_id", sa.UUID(), nullable=False),
        sa.Column("activity_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(200)),
        sa.Column("performed_by", sa.UUID(), nullable=False),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["deal_id"], ["pipeline_deals.id"]),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_deal_activities_id"), "deal_activities", ['id'])
    op.create_index(op.f("ix_deal_activities_deal_id"), "deal_activities", ['deal_id'])

    op.create_table(
        "enterprise_demos",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("lead_id", sa.UUID()),
        sa.Column("deal_id", sa.UUID()),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("scenario", sa.String(100), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("presenter_id", sa.UUID(), nullable=False),
        sa.Column("attendees", postgresql.JSONB(), nullable=False),
        sa.Column("custom_data", postgresql.JSONB()),
        sa.Column("outcome", sa.String(100)),
        sa.Column("feedback_score", sa.Integer()),
        sa.Column("feedback_notes", sa.Text()),
        sa.Column("recording_url", sa.String(500)),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["deal_id"], ["pipeline_deals.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_enterprise_demos_id"), "enterprise_demos", ['id'])
    op.create_index(op.f("ix_enterprise_demos_scheduled_at"), "enterprise_demos", ['scheduled_at'])
    op.create_index(op.f("ix_enterprise_demos_org_id"), "enterprise_demos", ['org_id'])

    op.create_table(
        "customer_onboarding",
        sa.Column("org_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("deal_id", sa.UUID()),
        sa.Column("current_stage", sa.String(50), nullable=False),
        sa.Column("assigned_csm", sa.UUID()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("target_go_live", sa.DateTime(timezone=True)),
        sa.Column("stage_data", postgresql.JSONB(), nullable=False),
        sa.Column("blockers", postgresql.JSONB(), nullable=False),
        sa.Column("health_score", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["deal_id"], ["pipeline_deals.id"]),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_customer_onboarding_current_stage"), "customer_onboarding", ['current_stage'])
    op.create_index(op.f("ix_customer_onboarding_org_id"), "customer_onboarding", ['org_id'], unique=True)
    op.create_index(op.f("ix_customer_onboarding_id"), "customer_onboarding", ['id'])

    op.create_table(
        "onboarding_tasks",
        sa.Column("onboarding_id", sa.UUID(), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("assigned_to", sa.UUID()),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["onboarding_id"], ["customer_onboarding.id"]),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_onboarding_tasks_id"), "onboarding_tasks", ['id'])
    op.create_index(op.f("ix_onboarding_tasks_onboarding_id"), "onboarding_tasks", ['onboarding_id'])

    op.create_table(
        "customer_health",
        sa.Column("org_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("usage_score", sa.Integer(), nullable=False),
        sa.Column("engagement_score", sa.Integer(), nullable=False),
        sa.Column("satisfaction_score", sa.Integer(), nullable=False),
        sa.Column("support_score", sa.Integer(), nullable=False),
        sa.Column("adoption_score", sa.Integer(), nullable=False),
        sa.Column("last_calculated", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("risk_factors", postgresql.JSONB(), nullable=False),
        sa.Column("positive_signals", postgresql.JSONB(), nullable=False),
        sa.Column("churn_probability", sa.Float(), nullable=False),
        sa.Column("next_review_at", sa.DateTime(timezone=True)),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_customer_health_id"), "customer_health", ['id'])
    op.create_index(op.f("ix_customer_health_status"), "customer_health", ['status'])
    op.create_index(op.f("ix_customer_health_org_id"), "customer_health", ['org_id'], unique=True)

    op.create_table(
        "usage_metrics",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_usage_metrics_id"), "usage_metrics", ['id'])
    op.create_index(op.f("ix_usage_metrics_org_id"), "usage_metrics", ['org_id'])

    op.create_table(
        "customer_feedback",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("feedback_type", sa.String(50), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("feature_area", sa.String(100)),
        sa.Column("sentiment", sa.String(20)),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_customer_feedback_org_id"), "customer_feedback", ['org_id'])
    op.create_index(op.f("ix_customer_feedback_id"), "customer_feedback", ['id'])

    op.create_table(
        "retention_workflows",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("workflow_type", sa.String(100), nullable=False),
        sa.Column("trigger", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("actions", postgresql.JSONB(), nullable=False),
        sa.Column("outcome", sa.String(100)),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_retention_workflows_org_id"), "retention_workflows", ['org_id'])
    op.create_index(op.f("ix_retention_workflows_id"), "retention_workflows", ['id'])

    op.create_table(
        "enterprise_pricing",
        sa.Column("org_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("plan_id", sa.UUID()),
        sa.Column("custom_monthly_price", sa.Float()),
        sa.Column("custom_annual_price", sa.Float()),
        sa.Column("billing_interval", sa.String(20), nullable=False),
        sa.Column("contract_start", sa.DateTime(timezone=True)),
        sa.Column("contract_end", sa.DateTime(timezone=True)),
        sa.Column("auto_renew", sa.Boolean(), nullable=False),
        sa.Column("max_users", sa.Integer()),
        sa.Column("max_agents", sa.Integer()),
        sa.Column("max_api_calls_per_month", sa.Integer()),
        sa.Column("max_storage_gb", sa.Integer()),
        sa.Column("custom_features", postgresql.JSONB(), nullable=False),
        sa.Column("discount_percent", sa.Float(), nullable=False),
        sa.Column("negotiated_by", sa.UUID()),
        sa.Column("notes", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_enterprise_pricing_id"), "enterprise_pricing", ['id'])
    op.create_index(op.f("ix_enterprise_pricing_org_id"), "enterprise_pricing", ['org_id'], unique=True)

    op.create_table(
        "usage_based_billing",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("billing_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("billing_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agent_executions", sa.Integer(), nullable=False),
        sa.Column("tokens_consumed", sa.Integer(), nullable=False),
        sa.Column("api_calls", sa.Integer(), nullable=False),
        sa.Column("storage_gb_used", sa.Float(), nullable=False),
        sa.Column("compute_hours", sa.Float(), nullable=False),
        sa.Column("total_cost", sa.Float(), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(), nullable=False),
        sa.Column("invoice_id", sa.UUID()),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_usage_based_billing_org_id"), "usage_based_billing", ['org_id'])
    op.create_index(op.f("ix_usage_based_billing_id"), "usage_based_billing", ['id'])

    op.create_table(
        "marketplace_revenue",
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("platform_fee", sa.Float(), nullable=False),
        sa.Column("developer_payout", sa.Float(), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_marketplace_revenue_agent_id"), "marketplace_revenue", ['agent_id'])
    op.create_index(op.f("ix_marketplace_revenue_org_id"), "marketplace_revenue", ['org_id'])
    op.create_index(op.f("ix_marketplace_revenue_id"), "marketplace_revenue", ['id'])

    op.create_table(
        "industry_solutions",
        sa.Column("industry", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("key_problems", postgresql.JSONB(), nullable=False),
        sa.Column("key_use_cases", postgresql.JSONB(), nullable=False),
        sa.Column("required_agents", postgresql.JSONB(), nullable=False),
        sa.Column("required_connectors", postgresql.JSONB(), nullable=False),
        sa.Column("compliance_requirements", postgresql.JSONB(), nullable=False),
        sa.Column("demo_scenarios", postgresql.JSONB(), nullable=False),
        sa.Column("roi_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("case_studies", postgresql.JSONB(), nullable=False),
        sa.Column("pricing_guidance", postgresql.JSONB()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_industry_solutions_id"), "industry_solutions", ['id'])
    op.create_index(op.f("ix_industry_solutions_industry"), "industry_solutions", ['industry'], unique=True)

    op.create_table(
        "partners",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("partner_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("website", sa.String(500)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("contact_email", sa.String(320)),
        sa.Column("contact_name", sa.String(200)),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("tier", sa.String(50), nullable=False),
        sa.Column("integration_status", sa.String(50), nullable=False),
        sa.Column("integration_notes", sa.Text()),
        sa.Column("revenue_share_percent", sa.Float(), nullable=False),
        sa.Column("joint_customers", sa.Integer(), nullable=False),
        sa.Column("pipeline_value", sa.Float(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_partners_partner_type"), "partners", ['partner_type'])
    op.create_index(op.f("ix_partners_id"), "partners", ['id'])
    op.create_index(op.f("ix_partners_status"), "partners", ['status'])

    op.create_table(
        "partnership_integrations",
        sa.Column("partner_id", sa.UUID(), nullable=False),
        sa.Column("integration_name", sa.String(200), nullable=False),
        sa.Column("integration_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("api_endpoint", sa.String(500)),
        sa.Column("auth_method", sa.String(100)),
        sa.Column("sync_frequency", sa.String(50)),
        sa.Column("data_mapping", postgresql.JSONB()),
        sa.Column("last_sync", sa.DateTime(timezone=True)),
        sa.Column("sync_status", sa.String(50)),
        sa.Column("error_log", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"]),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_partnership_integrations_id"), "partnership_integrations", ['id'])
    op.create_index(op.f("ix_partnership_integrations_partner_id"), "partnership_integrations", ['partner_id'])

    op.create_table(
        "market_opportunities",
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("industry", sa.String(50)),
        sa.Column("region", sa.String(100)),
        sa.Column("company_size", sa.String(50)),
        sa.Column("estimated_value", sa.Float(), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("signals", postgresql.JSONB(), nullable=False),
        sa.Column("recommended_approach", sa.Text()),
        sa.Column("competitive_landscape", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("assigned_to", sa.UUID()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_market_opportunities_id"), "market_opportunities", ['id'])

    op.create_table(
        "sales_predictions",
        sa.Column("org_id", sa.UUID()),
        sa.Column("lead_id", sa.UUID()),
        sa.Column("deal_id", sa.UUID()),
        sa.Column("prediction_type", sa.String(50), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("factors", postgresql.JSONB(), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("actual_outcome", sa.Float()),
        sa.Column("is_accurate", sa.Boolean()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["pipeline_deals.id"]),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_sales_predictions_org_id"), "sales_predictions", ['org_id'])
    op.create_index(op.f("ix_sales_predictions_id"), "sales_predictions", ['id'])

    op.create_table(
        "case_studies",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("industry", sa.String(50), nullable=False),
        sa.Column("company_size", sa.String(50), nullable=False),
        sa.Column("problem_statement", sa.Text(), nullable=False),
        sa.Column("solution_summary", sa.Text(), nullable=False),
        sa.Column("key_results", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("roi_percentage", sa.Float()),
        sa.Column("time_to_value_days", sa.Integer()),
        sa.Column("agents_used", postgresql.JSONB(), nullable=False),
        sa.Column("connectors_used", postgresql.JSONB(), nullable=False),
        sa.Column("testimonial", sa.Text()),
        sa.Column("customer_name", sa.String(200)),
        sa.Column("customer_title", sa.String(200)),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("tags", postgresql.JSONB(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_case_studies_industry"), "case_studies", ['industry'])
    op.create_index(op.f("ix_case_studies_org_id"), "case_studies", ['org_id'])
    op.create_index(op.f("ix_case_studies_id"), "case_studies", ['id'])

    op.create_table(
        "roi_calculators",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("calculator_type", sa.String(100), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), nullable=False),
        sa.Column("results", postgresql.JSONB(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_roi_calculators_org_id"), "roi_calculators", ['org_id'])
    op.create_index(op.f("ix_roi_calculators_id"), "roi_calculators", ['id'])

    op.create_table(
        "customer_success_reports",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("health_score", sa.Integer(), nullable=False),
        sa.Column("usage_summary", postgresql.JSONB(), nullable=False),
        sa.Column("adoption_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("business_impact", postgresql.JSONB(), nullable=False),
        sa.Column("recommendations", postgresql.JSONB(), nullable=False),
        sa.Column("risks", postgresql.JSONB(), nullable=False),
        sa.Column("next_steps", postgresql.JSONB(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_customer_success_reports_id"), "customer_success_reports", ['id'])
    op.create_index(op.f("ix_customer_success_reports_org_id"), "customer_success_reports", ['org_id'])

    op.create_table(
        "business_impact_measurements",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("measurement_type", sa.String(100), nullable=False),
        sa.Column("metric_name", sa.String(200), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("target_value", sa.Float()),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("change_percentage", sa.Float(), nullable=False),
        sa.Column("is_positive", sa.Boolean(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("attribution", postgresql.JSONB(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f("ix_business_impact_measurements_id"), "business_impact_measurements", ['id'])
    op.create_index(op.f("ix_business_impact_measurements_org_id"), "business_impact_measurements", ['org_id'])

    # SubscriptionPlan additions
    op.add_column("subscription_plans", sa.Column("tier", sa.String(50), nullable=True))
    op.add_column("subscription_plans", sa.Column("max_api_calls_per_month", sa.Integer(), nullable=False, server_default=sa.text("10000")))
    op.add_column("subscription_plans", sa.Column("max_storage_gb", sa.Integer(), nullable=False, server_default=sa.text("10")))
    op.add_column("subscription_plans", sa.Column("ai_model_access", postgresql.JSONB(), server_default=sa.text("'[]'")))
    op.add_column("subscription_plans", sa.Column("support_level", sa.String(50), server_default=sa.text("'email'"), nullable=False))


def downgrade() -> None:
    op.drop_table("business_impact_measurements")
    op.drop_table("customer_success_reports")
    op.drop_table("roi_calculators")
    op.drop_table("case_studies")
    op.drop_table("sales_predictions")
    op.drop_table("market_opportunities")
    op.drop_table("partnership_integrations")
    op.drop_table("partners")
    op.drop_table("industry_solutions")
    op.drop_table("marketplace_revenue")
    op.drop_table("usage_based_billing")
    op.drop_table("enterprise_pricing")
    op.drop_table("retention_workflows")
    op.drop_table("customer_feedback")
    op.drop_table("usage_metrics")
    op.drop_table("customer_health")
    op.drop_table("onboarding_tasks")
    op.drop_table("customer_onboarding")
    op.drop_table("enterprise_demos")
    op.drop_table("deal_activities")
    op.drop_table("pipeline_deals")
    op.drop_table("leads")
    op.drop_column("subscription_plans", "support_level")
    op.drop_column("subscription_plans", "ai_model_access")
    op.drop_column("subscription_plans", "max_storage_gb")
    op.drop_column("subscription_plans", "max_api_calls_per_month")
    op.drop_column("subscription_plans", "tier")