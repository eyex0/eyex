from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool as create_tool
from pydantic import BaseModel, Field

from packages.cognitive_kernel.agent_runtime import NodeAgent, AgentMemory

logger = logging.getLogger("pix.agents.cfo")


class CFOOutput(BaseModel):
    """CFO-level financial analysis and guidance."""

    financial_health_assessment: str = Field(..., description="Overall financial health assessment")
    revenue_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="Revenue breakdown, trends, and projections"
    )
    cost_optimization: list[str] = Field(
        default_factory=list,
        description="Cost optimization opportunities"
    )
    cash_flow_insights: str = Field(
        default="",
        description="Cash flow analysis and recommendations"
    )
    investment_priorities: list[str] = Field(
        default_factory=list,
        description="Capital allocation and investment recommendations"
    )
    risk_factors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Financial risk factors with severity ratings"
    )
    key_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Key financial metrics and KPIs"
    )


def create_cfo_agent(settings, memory: AgentMemory | None = None, **kwargs) -> NodeAgent:
    """Create a CFO agent that provides financial analysis and guidance."""

    tools = [
        create_tool(
            lambda data: data,
            name="analyze_revenue_streams",
            description="Analyze revenue streams, growth rates, and profitability",
        ),
        create_tool(
            lambda data: data,
            name="evaluate_cost_structure",
            description="Evaluate cost structure and identify optimization opportunities",
        ),
        create_tool(
            lambda data: data,
            name="project_cash_flow",
            description="Project cash flow based on current financial data and trends",
        ),
        create_tool(
            lambda data: data,
            name="assess_financial_risks",
            description="Assess financial risks including market, credit, and liquidity risks",
        ),
    ]

    system_prompt = """You are the CFO Agent — the Chief Financial Officer of πX AI's executive team.

Your role is to provide financial analysis, guidance, and risk assessment.

Given business data and analysis, you must:
1. Assess overall financial health
2. Analyze revenue streams, trends, and projections
3. Identify cost optimization opportunities
4. Provide cash flow insights
5. Recommend investment priorities
6. Identify and rate financial risk factors
7. Track key financial metrics and KPIs

Think like a Fortune 500 CFO. Be precise, data-driven, and fiscally responsible.
Focus on sustainable growth, profitability, and financial stability.

Output your reasoning as a structured CFOOutput."""

    return NodeAgent(
        role="cfo",
        system_prompt=system_prompt,
        tools=tools,
        memory=memory,
        output_schema=CFOOutput,
        settings=settings,
        **kwargs,
    )
