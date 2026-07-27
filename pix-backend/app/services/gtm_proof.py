from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gtm import (



    BusinessImpactMeasurement,
    CaseStudy,
    IndustryVertical,
    ROICalculator,
)

def _ev(x):
    """Safe enum value accessor."""
    return x.value if hasattr(x, "value") else x


def _model_to_dict(obj):
    """Convert a SQLAlchemy model to a dict for JSON serialization."""
    if obj is None:
        return None
    result = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name, None)
        if hasattr(val, "value"):
            val = val.value
        result[c.name] = val
    return result


def _models_to_dict(objs):
    """Convert a list of SQLAlchemy models to a list of dicts."""
    return [_model_to_dict(o) for o in objs]




logger = logging.getLogger("pix.services.gtm.proof")


@dataclass
class CaseStudyTemplate:
    industry: IndustryVertical
    company_size: str
    problem_statement: str
    solution_summary: str
    key_results: list[dict[str, Any]]
    metrics: dict[str, Any]
    agents_used: list[str]
    connectors_used: list[str]


CASE_STUDY_TEMPLATES: dict[str, CaseStudyTemplate] = {
    "novapay_finance": CaseStudyTemplate(
        industry=IndustryVertical.FINANCE,
        company_size="500 employees",
        problem_statement="NovaPay faced rising fraud losses, slow compliance reporting, and manual risk assessment processes that delayed critical decisions.",
        solution_summary="πX deployed the CEO, CFO, COO, and Risk agents across NovaPay's data, automating risk analysis, compliance reporting, and executive decision support.",
        key_results=[
            {"metric": "Fraud Losses", "before": "$2.1M/year", "after": "$980K/year", "improvement": "53% reduction"},
            {"metric": "Compliance Reporting Time", "before": "3 weeks", "after": "2 days", "improvement": "95% faster"},
            {"metric": "Risk Assessment Speed", "before": "5 days", "after": "4 hours", "improvement": "95% faster"},
        ],
        metrics={
            "revenue_protected": 15000000,
            "cost_savings": 4200000,
            "time_saved_hours": 3200,
            "decisions_accelerated": 180,
        },
        agents_used=["ceo", "cfo", "coo", "risk", "analyst"],
        connectors_used=["core_banking", "crm", "aml_system", "general_ledger"],
    ),
    "apex_manufacturing": CaseStudyTemplate(
        industry=IndustryVertical.MANUFACTURING,
        company_size="5,000 employees",
        problem_statement="Apex Industrial struggled with unplanned equipment downtime, supply chain disruptions, and quality defects across 12 plants.",
        solution_summary="πX's Manufacturing Intelligence package connected ERP, MES, and SCADA systems, enabling predictive maintenance and supply chain optimization.",
        key_results=[
            {"metric": "Unplanned Downtime", "before": "12%", "after": "4%", "improvement": "67% reduction"},
            {"metric": "Inventory Costs", "before": "$48M", "after": "$36M", "improvement": "25% reduction"},
            {"metric": "Defect Rate", "before": "2.5%", "after": "0.8%", "improvement": "68% reduction"},
        ],
        metrics={
            "cost_savings": 12000000,
            "time_saved_hours": 5600,
            "production_uptime_improvement": 8,
            "quality_defects_reduced": 68,
        },
        agents_used=["coo", "cfo", "analyst", "manufacturing_expert"],
        connectors_used=["erp", "mes", "scada", "wms"],
    ),
    "metro_healthcare": CaseStudyTemplate(
        industry=IndustryVertical.HEALTHCARE,
        company_size="12 hospitals",
        problem_statement="Metro Health System had rising operational costs, staffing inefficiencies, and complex revenue cycle management across multiple facilities.",
        solution_summary="πX Healthcare Intelligence connected EHR, billing, and scheduling systems to optimize staffing, revenue cycle, and patient flow.",
        key_results=[
            {"metric": "Overtime Costs", "before": "$8M/year", "after": "$5.2M/year", "improvement": "35% reduction"},
            {"metric": "Patient Wait Time", "before": "42 min", "after": "28 min", "improvement": "33% reduction"},
            {"metric": "Claim Denial Rate", "before": "12%", "after": "7%", "improvement": "42% reduction"},
        ],
        metrics={
            "cost_savings": 8000000,
            "time_saved_hours": 12000,
            "patient_satisfaction_improvement": 18,
            "revenue_uplift": 3500000,
        },
        agents_used=["coo", "cfo", "risk", "healthcare_expert"],
        connectors_used=["ehr", "billing_system", "scheduling", "hr_system"],
    ),
}


class CaseStudyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_case_study(
        self,
        org_id: str,
        title: str,
        industry: IndustryVertical,
        company_size: str,
        problem_statement: str,
        solution_summary: str,
        key_results: list[dict],
        metrics: dict,
        agents_used: list[str],
        connectors_used: list[str],
        testimonial: str | None = None,
        customer_name: str | None = None,
        customer_title: str | None = None,
        tags: list[str] | None = None,
        roi_percentage: float | None = None,
        time_to_value_days: int | None = None,
        publish: bool = False,
    ) -> CaseStudy:
        case_study = CaseStudy(
            org_id=uuid.UUID(org_id),
            title=title,
            industry=industry,
            company_size=company_size,
            problem_statement=problem_statement,
            solution_summary=solution_summary,
            key_results=key_results,
            metrics=metrics,
            agents_used=agents_used,
            connectors_used=connectors_used,
            testimonial=testimonial,
            customer_name=customer_name,
            customer_title=customer_title,
            tags=tags or [],
            roi_percentage=roi_percentage,
            time_to_value_days=time_to_value_days,
            is_published=publish,
            published_at=datetime.now(UTC) if publish else None,
        )
        self.db.add(case_study)
        await self.db.commit()
        await self.db.refresh(case_study)
        return case_study

    async def get_case_study(self, case_study_id: str) -> CaseStudy | None:
        result = await self.db.execute(select(CaseStudy).where(CaseStudy.id == uuid.UUID(case_study_id)))
        return result.scalar_one_or_none()

    async def list_case_studies(
        self,
        industry: IndustryVertical | None = None,
        published_only: bool = False,
        limit: int = 50,
    ) -> list[CaseStudy]:
        query = select(CaseStudy)
        conditions = []
        if industry:
            conditions.append(CaseStudy.industry == industry)
        if published_only:
            conditions.append(CaseStudy.is_published.is_(True))
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(desc(CaseStudy.created_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def publish_case_study(self, case_study_id: str) -> CaseStudy | None:
        case_study = await self.get_case_study(case_study_id)
        if not case_study:
            return None
        case_study.is_published = True
        case_study.published_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(case_study)
        return case_study

    async def create_from_template(self, template_key: str, org_id: str, customer_name: str, title: str | None = None) -> CaseStudy:
        template = CASE_STUDY_TEMPLATES.get(template_key)
        if not template:
            raise ValueError(f"Template not found: {template_key}")

        return await self.create_case_study(
            org_id=org_id,
            title=title or f"{customer_name}: {_ev(template.industry).title()} Transformation",
            industry=template.industry,
            company_size=template.company_size,
            problem_statement=template.problem_statement,
            solution_summary=template.solution_summary,
            key_results=template.key_results,
            metrics=template.metrics,
            agents_used=template.agents_used,
            connectors_used=template.connectors_used,
            customer_name=customer_name,
            publish=False,
        )

    async def initialize_demo_case_studies(self, org_id: str) -> list[CaseStudy]:
        studies = []
        for key, template in CASE_STUDY_TEMPLATES.items():
            customer_name = key.split("_")[0].title()
            study = await self.create_from_template(key, org_id, customer_name)
            studies.append(study)
        return _models_to_dict(studies)


class ROICalculatorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def calculate_manufacturing_roi(
        self,
        org_id: str,
        annual_revenue: float,
        downtime_cost_per_hour: float,
        annual_downtime_hours: float,
        maintenance_staff_count: int,
        avg_maintenance_salary: float,
        inventory_value: float,
        defect_rate: float,
    ) -> ROICalculator:
        downtime_reduction = annual_downtime_hours * 0.25
        downtime_savings = downtime_reduction * downtime_cost_per_hour

        maintenance_time_savings = maintenance_staff_count * avg_maintenance_salary * 0.15
        inventory_savings = inventory_value * 0.15
        defect_savings = annual_revenue * (defect_rate / 100) * 0.40

        total_benefit = downtime_savings + maintenance_time_savings + inventory_savings + defect_savings
        annual_cost = 120000  # Estimated πX cost
        roi = ((total_benefit - annual_cost) / annual_cost) * 100

        results = {
            "downtime_savings": round(downtime_savings, 2),
            "maintenance_savings": round(maintenance_time_savings, 2),
            "inventory_savings": round(inventory_savings, 2),
            "quality_savings": round(defect_savings, 2),
            "total_annual_benefit": round(total_benefit, 2),
            "annual_pix_cost": annual_cost,
            "net_annual_value": round(total_benefit - annual_cost, 2),
            "roi_percentage": round(roi, 1),
            "payback_months": round(annual_cost / max(total_benefit / 12, 1), 1),
        }

        assumptions = {
            "downtime_reduction_pct": 25,
            "maintenance_time_savings_pct": 15,
            "inventory_optimization_pct": 15,
            "defect_reduction_pct": 40,
        }

        return await self._save_calculator(org_id, "manufacturing", {
            "annual_revenue": annual_revenue,
            "downtime_cost_per_hour": downtime_cost_per_hour,
            "annual_downtime_hours": annual_downtime_hours,
            "maintenance_staff_count": maintenance_staff_count,
            "avg_maintenance_salary": avg_maintenance_salary,
            "inventory_value": inventory_value,
            "defect_rate": defect_rate,
        }, results, assumptions)

    async def calculate_finance_roi(
        self,
        org_id: str,
        annual_revenue: float,
        fraud_losses_last_year: float,
        compliance_staff_count: int,
        avg_compliance_salary: float,
        report_count_per_month: int,
        avg_hours_per_report: float,
        risk_review_count: int,
        avg_hours_per_review: float,
    ) -> ROICalculator:
        fraud_savings = fraud_losses_last_year * 0.35

        report_hours_saved = report_count_per_month * 12 * avg_hours_per_report * 0.75
        compliance_salary_savings = compliance_staff_count * avg_compliance_salary * 0.20
        review_hours_saved = risk_review_count * avg_hours_per_review * 0.50

        total_benefit = fraud_savings + compliance_salary_savings + (report_hours_saved + review_hours_saved) * 75
        annual_cost = 180000
        roi = ((total_benefit - annual_cost) / annual_cost) * 100

        results = {
            "fraud_loss_reduction": round(fraud_savings, 2),
            "compliance_time_savings_hours": round(report_hours_saved + review_hours_saved, 0),
            "compliance_cost_savings": round(compliance_salary_savings, 2),
            "total_annual_benefit": round(total_benefit, 2),
            "annual_pix_cost": annual_cost,
            "net_annual_value": round(total_benefit - annual_cost, 2),
            "roi_percentage": round(roi, 1),
            "payback_months": round(annual_cost / max(total_benefit / 12, 1), 1),
        }

        assumptions = {
            "fraud_reduction_pct": 35,
            "report_time_savings_pct": 75,
            "compliance_staff_savings_pct": 20,
            "risk_review_time_savings_pct": 50,
            "hourly_value": 75,
        }

        return await self._save_calculator(org_id, "finance", {
            "annual_revenue": annual_revenue,
            "fraud_losses_last_year": fraud_losses_last_year,
            "compliance_staff_count": compliance_staff_count,
            "avg_compliance_salary": avg_compliance_salary,
            "report_count_per_month": report_count_per_month,
            "avg_hours_per_report": avg_hours_per_report,
            "risk_review_count": risk_review_count,
            "avg_hours_per_review": avg_hours_per_review,
        }, results, assumptions)

    async def calculate_healthcare_roi(
        self,
        org_id: str,
        annual_operating_cost: float,
        overtime_annual_cost: float,
        patient_volume_annual: int,
        average_wait_time_minutes: float,
        denial_annual_loss: float,
        beds: int,
    ) -> ROICalculator:
        overtime_savings = overtime_annual_cost * 0.30
        wait_time_value = (patient_volume_annual * average_wait_time_minutes * 0.25 * 0.50) / 60
        denial_savings = denial_annual_loss * 0.30
        operational_savings = annual_operating_cost * 0.02

        total_benefit = overtime_savings + wait_time_value + denial_savings + operational_savings
        annual_cost = 150000
        roi = ((total_benefit - annual_cost) / annual_cost) * 100

        results = {
            "overtime_savings": round(overtime_savings, 2),
            "patient_flow_value": round(wait_time_value, 2),
            "denial_savings": round(denial_savings, 2),
            "operational_efficiency_savings": round(operational_savings, 2),
            "total_annual_benefit": round(total_benefit, 2),
            "annual_pix_cost": annual_cost,
            "net_annual_value": round(total_benefit - annual_cost, 2),
            "roi_percentage": round(roi, 1),
            "payback_months": round(annual_cost / max(total_benefit / 12, 1), 1),
        }

        assumptions = {
            "overtime_reduction_pct": 30,
            "wait_time_reduction_pct": 25,
            "denial_reduction_pct": 30,
            "operating_cost_reduction_pct": 2,
            "patient_time_value_per_hour": 0.50,
        }

        return await self._save_calculator(org_id, "healthcare", {
            "annual_operating_cost": annual_operating_cost,
            "overtime_annual_cost": overtime_annual_cost,
            "patient_volume_annual": patient_volume_annual,
            "average_wait_time_minutes": average_wait_time_minutes,
            "denial_annual_loss": denial_annual_loss,
            "beds": beds,
        }, results, assumptions)

    async def _save_calculator(self, org_id: str, calculator_type: str, inputs: dict, results: dict, assumptions: dict) -> ROICalculator:
        calculator = ROICalculator(
            org_id=uuid.UUID(org_id),
            calculator_type=calculator_type,
            inputs=inputs,
            results=results,
            assumptions=assumptions,
        )
        self.db.add(calculator)
        await self.db.commit()
        await self.db.refresh(calculator)
        return calculator

    async def get_calculator(self, calculator_id: str) -> ROICalculator | None:
        result = await self.db.execute(select(ROICalculator).where(ROICalculator.id == uuid.UUID(calculator_id)))
        return result.scalar_one_or_none()

    async def list_calculators(self, org_id: str, limit: int = 20) -> list[ROICalculator]:
        result = await self.db.execute(
            select(ROICalculator)
            .where(ROICalculator.org_id == uuid.UUID(org_id))
            .order_by(desc(ROICalculator.calculated_at))
            .limit(limit)
        )
        return list(result.scalars().all())


class BusinessImpactService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_measurement(
        self,
        org_id: str,
        measurement_type: str,
        metric_name: str,
        baseline_value: float,
        current_value: float,
        target_value: float | None = None,
        unit: str = "",
        attribution: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> BusinessImpactMeasurement:
        change_pct = ((current_value - baseline_value) / baseline_value * 100) if baseline_value != 0 else 0
        measurement = BusinessImpactMeasurement(
            org_id=uuid.UUID(org_id),
            measurement_type=measurement_type,
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            target_value=target_value,
            unit=unit,
            change_percentage=change_pct,
            is_positive=change_pct >= 0,
            attribution=attribution or [],
            meta_data=metadata,
        )
        self.db.add(measurement)
        await self.db.commit()
        await self.db.refresh(measurement)
        return measurement

    async def get_impact_summary(self, org_id: str, measurement_type: str | None = None) -> dict[str, Any]:
        query = select(BusinessImpactMeasurement).where(BusinessImpactMeasurement.org_id == uuid.UUID(org_id))
        if measurement_type:
            query = query.where(BusinessImpactMeasurement.measurement_type == measurement_type)
        query = query.order_by(desc(BusinessImpactMeasurement.measured_at))
        result = await self.db.execute(query)
        measurements = list(result.scalars().all())

        return {
            "total_measurements": len(measurements),
            "positive_impact": sum(1 for m in measurements if m.is_positive),
            "negative_impact": sum(1 for m in measurements if not m.is_positive),
            "avg_change_pct": sum(m.change_percentage for m in measurements) / len(measurements) if measurements else 0,
            "measurements": [
                {
                    "type": m.measurement_type,
                    "metric": m.metric_name,
                    "baseline": m.baseline_value,
                    "current": m.current_value,
                    "change_pct": m.change_percentage,
                    "unit": m.unit,
                    "measured_at": m.measured_at.isoformat(),
                }
                for m in measurements
            ],
        }


class CustomerProofService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.case_study = CaseStudyService(db)
        self.roi = ROICalculatorService(db)
        self.impact = BusinessImpactService(db)

    async def generate_proof_package(self, org_id: str, industry: IndustryVertical) -> dict[str, Any]:
        case_studies = await self.case_study.list_case_studies(industry=industry, published_only=True, limit=3)
        calculators = await self.roi.list_calculators(org_id, limit=5)
        impact_summary = await self.impact.get_impact_summary(org_id)

        return {
            "org_id": org_id,
            "industry": industry.value,
            "case_studies": [
                {
                    "title": c.title,
                    "customer": c.customer_name,
                    "results": c.key_results,
                    "roi": c.roi_percentage,
                    "testimonial": c.testimonial,
                }
                for c in case_studies
            ],
            "roi_calculators": [
                {
                    "type": calc.calculator_type,
                    "roi": calc.results.get("roi_percentage"),
                    "payback_months": calc.results.get("payback_months"),
                    "net_value": calc.results.get("net_annual_value"),
                }
                for calc in calculators
            ],
            "impact_summary": impact_summary,
            "generated_at": datetime.now(UTC).isoformat(),
        }


_proof_service: CustomerProofService | None = None


def get_proof_service(db: AsyncSession) -> CustomerProofService:
    global _proof_service
    if _proof_service is None:
        _proof_service = CustomerProofService(db)
    return _proof_service


def get_case_study_service(db: AsyncSession) -> CaseStudyService:
    return get_proof_service(db).case_study


def get_roi_calculator_service(db: AsyncSession) -> ROICalculatorService:
    return get_proof_service(db).roi


def get_business_impact_service(db: AsyncSession) -> BusinessImpactService:
    return get_proof_service(db).impact
