from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_cache
from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.gtm import (
    BillingInterval,
    DealStatus,
    IndustryVertical,
    LeadSource,
    LeadStatus,
    OnboardingStage,
    PartnershipType,
    PipelineStage,
    SubscriptionTier,
)
from app.models.user import User
from app.services.gtm_growth import get_growth_intelligence_service
from app.services.gtm_industry import get_industry_expansion_service
from app.services.gtm_partnerships import get_partnership_service
from app.services.gtm_pricing import (
    get_enterprise_pricing_service,
    get_marketplace_revenue_service,
    get_pricing_service,
    get_usage_billing_service,
)
from app.services.gtm_proof import (
    get_case_study_service,
    get_proof_service,
    get_roi_calculator_service,
)
from app.services.gtm_sales import (
    DemoSchedule,
    LeadCreate,
    PipelineDealCreate,
    get_demo_service,
    get_onboarding_service,
    get_sales_service,
)
from app.services.gtm_success import (
    get_feedback_service,
    get_health_service,
    get_impact_service,
    get_report_service,
    get_retention_service,
)

logger = logging.getLogger("pix.api.gtm")

gtm_router = APIRouter(prefix="/gtm", tags=["Go-To-Market"])


# -------------------------------------------------------------------------- #
#  Enterprise Sales Platform
# -------------------------------------------------------------------------- #

@gtm_router.post("/leads")
async def create_lead(
    email: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    company: str = Form(""),
    title: str = Form(""),
    phone: str = Form(""),
    source: LeadSource = Form(LeadSource.INBOUND),
    industry: IndustryVertical | None = Form(None),
    employee_count: int | None = Form(None),
    annual_revenue: float | None = Form(None),
    notes: str = Form(""),
    assigned_to: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_sales_service(db)
    data = LeadCreate(
        email=email,
        first_name=first_name,
        last_name=last_name,
        company=company or None,
        title=title or None,
        phone=phone or None,
        source=source,
        industry=industry,
        employee_count=employee_count,
        annual_revenue=annual_revenue,
        notes=notes or None,
        assigned_to=assigned_to or None,
    )
    lead = await service.create_lead(data)
    return {"status": "created", "lead_id": str(lead.id), "score": lead.score}


@gtm_router.get("/leads")
async def list_leads(
    status: LeadStatus | None = Query(None),
    source: LeadSource | None = Query(None),
    industry: IndustryVertical | None = Query(None),
    assigned_to: str = Query(""),
    min_score: int = Query(0, ge=0, le=100),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_sales_service(db)
    return await service.list_leads(
        status=status,
        source=source,
        industry=industry,
        assigned_to=assigned_to or None,
        min_score=min_score,
        page=page,
        per_page=per_page,
    )


@gtm_router.patch("/leads/{lead_id}/status")
async def update_lead_status(
    lead_id: str,
    status: LeadStatus = Form(...),
    notes: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_sales_service(db)
    lead = await service.update_lead_status(lead_id, status, notes or None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "updated", "lead_id": str(lead.id), "new_status": lead.status.value}


@gtm_router.post("/deals")
async def create_deal(
    lead_id: str = Form(...),
    name: str = Form(...),
    value: float = Form(0.0),
    probability: int = Form(10, ge=0, le=100),
    expected_close_date: datetime | None = Form(None),
    assigned_to: str = Form(""),
    competitor: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_sales_service(db)
    data = PipelineDealCreate(
        lead_id=lead_id,
        name=name,
        value=value,
        probability=probability,
        expected_close_date=expected_close_date,
        assigned_to=assigned_to or None,
        competitor=competitor or None,
    )
    deal = await service.create_deal(data)
    return {"status": "created", "deal_id": str(deal.id), "stage": deal.stage.value}


@gtm_router.get("/deals")
async def list_deals(
    stage: PipelineStage | None = Query(None),
    status: DealStatus | None = Query(None),
    assigned_to: str = Query(""),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_sales_service(db)
    return await service.list_deals(
        stage=stage,
        status=status,
        assigned_to=assigned_to or None,
        page=page,
        per_page=per_page,
    )


@gtm_router.get("/deals/pipeline-summary")
async def get_pipeline_summary(
    assigned_to: str = Query(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_sales_service(db)
    return await service.get_pipeline_summary(assigned_to=assigned_to or None)


@gtm_router.patch("/deals/{deal_id}/stage")
async def update_deal_stage(
    deal_id: str,
    stage: PipelineStage = Form(...),
    notes: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_sales_service(db)
    deal = await service.update_deal_stage(deal_id, stage, notes or None)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {"status": "updated", "deal_id": str(deal.id), "stage": deal.stage.value}


@gtm_router.post("/deals/{deal_id}/activities")
async def add_deal_activity(
    deal_id: str,
    activity_type: str = Form(...),
    description: str = Form(...),
    outcome: str = Form(""),
    duration_minutes: int | None = Form(None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_sales_service(db)
    activity = await service.add_deal_activity(deal_id, activity_type, description, str(user.id), outcome or None, duration_minutes)
    return {"status": "created", "activity_id": str(activity.id)}


@gtm_router.post("/demos")
async def schedule_demo(
    org_id: str = Form(...),
    title: str = Form(...),
    scenario: str = Form("standard"),
    scheduled_at: datetime | None = Form(None),
    lead_id: str = Form(""),
    deal_id: str = Form(""),
    presenter_id: str = Form(...),
    attendees: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_demo_service(db)
    schedule = DemoSchedule(
        org_id=org_id,
        title=title,
        scenario=scenario,
        scheduled_at=scheduled_at,
        lead_id=lead_id or None,
        deal_id=deal_id or None,
        presenter_id=presenter_id,
        attendees=[a.strip() for a in attendees.split(",") if a.strip()] if attendees else [],
    )
    demo = await service.schedule_demo(schedule)
    return {"status": "scheduled", "demo_id": str(demo.id)}


@gtm_router.get("/demos/scenarios")
async def list_demo_scenarios(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_demo_service(db)
    return {"scenarios": list(service.SCENARIOS.keys())}


@gtm_router.get("/demos/scenarios/{scenario}")
async def get_demo_scenario(
    scenario: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_demo_service(db)
    return {"scenario": scenario, **service.get_scenario_config(scenario)}


@gtm_router.post("/demos/{demo_id}/complete")
async def complete_demo(
    demo_id: str,
    outcome: str = Form(...),
    feedback_score: int | None = Form(None),
    feedback_notes: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_demo_service(db)
    demo = await service.complete_demo(demo_id, outcome, feedback_score, feedback_notes or None)
    if not demo:
        raise HTTPException(status_code=404, detail="Demo not found")
    return {"status": "completed", "demo_id": str(demo.id), "outcome": demo.outcome}


@gtm_router.post("/onboarding")
async def start_onboarding(
    org_id: str = Form(...),
    deal_id: str = Form(""),
    assigned_csm: str = Form(""),
    target_go_live: datetime | None = Form(None),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_onboarding_service(db)
    onboarding = await service.start_onboarding(
        org_id=org_id,
        deal_id=deal_id or None,
        assigned_csm=assigned_csm or None,
        target_go_live=target_go_live,
    )
    return {"status": "started", "onboarding_id": str(onboarding.id), "current_stage": onboarding.current_stage.value}


@gtm_router.get("/onboarding/{org_id}")
async def get_onboarding(
    org_id: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_onboarding_service(db)
    onboarding = await service.get_onboarding(org_id)
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding not found")
    return {"onboarding_id": str(onboarding.id), "current_stage": onboarding.current_stage.value, "health_score": onboarding.health_score}


@gtm_router.patch("/onboarding/{org_id}/stage")
async def advance_onboarding_stage(
    org_id: str,
    new_stage: OnboardingStage = Form(...),
    notes: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_onboarding_service(db)
    try:
        onboarding = await service.advance_stage(org_id, new_stage, notes or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding not found")
    return {"status": "advanced", "current_stage": onboarding.current_stage.value}


@gtm_router.post("/onboarding/tasks/{task_id}/complete")
async def complete_onboarding_task(
    task_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_onboarding_service(db)
    task = await service.complete_task(task_id, str(user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "completed", "task_id": str(task.id)}


# -------------------------------------------------------------------------- #
#  Customer Success System
# -------------------------------------------------------------------------- #

@gtm_router.post("/success/health/{org_id}/calculate")
async def calculate_customer_health(
    org_id: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_health_service(db)
    health = await service.calculate_health(org_id)
    return {
        "org_id": org_id,
        "overall_score": health.overall_score,
        "status": health.status.value,
        "churn_probability": round(health.churn_probability, 2),
        "risk_factors": health.risk_factors,
    }


@gtm_router.get("/success/health/{org_id}")
async def get_customer_health(
    org_id: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_health_service(db)
    health = await service.get_health(org_id)
    if not health:
        raise HTTPException(status_code=404, detail="Health record not found")
    return {
        "org_id": org_id,
        "overall_score": health.overall_score,
        "status": health.status.value,
        "scores": {
            "usage": health.usage_score,
            "engagement": health.engagement_score,
            "satisfaction": health.satisfaction_score,
            "support": health.support_score,
            "adoption": health.adoption_score,
        },
        "churn_probability": round(health.churn_probability, 2),
    }


@gtm_router.get("/success/health/at-risk")
async def get_at_risk_customers(
    threshold: int = Query(70, ge=0, le=100),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_health_service(db)
    customers = await service.list_at_risk(threshold)
    return {"customers": [{"org_id": str(c.org_id), "score": c.overall_score, "status": c.status.value} for c in customers]}


@gtm_router.post("/success/usage/{org_id}")
async def record_usage_metric(
    org_id: str,
    metric_name: str = Form(...),
    metric_value: float = Form(...),
    period_days: int = Form(1),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_health_service(db)
    period_end = datetime.now(UTC)
    period_start = period_end - timedelta(days=period_days)
    metric = await service.record_usage(org_id, metric_name, metric_value, period_start, period_end)
    return {"status": "recorded", "metric_id": str(metric.id)}


@gtm_router.post("/success/feedback")
async def submit_feedback(
    org_id: str = Form(...),
    user_id: str = Form(...),
    feedback_type: str = Form(...),
    rating: int = Form(..., ge=1, le=5),
    comment: str = Form(""),
    feature_area: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_feedback_service(db)
    feedback = await service.submit_feedback(org_id, user_id, feedback_type, rating, comment or None, feature_area or None)
    return {"status": "recorded", "feedback_id": str(feedback.id), "sentiment": feedback.sentiment}


@gtm_router.get("/success/feedback/{org_id}/summary")
async def get_feedback_summary(
    org_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_feedback_service(db)
    return await service.get_feedback_summary(org_id, days)


@gtm_router.post("/success/retention/{org_id}")
async def trigger_retention_workflow(
    org_id: str,
    workflow_type: str = Form(...),
    trigger: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_retention_service(db)
    try:
        workflow = await service.trigger_workflow(org_id, workflow_type, trigger)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "triggered", "workflow_id": str(workflow.id)}


@gtm_router.post("/success/reports/{org_id}")
async def generate_success_report(
    org_id: str,
    period_days: int = Form(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_report_service(db)
    report = await service.generate_report(org_id, period_days)
    return {"status": "generated", "report_id": str(report.id), "health_score": report.health_score}


@gtm_router.get("/success/reports/{org_id}")
async def list_success_reports(
    org_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_report_service(db)
    reports = await service.list_reports(org_id, limit)
    return {"reports": [{"id": str(r.id), "health_score": r.health_score, "generated_at": r.generated_at.isoformat()} for r in reports]}


@gtm_router.post("/success/impact/{org_id}")
async def record_business_impact(
    org_id: str,
    measurement_type: str = Form(...),
    metric_name: str = Form(...),
    baseline_value: float = Form(...),
    current_value: float = Form(...),
    target_value: float | None = Form(None),
    unit: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_impact_service(db)
    measurement = await service.record_measurement(org_id, measurement_type, metric_name, baseline_value, current_value, target_value, unit)
    return {
        "status": "recorded",
        "measurement_id": str(measurement.id),
        "change_pct": round(measurement.change_percentage, 2),
    }


# -------------------------------------------------------------------------- #
#  Pricing & Monetization
# -------------------------------------------------------------------------- #

@gtm_router.post("/pricing/initialize")
async def initialize_pricing(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_pricing_service(db)
    plans = await service.initialize_plans()
    return {"status": "initialized", "plans_added": len(plans)}


@gtm_router.get("/pricing/plans")
async def list_subscription_plans(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    cache = get_cache()
    cache_key = f"gtm:pricing:plans:{active_only}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached
    service = get_pricing_service(db)
    plans = await service.get_plans(active_only)
    payload = {
        "plans": [
            {"id": str(p.id), "name": p.name, "tier": p.tier, "monthly": p.price_monthly, "annual": p.price_yearly}
            for p in plans
        ]
    }
    await cache.set(cache_key, payload, ttl=600)
    return payload


@gtm_router.post("/pricing/enterprise/{org_id}")
async def create_enterprise_pricing(
    org_id: str,
    plan_tier: SubscriptionTier = Form(...),
    billing_interval: BillingInterval = Form(BillingInterval.ANNUAL),
    custom_monthly_price: float | None = Form(None),
    custom_annual_price: float | None = Form(None),
    contract_months: int = Form(12),
    max_users: int | None = Form(None),
    max_agents: int | None = Form(None),
    discount_percent: float = Form(0.0),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_enterprise_pricing_service(db)
    pricing = await service.create_enterprise_pricing(
        org_id=org_id,
        plan_tier=plan_tier,
        billing_interval=billing_interval,
        custom_monthly_price=custom_monthly_price,
        custom_annual_price=custom_annual_price,
        contract_months=contract_months,
        max_users=max_users,
        max_agents=max_agents,
        discount_percent=discount_percent,
    )
    return {"status": "created", "pricing_id": str(pricing.id)}


@gtm_router.get("/pricing/enterprise/{org_id}")
async def get_effective_price(
    org_id: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_enterprise_pricing_service(db)
    return await service.calculate_effective_price(org_id)


@gtm_router.post("/pricing/usage/{org_id}")
async def record_usage_billing(
    org_id: str,
    agent_executions: int = Form(0),
    tokens_consumed: int = Form(0),
    api_calls: int = Form(0),
    storage_gb: float = Form(0.0),
    compute_hours: float = Form(0.0),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_usage_billing_service(db)
    billing = await service.record_usage(org_id, agent_executions, tokens_consumed, api_calls, storage_gb, compute_hours)
    return {"status": "recorded", "total_cost": round(billing.total_cost, 4), "breakdown": billing.breakdown}


@gtm_router.get("/pricing/usage/{org_id}/current")
async def get_current_usage_billing(
    org_id: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_usage_billing_service(db)
    billing = await service.get_current_billing(org_id)
    if not billing:
        raise HTTPException(status_code=404, detail="No billing record found")
    return {"total_cost": round(billing.total_cost, 4), "breakdown": billing.breakdown, "status": billing.status}


@gtm_router.post("/pricing/marketplace/revenue")
async def record_marketplace_revenue(
    agent_id: str = Form(...),
    org_id: str = Form(...),
    transaction_type: str = Form(...),
    amount: float = Form(...),
    period: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_marketplace_revenue_service(db)
    revenue = await service.record_transaction(agent_id, org_id, transaction_type, amount, period=period)
    return {"status": "recorded", "revenue_id": str(revenue.id), "platform_fee": revenue.platform_fee}


# -------------------------------------------------------------------------- #
#  Industry Expansion
# -------------------------------------------------------------------------- #

@gtm_router.post("/industry/initialize")
async def initialize_industry_solutions(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_industry_expansion_service(db)
    solutions = await service.initialize_default_solutions()
    return {"status": "initialized", "solutions_added": len(solutions)}


@gtm_router.get("/industry")
async def list_industry_solutions(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_industry_expansion_service(db)
    solutions = await service.list_solutions()
    return {"industries": [service._solution_to_dict(s) for s in solutions]}


@gtm_router.get("/industry/{industry}")
async def get_industry_playbook(
    industry: IndustryVertical,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_industry_expansion_service(db)
    playbook = await service.get_playbook(industry)
    if "error" in playbook:
        raise HTTPException(status_code=404, detail=playbook["error"])
    return playbook


@gtm_router.post("/industry/{industry}/use-case")
async def recommend_use_case(
    industry: IndustryVertical,
    business_problem: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_industry_expansion_service(db)
    recommendations = await service.get_use_case_recommendation(industry, business_problem)
    return {"industry": industry.value, "problem": business_problem, "recommendations": recommendations}


@gtm_router.get("/industry/{industry}/demo-script")
async def get_industry_demo_script(
    industry: IndustryVertical,
    scenario_name: str = Query(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_industry_expansion_service(db)
    return await service.get_demo_script(industry, scenario_name or None)


@gtm_router.get("/industry/{industry}/pricing-recommendation")
async def get_industry_pricing_recommendation(
    industry: IndustryVertical,
    employee_count: int = Query(..., ge=1),
    annual_revenue: float | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_industry_expansion_service(db)
    return await service.get_pricing_recommendation(industry, employee_count, annual_revenue)


# -------------------------------------------------------------------------- #
#  Partnership Framework
# -------------------------------------------------------------------------- #

@gtm_router.post("/partnerships/initialize")
async def initialize_partners(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_partnership_service(db)
    partners = await service.initialize_default_partners()
    return {"status": "initialized", "partners_added": len(partners)}


@gtm_router.get("/partnerships")
async def list_partners(
    partner_type: PartnershipType | None = Query(None),
    status: str = Query(""),
    tier: str = Query(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_partnership_service(db)
    partners = await service.list_partners(partner_type, status or None, tier or None)
    return {"partners": [{"id": str(p.id), "name": p.name, "type": p.partner_type.value, "tier": p.tier, "status": p.status} for p in partners]}


@gtm_router.post("/partnerships")
async def create_partner(
    name: str = Form(...),
    partner_type: PartnershipType = Form(...),
    description: str = Form(...),
    website: str = Form(""),
    contact_email: str = Form(""),
    contact_name: str = Form(""),
    tier: str = Form("standard"),
    revenue_share_percent: float = Form(0.0),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_partnership_service(db)
    partner = await service.create_partner(name, partner_type, description, website or None, contact_email or None, contact_name or None, tier, revenue_share_percent)
    return {"status": "created", "partner_id": str(partner.id)}


@gtm_router.get("/partnerships/summary")
async def get_partnership_summary(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_partnership_service(db)
    return await service.get_partnership_summary()


@gtm_router.post("/partnerships/{partner_id}/integrations")
async def create_partner_integration(
    partner_id: str,
    integration_name: str = Form(...),
    integration_type: str = Form(...),
    api_endpoint: str = Form(""),
    auth_method: str = Form(""),
    sync_frequency: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_partnership_service(db)
    try:
        integration = await service.create_integration(partner_id, integration_name, integration_type, api_endpoint or None, auth_method or None, sync_frequency or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "created", "integration_id": str(integration.id)}


# -------------------------------------------------------------------------- #
#  Growth Intelligence
# -------------------------------------------------------------------------- #

@gtm_router.post("/growth/opportunities")
async def identify_market_opportunities(
    industry: IndustryVertical | None = Form(None),
    region: str = Form(""),
    company_size: str = Form(""),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_growth_intelligence_service(db)
    opportunities = await service.identify_market_opportunities(industry, region or None, company_size or None)
    return {"opportunities_added": len(opportunities)}


@gtm_router.get("/growth/opportunities")
async def list_market_opportunities(
    industry: IndustryVertical | None = Query(None),
    min_probability: int = Query(0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_growth_intelligence_service(db)
    opportunities = await service.get_opportunities(industry, min_probability=min_probability, limit=limit)
    return {"opportunities": [{"id": str(o.id), "title": o.title, "industry": o.industry.value if o.industry else None, "probability": o.probability, "estimated_value": o.estimated_value} for o in opportunities]}


@gtm_router.post("/growth/predict/lead/{lead_id}")
async def predict_lead_conversion(
    lead_id: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_growth_intelligence_service(db)
    prediction = await service.score_lead_potential(lead_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"prediction_type": prediction.prediction_type, "confidence": prediction.confidence, "predicted_value": prediction.predicted_value}


@gtm_router.post("/growth/predict/deal/{deal_id}")
async def predict_deal_close(
    deal_id: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_growth_intelligence_service(db)
    prediction = await service.predict_deal_close(deal_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {"prediction_type": prediction.prediction_type, "confidence": prediction.confidence, "predicted_value": prediction.predicted_value}


@gtm_router.get("/growth/recommendations")
async def get_growth_recommendations(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_growth_intelligence_service(db)
    recommendations = await service.get_growth_recommendations()
    return {"recommendations": [{"area": r.area, "priority": r.priority, "title": r.title, "expected_impact": r.expected_impact, "actions": r.actions} for r in recommendations]}


@gtm_router.get("/growth/forecast")
async def get_sales_forecast(
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_growth_intelligence_service(db)
    return await service.get_sales_forecast(days)


@gtm_router.get("/growth/dashboard")
async def get_growth_dashboard(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_growth_intelligence_service(db)
    return await service.get_dashboard()


# -------------------------------------------------------------------------- #
#  Customer Proof System
# -------------------------------------------------------------------------- #

@gtm_router.post("/proof/case-studies")
async def create_case_study(
    org_id: str = Form(...),
    title: str = Form(...),
    industry: IndustryVertical = Form(...),
    company_size: str = Form(...),
    problem_statement: str = Form(...),
    solution_summary: str = Form(...),
    key_results: str = Form("[]"),
    metrics: str = Form("{}"),
    agents_used: str = Form(""),
    connectors_used: str = Form(""),
    customer_name: str = Form(""),
    customer_title: str = Form(""),
    testimonial: str = Form(""),
    publish: bool = Form(False),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    import json
    service = get_case_study_service(db)
    study = await service.create_case_study(
        org_id=org_id,
        title=title,
        industry=industry,
        company_size=company_size,
        problem_statement=problem_statement,
        solution_summary=solution_summary,
        key_results=json.loads(key_results),
        metrics=json.loads(metrics),
        agents_used=[a.strip() for a in agents_used.split(",") if a.strip()],
        connectors_used=[c.strip() for c in connectors_used.split(",") if c.strip()],
        testimonial=testimonial or None,
        customer_name=customer_name or None,
        customer_title=customer_title or None,
        publish=publish,
    )
    return {"status": "created", "case_study_id": str(study.id)}


@gtm_router.get("/proof/case-studies")
async def list_case_studies(
    industry: IndustryVertical | None = Query(None),
    published_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_case_study_service(db)
    studies = await service.list_case_studies(industry, published_only, limit)
    return {"case_studies": [{"id": str(s.id), "title": s.title, "customer": s.customer_name, "industry": s.industry.value, "published": s.is_published} for s in studies]}


@gtm_router.post("/proof/case-studies/{case_study_id}/publish")
async def publish_case_study(
    case_study_id: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_case_study_service(db)
    study = await service.publish_case_study(case_study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Case study not found")
    return {"status": "published", "case_study_id": str(study.id)}


@gtm_router.post("/proof/roi/manufacturing/{org_id}")
async def calculate_manufacturing_roi(
    org_id: str,
    annual_revenue: float = Form(...),
    downtime_cost_per_hour: float = Form(...),
    annual_downtime_hours: float = Form(...),
    maintenance_staff_count: int = Form(...),
    avg_maintenance_salary: float = Form(...),
    inventory_value: float = Form(...),
    defect_rate: float = Form(...),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_roi_calculator_service(db)
    calc = await service.calculate_manufacturing_roi(org_id, annual_revenue, downtime_cost_per_hour, annual_downtime_hours, maintenance_staff_count, avg_maintenance_salary, inventory_value, defect_rate)
    return {"calculator_id": str(calc.id), "results": calc.results}


@gtm_router.post("/proof/roi/finance/{org_id}")
async def calculate_finance_roi(
    org_id: str,
    annual_revenue: float = Form(...),
    fraud_losses_last_year: float = Form(...),
    compliance_staff_count: int = Form(...),
    avg_compliance_salary: float = Form(...),
    report_count_per_month: int = Form(...),
    avg_hours_per_report: float = Form(...),
    risk_review_count: int = Form(...),
    avg_hours_per_review: float = Form(...),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_roi_calculator_service(db)
    calc = await service.calculate_finance_roi(org_id, annual_revenue, fraud_losses_last_year, compliance_staff_count, avg_compliance_salary, report_count_per_month, avg_hours_per_report, risk_review_count, avg_hours_per_review)
    return {"calculator_id": str(calc.id), "results": calc.results}


@gtm_router.post("/proof/roi/healthcare/{org_id}")
async def calculate_healthcare_roi(
    org_id: str,
    annual_operating_cost: float = Form(...),
    overtime_annual_cost: float = Form(...),
    patient_volume_annual: int = Form(...),
    average_wait_time_minutes: float = Form(...),
    denial_annual_loss: float = Form(...),
    beds: int = Form(...),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_roi_calculator_service(db)
    calc = await service.calculate_healthcare_roi(org_id, annual_operating_cost, overtime_annual_cost, patient_volume_annual, average_wait_time_minutes, denial_annual_loss, beds)
    return {"calculator_id": str(calc.id), "results": calc.results}


@gtm_router.get("/proof/roi/{org_id}")
async def list_roi_calculators(
    org_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_roi_calculator_service(db)
    calculators = await service.list_calculators(org_id, limit)
    return {"calculators": [{"id": str(c.id), "type": c.calculator_type, "roi": c.results.get("roi_percentage")} for c in calculators]}


@gtm_router.get("/proof/package/{org_id}")
async def generate_proof_package(
    org_id: str,
    industry: IndustryVertical = Query(...),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_proof_service(db)
    return await service.generate_proof_package(org_id, industry)
