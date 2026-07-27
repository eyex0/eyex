from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LeadSource(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    REFERRAL = "referral"
    EVENT = "event"
    CONTENT = "content"
    PARTNER = "partner"
    DEMO_REQUEST = "demo_request"
    TRIAL = "trial"


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    DEMO_SCHEDULED = "demo_scheduled"
    DEMO_COMPLETED = "demo_completed"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class PipelineStage(StrEnum):
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    DEMO = "demo"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED = "closed"


class DealStatus(StrEnum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"
    ON_HOLD = "on_hold"


class CustomerHealthStatus(StrEnum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    CHURNED = "churned"


class OnboardingStage(StrEnum):
    SIGNED = "signed"
    KICKOFF = "kickoff"
    DATA_CONNECT = "data_connect"
    AI_INIT = "ai_init"
    FIRST_REPORT = "first_report"
    TRAINING = "training"
    GO_LIVE = "go_live"
    COMPLETED = "completed"


class SubscriptionTier(StrEnum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingInterval(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class IndustryVertical(StrEnum):
    MANUFACTURING = "manufacturing"
    HEALTHCARE = "healthcare"
    LOGISTICS = "logistics"
    FINANCE = "finance"
    RETAIL = "retail"
    TECHNOLOGY = "technology"
    ENERGY = "energy"
    GOVERNMENT = "government"


class PartnershipType(StrEnum):
    CLOUD_PROVIDER = "cloud_provider"
    ENTERPRISE_SOFTWARE = "enterprise_software"
    INDUSTRY_PARTNER = "industry_partner"
    AI_ECOSYSTEM = "ai_ecosystem"
    SYSTEM_INTEGRATOR = "system_integrator"
    RESELLER = "reseller"
    REFERRAL = "referral"


class Lead(Base):
    __tablename__ = "leads"

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    company: Mapped[str] = mapped_column(String(256), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[LeadSource] = mapped_column(String(50), nullable=False, default=LeadSource.INBOUND)
    status: Mapped[LeadStatus] = mapped_column(String(50), nullable=False, default=LeadStatus.NEW, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    industry: Mapped[IndustryVertical | None] = mapped_column(String(50), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_followup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    pipeline_deals = relationship("PipelineDeal", back_populates="lead", lazy="selectin")


class PipelineDeal(Base):
    __tablename__ = "pipeline_deals"

    lead_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    stage: Mapped[PipelineStage] = mapped_column(String(50), nullable=False, default=PipelineStage.PROSPECTING, index=True)
    status: Mapped[DealStatus] = mapped_column(String(50), nullable=False, default=DealStatus.OPEN, index=True)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    probability: Mapped[int] = mapped_column(Integer, default=10)
    expected_close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    competitor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    loss_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    lead = relationship("Lead", back_populates="pipeline_deals")
    activities = relationship("DealActivity", back_populates="deal", lazy="selectin")


class DealActivity(Base):
    __tablename__ = "deal_activities"

    deal_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("pipeline_deals.id"), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    performed_by: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    deal = relationship("PipelineDeal", back_populates="activities")


class EnterpriseDemo(Base):
    __tablename__ = "enterprise_demos"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    lead_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    deal_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pipeline_deals.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    scenario: Mapped[str] = mapped_column(String(100), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="scheduled")
    presenter_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    attendees: Mapped[list[str]] = mapped_column(JSONB, default=list)
    custom_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    feedback_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    lead = relationship("Lead", lazy="selectin")
    deal = relationship("PipelineDeal", lazy="selectin")


class CustomerOnboarding(Base):
    __tablename__ = "customer_onboarding"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    deal_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pipeline_deals.id"), nullable=True)
    current_stage: Mapped[OnboardingStage] = mapped_column(String(50), nullable=False, default=OnboardingStage.SIGNED, index=True)
    assigned_csm: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_go_live: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stage_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    blockers: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    health_score: Mapped[int] = mapped_column(Integer, default=100)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    deal = relationship("PipelineDeal", lazy="selectin")


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    onboarding_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_onboarding.id"), nullable=False, index=True)
    stage: Mapped[OnboardingStage] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    onboarding = relationship("CustomerOnboarding", lazy="selectin")


class CustomerHealth(Base):
    __tablename__ = "customer_health"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    overall_score: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[CustomerHealthStatus] = mapped_column(String(50), nullable=False, default=CustomerHealthStatus.HEALTHY, index=True)
    usage_score: Mapped[int] = mapped_column(Integer, default=100)
    engagement_score: Mapped[int] = mapped_column(Integer, default=100)
    satisfaction_score: Mapped[int] = mapped_column(Integer, default=100)
    support_score: Mapped[int] = mapped_column(Integer, default=100)
    adoption_score: Mapped[int] = mapped_column(Integer, default=100)
    last_calculated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    risk_factors: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    positive_signals: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    churn_probability: Mapped[float] = mapped_column(Float, default=0.0)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class UsageMetric(Base):
    __tablename__ = "usage_metrics"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class CustomerFeedback(Base):
    __tablename__ = "customer_feedback"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class RetentionWorkflow(Base):
    __tablename__ = "retention_workflows"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actions: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class EnterprisePricing(Base):
    __tablename__ = "enterprise_pricing"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    plan_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=True)
    custom_monthly_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    custom_annual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    billing_interval: Mapped[BillingInterval] = mapped_column(String(20), default=BillingInterval.ANNUAL)
    contract_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contract_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_agents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_api_calls_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_storage_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custom_features: Mapped[list[str]] = mapped_column(JSONB, default=list)
    discount_percent: Mapped[float] = mapped_column(Float, default=0.0)
    negotiated_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    plan = relationship("SubscriptionPlan", lazy="selectin")


class UsageBasedBilling(Base):
    __tablename__ = "usage_based_billing"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    billing_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    billing_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    agent_executions: Mapped[int] = mapped_column(Integer, default=0)
    tokens_consumed: Mapped[int] = mapped_column(Integer, default=0)
    api_calls: Mapped[int] = mapped_column(Integer, default=0)
    storage_gb_used: Mapped[float] = mapped_column(Float, default=0.0)
    compute_hours: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    invoice_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")


class MarketplaceRevenue(Base):
    __tablename__ = "marketplace_revenue"

    agent_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    platform_fee: Mapped[float] = mapped_column(Float, default=0.0)
    developer_payout: Mapped[float] = mapped_column(Float, default=0.0)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed")
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class IndustrySolution(Base):
    __tablename__ = "industry_solutions"

    industry: Mapped[IndustryVertical] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    key_problems: Mapped[list[str]] = mapped_column(JSONB, default=list)
    key_use_cases: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    required_agents: Mapped[list[str]] = mapped_column(JSONB, default=list)
    required_connectors: Mapped[list[str]] = mapped_column(JSONB, default=list)
    compliance_requirements: Mapped[list[str]] = mapped_column(JSONB, default=list)
    demo_scenarios: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    roi_metrics: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    case_studies: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    pricing_guidance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Partner(Base):
    __tablename__ = "partners"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    partner_type: Mapped[PartnershipType] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    tier: Mapped[str] = mapped_column(String(50), default="standard")
    integration_status: Mapped[str] = mapped_column(String(50), default="not_started")
    integration_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue_share_percent: Mapped[float] = mapped_column(Float, default=0.0)
    joint_customers: Mapped[int] = mapped_column(Integer, default=0)
    pipeline_value: Mapped[float] = mapped_column(Float, default=0.0)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class PartnershipIntegration(Base):
    __tablename__ = "partnership_integrations"

    partner_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, index=True)
    integration_name: Mapped[str] = mapped_column(String(200), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="planning")
    api_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sync_frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    partner = relationship("Partner", lazy="selectin")


class MarketOpportunity(Base):
    __tablename__ = "market_opportunities"

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[IndustryVertical | None] = mapped_column(String(50), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_value: Mapped[float] = mapped_column(Float, default=0.0)
    probability: Mapped[int] = mapped_column(Integer, default=50)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    signals: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    recommended_approach: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitive_landscape: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(50), default="identified")
    assigned_to: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class SalesPrediction(Base):
    __tablename__ = "sales_predictions"

    org_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    lead_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    deal_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pipeline_deals.id"), nullable=True)
    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    factors: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    actual_outcome: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_accurate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class CaseStudy(Base):
    __tablename__ = "case_studies"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    industry: Mapped[IndustryVertical] = mapped_column(String(50), nullable=False, index=True)
    company_size: Mapped[str] = mapped_column(String(50), nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    solution_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_results: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    roi_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_to_value_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agents_used: Mapped[list[str]] = mapped_column(JSONB, default=list)
    connectors_used: Mapped[list[str]] = mapped_column(JSONB, default=list)
    testimonial: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    customer_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ROICalculator(Base):
    __tablename__ = "roi_calculators"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    calculator_type: Mapped[str] = mapped_column(String(100), nullable=False)
    inputs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    assumptions: Mapped[dict] = mapped_column(JSONB, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class CustomerSuccessReport(Base):
    __tablename__ = "customer_success_reports"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, default=100)
    usage_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    adoption_metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    business_impact: Mapped[dict] = mapped_column(JSONB, default=dict)
    recommendations: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    risks: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    next_steps: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class BusinessImpactMeasurement(Base):
    __tablename__ = "business_impact_measurements"

    org_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    measurement_type: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    change_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    is_positive: Mapped[bool] = mapped_column(Boolean, default=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    attribution: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
