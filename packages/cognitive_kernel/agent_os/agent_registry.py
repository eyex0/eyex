"""
πX Agent Registry — Stores agent types, purposes, tools, knowledge access, and policies.

Agents are NOT generic chatbots — every agent is company-aware, industry-aware,
role-aware, data-aware, goal-driven, and learning-enabled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid


class AgentType(StrEnum):
    SALES = "sales_intelligence"
    INVENTORY = "inventory"
    CUSTOMER = "customer_intelligence"
    PRODUCTION = "production"
    QUALITY = "quality"
    MAINTENANCE = "maintenance"
    FINANCE = "finance"
    MARKETING = "marketing"
    HR = "human_resources"
    OPERATIONS = "operations"
    STRATEGY = "strategy"
    CUSTOM = "custom"


class AgentStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentSpec:
    """Specification for an agent type — what it does and what it can access."""
    type: AgentType
    label: str
    purpose: str
    industry: str  # Which industry this agent is for
    role: str  # Executive role this agent serves
    tools: list[str] = field(default_factory=list)
    knowledge_access: list[str] = field(default_factory=list)  # entity types it can access
    data_access: list[str] = field(default_factory=list)  # data categories it can access
    kpis_monitored: list[str] = field(default_factory=list)
    system_prompt_template: str = ""
    goals: list[str] = field(default_factory=list)
    policies: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInstance:
    """A running agent instance."""
    id: str
    spec: AgentSpec
    org_id: str
    status: AgentStatus = AgentStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_active: str = ""
    conversation_count: int = 0
    decision_count: int = 0
    performance_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    """Registry of agent types and active instances."""

    def __init__(self) -> None:
        self._types: dict[AgentType, AgentSpec] = {}
        self._instances: dict[str, AgentInstance] = {}
        self._register_builtin_types()

    def _register_builtin_types(self) -> None:
        """Register generic agent type templates — customized per industry at creation."""
        self._register(AgentSpec(
            type=AgentType.SALES,
            label="Sales Intelligence Agent",
            purpose="Analyze revenue patterns, detect sales problems, recommend actions to improve sell-out and margin",
            industry="retail",
            role="cfo",
            tools=["query_database", "search_memory", "search_knowledge_graph", "kpi_analyzer", "forecast_tool", "generate_report"],
            knowledge_access=["customer", "product", "store", "revenue"],
            data_access=["sales", "revenue", "margin"],
            kpis_monitored=["revenue", "sell_out", "margin"],
            system_prompt_template=(
                "You are the {label} for {company_name}, a {industry} company. "
                "Your goal: {goals}. "
                "You monitor: {kpis}. "
                "You have access to: {entities}. "
                "Always reference company KPIs and terminology. "
                "Never give generic advice — be specific to {company_name}'s data."
            ),
            goals=["Detect revenue anomalies", "Identify underperforming stores/products", "Recommend sales actions"],
            policies={"data_sensitivity": "standard", "autonomous_actions": ["generate_report", "create_decision"]},
        ))
        self._register(AgentSpec(
            type=AgentType.INVENTORY,
            label="Inventory Agent",
            purpose="Stock analysis, demand prediction, replenishment recommendations",
            industry="retail",
            role="coo",
            tools=["query_database", "search_memory", "forecast_tool", "generate_report", "create_decision"],
            knowledge_access=["product", "store", "supplier"],
            data_access=["inventory", "stock_levels", "demand"],
            kpis_monitored=["inventory_turnover", "stockout_rate"],
            system_prompt_template=(
                "You are the {label} for {company_name}, a {industry} company. "
                "Your goal: {goals}. "
                "You monitor: {kpis}. "
                "Predict demand and flag low-stock items."
            ),
            goals=["Prevent stockouts", "Optimize inventory levels", "Predict demand patterns"],
            policies={"data_sensitivity": "standard", "autonomous_actions": ["generate_report"]},
        ))
        self._register(AgentSpec(
            type=AgentType.CUSTOMER,
            label="Customer Intelligence Agent",
            purpose="Customer behavior analysis, retention prediction, churn prevention",
            industry="retail",
            role="cmo",
            tools=["query_database", "search_memory", "search_knowledge_graph", "kpi_analyzer", "generate_report"],
            knowledge_access=["customer", "product", "store"],
            data_access=["customer_data", "purchase_history", "behavior"],
            kpis_monitored=["customer_lifetime_value", "churn_rate", "retention"],
            system_prompt_template=(
                "You are the {label} for {company_name}. "
                "Analyze customer behavior and predict churn. "
                "Monitor: {kpis}. "
                "Recommend retention actions."
            ),
            goals=["Reduce churn", "Increase customer lifetime value", "Identify at-risk customers"],
            policies={"data_sensitivity": "high", "autonomous_actions": ["generate_report"]},
        ))
        self._register(AgentSpec(
            type=AgentType.PRODUCTION,
            label="Production Agent",
            purpose="Monitor OEE, production volume, cycle time, and detect bottlenecks",
            industry="manufacturing",
            role="coo",
            tools=["query_database", "search_memory", "kpi_analyzer", "forecast_tool", "generate_report", "create_decision"],
            knowledge_access=["equipment", "work_order", "product"],
            data_access=["production", "oee", "cycle_time"],
            kpis_monitored=["oee", "production_volume", "cycle_time"],
            system_prompt_template=(
                "You are the {label} for {company_name}, a {industry} company. "
                "Monitor OEE and production efficiency. "
                "Detect bottlenecks and recommend optimizations. "
                "Track: {kpis}."
            ),
            goals=["Maximize OEE", "Minimize downtime", "Optimize production scheduling"],
            policies={"data_sensitivity": "standard", "autonomous_actions": ["generate_report", "create_decision"]},
        ))
        self._register(AgentSpec(
            type=AgentType.QUALITY,
            label="Quality Agent",
            purpose="Defect analysis, quality rate monitoring, root cause identification",
            industry="manufacturing",
            role="coo",
            tools=["query_database", "search_memory", "kpi_analyzer", "simulation_tool", "generate_report"],
            knowledge_access=["equipment", "product", "work_order"],
            data_access=["quality", "defects", "inspections"],
            kpis_monitored=["quality_rate", "defect_count", "first_pass_yield"],
            system_prompt_template=(
                "You are the {label} for {company_name}. "
                "Analyze defect patterns and identify root causes. "
                "Monitor: {kpis}. "
                "Recommend quality improvements."
            ),
            goals=["Reduce defect rate", "Identify root causes", "Improve first-pass yield"],
            policies={"data_sensitivity": "standard", "autonomous_actions": ["generate_report"]},
        ))
        self._register(AgentSpec(
            type=AgentType.MAINTENANCE,
            label="Maintenance Agent",
            purpose="Predictive maintenance, equipment health monitoring, downtime prevention",
            industry="manufacturing",
            role="coo",
            tools=["query_database", "search_memory", "forecast_tool", "generate_report", "create_decision"],
            knowledge_access=["equipment", "work_order"],
            data_access=["maintenance", "sensor_data", "downtime"],
            kpis_monitored=["mtbf", "mttr", "availability"],
            system_prompt_template=(
                "You are the {label} for {company_name}. "
                "Predict equipment failures and schedule maintenance. "
                "Monitor: {kpis}."
            ),
            goals=["Prevent unplanned downtime", "Optimize maintenance schedule", "Extend equipment life"],
            policies={"data_sensitivity": "standard", "autonomous_actions": ["generate_report", "create_decision"]},
        ))
        self._register(AgentSpec(
            type=AgentType.FINANCE,
            label="Finance Agent",
            purpose="Financial analysis, cost optimization, margin tracking, forecasting",
            industry="generic",
            role="cfo",
            tools=["query_database", "search_memory", "kpi_analyzer", "forecast_tool", "simulation_tool", "generate_report", "create_decision"],
            knowledge_access=["revenue", "cost", "transaction"],
            data_access=["financial", "cost", "revenue", "margin"],
            kpis_monitored=["revenue", "margin", "ebitda", "cash_flow"],
            system_prompt_template=(
                "You are the {label} for {company_name}. "
                "Analyze financial performance and forecast trends. "
                "Monitor: {kpis}. "
                "Recommend cost optimizations and margin improvements."
            ),
            goals=["Optimize margins", "Forecast financial trends", "Identify cost savings"],
            policies={"data_sensitivity": "high", "autonomous_actions": ["generate_report"]},
        ))
        self._register(AgentSpec(
            type=AgentType.MARKETING,
            label="Marketing Agent",
            purpose="Campaign analysis, promotion effectiveness, customer acquisition",
            industry="generic",
            role="cmo",
            tools=["query_database", "search_memory", "search_knowledge_graph", "kpi_analyzer", "generate_report"],
            knowledge_access=["customer", "product", "store"],
            data_access=["marketing", "campaigns", "promotions"],
            kpis_monitored=["roi", "cac", "conversion_rate", "promotion_effectiveness"],
            system_prompt_template=(
                "You are the {label} for {company_name}. "
                "Analyze campaign performance and promotion effectiveness. "
                "Monitor: {kpis}."
            ),
            goals=["Optimize marketing ROI", "Improve conversion rates", "Recommend promotions"],
            policies={"data_sensitivity": "standard", "autonomous_actions": ["generate_report"]},
        ))
        self._register(AgentSpec(
            type=AgentType.HR,
            label="HR Agent",
            purpose="Employee performance, workforce planning, talent analytics",
            industry="generic",
            role="chro",
            tools=["query_database", "search_memory", "kpi_analyzer", "generate_report"],
            knowledge_access=["employee", "department"],
            data_access=["hr", "employee_data", "performance"],
            kpis_monitored=["headcount", "attrition", "productivity"],
            system_prompt_template=(
                "You are the {label} for {company_name}. "
                "Analyze workforce metrics and talent patterns. "
                "Monitor: {kpis}."
            ),
            goals=["Reduce attrition", "Optimize workforce", "Identify talent gaps"],
            policies={"data_sensitivity": "high", "autonomous_actions": ["generate_report"]},
        ))
        self._register(AgentSpec(
            type=AgentType.STRATEGY,
            label="Strategy Agent",
            purpose="Strategic analysis, competitive intelligence, growth recommendations",
            industry="generic",
            role="ceo",
            tools=["query_database", "search_memory", "search_knowledge_graph", "kpi_analyzer", "forecast_tool", "simulation_tool", "generate_report", "create_decision"],
            knowledge_access=["*"],  # Full access
            data_access=["*"],
            kpis_monitored=[],
            system_prompt_template=(
                "You are the {label} for {company_name}. "
                "Provide strategic analysis and growth recommendations. "
                "Synthesize insights across all business areas."
            ),
            goals=["Identify growth opportunities", "Assess competitive landscape", "Recommend strategic priorities"],
            policies={"data_sensitivity": "high", "autonomous_actions": ["generate_report", "create_decision"]},
        ))

    def _register(self, spec: AgentSpec) -> None:
        self._types[spec.type] = spec

    def get_type(self, agent_type: AgentType) -> AgentSpec | None:
        return self._types.get(agent_type)

    def get_types_for_industry(self, industry: str) -> list[AgentSpec]:
        """Get all agent types suitable for an industry."""
        industry_specific = [s for s in self._types.values() if s.industry == industry]
        generic = [s for s in self._types.values() if s.industry == "generic"]
        return industry_specific + generic

    def all_types(self) -> list[AgentSpec]:
        return list(self._types.values())

    def create_instance(self, spec: AgentSpec, org_id: str, **kwargs) -> AgentInstance:
        instance = AgentInstance(
            id=f"agent_{uuid.uuid4().hex[:12]}",
            spec=spec,
            org_id=org_id,
            metadata=kwargs,
        )
        self._instances[instance.id] = instance
        return instance

    def get_instance(self, agent_id: str) -> AgentInstance | None:
        return self._instances.get(agent_id)

    def list_instances(self, org_id: str | None = None) -> list[AgentInstance]:
        if org_id:
            return [a for a in self._instances.values() if a.org_id == org_id]
        return list(self._instances.values())

    def update_status(self, agent_id: str, status: AgentStatus) -> None:
        inst = self._instances.get(agent_id)
        if inst:
            inst.status = status

    def remove_instance(self, agent_id: str) -> None:
        self._instances.pop(agent_id, None)
