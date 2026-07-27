from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# --------------------------------------------------------------------------- #
#  M1: Enterprise AI Governance
# --------------------------------------------------------------------------- #


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class ActionRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AIGovernancePolicy(Base):
    __tablename__ = "ai_governance_policies"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_type: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[ActionRiskLevel] = mapped_column(
        String(50), nullable=False, default=ActionRiskLevel.MEDIUM
    )
    action_types: Mapped[list[str]] = mapped_column(JSONB, default=list)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_explanation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approver_roles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    max_auto_approve_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AIActionRequest(Base):
    __tablename__ = "ai_action_requests"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        String(50), nullable=False, default=ApprovalStatus.PENDING, index=True
    )
    risk_level: Mapped[ActionRiskLevel] = mapped_column(
        String(50), nullable=False, default=ActionRiskLevel.MEDIUM
    )
    requested_by: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    proposed_action: Mapped[dict] = mapped_column(JSONB, default=dict)
    estimated_impact: Mapped[dict] = mapped_column(JSONB, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AIApprovalWorkflow(Base):
    __tablename__ = "ai_approval_workflows"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_action_types: Mapped[list[str]] = mapped_column(JSONB, default=list)
    trigger_risk_levels: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    steps: Mapped[list[dict]] = mapped_column(JSONB, default=list)


class AIApprovalDecision(Base):
    __tablename__ = "ai_approval_decisions"

    request_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_action_requests.id"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    decided_by: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class HumanReviewTask(Base):
    __tablename__ = "human_review_tasks"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_action_requests.id"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ExplainableAIReport(Base):
    __tablename__ = "explainable_ai_reports"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_action_requests.id"), nullable=True
    )
    report_type: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning_steps: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    evidence: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    input_features: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[list[str]] = mapped_column(JSONB, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


# --------------------------------------------------------------------------- #
#  M2: Enterprise Security Layer
# --------------------------------------------------------------------------- #


class IdentityProvider(Base):
    __tablename__ = "identity_providers"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class DataIsolationRule(Base):
    __tablename__ = "data_isolation_rules"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(256), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    allowed_roles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    denied_roles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    conditions: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class EncryptionKey(Base):
    __tablename__ = "encryption_keys"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    key_name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    key_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), default="AES-256-GCM")
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


# --------------------------------------------------------------------------- #
#  M3: AI Reliability Engineering
# --------------------------------------------------------------------------- #


class AgentHealthCheck(Base):
    __tablename__ = "agent_health_checks"

    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    check_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    diagnostics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AgentRecoveryAction(Base):
    __tablename__ = "agent_recovery_actions"

    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AgentPerformanceScore(Base):
    __tablename__ = "agent_performance_scores"

    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    accuracy_score: Mapped[float] = mapped_column(Float, default=0.0)
    speed_score: Mapped[float] = mapped_column(Float, default=0.0)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.0)
    usefulness_score: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    factors: Mapped[dict] = mapped_column(JSONB, default=dict)


class WorkflowReliabilityMetric(Base):
    __tablename__ = "workflow_reliability_metrics"

    workflow_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    successful_executions: Mapped[int] = mapped_column(Integer, default=0)
    failed_executions: Mapped[int] = mapped_column(Integer, default=0)
    retried_executions: Mapped[int] = mapped_column(Integer, default=0)
    avg_duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    p95_duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    availability_pct: Mapped[float] = mapped_column(Float, default=100.0)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


# --------------------------------------------------------------------------- #
#  M4: Enterprise Intelligence Analytics
# --------------------------------------------------------------------------- #


class BusinessImpactMetric(Base):
    __tablename__ = "business_impact_metrics"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric_category: Mapped[str] = mapped_column(String(100), nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    change_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    financial_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    attribution: Mapped[dict] = mapped_column(JSONB, default=dict)


class TimeSavedMetric(Base):
    __tablename__ = "time_saved_metrics"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    manual_hours: Mapped[float] = mapped_column(Float, nullable=False)
    ai_hours: Mapped[float] = mapped_column(Float, nullable=False)
    hours_saved: Mapped[float] = mapped_column(Float, nullable=False)
    frequency_per_month: Mapped[int] = mapped_column(Integer, default=1)
    annual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DecisionImprovementMetric(Base):
    __tablename__ = "decision_improvement_metrics"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False)
    decisions_supported: Mapped[int] = mapped_column(Integer, default=0)
    decisions_improved: Mapped[int] = mapped_column(Integer, default=0)
    avg_confidence_before: Mapped[float] = mapped_column(Float, default=0.0)
    avg_confidence_after: Mapped[float] = mapped_column(Float, default=0.0)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    examples: Mapped[list[dict]] = mapped_column(JSONB, default=list)


class RiskPreventionMetric(Base):
    __tablename__ = "risk_prevention_metrics"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    risk_category: Mapped[str] = mapped_column(String(100), nullable=False)
    risks_identified: Mapped[int] = mapped_column(Integer, default=0)
    risks_mitigated: Mapped[int] = mapped_column(Integer, default=0)
    potential_loss_avoided: Mapped[float] = mapped_column(Float, default=0.0)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    details: Mapped[list[dict]] = mapped_column(JSONB, default=list)


class AIPerformanceMetric(Base):
    __tablename__ = "ai_performance_metrics"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


# --------------------------------------------------------------------------- #
#  M5: AI Agent Lifecycle Management
# --------------------------------------------------------------------------- #


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, default=dict)
    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AgentTestRun(Base):
    __tablename__ = "agent_test_runs"

    agent_version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_versions.id"), nullable=False, index=True
    )
    test_suite: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    passed_tests: Mapped[int] = mapped_column(Integer, default=0)
    failed_tests: Mapped[int] = mapped_column(Integer, default=0)
    results: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AgentDeployment(Base):
    __tablename__ = "agent_deployments"

    agent_version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_versions.id"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="deploying")
    deployed_by: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    traffic_percent: Mapped[int] = mapped_column(Integer, default=100)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AgentRetirement(Base):
    __tablename__ = "agent_retirements"

    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="scheduled")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_agent_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    migration_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


# --------------------------------------------------------------------------- #
#  M6: Enterprise Integration Platform
# --------------------------------------------------------------------------- #


class EnterpriseConnector(Base):
    __tablename__ = "enterprise_connectors"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="inactive", index=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    auth_method: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rate_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    health_status: Mapped[str] = mapped_column(String(50), default="unknown")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class IntegrationSync(Base):
    __tablename__ = "integration_syncs"

    connector_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enterprise_connectors.id"), nullable=False, index=True
    )
    sync_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ConnectorCredential(Base):
    __tablename__ = "connector_credentials"

    connector_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enterprise_connectors.id"), nullable=False, index=True
    )
    credential_type: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# --------------------------------------------------------------------------- #
#  M7: πX Intelligence Marketplace
# --------------------------------------------------------------------------- #


class CertifiedAgent(Base):
    __tablename__ = "certified_agents"

    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    certification_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    certified_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    certified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    certification_level: Mapped[str] = mapped_column(String(50), default="standard")
    compliance_tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    security_score: Mapped[float] = mapped_column(Float, default=0.0)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AgentTemplate(Base):
    __tablename__ = "agent_templates"

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    template_type: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, default=dict)
    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools: Mapped[list[str]] = mapped_column(JSONB, default=list)
    required_connectors: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class DeveloperApplication(Base):
    __tablename__ = "developer_applications"

    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    developer_name: Mapped[str] = mapped_column(String(256), nullable=False)
    developer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    application_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    portfolio: Mapped[dict] = mapped_column(JSONB, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
