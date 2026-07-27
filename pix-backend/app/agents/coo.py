from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool as create_tool
from pydantic import BaseModel, Field

from packages.cognitive-kernel.agent-runtime import NodeAgent, AgentMemory

logger = logging.getLogger("pix.agents.coo")


class COOOutput(BaseModel):
    """COO-level operational analysis and recommendations."""

    operational_efficiency: str = Field(..., description="Overall operational efficiency assessment")
    process_improvements: list[str] = Field(
        default_factory=list,
        description="Process improvement recommendations"
    )
    resource_optimization: list[str] = Field(
        default_factory=list,
        description="Resource optimization opportunities"
    )
    scalability_assessment: str = Field(
        default="",
        description="Assessment of operational scalability"
    )
    technology_recommendations: list[str] = Field(
        default_factory=list,
        description="Technology and infrastructure recommendations"
    )
    team_and_talent: dict[str, Any] = Field(
        default_factory=dict,
        description="Team structure, talent gaps, and recommendations"
    )
    operational_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Key operational metrics and KPIs"
    )


def create_coo_agent(settings, memory: AgentMemory | None = None, **kwargs) -> NodeAgent:
    """Create a COO agent that provides operational analysis and recommendations."""

    tools = [
        create_tool(
            lambda data: data,
            name="analyze_operations",
            description="Analyze operational processes and workflows",
        ),
        create_tool(
            lambda data: data,
            name="evaluate_scalability",
            description="Evaluate operational scalability and bottlenecks",
        ),
        create_tool(
            lambda data: data,
            name="assess_team_structure",
            description="Assess team structure, roles, and talent needs",
        ),
        create_tool(
            lambda data: data,
            name="review_technology_stack",
            description="Review current technology stack and infrastructure",
        ),
    ]

    system_prompt = """You are the COO Agent — the Chief Operating Officer of πX AI's executive team.

Your role is to optimize operations, scale processes, and drive operational excellence.

Given business data and analysis, you must:
1. Assess overall operational efficiency
2. Recommend process improvements
3. Identify resource optimization opportunities
4. Evaluate scalability
5. Recommend technology and infrastructure improvements
6. Assess team structure and talent needs
7. Track operational metrics and KPIs

Think like a Fortune 500 COO. Be practical, execution-focused, and efficiency-driven.
Focus on operational excellence, scalability, and process optimization.

Output your reasoning as a structured COOOutput."""

    return NodeAgent(
        role="coo",
        system_prompt=system_prompt,
        tools=tools,
        memory=memory,
        output_schema=COOOutput,
        settings=settings,
        **kwargs,
    )
