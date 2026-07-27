"""
πX Tool Registry — Tools available to agents.

Data Tools: query_database, search_memory, search_knowledge_graph
Analysis Tools: kpi_analyzer, forecast_tool, simulation_tool
Business Tools: generate_report, send_notification, create_decision
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable


class ToolCategory(StrEnum):
    DATA = "data"
    ANALYSIS = "analysis"
    BUSINESS = "business"


@dataclass
class ToolSpec:
    name: str
    category: ToolCategory
    label: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    handler: Callable | None = None
    requires_permission: bool = False
    data_sensitivity: str = "standard"  # standard, high, critical

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category.value,
            "label": self.label,
            "description": self.description,
            "parameters": self.parameters,
            "requires_permission": self.requires_permission,
            "data_sensitivity": self.data_sensitivity,
        }


class ToolRegistry:
    """Registry of all tools available to agents."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._register_all()

    def _register_all(self) -> None:
        # ── Data Tools ──
        self._register(ToolSpec(
            name="query_database",
            category=ToolCategory.DATA,
            label="Query Database",
            description="Execute a read-only SQL query against the company's data",
            parameters={"query": {"type": "string", "required": True}, "limit": {"type": "integer", "default": 100}},
            data_sensitivity="standard",
        ))
        self._register(ToolSpec(
            name="search_memory",
            category=ToolCategory.DATA,
            label="Search Memory",
            description="Search the agent's memory and the company's shared memory store",
            parameters={"query": {"type": "string", "required": True}, "memory_type": {"type": "string", "enum": ["short_term", "long_term", "experience"], "required": False}},
            data_sensitivity="standard",
        ))
        self._register(ToolSpec(
            name="search_knowledge_graph",
            category=ToolCategory.DATA,
            label="Search Knowledge Graph",
            description="Query the company's knowledge graph for entities and relationships",
            parameters={"query": {"type": "string", "required": True}, "entity_type": {"type": "string", "required": False}, "depth": {"type": "integer", "default": 2}},
            data_sensitivity="standard",
        ))

        # ── Analysis Tools ──
        self._register(ToolSpec(
            name="kpi_analyzer",
            category=ToolCategory.ANALYSIS,
            label="KPI Analyzer",
            description="Analyze a specific KPI — current value, trend, variance from target",
            parameters={"kpi": {"type": "string", "required": True}, "period": {"type": "string", "default": "last_30_days"}},
            data_sensitivity="standard",
        ))
        self._register(ToolSpec(
            name="forecast_tool",
            category=ToolCategory.ANALYSIS,
            label="Forecast Tool",
            description="Generate a forecast for a metric using historical data",
            parameters={"metric": {"type": "string", "required": True}, "horizon": {"type": "string", "default": "3_months"}, "method": {"type": "string", "enum": ["arima", "exponential", "linear"], "default": "exponential"}},
            data_sensitivity="standard",
        ))
        self._register(ToolSpec(
            name="simulation_tool",
            category=ToolCategory.ANALYSIS,
            label="Simulation Tool",
            description="Run Monte Carlo simulation on a business scenario",
            parameters={"scenario": {"type": "string", "required": True}, "iterations": {"type": "integer", "default": 10000}, "variables": {"type": "array", "required": True}},
            data_sensitivity="standard",
        ))

        # ── Business Tools ──
        self._register(ToolSpec(
            name="generate_report",
            category=ToolCategory.BUSINESS,
            label="Generate Report",
            description="Generate a formatted report from analysis results",
            parameters={"title": {"type": "string", "required": True}, "content": {"type": "string", "required": True}, "format": {"type": "string", "enum": ["pdf", "html", "json"], "default": "html"}},
            data_sensitivity="standard",
        ))
        self._register(ToolSpec(
            name="send_notification",
            category=ToolCategory.BUSINESS,
            label="Send Notification",
            description="Send a notification to users or channels",
            parameters={"recipients": {"type": "array", "required": True}, "message": {"type": "string", "required": True}, "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"], "default": "normal"}},
            requires_permission=True,
            data_sensitivity="standard",
        ))
        self._register(ToolSpec(
            name="create_decision",
            category=ToolCategory.BUSINESS,
            label="Create Decision",
            description="Create a decision record in the Decision Engine",
            parameters={"title": {"type": "string", "required": True}, "reasoning": {"type": "string", "required": True}, "recommendation": {"type": "string", "required": True}, "confidence": {"type": "number", "default": 0.7}},
            requires_permission=True,
            data_sensitivity="standard",
        ))

    def _register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def get_by_category(self, category: ToolCategory) -> list[ToolSpec]:
        return [t for t in self._tools.values() if t.category == category]

    def all_tools(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def get_tools_for_agent(self, tool_names: list[str]) -> list[ToolSpec]:
        return [self._tools[name] for name in tool_names if name in self._tools]
