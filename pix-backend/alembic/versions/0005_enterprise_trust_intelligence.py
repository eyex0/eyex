"""Add Enterprise Trust and Intelligence Infrastructure tables."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # M1: AI Governance
    op.create_table(
        "ai_governance_policies",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("policy_type", sa.String(100), nullable=False),
        sa.Column("risk_level", sa.String(50), nullable=False),
        sa.Column("action_types", postgresql.JSONB(), nullable=False),
        sa.Column("auto_approve", sa.Boolean(), nullable=False),
        sa.Column("require_explanation", sa.Boolean(), nullable=False),
        sa.Column("require_human_review", sa.Boolean(), nullable=False),
        sa.Column("approver_roles", postgresql.JSONB(), nullable=False),
        sa.Column("max_auto_approve_value", sa.Float()),
        sa.Column("rules", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_governance_policies_org_id"), "ai_governance_policies", ["org_id"])
    op.create_index(op.f("ix_ai_governance_policies_id"), "ai_governance_policies", ["id"])

    op.create_table(
        "ai_action_requests",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID()),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("risk_level", sa.String(50), nullable=False),
        sa.Column("requested_by", sa.UUID(), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("input_data", postgresql.JSONB(), nullable=False),
        sa.Column("proposed_action", postgresql.JSONB(), nullable=False),
        sa.Column("estimated_impact", postgresql.JSONB(), nullable=False),
        sa.Column("explanation", sa.Text()),
        sa.Column("approved_by", sa.UUID()),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("execution_result", postgresql.JSONB()),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_action_requests_org_id"), "ai_action_requests", ["org_id"])
    op.create_index(op.f("ix_ai_action_requests_agent_id"), "ai_action_requests", ["agent_id"])
    op.create_index(op.f("ix_ai_action_requests_status"), "ai_action_requests", ["status"])
    op.create_index(op.f("ix_ai_action_requests_id"), "ai_action_requests", ["id"])

    op.create_table(
        "ai_approval_workflows",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("trigger_action_types", postgresql.JSONB(), nullable=False),
        sa.Column("trigger_risk_levels", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_approval_workflows_org_id"), "ai_approval_workflows", ["org_id"])
    op.create_index(op.f("ix_ai_approval_workflows_id"), "ai_approval_workflows", ["id"])

    op.create_table(
        "ai_approval_decisions",
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("decided_by", sa.UUID(), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("comments", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["request_id"], ["ai_action_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_approval_decisions_request_id"), "ai_approval_decisions", ["request_id"]
    )
    op.create_index(op.f("ix_ai_approval_decisions_id"), "ai_approval_decisions", ["id"])

    op.create_table(
        "human_review_tasks",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID()),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assigned_to", sa.UUID()),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(50), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("resolution", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["request_id"], ["ai_action_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_human_review_tasks_org_id"), "human_review_tasks", ["org_id"])
    op.create_index(op.f("ix_human_review_tasks_id"), "human_review_tasks", ["id"])

    op.create_table(
        "explainable_ai_reports",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("request_id", sa.UUID()),
        sa.Column("report_type", sa.String(100), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reasoning_steps", postgresql.JSONB(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("input_features", postgresql.JSONB(), nullable=False),
        sa.Column("output_explanation", sa.Text()),
        sa.Column("limitations", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["request_id"], ["ai_action_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_explainable_ai_reports_org_id"), "explainable_ai_reports", ["org_id"])
    op.create_index(
        op.f("ix_explainable_ai_reports_agent_id"), "explainable_ai_reports", ["agent_id"]
    )
    op.create_index(op.f("ix_explainable_ai_reports_id"), "explainable_ai_reports", ["id"])

    # M2: Enterprise Security
    op.create_table(
        "identity_providers",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("provider_type", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_identity_providers_org_id"), "identity_providers", ["org_id"])
    op.create_index(op.f("ix_identity_providers_id"), "identity_providers", ["id"])

    op.create_table(
        "security_alerts",
        sa.Column("org_id", sa.UUID()),
        sa.Column("alert_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", sa.UUID()),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("recommended_action", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_security_alerts_org_id"), "security_alerts", ["org_id"])
    op.create_index(op.f("ix_security_alerts_alert_type"), "security_alerts", ["alert_type"])
    op.create_index(op.f("ix_security_alerts_severity"), "security_alerts", ["severity"])
    op.create_index(op.f("ix_security_alerts_status"), "security_alerts", ["status"])
    op.create_index(op.f("ix_security_alerts_id"), "security_alerts", ["id"])

    op.create_table(
        "data_isolation_rules",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("rule_name", sa.String(256), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("allowed_roles", postgresql.JSONB(), nullable=False),
        sa.Column("denied_roles", postgresql.JSONB(), nullable=False),
        sa.Column("conditions", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_isolation_rules_org_id"), "data_isolation_rules", ["org_id"])
    op.create_index(op.f("ix_data_isolation_rules_id"), "data_isolation_rules", ["id"])

    op.create_table(
        "encryption_keys",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("key_name", sa.String(200), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(256), nullable=False),
        sa.Column("algorithm", sa.String(50), nullable=False),
        sa.Column("purpose", sa.String(100), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_encryption_keys_org_id"), "encryption_keys", ["org_id"])
    op.create_index(op.f("ix_encryption_keys_id"), "encryption_keys", ["id"])

    # M3: AI Reliability Engineering
    op.create_table(
        "agent_health_checks",
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("org_id", sa.UUID()),
        sa.Column("check_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("diagnostics", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_health_checks_agent_id"), "agent_health_checks", ["agent_id"])
    op.create_index(op.f("ix_agent_health_checks_status"), "agent_health_checks", ["status"])
    op.create_index(op.f("ix_agent_health_checks_id"), "agent_health_checks", ["id"])

    op.create_table(
        "agent_recovery_actions",
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("org_id", sa.UUID()),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("triggered_by", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("result", sa.Text()),
        sa.Column("success", sa.Boolean()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_recovery_actions_agent_id"), "agent_recovery_actions", ["agent_id"]
    )
    op.create_index(op.f("ix_agent_recovery_actions_id"), "agent_recovery_actions", ["id"])

    op.create_table(
        "agent_performance_scores",
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("org_id", sa.UUID()),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=False),
        sa.Column("speed_score", sa.Float(), nullable=False),
        sa.Column("reliability_score", sa.Float(), nullable=False),
        sa.Column("usefulness_score", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("factors", postgresql.JSONB(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_performance_scores_agent_id"), "agent_performance_scores", ["agent_id"]
    )
    op.create_index(op.f("ix_agent_performance_scores_id"), "agent_performance_scores", ["id"])

    op.create_table(
        "workflow_reliability_metrics",
        sa.Column("workflow_name", sa.String(200), nullable=False),
        sa.Column("org_id", sa.UUID()),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_executions", sa.Integer(), nullable=False),
        sa.Column("successful_executions", sa.Integer(), nullable=False),
        sa.Column("failed_executions", sa.Integer(), nullable=False),
        sa.Column("retried_executions", sa.Integer(), nullable=False),
        sa.Column("avg_duration_ms", sa.Float(), nullable=False),
        sa.Column("p95_duration_ms", sa.Float(), nullable=False),
        sa.Column("availability_pct", sa.Float(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_reliability_metrics_workflow_name"),
        "workflow_reliability_metrics",
        ["workflow_name"],
    )
    op.create_index(
        op.f("ix_workflow_reliability_metrics_id"), "workflow_reliability_metrics", ["id"]
    )

    # M4: Enterprise Intelligence Analytics
    op.create_table(
        "business_impact_metrics",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("metric_name", sa.String(200), nullable=False),
        sa.Column("metric_category", sa.String(100), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("target_value", sa.Float()),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("change_percentage", sa.Float(), nullable=False),
        sa.Column("financial_value", sa.Float()),
        sa.Column(
            "measured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("attribution", postgresql.JSONB(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_business_impact_metrics_org_id"), "business_impact_metrics", ["org_id"]
    )
    op.create_index(op.f("ix_business_impact_metrics_id"), "business_impact_metrics", ["id"])

    op.create_table(
        "time_saved_metrics",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("activity_type", sa.String(100), nullable=False),
        sa.Column("manual_hours", sa.Float(), nullable=False),
        sa.Column("ai_hours", sa.Float(), nullable=False),
        sa.Column("hours_saved", sa.Float(), nullable=False),
        sa.Column("frequency_per_month", sa.Integer(), nullable=False),
        sa.Column("annual_value", sa.Float()),
        sa.Column(
            "measured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_time_saved_metrics_org_id"), "time_saved_metrics", ["org_id"])
    op.create_index(op.f("ix_time_saved_metrics_id"), "time_saved_metrics", ["id"])

    op.create_table(
        "decision_improvement_metrics",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("decision_type", sa.String(100), nullable=False),
        sa.Column("decisions_supported", sa.Integer(), nullable=False),
        sa.Column("decisions_improved", sa.Integer(), nullable=False),
        sa.Column("avg_confidence_before", sa.Float(), nullable=False),
        sa.Column("avg_confidence_after", sa.Float(), nullable=False),
        sa.Column(
            "measured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("examples", postgresql.JSONB(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_decision_improvement_metrics_org_id"), "decision_improvement_metrics", ["org_id"]
    )
    op.create_index(
        op.f("ix_decision_improvement_metrics_id"), "decision_improvement_metrics", ["id"]
    )

    op.create_table(
        "risk_prevention_metrics",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("risk_category", sa.String(100), nullable=False),
        sa.Column("risks_identified", sa.Integer(), nullable=False),
        sa.Column("risks_mitigated", sa.Integer(), nullable=False),
        sa.Column("potential_loss_avoided", sa.Float(), nullable=False),
        sa.Column(
            "measured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_risk_prevention_metrics_org_id"), "risk_prevention_metrics", ["org_id"]
    )
    op.create_index(op.f("ix_risk_prevention_metrics_id"), "risk_prevention_metrics", ["id"])

    op.create_table(
        "ai_performance_metrics",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_performance_metrics_org_id"), "ai_performance_metrics", ["org_id"])
    op.create_index(
        op.f("ix_ai_performance_metrics_agent_id"), "ai_performance_metrics", ["agent_id"]
    )
    op.create_index(op.f("ix_ai_performance_metrics_id"), "ai_performance_metrics", ["id"])

    # M5: AI Agent Lifecycle Management
    op.create_table(
        "agent_versions",
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("org_id", sa.UUID()),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("agent_type", sa.String(100), nullable=False),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column("prompt_template", sa.Text()),
        sa.Column("tools", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.Column("changelog", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_versions_agent_id"), "agent_versions", ["agent_id"])
    op.create_index(op.f("ix_agent_versions_id"), "agent_versions", ["id"])

    op.create_table(
        "agent_test_runs",
        sa.Column("agent_version_id", sa.UUID(), nullable=False),
        sa.Column("test_suite", sa.String(200), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("total_tests", sa.Integer(), nullable=False),
        sa.Column("passed_tests", sa.Integer(), nullable=False),
        sa.Column("failed_tests", sa.Integer(), nullable=False),
        sa.Column("results", postgresql.JSONB(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_test_runs_agent_version_id"), "agent_test_runs", ["agent_version_id"]
    )
    op.create_index(op.f("ix_agent_test_runs_id"), "agent_test_runs", ["id"])

    op.create_table(
        "agent_deployments",
        sa.Column("agent_version_id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("deployed_by", sa.UUID(), nullable=False),
        sa.Column(
            "deployed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True)),
        sa.Column("rollback_reason", sa.Text()),
        sa.Column("traffic_percent", sa.Integer(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_deployments_org_id"), "agent_deployments", ["org_id"])
    op.create_index(op.f("ix_agent_deployments_id"), "agent_deployments", ["id"])

    op.create_table(
        "agent_retirements",
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_by_agent_id", sa.String(100)),
        sa.Column("migration_notes", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_retirements_org_id"), "agent_retirements", ["org_id"])
    op.create_index(op.f("ix_agent_retirements_id"), "agent_retirements", ["id"])

    # M6: Enterprise Integration Platform
    op.create_table(
        "enterprise_connectors",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("connector_type", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("auth_method", sa.String(100), nullable=False),
        sa.Column("endpoint_url", sa.String(500)),
        sa.Column("rate_limit", sa.Integer()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("health_status", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_enterprise_connectors_org_id"), "enterprise_connectors", ["org_id"])
    op.create_index(
        op.f("ix_enterprise_connectors_connector_type"), "enterprise_connectors", ["connector_type"]
    )
    op.create_index(op.f("ix_enterprise_connectors_status"), "enterprise_connectors", ["status"])
    op.create_index(op.f("ix_enterprise_connectors_id"), "enterprise_connectors", ["id"])

    op.create_table(
        "integration_syncs",
        sa.Column("connector_id", sa.UUID(), nullable=False),
        sa.Column("sync_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("records_failed", sa.Integer(), nullable=False),
        sa.Column("error_log", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["connector_id"], ["enterprise_connectors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_integration_syncs_connector_id"), "integration_syncs", ["connector_id"]
    )
    op.create_index(op.f("ix_integration_syncs_id"), "integration_syncs", ["id"])

    op.create_table(
        "connector_credentials",
        sa.Column("connector_id", sa.UUID(), nullable=False),
        sa.Column("credential_type", sa.String(100), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.String(256), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_rotated_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["connector_id"], ["enterprise_connectors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_connector_credentials_connector_id"), "connector_credentials", ["connector_id"]
    )
    op.create_index(op.f("ix_connector_credentials_id"), "connector_credentials", ["id"])

    # M7: EyeX Intelligence Marketplace
    op.create_table(
        "certified_agents",
        sa.Column("agent_id", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("industry", sa.String(100)),
        sa.Column("certification_status", sa.String(50), nullable=False),
        sa.Column("certified_by", sa.UUID()),
        sa.Column("certified_at", sa.DateTime(timezone=True)),
        sa.Column("certification_level", sa.String(50), nullable=False),
        sa.Column("compliance_tags", postgresql.JSONB(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("security_score", sa.Float(), nullable=False),
        sa.Column("reliability_score", sa.Float(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_certified_agents_agent_id"), "certified_agents", ["agent_id"], unique=True
    )
    op.create_index(op.f("ix_certified_agents_id"), "certified_agents", ["id"])

    op.create_table(
        "agent_templates",
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("industry", sa.String(100)),
        sa.Column("template_type", sa.String(100), nullable=False),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column("prompt_template", sa.Text()),
        sa.Column("tools", postgresql.JSONB(), nullable=False),
        sa.Column("required_connectors", postgresql.JSONB(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.UUID()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_templates_id"), "agent_templates", ["id"])

    op.create_table(
        "developer_applications",
        sa.Column("org_id", sa.UUID()),
        sa.Column("developer_name", sa.String(256), nullable=False),
        sa.Column("developer_email", sa.String(320), nullable=False),
        sa.Column("application_status", sa.String(50), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("reviewed_by", sa.UUID()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("portfolio", postgresql.JSONB(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("meta_data", postgresql.JSONB()),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_developer_applications_org_id"), "developer_applications", ["org_id"])
    op.create_index(op.f("ix_developer_applications_id"), "developer_applications", ["id"])


def downgrade() -> None:
    op.drop_table("developer_applications")
    op.drop_table("agent_templates")
    op.drop_table("certified_agents")
    op.drop_table("connector_credentials")
    op.drop_table("integration_syncs")
    op.drop_table("enterprise_connectors")
    op.drop_table("agent_retirements")
    op.drop_table("agent_deployments")
    op.drop_table("agent_test_runs")
    op.drop_table("agent_versions")
    op.drop_table("ai_performance_metrics")
    op.drop_table("risk_prevention_metrics")
    op.drop_table("decision_improvement_metrics")
    op.drop_table("time_saved_metrics")
    op.drop_table("business_impact_metrics")
    op.drop_table("workflow_reliability_metrics")
    op.drop_table("agent_performance_scores")
    op.drop_table("agent_recovery_actions")
    op.drop_table("agent_health_checks")
    op.drop_table("encryption_keys")
    op.drop_table("data_isolation_rules")
    op.drop_table("security_alerts")
    op.drop_table("identity_providers")
    op.drop_table("explainable_ai_reports")
    op.drop_table("human_review_tasks")
    op.drop_table("ai_approval_decisions")
    op.drop_table("ai_approval_workflows")
    op.drop_table("ai_action_requests")
    op.drop_table("ai_governance_policies")
