from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gtm import Partner, PartnershipIntegration, PartnershipType

logger = logging.getLogger("pix.services.gtm.partnerships")


@dataclass
class PartnerTemplate:
    name: str
    partner_type: PartnershipType
    description: str
    website: str
    contact_email: str
    integration_opportunities: list[dict[str, Any]]
    revenue_share_percent: float


DEFAULT_PARTNERS: list[PartnerTemplate] = [
    PartnerTemplate(
        name="Amazon Web Services",
        partner_type=PartnershipType.CLOUD_PROVIDER,
        description="Co-sell and deploy EyeX on AWS infrastructure with reserved capacity programs.",
        website="https://aws.amazon.com",
        contact_email="partners@aws.amazon.com",
        integration_opportunities=[
            {"name": "AWS Marketplace Listing", "status": "planning", "category": "listing"},
            {"name": "Amazon Bedrock Model Access", "status": "planning", "category": "ai"},
            {"name": "SageMaker Connector", "status": "planning", "category": "data"},
        ],
        revenue_share_percent=0.0,
    ),
    PartnerTemplate(
        name="Microsoft Azure",
        partner_type=PartnershipType.CLOUD_PROVIDER,
        description="Deploy EyeX on Azure, integrate with Microsoft 365 and Azure OpenAI Service.",
        website="https://azure.microsoft.com",
        contact_email="partners@microsoft.com",
        integration_opportunities=[
            {"name": "Azure Marketplace Listing", "status": "planning", "category": "listing"},
            {"name": "Azure OpenAI Integration", "status": "planning", "category": "ai"},
            {"name": "Entra ID SSO", "status": "planning", "category": "security"},
        ],
        revenue_share_percent=0.0,
    ),
    PartnerTemplate(
        name="Google Cloud",
        partner_type=PartnershipType.CLOUD_PROVIDER,
        description="Run EyeX on GCP with Vertex AI and BigQuery integrations.",
        website="https://cloud.google.com",
        contact_email="partners@google.com",
        integration_opportunities=[
            {"name": "Google Cloud Marketplace", "status": "planning", "category": "listing"},
            {"name": "Vertex AI Connector", "status": "planning", "category": "ai"},
            {"name": "BigQuery Analytics", "status": "planning", "category": "data"},
        ],
        revenue_share_percent=0.0,
    ),
    PartnerTemplate(
        name="Salesforce",
        partner_type=PartnershipType.ENTERPRISE_SOFTWARE,
        description="Two-way sync with Salesforce CRM for customer intelligence and sales workflows.",
        website="https://salesforce.com",
        contact_email="partners@salesforce.com",
        integration_opportunities=[
            {"name": "Salesforce AppExchange", "status": "planning", "category": "listing"},
            {"name": "CRM Data Connector", "status": "planning", "category": "data"},
            {"name": "Einstein AI Co-Sell", "status": "exploring", "category": "ai"},
        ],
        revenue_share_percent=15.0,
    ),
    PartnerTemplate(
        name="SAP",
        partner_type=PartnershipType.ENTERPRISE_SOFTWARE,
        description="Integrate EyeX with SAP ERP and S/4HANA for manufacturing and finance customers.",
        website="https://sap.com",
        contact_email="partners@sap.com",
        integration_opportunities=[
            {"name": "SAP Store Listing", "status": "planning", "category": "listing"},
            {"name": "S/4HANA Connector", "status": "planning", "category": "data"},
            {"name": "SAP BTP Integration", "status": "exploring", "category": "platform"},
        ],
        revenue_share_percent=15.0,
    ),
    PartnerTemplate(
        name="Workday",
        partner_type=PartnershipType.ENTERPRISE_SOFTWARE,
        description="Connect EyeX with Workday for HR analytics and workforce planning.",
        website="https://workday.com",
        contact_email="partners@workday.com",
        integration_opportunities=[
            {"name": "Workday Integration Cloud", "status": "exploring", "category": "data"},
            {"name": "HR Analytics Connector", "status": "planning", "category": "data"},
        ],
        revenue_share_percent=15.0,
    ),
    PartnerTemplate(
        name="McKinsey & Company",
        partner_type=PartnershipType.INDUSTRY_PARTNER,
        description="Joint consulting engagements combining McKinsey expertise with EyeX AI platform.",
        website="https://mckinsey.com",
        contact_email="alliance@mckinsey.com",
        integration_opportunities=[
            {"name": "Joint GTM Playbook", "status": "planning", "category": "gtm"},
            {"name": "Benchmark Data Sharing", "status": "exploring", "category": "data"},
        ],
        revenue_share_percent=20.0,
    ),
    PartnerTemplate(
        name="OpenAI",
        partner_type=PartnershipType.AI_ECOSYSTEM,
        description="Preferred model provider partnership for GPT-4o and future frontier models.",
        website="https://openai.com",
        contact_email="partners@openai.com",
        integration_opportunities=[
            {"name": "Model Fine-Tuning", "status": "active", "category": "ai"},
            {"name": "Reserved Throughput", "status": "planning", "category": "ai"},
        ],
        revenue_share_percent=0.0,
    ),
    PartnerTemplate(
        name="Anthropic",
        partner_type=PartnershipType.AI_ECOSYSTEM,
        description="Integrate Claude models for reasoning-heavy enterprise use cases.",
        website="https://anthropic.com",
        contact_email="partners@anthropic.com",
        integration_opportunities=[
            {"name": "Claude API Integration", "status": "planning", "category": "ai"},
            {"name": "Constitutional AI Alignment", "status": "exploring", "category": "ai"},
        ],
        revenue_share_percent=0.0,
    ),
    PartnerTemplate(
        name="Deloitte",
        partner_type=PartnershipType.SYSTEM_INTEGRATOR,
        description="Deloitte implements EyeX for enterprise clients with change management and support.",
        website="https://deloitte.com",
        contact_email="alliance@deloitte.com",
        integration_opportunities=[
            {"name": "Implementation Methodology", "status": "planning", "category": "services"},
            {"name": "Co-Sell Agreement", "status": "planning", "category": "gtm"},
        ],
        revenue_share_percent=10.0,
    ),
]


class PartnershipService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def initialize_default_partners(self) -> list[Partner]:
        partners = []
        for template in DEFAULT_PARTNERS:
            existing = await self.db.execute(select(Partner).where(Partner.name == template.name))
            if existing.scalar_one_or_none():
                continue

            partner = Partner(
                name=template.name,
                partner_type=template.partner_type,
                description=template.description,
                website=template.website,
                contact_email=template.contact_email,
                status="active",
                tier="strategic" if template.partner_type in (PartnershipType.CLOUD_PROVIDER, PartnershipType.AI_ECOSYSTEM) else "standard",
                integration_status="planning",
                revenue_share_percent=template.revenue_share_percent,
            )
            self.db.add(partner)
            partners.append(partner)

        await self.db.commit()

        for partner, template in zip(partners, DEFAULT_PARTNERS):
            await self.db.refresh(partner)
            for opp in template.integration_opportunities:
                integration = PartnershipIntegration(
                    partner_id=partner.id,
                    integration_name=opp["name"],
                    integration_type=opp.get("category", "other"),
                    status=opp.get("status", "planning"),
                    data_mapping={},
                )
                self.db.add(integration)

        await self.db.commit()

        for p in partners:
            await self.db.refresh(p)
        return partners

    async def create_partner(
        self,
        name: str,
        partner_type: PartnershipType,
        description: str,
        website: str | None = None,
        contact_email: str | None = None,
        contact_name: str | None = None,
        tier: str = "standard",
        revenue_share_percent: float = 0.0,
        metadata: dict | None = None,
    ) -> Partner:
        partner = Partner(
            name=name,
            partner_type=partner_type,
            description=description,
            website=website,
            contact_email=contact_email,
            contact_name=contact_name,
            tier=tier,
            revenue_share_percent=revenue_share_percent,
            meta_data=metadata,
        )
        self.db.add(partner)
        await self.db.commit()
        await self.db.refresh(partner)
        return partner

    async def get_partner(self, partner_id: str) -> Partner | None:
        result = await self.db.execute(select(Partner).where(Partner.id == uuid.UUID(partner_id)))
        return result.scalar_one_or_none()

    async def list_partners(
        self,
        partner_type: PartnershipType | None = None,
        status: str | None = None,
        tier: str | None = None,
    ) -> list[Partner]:
        query = select(Partner)
        conditions = []
        if partner_type:
            conditions.append(Partner.partner_type == partner_type)
        if status:
            conditions.append(Partner.status == status)
        if tier:
            conditions.append(Partner.tier == tier)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(Partner.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_integration(
        self,
        partner_id: str,
        integration_name: str,
        integration_type: str,
        api_endpoint: str | None = None,
        auth_method: str | None = None,
        sync_frequency: str | None = None,
        data_mapping: dict | None = None,
        metadata: dict | None = None,
    ) -> PartnershipIntegration:
        partner = await self.get_partner(partner_id)
        if not partner:
            raise ValueError(f"Partner not found: {partner_id}")

        integration = PartnershipIntegration(
            partner_id=uuid.UUID(partner_id),
            integration_name=integration_name,
            integration_type=integration_type,
            api_endpoint=api_endpoint,
            auth_method=auth_method,
            sync_frequency=sync_frequency,
            data_mapping=data_mapping,
            meta_data=metadata,
        )
        self.db.add(integration)
        await self.db.commit()
        await self.db.refresh(integration)

        partner.integration_status = "in_progress"
        await self.db.commit()
        return integration

    async def update_integration_status(
        self, integration_id: str, status: str, last_sync: datetime | None = None, error_log: str | None = None
    ) -> PartnershipIntegration | None:
        result = await self.db.execute(
            select(PartnershipIntegration).where(PartnershipIntegration.id == uuid.UUID(integration_id))
        )
        integration = result.scalar_one_or_none()
        if not integration:
            return None
        integration.status = status
        integration.sync_status = status
        if last_sync:
            integration.last_sync = last_sync
        if error_log:
            integration.error_log = error_log
        await self.db.commit()
        await self.db.refresh(integration)
        return integration

    async def get_partner_integrations(self, partner_id: str) -> list[PartnershipIntegration]:
        result = await self.db.execute(
            select(PartnershipIntegration).where(PartnershipIntegration.partner_id == uuid.UUID(partner_id))
        )
        return list(result.scalars().all())

    async def get_partnership_summary(self) -> dict[str, Any]:
        result = await self.db.execute(select(Partner))
        partners = list(result.scalars().all())

        by_type = defaultdict(lambda: {"count": 0, "pipeline_value": 0.0, "joint_customers": 0})
        for p in partners:
            by_type[p.partner_type.value]["count"] += 1
            by_type[p.partner_type.value]["pipeline_value"] += p.pipeline_value
            by_type[p.partner_type.value]["joint_customers"] += p.joint_customers

        integration_result = await self.db.execute(select(PartnershipIntegration))
        integrations = list(integration_result.scalars().all())

        by_status = defaultdict(int)
        for i in integrations:
            by_status[i.status] += 1

        return {
            "total_partners": len(partners),
            "total_integrations": len(integrations),
            "by_type": dict(by_type),
            "integration_status": dict(by_status),
            "total_pipeline_value": sum(p.pipeline_value for p in partners),
            "total_joint_customers": sum(p.joint_customers for p in partners),
        }

    async def update_partner_metrics(
        self, partner_id: str, pipeline_value: float | None = None, joint_customers: int | None = None
    ) -> Partner | None:
        partner = await self.get_partner(partner_id)
        if not partner:
            return None
        if pipeline_value is not None:
            partner.pipeline_value = pipeline_value
        if joint_customers is not None:
            partner.joint_customers = joint_customers
        await self.db.commit()
        await self.db.refresh(partner)
        return partner


_partnership_service: PartnershipService | None = None


def get_partnership_service(db: AsyncSession) -> PartnershipService:
    global _partnership_service
    if _partnership_service is None:
        _partnership_service = PartnershipService(db)
    return _partnership_service
