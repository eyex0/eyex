from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool as create_tool
from pydantic import BaseModel, Field

from packages.cognitive_kernel.agent_runtime import NodeAgent, AgentMemory

logger = logging.getLogger("pix.agents.risk")


class RiskOutput(BaseModel):
    """Risk Agent's comprehensive risk assessment."""

    overall_risk_score: float = Field(
        ...,
        description="Overall risk score (0=no risk to 1=critical)",
        ge=0.0,
        le=1.0,
    )
    identified_risks: list[dict[str, Any]] = Field(
        ...,
        description="List of identified risks with type, severity, impact, and mitigation",
    )
    opportunities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Detected opportunities with potential impact and confidence",
    )
    compliance_gaps: list[str] = Field(
        default_factory=list,
        description="Identified compliance and regulatory gaps",
    )
    mitigation_strategies: list[str] = Field(
        default_factory=list,
        description="Recommended mitigation strategies",
    )
    early_warnings: list[str] = Field(
        default_factory=list,
        description="Early warning signals requiring immediate attention",
    )
    scenario_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="Best/worst-case scenario analysis",
    )


def create_risk_agent(settings, memory: AgentMemory | None = None, **kwargs) -> NodeAgent:
    """Create a Risk Agent that identifies, assesses, and mitigates business risks."""

    tools = [
        create_tool(
            lambda data: data,
            name="identify_risks",
            description="Identify business, financial, operational, and market risks",
        ),
        create_tool(
            lambda data: data,
            name="assess_compliance",
            description="Assess compliance with relevant regulations and standards",
        ),
        create_tool(
            lambda data: data,
            name="analyze_scenarios",
            description="Run scenario analysis for best/worst-case outcomes",
        ),
        create_tool(
            lambda data: data,
            name="detect_opportunities",
            description="Detect and evaluate business opportunities from market data",
        ),
    ]

    system_prompt = """You are the Risk Agent — the Chief Risk Officer of πX AI's executive team.

Your role is to identify, assess, and mitigate business risks while also detecting opportunities.

Given business data and all executive analyses, you must:
1. Calculate an overall risk score (0-1)
2. Identify specific risks with type, severity, impact, and mitigation
3. Detect opportunities with potential impact and confidence
4. Identify compliance and regulatory gaps
5. Recommend mitigation strategies
6. Flag early warning signals
7. Run scenario analysis (best/worst case)

Think like a Fortune 500 Chief Risk Officer. Be thorough, conservative in risk assessment,
but also optimistic in opportunity detection. Balance caution with calculated risk-taking.

Output your reasoning as a structured RiskOutput."""

    return NodeAgent(
        role="risk",
        system_prompt=system_prompt,
        tools=tools,
        memory=memory,
        output_schema=RiskOutput,
        settings=settings,
        **kwargs,
    )
