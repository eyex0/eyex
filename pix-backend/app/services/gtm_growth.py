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
    IndustryVertical,
    Lead,
    MarketOpportunity,
    PipelineDeal,
    SalesPrediction,
)

logger = logging.getLogger("pix.services.gtm.growth")


@dataclass
class MarketSignal:
    signal_type: str
    description: str
    strength: float  # 0-1
    source: str


@dataclass
class GrowthRecommendation:
    area: str
    priority: str
    title: str
    description: str
    expected_impact: float
    actions: list[str]


class GrowthIntelligenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def identify_market_opportunities(
        self,
        industry: IndustryVertical | None = None,
        region: str | None = None,
        company_size: str | None = None,
    ) -> list[MarketOpportunity]:
        opportunities = []

        opportunity_data = [
            {
                "title": "Digital Transformation Acceleration",
                "description": "Enterprises are accelerating AI adoption post-pandemic. High demand for AI operating systems.",
                "industry": IndustryVertical.MANUFACTURING,
                "region": "North America",
                "company_size": "enterprise",
                "estimated_value": 5000000,
                "probability": 75,
                "source": "market_research",
                "signals": [
                    {"type": "trend", "description": "AI adoption up 40% YoY", "strength": 0.8, "source": "industry_report"},
                    {"type": "regulatory", "description": "New compliance mandates driving automation", "strength": 0.7, "source": "regulatory_news"},
                ],
                "recommended_approach": "Target COOs and CFOs with ROI-driven manufacturing demos.",
                "competitive_landscape": [
                    {"competitor": "Palantir", "strength": "Data integration", "weakness": "Complex deployment"},
                    {"competitor": "Databricks", "strength": "Lakehouse", "weakness": "No agent orchestration"},
                ],
            },
            {
                "title": "Healthcare Cost Optimization",
                "description": "Health systems face margin pressure and need operational efficiency tools.",
                "industry": IndustryVertical.HEALTHCARE,
                "region": "Europe",
                "company_size": "enterprise",
                "estimated_value": 3500000,
                "probability": 65,
                "source": "customer_insights",
                "signals": [
                    {"type": "financial", "description": "Hospital margins down 15%", "strength": 0.9, "source": "earnings_calls"},
                    {"type": "trend", "description": "AI clinical operations pilots increasing", "strength": 0.6, "source": "industry_report"},
                ],
                "recommended_approach": "Lead with revenue cycle and staffing optimization use cases.",
                "competitive_landscape": [
                    {"competitor": "Epic", "strength": "EHR dominance", "weakness": "Limited analytics"},
                ],
            },
            {
                "title": "Finance Risk Modernization",
                "description": "Banks and fintechs need real-time risk detection and compliance automation.",
                "industry": IndustryVertical.FINANCE,
                "region": "Middle East",
                "company_size": "mid_market",
                "estimated_value": 4200000,
                "probability": 80,
                "source": "partner_referral",
                "signals": [
                    {"type": "regulatory", "description": "New Basel requirements", "strength": 0.85, "source": "central_bank"},
                    {"type": "trend", "description": "Fraud losses rising 25%", "strength": 0.8, "source": "industry_report"},
                ],
                "recommended_approach": "Partner with local system integrators for compliance-heavy deployments.",
                "competitive_landscape": [
                    {"competitor": "SAS", "strength": "Risk analytics", "weakness": "Legacy UX"},
                    {"competitor": "FICO", "strength": "Fraud scoring", "weakness": "Limited AI agents"},
                ],
            },
            {
                "title": "Retail Personalization at Scale",
                "description": "Retailers need AI-driven demand forecasting and dynamic pricing.",
                "industry": IndustryVertical.RETAIL,
                "region": "North America",
                "company_size": "mid_market",
                "estimated_value": 2800000,
                "probability": 70,
                "source": "web_intent",
                "signals": [
                    {"type": "trend", "description": "E-commerce growth stabilizing, margin focus increasing", "strength": 0.75, "source": "market_data"},
                    {"type": "financial", "description": "Inventory markdowns hurting margins", "strength": 0.8, "source": "retail_earnings"},
                ],
                "recommended_approach": "Demo dynamic pricing and demand forecasting with 6-week ROI proof.",
                "competitive_landscape": [
                    {"competitor": "DemandTec", "strength": "Pricing", "weakness": "Narrow scope"},
                    {"competitor": "Blue Yonder", "strength": "Supply chain", "weakness": "Slow implementation"},
                ],
            },
            {
                "title": "Logistics Network Optimization",
                "description": "3PLs and shippers are investing in route optimization and warehouse automation.",
                "industry": IndustryVertical.LOGISTICS,
                "region": "Asia Pacific",
                "company_size": "enterprise",
                "estimated_value": 3900000,
                "probability": 72,
                "source": "event",
                "signals": [
                    {"type": "trend", "description": "Fuel costs remain volatile", "strength": 0.8, "source": "commodity_data"},
                    {"type": "regulatory", "description": "ESG reporting requirements", "strength": 0.65, "source": "regulatory"},
                ],
                "recommended_approach": "Co-sell with AWS and Azure field teams for logistics vertical.",
                "competitive_landscape": [
                    {"competitor": "project44", "strength": "Visibility", "weakness": "No optimization"},
                    {"competitor": "FourKites", "strength": "Real-time tracking", "weakness": "Limited AI"},
                ],
            },
        ]

        for data in opportunity_data:
            if industry and data["industry"] != industry:
                continue
            if region and data["region"] != region:
                continue
            if company_size and data["company_size"] != company_size:
                continue

            opp = MarketOpportunity(
                title=data["title"],
                description=data["description"],
                industry=data["industry"],
                region=data["region"],
                company_size=data["company_size"],
                estimated_value=data["estimated_value"],
                probability=data["probability"],
                source=data["source"],
                signals=data["signals"],
                recommended_approach=data["recommended_approach"],
                competitive_landscape=data["competitive_landscape"],
            )
            self.db.add(opp)
            opportunities.append(opp)

        await self.db.commit()
        for opp in opportunities:
            await self.db.refresh(opp)
        return opportunities

    async def get_opportunities(
        self,
        industry: IndustryVertical | None = None,
        status: str | None = None,
        min_probability: int = 0,
        limit: int = 50,
    ) -> list[MarketOpportunity]:
        query = select(MarketOpportunity)
        conditions = []
        if industry:
            conditions.append(MarketOpportunity.industry == industry)
        if status:
            conditions.append(MarketOpportunity.status == status)
        if min_probability > 0:
            conditions.append(MarketOpportunity.probability >= min_probability)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(desc(MarketOpportunity.probability)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def score_lead_potential(self, lead_id: str) -> SalesPrediction | None:
        lead = await self.db.execute(select(Lead).where(Lead.id == uuid.UUID(lead_id)))
        lead = lead.scalar_one_or_none()
        if not lead:
            return None

        score = lead.score or 50
        industry_boost = 10 if lead.industry in (IndustryVertical.FINANCE, IndustryVertical.HEALTHCARE, IndustryVertical.MANUFACTURING) else 0
        size_boost = min(20, (lead.employee_count or 0) // 100)
        final_probability = min(95, score + industry_boost + size_boost)

        factors = [
            {"name": "lead_score", "value": score, "weight": 0.4},
            {"name": "industry_fit", "value": industry_boost, "weight": 0.3},
            {"name": "company_size", "value": size_boost, "weight": 0.3},
        ]

        estimated_value = 0.0
        if lead.employee_count:
            if lead.employee_count < 50:
                estimated_value = 5000
            elif lead.employee_count < 500:
                estimated_value = 25000
            else:
                estimated_value = 75000

        prediction = SalesPrediction(
            lead_id=lead.id,
            prediction_type="lead_conversion",
            predicted_value=estimated_value,
            confidence=final_probability / 100,
            factors=factors,
            model_version="gtm-v1",
        )
        self.db.add(prediction)
        await self.db.commit()
        await self.db.refresh(prediction)
        return prediction

    async def predict_deal_close(self, deal_id: str) -> SalesPrediction | None:
        deal = await self.db.execute(select(PipelineDeal).where(PipelineDeal.id == uuid.UUID(deal_id)))
        deal = deal.scalar_one_or_none()
        if not deal:
            return None

        probability = min(95, deal.probability + 5)
        factors = [
            {"name": "stage", "value": deal.stage.value, "weight": 0.35},
            {"name": "deal_value", "value": deal.value, "weight": 0.25},
            {"name": "probability", "value": deal.probability, "weight": 0.4},
        ]

        prediction = SalesPrediction(
            deal_id=deal.id,
            org_id=deal.org_id,
            prediction_type="deal_close",
            predicted_value=deal.value * (probability / 100),
            confidence=probability / 100,
            factors=factors,
            model_version="gtm-v1",
        )
        self.db.add(prediction)
        await self.db.commit()
        await self.db.refresh(prediction)
        return prediction

    async def get_growth_recommendations(self) -> list[GrowthRecommendation]:
        pipeline_summary = await self.db.execute(
            select(
                func.count(PipelineDeal.id),
                func.sum(PipelineDeal.value),
                PipelineDeal.stage,
            ).where(PipelineDeal.status == "open").group_by(PipelineDeal.stage)
        )
        stage_data = pipeline_summary.all()

        recommendations = []
        total_open_value = 0.0
        stage_counts = {}
        for count, value, stage in stage_data:
            stage_counts[stage.value] = count
            total_open_value += value or 0

        if stage_counts.get("prospecting", 0) > stage_counts.get("demo", 0) * 2:
            recommendations.append(
                GrowthRecommendation(
                    area="pipeline_velocity",
                    priority="high",
                    title="Accelerate Demo Conversion",
                    description="Many leads stuck in prospecting. Increase demo scheduling and use-case matching.",
                    expected_impact=0.15,
                    actions=["Automate demo scheduling", "Create industry-specific demo scripts", "Increase SDR follow-up cadence"],
                )
            )

        if total_open_value > 1_000_000:
            recommendations.append(
                GrowthRecommendation(
                    area="revenue",
                    priority="high",
                    title="Focus on High-Value Deals",
                    description="Open pipeline exceeds $1M. Prioritize enterprise deals and executive engagement.",
                    expected_impact=0.20,
                    actions=["Assign executive sponsors", "Create executive business reviews", "Accelerate procurement support"],
                )
            )

        recommendations.append(
            GrowthRecommendation(
                area="expansion",
                priority="medium",
                title="Expand into Healthcare and Finance",
                description="These verticals show highest market opportunity scores and shortest sales cycles.",
                expected_impact=0.25,
                actions=["Build vertical case studies", "Partner with industry associations", "Run targeted campaigns"],
            )
        )

        recommendations.append(
            GrowthRecommendation(
                area="retention",
                priority="medium",
                title="Improve Customer Health Monitoring",
                description="Proactive health scoring can reduce churn and drive expansion revenue.",
                expected_impact=0.10,
                actions=["Automate health score calculation", "Trigger retention workflows", "Publish monthly success reports"],
            )
        )

        return recommendations

    async def get_sales_forecast(self, days: int = 90) -> dict[str, Any]:
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(
            select(PipelineDeal).where(
                and_(
                    PipelineDeal.status == "open",
                    PipelineDeal.expected_close_date >= since,
                )
            )
        )
        deals = list(result.scalars().all())

        weighted_total = sum(d.value * (d.probability / 100) for d in deals)
        best_case = sum(d.value * 0.8 for d in deals)
        worst_case = sum(d.value * 0.2 for d in deals)
        expected_count = len(deals) * (sum(d.probability for d in deals) / max(len(deals) * 100, 1))

        by_month = defaultdict(float)
        for d in deals:
            if d.expected_close_date:
                month = d.expected_close_date.strftime("%Y-%m")
                by_month[month] += d.value * (d.probability / 100)

        return {
            "period_days": days,
            "total_deals": len(deals),
            "pipeline_value": sum(d.value for d in deals),
            "weighted_forecast": round(weighted_total, 2),
            "best_case": round(best_case, 2),
            "worst_case": round(worst_case, 2),
            "expected_wins": round(expected_count, 1),
            "by_month": dict(by_month),
        }

    async def get_dashboard(self) -> dict[str, Any]:
        opportunities = await self.get_opportunities(limit=100)
        recommendations = await self.get_growth_recommendations()
        forecast = await self.get_sales_forecast()

        return {
            "market_opportunities": {
                "total": len(opportunities),
                "high_value": sum(1 for o in opportunities if o.estimated_value > 3_000_000),
                "avg_probability": sum(o.probability for o in opportunities) / max(len(opportunities), 1),
                "total_estimated_value": sum(o.estimated_value for o in opportunities),
            },
            "growth_recommendations": [
                {"area": r.area, "priority": r.priority, "title": r.title, "expected_impact": r.expected_impact, "actions": r.actions}
                for r in recommendations
            ],
            "sales_forecast": forecast,
            "generated_at": datetime.now(UTC).isoformat(),
        }


_growth_service: GrowthIntelligenceService | None = None


def get_growth_intelligence_service(db: AsyncSession) -> GrowthIntelligenceService:
    global _growth_service
    if _growth_service is None:
        _growth_service = GrowthIntelligenceService(db)
    return _growth_service
