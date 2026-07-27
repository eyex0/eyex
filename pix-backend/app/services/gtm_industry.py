from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gtm import IndustrySolution, IndustryVertical

logger = logging.getLogger("pix.services.gtm.industry")


@dataclass
class IndustryGTMPlaybook:
    industry: IndustryVertical
    name: str
    description: str
    key_problems: list[str]
    key_use_cases: list[dict[str, Any]]
    required_agents: list[str]
    required_connectors: list[str]
    compliance_requirements: list[str]
    demo_scenarios: list[dict[str, Any]]
    roi_metrics: list[dict[str, Any]]
    case_studies: list[dict[str, Any]]
    pricing_guidance: dict[str, Any]


INDUSTRY_PLAYBOOKS: dict[IndustryVertical, IndustryGTMPlaybook] = {
    IndustryVertical.MANUFACTURING: IndustryGTMPlaybook(
        industry=IndustryVertical.MANUFACTURING,
        name="Manufacturing Intelligence",
        description="Optimize production, supply chain, quality, and predictive maintenance with AI agents.",
        key_problems=[
            "Unplanned downtime costing millions",
            "Supply chain disruptions and inventory mismatches",
            "Quality defects and recalls",
            "Energy consumption inefficiency",
            "Workforce safety incidents",
        ],
        key_use_cases=[
            {"title": "Predictive Maintenance", "description": "Predict equipment failures before they happen", "agents": ["coo", "analyst"], "impact": "25% reduction in downtime"},
            {"title": "Demand Forecasting", "description": "Forecast demand across products and regions", "agents": ["cfo", "analyst"], "impact": "20% inventory optimization"},
            {"title": "Quality Control", "description": "Identify root causes of quality issues", "agents": ["coo", "risk"], "impact": "40% defect reduction"},
            {"title": "Energy Optimization", "description": "Optimize energy usage across plants", "agents": ["cfo", "coo"], "impact": "15% cost savings"},
        ],
        required_agents=["ceo", "cfo", "coo", "risk", "analyst", "strategist", "manufacturing_expert"],
        required_connectors=["erp", "mes", "scada", "plm", "wms"],
        compliance_requirements=["ISO 9001", "ISO 14001", "OSHA", "IEC 62443"],
        demo_scenarios=[
            {"name": "Downtime Prevention", "data": "Historical machine sensor data and maintenance logs", "outcome": "Predicted failure 48 hours in advance"},
            {"name": "Supply Chain Resilience", "data": "Supplier performance and inventory levels", "outcome": "Identified alternative suppliers and safety stock adjustments"},
        ],
        roi_metrics=[
            {"metric": "Unplanned Downtime Reduction", "typical": "20-30%", "unit": "%"},
            {"metric": "Inventory Cost Savings", "typical": "15-25%", "unit": "%"},
            {"metric": "Quality Defect Reduction", "typical": "30-50%", "unit": "%"},
        ],
        case_studies=[
            {"company": "Apex Industrial", "size": "5,000 employees", "result": "$12M annual savings from predictive maintenance", "quote": "πX transformed our maintenance strategy."},
        ],
        pricing_guidance={
            "starter_monthly": 499,
            "professional_monthly": 1999,
            "enterprise_monthly": 4999,
            "usage_multiplier": 1.5,
            "notes": "Pricing scales by number of plants and connected machines.",
        },
    ),
    IndustryVertical.HEALTHCARE: IndustryGTMPlaybook(
        industry=IndustryVertical.HEALTHCARE,
        name="Healthcare Intelligence",
        description="Improve patient outcomes, operational efficiency, compliance, and financial performance.",
        key_problems=[
            "Rising operational costs",
            "Clinical workflow inefficiencies",
            "Regulatory compliance complexity",
            "Patient no-shows and readmissions",
            "Staff burnout and scheduling gaps",
        ],
        key_use_cases=[
            {"title": "Operational Efficiency", "description": "Optimize scheduling, staffing, and resource allocation", "agents": ["coo", "cfo"], "impact": "18% efficiency gain"},
            {"title": "Revenue Cycle Management", "description": "Improve billing accuracy and reduce denials", "agents": ["cfo", "analyst"], "impact": "12% revenue uplift"},
            {"title": "Compliance Monitoring", "description": "Continuously monitor HIPAA and quality compliance", "agents": ["risk", "coo"], "impact": "Zero audit findings"},
            {"title": "Patient Flow Optimization", "description": "Predict admission and discharge patterns", "agents": ["coo", "analyst"], "impact": "25% reduced wait times"},
        ],
        required_agents=["ceo", "cfo", "coo", "risk", "analyst", "healthcare_expert"],
        required_connectors=["ehr", "billing_system", "scheduling", "hr_system", "claims"],
        compliance_requirements=["HIPAA", "HITECH", " Joint Commission", "CMS"],
        demo_scenarios=[
            {"name": "Revenue Leakage Detection", "data": "Billing and claims data", "outcome": "Identified $2M in recoverable revenue"},
            {"name": "Staff Optimization", "data": "Historical patient volumes and staffing levels", "outcome": "Reduced overtime by 22%"},
        ],
        roi_metrics=[
            {"metric": "Cost-to-Collect Reduction", "typical": "10-15%", "unit": "%"},
            {"metric": "Patient Wait Time Reduction", "typical": "20-30%", "unit": "%"},
            {"metric": "Denial Rate Reduction", "typical": "15-25%", "unit": "%"},
        ],
        case_studies=[
            {"company": "Metro Health System", "size": "12 hospitals", "result": "$8M operational savings in year one", "quote": "πX gave us visibility we never had before."},
        ],
        pricing_guidance={
            "starter_monthly": 999,
            "professional_monthly": 2999,
            "enterprise_monthly": 7999,
            "usage_multiplier": 2.0,
            "notes": "Enterprise pricing includes BAAs, HIPAA compliance, and dedicated support.",
        },
    ),
    IndustryVertical.LOGISTICS: IndustryGTMPlaybook(
        industry=IndustryVertical.LOGISTICS,
        name="Logistics Intelligence",
        description="Optimize routes, fleets, warehouses, and delivery networks with AI-driven decisions.",
        key_problems=[
            "Fuel costs volatility",
            "Route inefficiencies",
            "Warehouse capacity constraints",
            "Delivery delays and customer complaints",
            "Carrier performance variability",
        ],
        key_use_cases=[
            {"title": "Route Optimization", "description": "Optimize delivery routes in real-time", "agents": ["coo", "analyst"], "impact": "15% fuel savings"},
            {"title": "Demand-Sensing", "description": "Predict shipment volumes and warehouse needs", "agents": ["cfo", "analyst"], "impact": "20% better capacity planning"},
            {"title": "Carrier Selection", "description": "Score and select optimal carriers", "agents": ["coo", "strategist"], "impact": "10% cost reduction"},
            {"title": "Warehouse Efficiency", "description": "Optimize picking and workforce allocation", "agents": ["coo"], "impact": "30% throughput increase"},
        ],
        required_agents=["ceo", "cfo", "coo", "risk", "analyst", "logistics_expert"],
        required_connectors=["tms", "wms", "gps_telemetry", "erp", "carrier_api"],
        compliance_requirements=["DOT", "Customs", "ISO 28000", "GDPR for EU routes"],
        demo_scenarios=[
            {"name": "Last-Mile Optimization", "data": "Delivery addresses, traffic, vehicle capacity", "outcome": "Reduced delivery time by 18%"},
            {"name": "Freight Cost Analysis", "data": "Carrier invoices and shipment data", "outcome": "Found $1.5M in overcharges"},
        ],
        roi_metrics=[
            {"metric": "Fuel Cost Reduction", "typical": "10-20%", "unit": "%"},
            {"metric": "On-Time Delivery Improvement", "typical": "15-25%", "unit": "%"},
            {"metric": "Warehouse Throughput Gain", "typical": "20-35%", "unit": "%"},
        ],
        case_studies=[
            {"company": "Global Freight Co", "size": "2,000 trucks", "result": "$6M annual logistics savings", "quote": "πX optimized our entire network."},
        ],
        pricing_guidance={
            "starter_monthly": 599,
            "professional_monthly": 2499,
            "enterprise_monthly": 5999,
            "usage_multiplier": 1.8,
            "notes": "Pricing scales by fleet size, warehouse count, and shipment volume.",
        },
    ),
    IndustryVertical.FINANCE: IndustryGTMPlaybook(
        industry=IndustryVertical.FINANCE,
        name="Finance Intelligence",
        description="Enhance risk management, compliance, fraud detection, and investment decisions.",
        key_problems=[
            "Regulatory reporting burden",
            "Fraud and financial crime",
            "Credit risk assessment",
            "Portfolio optimization",
            "Customer churn in banking",
        ],
        key_use_cases=[
            {"title": "Risk Assessment", "description": "Assess credit, market, and operational risks", "agents": ["risk", "cfo"], "impact": "30% faster risk reviews"},
            {"title": "Fraud Detection", "description": "Identify anomalous transactions and patterns", "agents": ["risk", "analyst"], "impact": "50% fraud reduction"},
            {"title": "Regulatory Reporting", "description": "Automate compliance reports and audits", "agents": ["cfo", "risk"], "impact": "80% time savings"},
            {"title": "Customer Intelligence", "description": "Predict churn and cross-sell opportunities", "agents": ["ceo", "analyst"], "impact": "15% revenue uplift"},
        ],
        required_agents=["ceo", "cfo", "coo", "risk", "analyst", "finance_expert"],
        required_connectors=["core_banking", "trading_platform", "crm", "aml_system", "general_ledger"],
        compliance_requirements=["SOX", "Basel III/IV", "GDPR", "PCI-DSS", "AML/KYC"],
        demo_scenarios=[
            {"name": "Credit Risk Scoring", "data": "Loan portfolio and macroeconomic indicators", "outcome": "Reduced defaults by 12%"},
            {"name": "Fraud Pattern Detection", "data": "Transaction history and alerts", "outcome": "Flagged $5M in suspicious activity"},
        ],
        roi_metrics=[
            {"metric": "Fraud Loss Reduction", "typical": "30-50%", "unit": "%"},
            {"metric": "Compliance Reporting Time Reduction", "typical": "60-80%", "unit": "%"},
            {"metric": "Credit Default Reduction", "typical": "10-20%", "unit": "%"},
        ],
        case_studies=[
            {"company": "NovaPay", "size": "Fintech, 500 employees", "result": "$15M revenue protected and 40% faster compliance", "quote": "πX is our competitive edge in risk management."},
        ],
        pricing_guidance={
            "starter_monthly": 1299,
            "professional_monthly": 3999,
            "enterprise_monthly": 9999,
            "usage_multiplier": 2.5,
            "notes": "Enterprise includes SOC 2, custom SLAs, and dedicated security review.",
        },
    ),
    IndustryVertical.RETAIL: IndustryGTMPlaybook(
        industry=IndustryVertical.RETAIL,
        name="Retail Intelligence",
        description="Optimize merchandising, pricing, demand forecasting, and customer experience.",
        key_problems=[
            "Inventory markdowns and stockouts",
            "Pricing pressure from competitors",
            "Customer churn and loyalty decline",
            "Supply chain delays",
            "Omnichannel complexity",
        ],
        key_use_cases=[
            {"title": "Demand Forecasting", "description": "Predict product demand by channel and region", "agents": ["cfo", "analyst"], "impact": "25% stockout reduction"},
            {"title": "Dynamic Pricing", "description": "Optimize prices based on demand and competition", "agents": ["cfo", "strategist"], "impact": "5% margin improvement"},
            {"title": "Customer Segmentation", "description": "Segment customers for targeted campaigns", "agents": ["ceo", "analyst"], "impact": "20% campaign ROI uplift"},
            {"title": "Omnichannel Optimization", "description": "Balance inventory across channels", "agents": ["coo", "analyst"], "impact": "15% inventory efficiency"},
        ],
        required_agents=["ceo", "cfo", "coo", "analyst", "strategist", "retail_expert"],
        required_connectors=["pos", "ecommerce", "inventory", "crm", "marketing_platform"],
        compliance_requirements=["PCI-DSS", "GDPR/CCPA", "Consumer Protection"],
        demo_scenarios=[
            {"name": "Assortment Planning", "data": "Sales, inventory, and customer data", "outcome": "Increased basket size by 12%"},
            {"name": "Churn Prediction", "data": "Customer purchase history", "outcome": "Reduced churn by 18%"},
        ],
        roi_metrics=[
            {"metric": "Gross Margin Improvement", "typical": "3-7%", "unit": "%"},
            {"metric": "Stockout Reduction", "typical": "20-35%", "unit": "%"},
            {"metric": "Marketing ROI Uplift", "typical": "15-30%", "unit": "%"},
        ],
        case_studies=[
            {"company": "StyleMart", "size": "500 stores", "result": "$22M revenue increase from demand forecasting", "quote": "πX made our merchandising proactive."},
        ],
        pricing_guidance={
            "starter_monthly": 799,
            "professional_monthly": 2499,
            "enterprise_monthly": 5999,
            "usage_multiplier": 1.6,
            "notes": "Pricing scales by number of SKUs, stores, and transaction volume.",
        },
    ),
}


class IndustryExpansionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def initialize_default_solutions(self) -> list[IndustrySolution]:
        solutions = []
        for vertical, playbook in INDUSTRY_PLAYBOOKS.items():
            existing = await self.db.execute(
                select(IndustrySolution).where(IndustrySolution.industry == vertical)
            )
            if existing.scalar_one_or_none():
                continue

            solution = IndustrySolution(
                industry=vertical,
                name=playbook.name,
                description=playbook.description,
                key_problems=playbook.key_problems,
                key_use_cases=playbook.key_use_cases,
                required_agents=playbook.required_agents,
                required_connectors=playbook.required_connectors,
                compliance_requirements=playbook.compliance_requirements,
                demo_scenarios=playbook.demo_scenarios,
                roi_metrics=playbook.roi_metrics,
                case_studies=playbook.case_studies,
                pricing_guidance=playbook.pricing_guidance,
                is_active=True,
                sort_order=list(IndustryVertical).index(vertical),
            )
            self.db.add(solution)
            solutions.append(solution)

        await self.db.commit()
        for s in solutions:
            await self.db.refresh(s)
        return solutions

    async def get_solution(self, industry: IndustryVertical) -> IndustrySolution | None:
        result = await self.db.execute(
            select(IndustrySolution).where(IndustrySolution.industry == industry)
        )
        return result.scalar_one_or_none()

    async def list_solutions(self, active_only: bool = True) -> list[IndustrySolution]:
        query = select(IndustrySolution)
        if active_only:
            query = query.where(IndustrySolution.is_active)
        query = query.order_by(IndustrySolution.sort_order)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_playbook(self, industry: IndustryVertical) -> dict[str, Any]:
        solution = await self.get_solution(industry)
        if not solution:
            playbook = INDUSTRY_PLAYBOOKS.get(industry)
            if not playbook:
                return {"error": f"Industry not found: {industry}"}
            return self._playbook_to_dict(playbook)
        return self._solution_to_dict(solution)

    async def get_use_case_recommendation(self, industry: IndustryVertical, business_problem: str) -> list[dict[str, Any]]:
        playbook = await self.get_playbook(industry)
        if "error" in playbook:
            return []

        keywords = set(business_problem.lower().split())
        scored = []
        for uc in playbook["key_use_cases"]:
            title = uc["title"].lower()
            desc = uc["description"].lower()
            score = sum(1 for k in keywords if k in title or k in desc)
            if score > 0:
                scored.append((score, uc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [uc for _, uc in scored[:3]]

    async def get_demo_script(self, industry: IndustryVertical, scenario_name: str | None = None) -> dict[str, Any]:
        playbook = await self.get_playbook(industry)
        if "error" in playbook:
            return playbook

        scenarios = playbook["demo_scenarios"]
        if scenario_name:
            scenario = next((s for s in scenarios if s["name"] == scenario_name), None)
        else:
            scenario = scenarios[0] if scenarios else None

        return {
            "industry": industry.value,
            "scenario": scenario,
            "key_problems": playbook["key_problems"],
            "roi_metrics": playbook["roi_metrics"],
            "required_agents": playbook["required_agents"],
            "compliance": playbook["compliance_requirements"],
            "talking_points": [
                f"Address: {playbook['key_problems'][0]}",
                f"Demonstrate: {scenario['name'] if scenario else 'AI analysis'}",
                f"Quantify: {playbook['roi_metrics'][0]['metric']} ({playbook['roi_metrics'][0]['typical']})",
            ],
        }

    async def get_pricing_recommendation(self, industry: IndustryVertical, employee_count: int, annual_revenue: float | None = None) -> dict[str, Any]:
        playbook = await self.get_playbook(industry)
        if "error" in playbook:
            return playbook

        guidance = playbook["pricing_guidance"]
        multiplier = guidance["usage_multiplier"]

        if employee_count < 50:
            recommended = "starter"
            base_price = guidance["starter_monthly"]
        elif employee_count < 500:
            recommended = "professional"
            base_price = guidance["professional_monthly"]
        else:
            recommended = "enterprise"
            base_price = guidance["enterprise_monthly"]

        estimated_annual = base_price * multiplier * 12

        return {
            "industry": industry.value,
            "recommended_plan": recommended,
            "estimated_monthly": round(base_price * multiplier, 2),
            "estimated_annual": round(estimated_annual, 2),
            "currency": "USD",
            "notes": guidance["notes"],
            "assumptions": {
                "employee_count": employee_count,
                "annual_revenue": annual_revenue,
                "usage_multiplier": multiplier,
            },
        }

    def _playbook_to_dict(self, playbook: IndustryGTMPlaybook) -> dict[str, Any]:
        return {
            "industry": playbook.industry.value,
            "name": playbook.name,
            "description": playbook.description,
            "key_problems": playbook.key_problems,
            "key_use_cases": playbook.key_use_cases,
            "required_agents": playbook.required_agents,
            "required_connectors": playbook.required_connectors,
            "compliance_requirements": playbook.compliance_requirements,
            "demo_scenarios": playbook.demo_scenarios,
            "roi_metrics": playbook.roi_metrics,
            "case_studies": playbook.case_studies,
            "pricing_guidance": playbook.pricing_guidance,
        }

    def _solution_to_dict(self, solution: IndustrySolution) -> dict[str, Any]:
        return {
            "id": str(solution.id),
            "industry": solution.industry.value,
            "name": solution.name,
            "description": solution.description,
            "key_problems": solution.key_problems,
            "key_use_cases": solution.key_use_cases,
            "required_agents": solution.required_agents,
            "required_connectors": solution.required_connectors,
            "compliance_requirements": solution.compliance_requirements,
            "demo_scenarios": solution.demo_scenarios,
            "roi_metrics": solution.roi_metrics,
            "case_studies": solution.case_studies,
            "pricing_guidance": solution.pricing_guidance,
            "is_active": solution.is_active,
            "sort_order": solution.sort_order,
        }


_industry_service: IndustryExpansionService | None = None


def get_industry_expansion_service(db: AsyncSession) -> IndustryExpansionService:
    global _industry_service
    if _industry_service is None:
        _industry_service = IndustryExpansionService(db)
    return _industry_service
