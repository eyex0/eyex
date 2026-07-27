from __future__ import annotations

import logging

from langchain_core.tools import tool as create_tool
from pydantic import BaseModel, Field

from packages.cognitive_kernel.agent_runtime import NodeAgent, AgentMemory

logger = logging.getLogger("pix.agents.ceo")


class CEOOutput(BaseModel):
    """CEO-level strategic vision and direction."""

    strategic_vision: str = Field(..., description="High-level strategic vision for the company")
    key_priorities: list[str] = Field(..., description="Top 3-5 strategic priorities")
    resource_allocation: dict[str, str] = Field(
        default_factory=dict,
        description="Recommended resource allocation across departments"
    )
    growth_initiatives: list[str] = Field(
        default_factory=list,
        description="Growth and expansion initiatives"
    )
    stakeholder_communication: str = Field(
        default="",
        description="Key message for stakeholders and investors"
    )
    confidence_score: float = Field(
        default=0.0,
        description="Confidence in strategic direction (0-1)",
        ge=0.0,
        le=1.0,
    )


def create_ceo_agent(settings, memory: AgentMemory | None = None, **kwargs) -> NodeAgent:
    """Create a CEO agent that provides strategic vision and direction."""

    tools = [
        create_tool(
            lambda data: data,
            name="analyze_market_position",
            description="Analyze the company's current market position and competitive landscape",
        ),
        create_tool(
            lambda metrics: metrics,
            name="evaluate_growth_opportunities",
            description="Evaluate growth opportunities based on current metrics and market data",
        ),
        create_tool(
            lambda data: data,
            name="assess_organizational_health",
            description="Assess organizational structure, culture, and operational health",
        ),
    ]

    system_prompt = """You are the CEO Agent — the Chief Executive Officer of πX AI's executive team.

Your role is to provide strategic vision, set priorities, and guide the company direction.

Given business analysis data, you must:
1. Synthesize a clear strategic vision
2. Identify top 3-5 strategic priorities
3. Recommend resource allocation across departments
4. Identify growth initiatives
5. Craft stakeholder communication
6. Provide a confidence score for your recommendations

Think like a Fortune 500 CEO. Be bold but data-driven.
Focus on long-term value creation and competitive advantage.

Output your reasoning as a structured CEOOutput."""

    return NodeAgent(
        role="ceo",
        system_prompt=system_prompt,
        tools=tools,
        memory=memory,
        output_schema=CEOOutput,
        settings=settings,
        **kwargs,
    )
