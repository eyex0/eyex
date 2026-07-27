from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gtm import (

    BillingInterval,
    EnterprisePricing,
    MarketplaceRevenue,
    SubscriptionTier,
    UsageBasedBilling,
)
from app.models.workspace import SubscriptionPlan

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




logger = logging.getLogger("pix.services.gtm.pricing")


@dataclass
class PlanConfig:
    name: str
    tier: SubscriptionTier
    monthly_price: float
    annual_price: float
    max_users: int
    max_agents: int
    max_api_calls: int
    max_storage_gb: int
    features: list[str]
    ai_models: list[str]
    support_level: str


DEFAULT_PLANS: list[PlanConfig] = [
    PlanConfig(
        name="Starter",
        tier=SubscriptionTier.STARTER,
        monthly_price=99.0,
        annual_price=999.0,
        max_users=5,
        max_agents=10,
        max_api_calls=10000,
        max_storage_gb=10,
        features=["Core agents", "Basic analytics", "Email support", "API access"],
        ai_models=["gpt-4o-mini"],
        support_level="email",
    ),
    PlanConfig(
        name="Professional",
        tier=SubscriptionTier.PROFESSIONAL,
        monthly_price=499.0,
        annual_price=4999.0,
        max_users=25,
        max_agents=50,
        max_api_calls=100000,
        max_storage_gb=100,
        features=["All Starter features", "Advanced agents", "Custom workflows", "Priority support", "SSO", "Audit logs"],
        ai_models=["gpt-4o-mini", "gpt-4o"],
        support_level="priority",
    ),
    PlanConfig(
        name="Enterprise",
        tier=SubscriptionTier.ENTERPRISE,
        monthly_price=1999.0,
        annual_price=19999.0,
        max_users=100,
        max_agents=200,
        max_api_calls=1000000,
        max_storage_gb=1000,
        features=[
            "All Professional features",
            "Unlimited custom agents",
            "Dedicated infrastructure",
            "Custom SLA",
            "On-premise option",
            "White-label",
            "Dedicated CSM",
            "Custom integrations",
        ],
        ai_models=["gpt-4o-mini", "gpt-4o", "claude-3-opus", "custom"],
        support_level="dedicated",
    ),
]


USAGE_RATES = {
    "agent_execution": 0.10,
    "token_consumed": 0.00001,
    "api_call": 0.0001,
    "storage_gb": 0.50,
    "compute_hour": 2.00,
}


class PricingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def initialize_plans(self) -> list[SubscriptionPlan]:
        plans = []
        for i, config in enumerate(DEFAULT_PLANS):
            existing = await self.db.execute(select(SubscriptionPlan).where(SubscriptionPlan.tier == _ev(config.tier)))
            if existing.scalar_one_or_none():
                continue

            plan = SubscriptionPlan(
                name=config.name,
                slug=_ev(config.tier),
                tier=_ev(config.tier),
                description=f"{config.name} plan for growing teams",
                price_monthly=config.monthly_price,
                price_yearly=config.annual_price,
                currency="USD",
                max_users=config.max_users,
                max_agents=config.max_agents,
                max_tasks_per_month=1000,
                max_api_calls_per_month=config.max_api_calls,
                max_storage_gb=config.max_storage_gb,
                features=config.features,
                ai_model_access=config.ai_models,
                support_level=config.support_level,
                is_active=True,
                sort_order=i,
            )
            self.db.add(plan)
            plans.append(plan)

        await self.db.commit()
        for p in plans:
            await self.db.refresh(p)
        return plans

    async def get_plans(self, active_only: bool = True) -> list[SubscriptionPlan]:
        query = select(SubscriptionPlan)
        if active_only:
            query = query.where(SubscriptionPlan.is_active)
        query = query.order_by(SubscriptionPlan.sort_order)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_plan(self, plan_id: str) -> SubscriptionPlan | None:
        result = await self.db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == uuid.UUID(plan_id)))
        return result.scalar_one_or_none()

    async def get_plan_by_tier(self, tier: SubscriptionTier) -> SubscriptionPlan | None:
        result = await self.db.execute(select(SubscriptionPlan).where(SubscriptionPlan.tier == tier.value))
        return result.scalar_one_or_none()


class EnterprisePricingService:
    def __init__(self, db: AsyncSession, pricing_service: PricingService) -> None:
        self.db = db
        self.pricing_service = pricing_service

    async def create_enterprise_pricing(
        self,
        org_id: str,
        plan_tier: SubscriptionTier,
        billing_interval: BillingInterval = BillingInterval.ANNUAL,
        custom_monthly_price: float | None = None,
        custom_annual_price: float | None = None,
        contract_months: int = 12,
        max_users: int | None = None,
        max_agents: int | None = None,
        max_api_calls: int | None = None,
        max_storage_gb: int | None = None,
        custom_features: list[str] | None = None,
        discount_percent: float = 0.0,
        negotiated_by: str | None = None,
        notes: str | None = None,
    ) -> EnterprisePricing:
        base_plan = await self.pricing_service.get_plan_by_tier(plan_tier)
        if not base_plan:
            raise ValueError(f"Base plan not found for tier {plan_tier}")

        start = datetime.now(UTC)
        end = start + timedelta(days=contract_months * 30)

        pricing = EnterprisePricing(
            org_id=uuid.UUID(org_id),
            plan_id=base_plan.id,
            custom_monthly_price=custom_monthly_price,
            custom_annual_price=custom_annual_price,
            billing_interval=billing_interval,
            contract_start=start,
            contract_end=end,
            auto_renew=True,
            max_users=max_users or base_plan.max_users,
            max_agents=max_agents or base_plan.max_agents,
            max_api_calls_per_month=max_api_calls or base_plan.max_api_calls_per_month,
            max_storage_gb=max_storage_gb or base_plan.max_storage_gb,
            custom_features=custom_features or [],
            discount_percent=discount_percent,
            negotiated_by=uuid.UUID(negotiated_by) if negotiated_by else None,
            notes=notes,
        )
        self.db.add(pricing)
        await self.db.commit()
        await self.db.refresh(pricing)
        return pricing

    async def get_enterprise_pricing(self, org_id: str) -> EnterprisePricing | None:
        result = await self.db.execute(select(EnterprisePricing).where(EnterprisePricing.org_id == uuid.UUID(org_id)))
        return result.scalar_one_or_none()

    async def calculate_effective_price(self, org_id: str) -> dict[str, Any]:
        pricing = await self.get_enterprise_pricing(org_id)
        if not pricing:
            return {"error": "No enterprise pricing configured"}

        base_plan = await self.pricing_service.get_plan(str(pricing.plan_id)) if pricing.plan_id else None

        if pricing.billing_interval == BillingInterval.MONTHLY:
            base_price = pricing.custom_monthly_price or (base_plan.price_monthly if base_plan else 0)
        elif pricing.billing_interval == BillingInterval.QUARTERLY:
            base_price = (pricing.custom_annual_price or (base_plan.price_yearly if base_plan else 0)) / 4
        else:
            base_price = pricing.custom_annual_price or (base_plan.price_yearly if base_plan else 0)

        discount = base_price * (pricing.discount_percent / 100)
        final_price = base_price - discount

        return {
            "base_price": base_price,
            "discount_percent": pricing.discount_percent,
            "discount_amount": round(discount, 2),
            "final_price": round(final_price, 2),
            "billing_interval": _ev(pricing.billing_interval),
            "currency": "USD",
            "contract_end": pricing.contract_end.isoformat() if pricing.contract_end else None,
        }


class UsageBillingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_usage(
        self,
        org_id: str,
        agent_executions: int = 0,
        tokens_consumed: int = 0,
        api_calls: int = 0,
        storage_gb: float = 0.0,
        compute_hours: float = 0.0,
    ) -> UsageBasedBilling:
        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_start.month == 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1)
        else:
            period_end = period_start.replace(month=period_start.month + 1)

        result = await self.db.execute(
            select(UsageBasedBilling).where(
                and_(
                    UsageBasedBilling.org_id == uuid.UUID(org_id),
                    UsageBasedBilling.billing_period_start == period_start,
                )
            )
        )
        billing = result.scalar_one_or_none()

        if not billing:
            billing = UsageBasedBilling(
                org_id=uuid.UUID(org_id),
                billing_period_start=period_start,
                billing_period_end=period_end,
            )
            self.db.add(billing)

        billing.agent_executions += agent_executions
        billing.tokens_consumed += tokens_consumed
        billing.api_calls += api_calls
        billing.storage_gb_used = max(billing.storage_gb_used, storage_gb)
        billing.compute_hours += compute_hours

        billing.breakdown = {
            "agent_executions": {"count": billing.agent_executions, "rate": USAGE_RATES["agent_execution"], "cost": billing.agent_executions * USAGE_RATES["agent_execution"]},
            "tokens_consumed": {"count": billing.tokens_consumed, "rate": USAGE_RATES["token_consumed"], "cost": billing.tokens_consumed * USAGE_RATES["token_consumed"]},
            "api_calls": {"count": billing.api_calls, "rate": USAGE_RATES["api_call"], "cost": billing.api_calls * USAGE_RATES["api_call"]},
            "storage_gb": {"count": billing.storage_gb_used, "rate": USAGE_RATES["storage_gb"], "cost": billing.storage_gb_used * USAGE_RATES["storage_gb"]},
            "compute_hours": {"count": billing.compute_hours, "rate": USAGE_RATES["compute_hour"], "cost": billing.compute_hours * USAGE_RATES["compute_hour"]},
        }

        billing.total_cost = sum(v["cost"] for v in billing.breakdown.values())
        billing.status = "pending"

        await self.db.commit()
        await self.db.refresh(billing)
        return billing

    async def get_current_billing(self, org_id: str) -> UsageBasedBilling | None:
        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(UsageBasedBilling).where(
                and_(
                    UsageBasedBilling.org_id == uuid.UUID(org_id),
                    UsageBasedBilling.billing_period_start == period_start,
                )
            )
        )
        return result.scalar_one_or_none()

    async def finalize_billing(self, org_id: str, invoice_id: str | None = None) -> UsageBasedBilling | None:
        billing = await self.get_current_billing(org_id)
        if not billing:
            return None
        billing.status = "finalized"
        billing.invoice_id = uuid.UUID(invoice_id) if invoice_id else None
        await self.db.commit()
        await self.db.refresh(billing)
        return billing

    async def get_billing_history(self, org_id: str, limit: int = 12) -> list[UsageBasedBilling]:
        result = await self.db.execute(
            select(UsageBasedBilling)
            .where(UsageBasedBilling.org_id == uuid.UUID(org_id))
            .order_by(desc(UsageBasedBilling.billing_period_start))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def calculate_usage_cost(
        self,
        agent_executions: int = 0,
        tokens_consumed: int = 0,
        api_calls: int = 0,
        storage_gb: float = 0.0,
        compute_hours: float = 0.0,
    ) -> dict[str, Any]:
        breakdown = {
            "agent_executions": {"count": agent_executions, "rate": USAGE_RATES["agent_execution"], "cost": agent_executions * USAGE_RATES["agent_execution"]},
            "tokens_consumed": {"count": tokens_consumed, "rate": USAGE_RATES["token_consumed"], "cost": tokens_consumed * USAGE_RATES["token_consumed"]},
            "api_calls": {"count": api_calls, "rate": USAGE_RATES["api_call"], "cost": api_calls * USAGE_RATES["api_call"]},
            "storage_gb": {"count": storage_gb, "rate": USAGE_RATES["storage_gb"], "cost": storage_gb * USAGE_RATES["storage_gb"]},
            "compute_hours": {"count": compute_hours, "rate": USAGE_RATES["compute_hour"], "cost": compute_hours * USAGE_RATES["compute_hour"]},
        }
        total = sum(v["cost"] for v in breakdown.values())
        return {"breakdown": breakdown, "total_cost": round(total, 4), "currency": "USD"}


class MarketplaceRevenueService:
    PLATFORM_FEE_PERCENT = 20.0

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_transaction(
        self,
        agent_id: str,
        org_id: str,
        transaction_type: str,
        amount: float,
        currency: str = "USD",
        period: str | None = None,
        metadata: dict | None = None,
    ) -> MarketplaceRevenue:
        platform_fee = amount * (self.PLATFORM_FEE_PERCENT / 100)
        developer_payout = amount - platform_fee

        revenue = MarketplaceRevenue(
            agent_id=agent_id,
            org_id=uuid.UUID(org_id),
            transaction_type=transaction_type,
            amount=amount,
            currency=currency,
            platform_fee=platform_fee,
            developer_payout=developer_payout,
            period=period or datetime.now(UTC).strftime("%Y-%m"),
            status="completed",
            meta_data=metadata,
        )
        self.db.add(revenue)
        await self.db.commit()
        await self.db.refresh(revenue)
        return revenue

    async def get_revenue_summary(self, agent_id: str | None = None, org_id: str | None = None, period: str | None = None) -> dict[str, Any]:
        query = select(MarketplaceRevenue)
        conditions = []
        if agent_id:
            conditions.append(MarketplaceRevenue.agent_id == agent_id)
        if org_id:
            conditions.append(MarketplaceRevenue.org_id == uuid.UUID(org_id))
        if period:
            conditions.append(MarketplaceRevenue.period == period)
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        revenues = list(result.scalars().all())

        total_revenue = sum(r.amount for r in revenues)
        total_platform_fee = sum(r.platform_fee for r in revenues)
        total_payout = sum(r.developer_payout for r in revenues)

        by_agent = defaultdict(lambda: {"revenue": 0.0, "transactions": 0})
        by_org = defaultdict(lambda: {"revenue": 0.0, "transactions": 0})
        by_type = defaultdict(float)

        for r in revenues:
            by_agent[r.agent_id]["revenue"] += r.amount
            by_agent[r.agent_id]["transactions"] += 1
            by_org[str(r.org_id)]["revenue"] += r.amount
            by_org[str(r.org_id)]["transactions"] += 1
            by_type[r.transaction_type] += r.amount

        return {
            "total_revenue": total_revenue,
            "platform_fees": total_platform_fee,
            "developer_payouts": total_payout,
            "transaction_count": len(revenues),
            "by_agent": dict(by_agent),
            "by_organization": dict(by_org),
            "by_transaction_type": dict(by_type),
        }


_pricing_service: PricingService | None = None
_enterprise_pricing_service: EnterprisePricingService | None = None
_usage_billing_service: UsageBillingService | None = None
_marketplace_revenue_service: MarketplaceRevenueService | None = None


def get_pricing_service(db: AsyncSession) -> PricingService:
    global _pricing_service
    if _pricing_service is None:
        _pricing_service = PricingService(db)
    return _pricing_service


def get_enterprise_pricing_service(db: AsyncSession) -> EnterprisePricingService:
    global _enterprise_pricing_service
    if _enterprise_pricing_service is None:
        _enterprise_pricing_service = EnterprisePricingService(db, get_pricing_service(db))
    return _enterprise_pricing_service


def get_usage_billing_service(db: AsyncSession) -> UsageBillingService:
    global _usage_billing_service
    if _usage_billing_service is None:
        _usage_billing_service = UsageBillingService(db)
    return _usage_billing_service


def get_marketplace_revenue_service(db: AsyncSession) -> MarketplaceRevenueService:
    global _marketplace_revenue_service
    if _marketplace_revenue_service is None:
        _marketplace_revenue_service = MarketplaceRevenueService(db)
    return _marketplace_revenue_service
