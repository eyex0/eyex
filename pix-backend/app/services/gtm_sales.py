from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gtm import (
    CustomerOnboarding,
    DealActivity,
    DealStatus,
    EnterpriseDemo,
    IndustryVertical,
    Lead,
    LeadSource,
    LeadStatus,
    OnboardingStage,
    OnboardingTask,
    PipelineDeal,
    PipelineStage,
)

logger = logging.getLogger("pix.services.gtm.sales")


@dataclass
class LeadCreate:
    email: str
    first_name: str
    last_name: str
    company: str | None = None
    title: str | None = None
    phone: str | None = None
    source: LeadSource = LeadSource.INBOUND
    industry: IndustryVertical | None = None
    employee_count: int | None = None
    annual_revenue: float | None = None
    notes: str | None = None
    assigned_to: str | None = None


@dataclass
class PipelineDealCreate:
    lead_id: str
    org_id: str | None = None
    name: str = ""
    value: float = 0.0
    probability: int = 10
    expected_close_date: datetime | None = None
    assigned_to: str | None = None
    competitor: str | None = None


@dataclass
class DemoSchedule:
    org_id: str
    lead_id: str | None = None
    deal_id: str | None = None
    title: str = ""
    scenario: str = "standard"
    scheduled_at: datetime | None = None
    presenter_id: str = ""
    attendees: list[str] | None = None
    custom_data: dict | None = None


class LeadScoringEngine:
    """Scores leads based on firmographics, engagement, and behavior."""

    INDUSTRY_SCORES = {
        IndustryVertical.FINANCE: 90,
        IndustryVertical.HEALTHCARE: 85,
        IndustryVertical.MANUFACTURING: 80,
        IndustryVertical.LOGISTICS: 75,
        IndustryVertical.RETAIL: 70,
        IndustryVertical.TECHNOLOGY: 85,
        IndustryVertical.ENERGY: 75,
        IndustryVertical.GOVERNMENT: 60,
    }

    SOURCE_SCORES = {
        LeadSource.DEMO_REQUEST: 50,
        LeadSource.TRIAL: 40,
        LeadSource.REFERRAL: 35,
        LeadSource.EVENT: 30,
        LeadSource.INBOUND: 25,
        LeadSource.CONTENT: 20,
        LeadSource.OUTBOUND: 15,
        LeadSource.PARTNER: 30,
    }

    SIZE_SCORES = [
        (1000, 30),
        (500, 25),
        (200, 20),
        (100, 15),
        (50, 10),
        (10, 5),
        (0, 0),
    ]

    REVENUE_SCORES = [
        (1_000_000_000, 30),
        (100_000_000, 25),
        (50_000_000, 20),
        (10_000_000, 15),
        (1_000_000, 10),
        (0, 0),
    ]

    def calculate_score(self, lead: Lead) -> int:
        score = 0

        if lead.industry:
            score += self.INDUSTRY_SCORES.get(lead.industry, 0)

        score += self.SOURCE_SCORES.get(lead.source, 0)

        if lead.employee_count:
            for threshold, pts in self.SIZE_SCORES:
                if lead.employee_count >= threshold:
                    score += pts
                    break

        if lead.annual_revenue:
            for threshold, pts in self.REVENUE_SCORES:
                if lead.annual_revenue >= threshold:
                    score += pts
                    break

        return min(score, 100)


class EnterpriseSalesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.scorer = LeadScoringEngine()

    async def create_lead(self, data: LeadCreate) -> Lead:
        lead = Lead(
            email=data.email.lower().strip(),
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            company=data.company.strip() if data.company else None,
            title=data.title.strip() if data.title else None,
            phone=data.phone.strip() if data.phone else None,
            source=data.source,
            industry=data.industry,
            employee_count=data.employee_count,
            annual_revenue=data.annual_revenue,
            notes=data.notes,
            assigned_to=uuid.UUID(data.assigned_to) if data.assigned_to else None,
        )
        lead.score = self.scorer.calculate_score(lead)
        self.db.add(lead)
        await self.db.commit()
        await self.db.refresh(lead)
        logger.info("Created lead %s (%s) with score %d", lead.id, lead.email, lead.score)
        return lead

    async def get_lead(self, lead_id: str) -> Lead | None:
        result = await self.db.execute(select(Lead).where(Lead.id == uuid.UUID(lead_id)))
        return result.scalar_one_or_none()

    async def update_lead_status(self, lead_id: str, status: LeadStatus, notes: str | None = None) -> Lead | None:
        lead = await self.get_lead(lead_id)
        if not lead:
            return None
        lead.status = status
        if notes:
            lead.notes = (lead.notes or "") + f"\n[{datetime.now(UTC).isoformat()}] {notes}"
        lead.last_contacted_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(lead)
        return lead

    async def assign_lead(self, lead_id: str, user_id: str) -> Lead | None:
        lead = await self.get_lead(lead_id)
        if not lead:
            return None
        lead.assigned_to = uuid.UUID(user_id)
        await self.db.commit()
        await self.db.refresh(lead)
        return lead

    async def list_leads(
        self,
        status: LeadStatus | None = None,
        assigned_to: str | None = None,
        source: LeadSource | None = None,
        industry: IndustryVertical | None = None,
        min_score: int = 0,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        query = select(Lead)
        conditions = []
        if status:
            conditions.append(Lead.status == status)
        if assigned_to:
            conditions.append(Lead.assigned_to == uuid.UUID(assigned_to))
        if source:
            conditions.append(Lead.source == source)
        if industry:
            conditions.append(Lead.industry == industry)
        if min_score > 0:
            conditions.append(Lead.score >= min_score)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(Lead.score), desc(Lead.created_at))

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        result = await self.db.execute(query)
        leads = result.scalars().all()

        return {
            "items": leads,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    async def create_deal(self, data: PipelineDealCreate) -> PipelineDeal:
        deal = PipelineDeal(
            lead_id=uuid.UUID(data.lead_id),
            org_id=uuid.UUID(data.org_id) if data.org_id else None,
            name=data.name,
            value=data.value,
            probability=data.probability,
            expected_close_date=data.expected_close_date,
            assigned_to=uuid.UUID(data.assigned_to) if data.assigned_to else None,
            competitor=data.competitor,
        )
        self.db.add(deal)
        await self.db.commit()
        await self.db.refresh(deal)

        lead = await self.get_lead(data.lead_id)
        if lead and lead.status in (LeadStatus.NEW, LeadStatus.CONTACTED):
            lead.status = LeadStatus.QUALIFIED
            await self.db.commit()

        logger.info("Created deal %s for lead %s", deal.id, data.lead_id)
        return deal

    async def get_deal(self, deal_id: str) -> PipelineDeal | None:
        result = await self.db.execute(
            select(PipelineDeal).where(PipelineDeal.id == uuid.UUID(deal_id))
        )
        return result.scalar_one_or_none()

    async def update_deal_stage(self, deal_id: str, stage: PipelineStage, notes: str | None = None) -> PipelineDeal | None:
        deal = await self.get_deal(deal_id)
        if not deal:
            return None
        old_stage = deal.stage
        deal.stage = stage
        if notes:
            deal.notes = (deal.notes or "") + f"\n[{datetime.now(UTC).isoformat()}] Stage {old_stage.value} → {stage.value}: {notes}"

        if stage == PipelineStage.CLOSED:
            deal.status = DealStatus.WON
            deal.actual_close_date = datetime.now(UTC)
            if deal.lead:
                deal.lead.status = LeadStatus.CLOSED_WON

        await self.db.commit()
        await self.db.refresh(deal)
        return deal

    async def update_deal_status(self, deal_id: str, status: DealStatus, loss_reason: str | None = None) -> PipelineDeal | None:
        deal = await self.get_deal(deal_id)
        if not deal:
            return None
        deal.status = status
        if status == DealStatus.LOST and loss_reason:
            deal.loss_reason = loss_reason
            if deal.lead:
                deal.lead.status = LeadStatus.CLOSED_LOST
        if status == DealStatus.WON:
            deal.actual_close_date = datetime.now(UTC)
            if deal.lead:
                deal.lead.status = LeadStatus.CLOSED_WON
        await self.db.commit()
        await self.db.refresh(deal)
        return deal

    async def add_deal_activity(self, deal_id: str, activity_type: str, description: str, performed_by: str, outcome: str | None = None, duration_minutes: int | None = None) -> DealActivity:
        activity = DealActivity(
            deal_id=uuid.UUID(deal_id),
            activity_type=activity_type,
            description=description,
            outcome=outcome,
            performed_by=uuid.UUID(performed_by),
            duration_minutes=duration_minutes,
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def get_deal_activities(self, deal_id: str) -> list[DealActivity]:
        result = await self.db.execute(
            select(DealActivity).where(DealActivity.deal_id == uuid.UUID(deal_id)).order_by(desc(DealActivity.created_at))
        )
        return list(result.scalars().all())

    async def list_deals(
        self,
        stage: PipelineStage | None = None,
        status: DealStatus | None = None,
        assigned_to: str | None = None,
        org_id: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        query = select(PipelineDeal)
        conditions = []
        if stage:
            conditions.append(PipelineDeal.stage == stage)
        if status:
            conditions.append(PipelineDeal.status == status)
        if assigned_to:
            conditions.append(PipelineDeal.assigned_to == uuid.UUID(assigned_to))
        if org_id:
            conditions.append(PipelineDeal.org_id == uuid.UUID(org_id))
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(PipelineDeal.created_at))

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        result = await self.db.execute(query)
        deals = result.scalars().all()

        return {
            "items": deals,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    async def get_pipeline_summary(self, assigned_to: str | None = None) -> dict[str, Any]:
        query = select(PipelineDeal).where(PipelineDeal.status == DealStatus.OPEN)
        if assigned_to:
            query = query.where(PipelineDeal.assigned_to == uuid.UUID(assigned_to))

        result = await self.db.execute(query)
        deals = result.scalars().all()

        summary = {
            "total_deals": len(deals),
            "total_value": sum(d.value for d in deals),
            "weighted_value": sum(d.value * d.probability / 100 for d in deals),
            "by_stage": defaultdict(lambda: {"count": 0, "value": 0.0, "weighted_value": 0.0}),
            "by_status": defaultdict(int),
        }

        for deal in deals:
            summary["by_stage"][deal.stage.value]["count"] += 1
            summary["by_stage"][deal.stage.value]["value"] += deal.value
            summary["by_stage"][deal.stage.value]["weighted_value"] += deal.value * deal.probability / 100
            summary["by_status"][deal.status.value] += 1

        summary["by_stage"] = dict(summary["by_stage"])
        summary["by_status"] = dict(summary["by_status"])
        return summary


class DemoWorkflowService:
    SCENARIOS = {
        "standard": {
            "name": "Standard Enterprise Demo",
            "duration_minutes": 45,
            "steps": ["intro", "problem", "ai_analysis", "executive_recommendations", "impact", "next_steps"],
        },
        "executive": {
            "name": "Executive Briefing",
            "duration_minutes": 30,
            "steps": ["intro", "executive_summary", "roi_projection", "competitive_advantage", "next_steps"],
        },
        "technical": {
            "name": "Technical Deep Dive",
            "duration_minutes": 60,
            "steps": ["architecture", "data_ingestion", "agent_workflows", "security", "integration", "qa"],
        },
        "industry": {
            "name": "Industry-Specific Demo",
            "duration_minutes": 45,
            "steps": ["industry_challenges", "tailored_solution", "compliance", "case_study", "next_steps"],
        },
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def schedule_demo(self, data: DemoSchedule) -> EnterpriseDemo:
        demo = EnterpriseDemo(
            org_id=uuid.UUID(data.org_id),
            lead_id=uuid.UUID(data.lead_id) if data.lead_id else None,
            deal_id=uuid.UUID(data.deal_id) if data.deal_id else None,
            title=data.title,
            scenario=data.scenario,
            scheduled_at=data.scheduled_at or datetime.now(UTC) + timedelta(days=3),
            presenter_id=uuid.UUID(data.presenter_id),
            attendees=data.attendees or [],
            custom_data=data.custom_data,
        )
        self.db.add(demo)
        await self.db.commit()
        await self.db.refresh(demo)

        if data.lead_id:
            lead = await self.db.get(Lead, uuid.UUID(data.lead_id))
            if lead and lead.status == LeadStatus.QUALIFIED:
                lead.status = LeadStatus.DEMO_SCHEDULED
                await self.db.commit()

        logger.info("Scheduled demo %s for org %s", demo.id, data.org_id)
        return demo

    async def complete_demo(self, demo_id: str, outcome: str, feedback_score: int | None = None, feedback_notes: str | None = None, recording_url: str | None = None) -> EnterpriseDemo | None:
        result = await self.db.execute(select(EnterpriseDemo).where(EnterpriseDemo.id == uuid.UUID(demo_id)))
        demo = result.scalar_one_or_none()
        if not demo:
            return None
        demo.status = "completed"
        demo.completed_at = datetime.now(UTC)
        demo.outcome = outcome
        demo.feedback_score = feedback_score
        demo.feedback_notes = feedback_notes
        demo.recording_url = recording_url
        await self.db.commit()
        await self.db.refresh(demo)

        if demo.lead_id:
            lead = await self.db.get(Lead, demo.lead_id)
            if lead and lead.status == LeadStatus.DEMO_SCHEDULED:
                lead.status = LeadStatus.DEMO_COMPLETED
                await self.db.commit()

        return demo

    async def get_demo(self, demo_id: str) -> EnterpriseDemo | None:
        result = await self.db.execute(select(EnterpriseDemo).where(EnterpriseDemo.id == uuid.UUID(demo_id)))
        return result.scalar_one_or_none()

    async def list_demos(self, org_id: str | None = None, status: str | None = None, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        query = select(EnterpriseDemo)
        conditions = []
        if org_id:
            conditions.append(EnterpriseDemo.org_id == uuid.UUID(org_id))
        if status:
            conditions.append(EnterpriseDemo.status == status)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(EnterpriseDemo.scheduled_at))

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        result = await self.db.execute(query)
        demos = result.scalars().all()

        return {
            "items": demos,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    def get_scenario_config(self, scenario: str) -> dict[str, Any]:
        return self.SCENARIOS.get(scenario, self.SCENARIOS["standard"])


class OnboardingService:
    STAGE_ORDER = [
        OnboardingStage.SIGNED,
        OnboardingStage.KICKOFF,
        OnboardingStage.DATA_CONNECT,
        OnboardingStage.AI_INIT,
        OnboardingStage.FIRST_REPORT,
        OnboardingStage.TRAINING,
        OnboardingStage.GO_LIVE,
        OnboardingStage.COMPLETED,
    ]

    DEFAULT_TASKS = {
        OnboardingStage.KICKOFF: [
            ("Kickoff Call", "Conduct kickoff call with customer stakeholders", 1),
            ("Define Success Criteria", "Document success metrics and KPIs", 2),
            ("Assign Team", "Assign CSM and technical resources", 1),
        ],
        OnboardingStage.DATA_CONNECT: [
            ("Connect Data Sources", "Configure connectors for ERP, CRM, databases", 3),
            ("Validate Data Quality", "Run data quality checks and profiling", 2),
            ("Map Data Schema", "Map customer data to EyeX schema", 2),
        ],
        OnboardingStage.AI_INIT: [
            ("Initialize Knowledge Graph", "Build initial knowledge graph from data", 2),
            ("Configure Agents", "Enable and configure industry-specific agents", 1),
            ("Run First Analysis", "Execute initial AI analysis", 2),
        ],
        OnboardingStage.FIRST_REPORT: [
            ("Generate First Report", "Create first executive intelligence report", 1),
            ("Review with Customer", "Walk through report with stakeholders", 1),
            ("Gather Feedback", "Collect feedback on insights quality", 1),
        ],
        OnboardingStage.TRAINING: [
            ("Admin Training", "Train customer admins on platform", 2),
            ("User Training", "Conduct end-user training sessions", 3),
            ("Create Documentation", "Provide customized documentation", 1),
        ],
        OnboardingStage.GO_LIVE: [
            ("Final Validation", "Validate all systems operational", 1),
            ("Go-Live Announcement", "Communicate go-live to organization", 1),
            ("Handoff to Support", "Transition to ongoing support", 1),
        ],
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def start_onboarding(self, org_id: str, deal_id: str | None = None, assigned_csm: str | None = None, target_go_live: datetime | None = None) -> CustomerOnboarding:
        existing = await self.db.execute(select(CustomerOnboarding).where(CustomerOnboarding.org_id == uuid.UUID(org_id)))
        if existing.scalar_one_or_none():
            raise ValueError(f"Onboarding already exists for org {org_id}")

        onboarding = CustomerOnboarding(
            org_id=uuid.UUID(org_id),
            deal_id=uuid.UUID(deal_id) if deal_id else None,
            assigned_csm=uuid.UUID(assigned_csm) if assigned_csm else None,
            target_go_live=target_go_live,
            current_stage=OnboardingStage.SIGNED,
        )
        self.db.add(onboarding)
        await self.db.commit()
        await self.db.refresh(onboarding)

        for stage, tasks in self.DEFAULT_TASKS.items():
            for title, description, priority in tasks:
                task = OnboardingTask(
                    onboarding_id=onboarding.id,
                    stage=stage,
                    title=title,
                    description=description,
                    priority=priority,
                )
                self.db.add(task)

        await self.db.commit()
        logger.info("Started onboarding for org %s", org_id)
        return onboarding

    async def get_onboarding(self, org_id: str) -> CustomerOnboarding | None:
        result = await self.db.execute(select(CustomerOnboarding).where(CustomerOnboarding.org_id == uuid.UUID(org_id)))
        return result.scalar_one_or_none()

    async def advance_stage(self, org_id: str, new_stage: OnboardingStage, notes: str | None = None) -> CustomerOnboarding | None:
        onboarding = await self.get_onboarding(org_id)
        if not onboarding:
            return None

        current_idx = self.STAGE_ORDER.index(onboarding.current_stage)
        new_idx = self.STAGE_ORDER.index(new_stage)

        if new_idx <= current_idx:
            raise ValueError("Cannot move to previous or same stage")

        for stage in self.STAGE_ORDER[current_idx + 1 : new_idx + 1]:
            result = await self.db.execute(
                select(OnboardingTask).where(
                    and_(OnboardingTask.onboarding_id == onboarding.id, OnboardingTask.stage == stage, OnboardingTask.status == "pending")
                )
            )
            pending = result.scalars().all()
            if pending and stage != new_stage:
                raise ValueError(f"Stage {stage.value} has {len(pending)} incomplete tasks")

        onboarding.current_stage = new_stage
        if notes:
            onboarding.notes = (onboarding.notes or "") + f"\n[{datetime.now(UTC).isoformat()}] Advanced to {new_stage.value}: {notes}"

        if new_stage == OnboardingStage.COMPLETED:
            onboarding.completed_at = datetime.now(UTC)
            onboarding.health_score = 100

        await self.db.commit()
        await self.db.refresh(onboarding)
        return onboarding

    async def complete_task(self, task_id: str, completed_by: str) -> OnboardingTask | None:
        result = await self.db.execute(select(OnboardingTask).where(OnboardingTask.id == uuid.UUID(task_id)))
        task = result.scalar_one_or_none()
        if not task:
            return None
        task.status = "completed"
        task.completed_at = datetime.now(UTC)
        task.assigned_to = uuid.UUID(completed_by) if completed_by else task.assigned_to
        await self.db.commit()
        await self.db.refresh(task)

        onboarding = await self.get_onboarding(str(task.onboarding_id))
        if onboarding:
            stage_tasks = await self.db.execute(
                select(OnboardingTask).where(and_(OnboardingTask.onboarding_id == onboarding.id, OnboardingTask.stage == onboarding.current_stage))
            )
            all_tasks = stage_tasks.scalars().all()
            completed_count = sum(1 for t in all_tasks if t.status == "completed")
            total_count = len(all_tasks)
            if total_count > 0:
                onboarding.health_score = min(100, int(50 + (completed_count / total_count) * 50))
            await self.db.commit()

        return task

    async def add_blocker(self, org_id: str, description: str, severity: str = "medium") -> CustomerOnboarding | None:
        onboarding = await self.get_onboarding(org_id)
        if not onboarding:
            return None
        blocker = {
            "id": str(uuid.uuid4()),
            "description": description,
            "severity": severity,
            "created_at": datetime.now(UTC).isoformat(),
            "resolved": False,
        }
        onboarding.blockers = onboarding.blockers + [blocker]
        onboarding.health_score = max(0, onboarding.health_score - (15 if severity == "high" else 10 if severity == "medium" else 5))
        await self.db.commit()
        await self.db.refresh(onboarding)
        return onboarding

    async def resolve_blocker(self, org_id: str, blocker_id: str) -> CustomerOnboarding | None:
        onboarding = await self.get_onboarding(org_id)
        if not onboarding:
            return None
        for blocker in onboarding.blockers:
            if blocker["id"] == blocker_id:
                blocker["resolved"] = True
                blocker["resolved_at"] = datetime.now(UTC).isoformat()
                break
        onboarding.health_score = min(100, onboarding.health_score + 5)
        await self.db.commit()
        await self.db.refresh(onboarding)
        return onboarding


_sales_service: EnterpriseSalesService | None = None
_demo_service: DemoWorkflowService | None = None
_onboarding_service: OnboardingService | None = None


def get_sales_service(db: AsyncSession) -> EnterpriseSalesService:
    global _sales_service
    if _sales_service is None:
        _sales_service = EnterpriseSalesService(db)
    return _sales_service


def get_demo_service(db: AsyncSession) -> DemoWorkflowService:
    global _demo_service
    if _demo_service is None:
        _demo_service = DemoWorkflowService(db)
    return _demo_service


def get_onboarding_service(db: AsyncSession) -> OnboardingService:
    global _onboarding_service
    if _onboarding_service is None:
        _onboarding_service = OnboardingService(db)
    return _onboarding_service
