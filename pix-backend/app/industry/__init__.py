from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("pix.industry")


@dataclass
class IndustryConfig:
    name: str
    kpi_categories: list[str] = field(default_factory=list)
    risk_templates: list[dict[str, str]] = field(default_factory=list)
    compliance_requirements: list[str] = field(default_factory=list)
    agent_overrides: dict[str, str] = field(default_factory=dict)
    metric_definitions: dict[str, str] = field(default_factory=dict)


MANUFACTURING = IndustryConfig(
    name="manufacturing",
    kpi_categories=["Production Efficiency", "Quality Control", "Supply Chain", "Inventory", "Equipment"],
    risk_templates=[
        {"risk": "Supply chain disruption", "severity": "high", "mitigation": "Diversify suppliers"},
        {"risk": "Equipment downtime", "severity": "high", "mitigation": "Predictive maintenance program"},
        {"risk": "Quality defects", "severity": "medium", "mitigation": "Statistical process control"},
        {"risk": "Inventory obsolescence", "severity": "medium", "mitigation": "Just-in-time inventory"},
        {"risk": "Regulatory non-compliance", "severity": "high", "mitigation": "Compliance management system"},
    ],
    compliance_requirements=["ISO 9001", "ISO 14001", "OSHA", "REACH"],
    metric_definitions={
        "oee": "Overall Equipment Effectiveness (%)",
        "cycle_time": "Average production cycle time (hours)",
        "defect_rate": "Defects per million units",
        "inventory_turnover": "Inventory turnover ratio",
        "on_time_delivery": "On-time delivery rate (%)",
        "capacity_utilization": "Capacity utilization rate (%)",
        "scrap_rate": "Scrap material rate (%)",
        "downtime_percentage": "Equipment downtime percentage",
    },
)

HEALTHCARE = IndustryConfig(
    name="healthcare",
    kpi_categories=["Patient Outcomes", "Operational Efficiency", "Financial Health", "Compliance", "Staffing"],
    risk_templates=[
        {"risk": "Patient data breach", "severity": "critical", "mitigation": "HIPAA compliance + encryption"},
        {"risk": "Regulatory penalties", "severity": "high", "mitigation": "Continuous compliance monitoring"},
        {"risk": "Staff shortage", "severity": "high", "mitigation": "Talent pipeline + retention programs"},
        {"risk": "Medical malpractice liability", "severity": "high", "mitigation": "Quality assurance + insurance"},
        {"risk": "Reimbursement changes", "severity": "medium", "mitigation": "Revenue diversification"},
    ],
    compliance_requirements=["HIPAA", "GDPR", "ISO 27001", "JCI Accreditation"],
    metric_definitions={
        "patient_satisfaction": "Patient satisfaction score (0-100)",
        "readmission_rate": "30-day readmission rate (%)",
        "bed_occupancy": "Bed occupancy rate (%)",
        "avg_length_of_stay": "Average length of stay (days)",
        "revenue_per_patient": "Revenue per patient ($)",
        "staff_to_patient_ratio": "Staff to patient ratio",
        "claim_denial_rate": "Insurance claim denial rate (%)",
        "telemedicine_utilization": "Telemedicine utilization rate (%)",
    },
)

LOGISTICS = IndustryConfig(
    name="logistics",
    kpi_categories=["Delivery Performance", "Fleet Management", "Warehouse Operations", "Cost Efficiency", "Customer Satisfaction"],
    risk_templates=[
        {"risk": "Fuel price volatility", "severity": "high", "mitigation": "Fuel hedging + route optimization"},
        {"risk": "Driver shortage", "severity": "high", "mitigation": "Compensation + training programs"},
        {"risk": "Warehouse capacity constraints", "severity": "medium", "mitigation": "Automation + expansion"},
        {"risk": "Customer delivery failures", "severity": "high", "mitigation": "Real-time tracking + backup plans"},
        {"risk": "Fleet maintenance costs", "severity": "medium", "mitigation": "Predictive maintenance"},
    ],
    compliance_requirements=["FMCSA", "DOT", "Customs Compliance", "Safety Regulations"],
    metric_definitions={
        "on_time_delivery": "On-time delivery rate (%)",
        "cost_per_mile": "Cost per mile ($)",
        "fleet_utilization": "Fleet utilization rate (%)",
        "warehouse_throughput": "Warehouse throughput (units/hour)",
        "damage_rate": "Cargo damage rate (%)",
        "fuel_efficiency": "Fuel efficiency (MPG)",
        "avg_delivery_time": "Average delivery time (hours)",
        "customer_retention": "Customer retention rate (%)",
    },
)

FINANCE = IndustryConfig(
    name="finance",
    kpi_categories=["Revenue & Growth", "Risk Management", "Operational Efficiency", "Customer Metrics", "Capital"],
    risk_templates=[
        {"risk": "Credit default risk", "severity": "high", "mitigation": "Enhanced underwriting + diversification"},
        {"risk": "Market volatility", "severity": "high", "mitigation": "Hedging + risk limits"},
        {"risk": "Regulatory fines", "severity": "critical", "mitigation": "Compliance automation + audit"},
        {"risk": "Cybersecurity threats", "severity": "critical", "mitigation": "SOC 2 + penetration testing"},
        {"risk": "Liquidity shortage", "severity": "high", "mitigation": "Stress testing + credit lines"},
    ],
    compliance_requirements=["SOX", "Basel III", "MiFID II", "KYC/AML", "GDPR"],
    metric_definitions={
        "net_interest_margin": "Net interest margin (%)",
        "cost_to_income": "Cost-to-income ratio (%)",
        "roa": "Return on assets (%)",
        "roe": "Return on equity (%)",
        "capital_adequacy": "Capital adequacy ratio (%)",
        "npl_ratio": "Non-performing loan ratio (%)",
        "customer_acquisition_cost": "Customer acquisition cost ($)",
        "aum": "Assets under management ($)",
    },
)

RETAIL = IndustryConfig(
    name="retail",
    kpi_categories=["Sales Performance", "Customer Experience", "Inventory Management", "Store Operations", "E-commerce"],
    risk_templates=[
        {"risk": "Inventory shrinkage", "severity": "high", "mitigation": "Loss prevention + RFID tracking"},
        {"risk": "Seasonal demand fluctuation", "severity": "medium", "mitigation": "Demand forecasting + flexible staffing"},
        {"risk": "E-commerce competition", "severity": "high", "mitigation": "Omnichannel strategy + loyalty program"},
        {"risk": "Supply chain delays", "severity": "medium", "mitigation": "Multi-supplier strategy + safety stock"},
        {"risk": "Payment fraud", "severity": "high", "mitigation": "Fraud detection AI + 3D Secure"},
    ],
    compliance_requirements=["PCI DSS", "GDPR", "Consumer Protection Laws"],
    metric_definitions={
        "same_store_sales": "Same-store sales growth (%)",
        "average_transaction_value": "Average transaction value ($)",
        "customer_lifetime_value": "Customer lifetime value ($)",
        "conversion_rate": "Online conversion rate (%)",
        "inventory_turnover": "Inventory turnover ratio",
        "return_rate": "Product return rate (%)",
        "foot_traffic": "Store foot traffic (visitors/day)",
        "basket_size": "Average basket size (items)",
    },
)

INDUSTRY_CONFIGS: dict[str, IndustryConfig] = {
    "manufacturing": MANUFACTURING,
    "healthcare": HEALTHCARE,
    "logistics": LOGISTICS,
    "finance": FINANCE,
    "retail": RETAIL,
}

INDUSTRY_EXECUTIVE_PROMPTS: dict[str, dict[str, str]] = {
    "manufacturing": {
        "ceo": "Focus on production efficiency, supply chain resilience, and market expansion for manufacturing companies.",
        "cfo": "Analyze manufacturing cost structure, CAPEX requirements, inventory carrying costs, and working capital.",
        "coo": "Optimize production lines, reduce downtime, improve quality control, and streamline supply chain.",
        "risk": "Assess supply chain disruption risk, equipment failure, quality defects, and regulatory compliance.",
    },
    "healthcare": {
        "ceo": "Focus on patient outcomes, regulatory compliance, and strategic growth in healthcare delivery.",
        "cfo": "Analyze revenue cycle management, reimbursement rates, cost per procedure, and payer mix.",
        "coo": "Optimize patient flow, staff scheduling, resource utilization, and telemedicine operations.",
        "risk": "Assess patient data security, regulatory penalties, malpractice liability, and staffing shortages.",
    },
    "logistics": {
        "ceo": "Focus on network expansion, fleet optimization, and customer experience in logistics.",
        "cfo": "Analyze cost per mile, fleet financing, fuel hedging, and warehouse capital efficiency.",
        "coo": "Optimize route planning, warehouse operations, driver scheduling, and last-mile delivery.",
        "risk": "Assess fuel price volatility, driver shortage, delivery failures, and fleet maintenance costs.",
    },
    "finance": {
        "ceo": "Focus on asset growth, risk-adjusted returns, digital transformation, and regulatory compliance.",
        "cfo": "Analyze capital adequacy, liquidity ratios, cost of funds, and return on equity.",
        "coo": "Optimize branch operations, digital banking, customer onboarding, and back-office efficiency.",
        "risk": "Assess credit risk, market risk, operational risk, cybersecurity threats, and regulatory compliance.",
    },
    "retail": {
        "ceo": "Focus on omnichannel growth, brand strength, customer loyalty, and market share expansion.",
        "cfo": "Analyze same-store sales, gross margin, inventory turnover, and store-level profitability.",
        "coo": "Optimize store operations, supply chain, inventory management, and omnichannel fulfillment.",
        "risk": "Assess inventory shrinkage, seasonal demand fluctuations, e-commerce competition, and payment fraud.",
    },
}


class IndustrySolutionManager:
    """Manages industry-specific configurations, templates, and agent overrides."""

    def __init__(self) -> None:
        self._configs = INDUSTRY_CONFIGS

    def list_industries(self) -> list[str]:
        return list(self._configs.keys())

    def get_config(self, industry: str) -> IndustryConfig | None:
        return self._configs.get(industry)

    def get_kpi_categories(self, industry: str) -> list[str]:
        config = self.get_config(industry)
        return config.kpi_categories if config else []

    def get_risk_templates(self, industry: str) -> list[dict[str, str]]:
        config = self.get_config(industry)
        return config.risk_templates if config else []

    def get_metrics(self, industry: str) -> dict[str, str]:
        config = self.get_config(industry)
        return config.metric_definitions if config else {}

    def get_compliance(self, industry: str) -> list[str]:
        config = self.get_config(industry)
        return config.compliance_requirements if config else []

    def get_executive_prompt(self, industry: str, agent: str) -> str | None:
        prompts = INDUSTRY_EXECUTIVE_PROMPTS.get(industry)
        return prompts.get(agent) if prompts else None

    def get_industry_summary(self, industry: str) -> dict[str, Any]:
        config = self.get_config(industry)
        if not config:
            return {}
        return {
            "industry": industry,
            "kpi_categories": config.kpi_categories,
            "risk_templates": config.risk_templates,
            "compliance_requirements": config.compliance_requirements,
            "metric_count": len(config.metric_definitions),
            "metrics": config.metric_definitions,
        }


_manager: IndustrySolutionManager | None = None


def get_industry_manager() -> IndustrySolutionManager:
    global _manager
    if _manager is None:
        _manager = IndustrySolutionManager()
    return _manager
